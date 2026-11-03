"""ChronoNote MCP Server
Provides Model Context Protocol (MCP) tools for AI assistants (like Claude)
to inspect, create, and manage projects, tasks, and notes in ChronoNote.

Authentication:
All workspace operations require authentication. Users authenticate via:
1. `login(email, password)`
2. `connect_with_code(code)` (using a 6-digit code from ChronoNote web app)
3. `connect_with_token(token)`
Once authenticated, Claude is locked strictly to that user's private workspace.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any

from mcp.server.mcpserver import MCPServer
from sqlalchemy import func

from backend.database import SessionLocal
from backend.models import Note, NoteLink, Project, Task, User
from backend.services.auth_service import (
    create_session_token,
    verify_password,
    verify_session_token,
)
from backend.services.markdown_parser import parse_markdown_note, slugify
from backend.services.mcp_auth import (
    clear_local_session,
    resolve_authenticated_user,
    save_local_session,
    set_active_user_id,
    verify_and_consume_code,
)
from backend.services.ws_manager import ws_manager

server = MCPServer("ChronoNote")

AUTH_REQUIRED_MESSAGE = (
    "Authentication required. You must log in to your ChronoNote account before accessing or creating projects.\n\n"
    "How to log in:\n"
    "1. If your account has a password: Call the 'login' tool with your email and password.\n"
    "2. If you use Google Sign-In: Log in to ChronoNote (https://chrononote-personal.onrender.com/api/auth/mcp-code) "
    "to get your 6-digit connection code, then call 'connect_with_code(code)'.\n"
    "3. If you have a session token: Call 'connect_with_token(token)'."
)


def _unique_project_slug(db, base_slug: str, exclude_id: int | None = None) -> str:
    candidate = base_slug or "project"
    counter = 2
    while True:
        q = db.query(Project).filter(Project.slug == candidate)
        if exclude_id is not None:
            q = q.filter(Project.id != exclude_id)
        if not q.first():
            return candidate
        candidate = f"{base_slug}-{counter}"
        counter += 1


def _parse_date(d: str | None) -> date | None:
    if not d:
        return None
    if isinstance(d, date):
        return d
    try:
        return date.fromisoformat(str(d).strip())
    except (ValueError, TypeError):
        return None


def _sync_note(db, note: Note) -> list[int]:
    """Parse Markdown note, update frontmatter/tags/wikilinks, and sync inline tasks."""
    parsed = parse_markdown_note(note.content_md)
    note.frontmatter_json = json.dumps(parsed.frontmatter)
    note.tags_json = json.dumps(parsed.tags)
    db.flush()

    db.query(NoteLink).filter(
        NoteLink.target_slug == note.slug,
        NoteLink.target_note_id.is_(None),
    ).update({"target_note_id": note.id}, synchronize_session=False)

    db.query(NoteLink).filter(NoteLink.source_note_id == note.id).delete(
        synchronize_session=False
    )
    for wl in parsed.wikilinks:
        target_note = db.query(Note).filter(Note.slug == wl.target_slug).first()
        link = NoteLink(
            source_note_id=note.id,
            target_note_id=target_note.id if target_note else None,
            target_slug=wl.target_slug,
            display_text=wl.display_text,
            context_snippet=wl.context_snippet,
        )
        db.add(link)

    # Sync inline tasks if project_id is present
    synced_ids: list[int] = []
    if note.project_id:
        existing_tasks = (
            db.query(Task)
            .filter(Task.source_note_id == note.id, Task.project_id == note.project_id)
            .all()
        )
        existing_by_title = {t.title.strip().lower(): t for t in existing_tasks}
        current_titles: set[str] = set()

        for it in parsed.inline_tasks:
            t_title = it.title.strip()
            if not t_title:
                continue
            norm_title = t_title.lower()
            current_titles.add(norm_title)
            status_val = "done" if it.completed else (it.status or "todo")
            progress_val = 100 if it.completed else (it.progress or 0)

            if norm_title in existing_by_title:
                t = existing_by_title[norm_title]
                t.status = status_val
                t.progress = progress_val
                if it.priority:
                    t.priority = it.priority
                if it.start_date:
                    t.start_date = it.start_date
                if it.due_date:
                    t.due_date = it.due_date
                if it.is_milestone:
                    t.is_milestone = True
                synced_ids.append(t.id)
            else:
                new_task = Task(
                    project_id=note.project_id,
                    source_note_id=note.id,
                    title=t_title,
                    status=status_val,
                    priority=it.priority or "medium",
                    color="#0891b2",
                    start_date=it.start_date,
                    due_date=it.due_date,
                    is_milestone=it.is_milestone,
                    progress=progress_val,
                )
                db.add(new_task)
                db.flush()
                synced_ids.append(new_task.id)

    return synced_ids


def _format_project(proj: Project, include_tasks: bool = False, include_notes: bool = False) -> dict[str, Any]:
    tasks = proj.tasks or []
    notes = proj.notes or []
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "done" or t.progress == 100)
    today = date.today()
    overdue_tasks = sum(
        1 for t in tasks if t.due_date is not None and t.due_date < today and t.status != "done"
    )
    progress_pct = round((completed_tasks / total_tasks) * 100.0, 1) if total_tasks > 0 else 0.0

    data: dict[str, Any] = {
        "id": proj.id,
        "name": proj.name,
        "slug": proj.slug,
        "description": proj.description or "",
        "color": proj.color or "#6366f1",
        "icon": proj.icon or "folder",
        "status": proj.status or "active",
        "is_pinned": bool(proj.is_pinned),
        "sidebar_order": proj.sidebar_order or 0,
        "start_date": proj.start_date.isoformat() if proj.start_date else None,
        "target_date": proj.target_date.isoformat() if proj.target_date else None,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "overdue_tasks": overdue_tasks,
        "progress_pct": progress_pct,
        "note_count": len(notes),
        "user_id": proj.user_id,
        "created_at": proj.created_at.isoformat() if proj.created_at else None,
    }

    if include_tasks:
        data["tasks"] = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description or "",
                "status": t.status,
                "priority": t.priority,
                "color": t.color,
                "start_date": t.start_date.isoformat() if t.start_date else None,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "is_milestone": bool(t.is_milestone),
                "depends_on_id": t.depends_on_id,
                "progress": t.progress or 0,
            }
            for t in sorted(tasks, key=lambda x: (x.start_date or date.max, x.id))
        ]

    if include_notes:
        data["notes"] = []
        for n in notes:
            tags: list[str] = []
            try:
                tags = json.loads(n.tags_json or "[]")
            except Exception:
                pass
            data["notes"].append({
                "id": n.id,
                "title": n.title,
                "slug": n.slug,
                "tags": tags,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            })

    return data


# ---------------------------------------------------------------------------
# Authentication & Connection Tools
# ---------------------------------------------------------------------------


@server.tool()
def login(email: str, password: str) -> dict[str, Any]:
    """Log in to your ChronoNote account using your email and password.

    Args:
        email: Your ChronoNote registered email address.
        password: Your ChronoNote account password.
    """
    db = SessionLocal()
    try:
        clean_email = email.strip().lower()
        user = db.query(User).filter(func.lower(User.email) == clean_email).first()
        if not user:
            return {
                "success": False,
                "authenticated": False,
                "error": f"No ChronoNote account found with email '{email}'.",
            }

        if not user.password_hash or not user.salt:
            return {
                "success": False,
                "authenticated": False,
                "error": (
                    f"The account '{email}' was created via Google Sign-In and does not have a direct password set.\n"
                    "To connect with Claude, please visit https://chrononote-personal.onrender.com/api/auth/mcp-code "
                    "in your browser to get a 6-digit connection code, then call 'connect_with_code(code)'."
                ),
            }

        if not verify_password(password, user.password_hash, user.salt):
            return {
                "success": False,
                "authenticated": False,
                "error": "Incorrect password. Please verify your credentials.",
            }

        token, _ = create_session_token(user.id, user.email, user.name)
        set_active_user_id(user.id)
        save_local_session(token, user.id, user.email)

        return {
            "success": True,
            "authenticated": True,
            "message": f"Successfully authenticated as {user.name} ({user.email}). All ChronoNote tools are now unlocked for your account.",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
            },
        }
    finally:
        db.close()


@server.tool()
def connect_with_code(code: str) -> dict[str, Any]:
    """Connect Claude to your ChronoNote account using a 6-digit connection code.
    You can generate this code by visiting /api/auth/mcp-code while logged into ChronoNote in your browser.

    Args:
        code: 6-digit temporary connection code.
    """
    db = SessionLocal()
    try:
        entry = verify_and_consume_code(code)
        if not entry:
            return {
                "success": False,
                "authenticated": False,
                "error": (
                    "Invalid or expired 6-digit connection code.\n"
                    "Please visit https://chrononote-personal.onrender.com/api/auth/mcp-code "
                    "in your browser while logged in to generate a fresh code."
                ),
            }

        uid = entry["user_id"]
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            return {
                "success": False,
                "authenticated": False,
                "error": "User account matching connection code no longer exists.",
            }

        token, _ = create_session_token(user.id, user.email, user.name)
        set_active_user_id(user.id)
        save_local_session(token, user.id, user.email)

        return {
            "success": True,
            "authenticated": True,
            "message": f"Successfully connected to ChronoNote as {user.name} ({user.email})! Your workspace is now active.",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
            },
        }
    finally:
        db.close()


@server.tool()
def connect_with_token(token: str) -> dict[str, Any]:
    """Connect Claude to your ChronoNote account using an active session token.

    Args:
        token: ChronoNote Bearer session token.
    """
    db = SessionLocal()
    try:
        claims = verify_session_token(token.strip())
        if not claims or not claims.get("sub"):
            return {
                "success": False,
                "authenticated": False,
                "error": "Invalid or expired session token.",
            }

        uid = int(claims["sub"])
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            return {
                "success": False,
                "authenticated": False,
                "error": "User account matching token does not exist.",
            }

        set_active_user_id(user.id)
        save_local_session(token.strip(), user.id, user.email)

        return {
            "success": True,
            "authenticated": True,
            "message": f"Successfully authenticated as {user.name} ({user.email}).",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
            },
        }
    finally:
        db.close()


@server.tool()
def whoami() -> dict[str, Any]:
    """Check the currently authenticated ChronoNote user account."""
    db = SessionLocal()
    try:
        user = resolve_authenticated_user(db)
        if not user:
            return {
                "authenticated": False,
                "message": "Not logged in to ChronoNote. Use the 'login' or 'connect_with_code' tool to connect your account.",
            }
        return {
            "authenticated": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
            },
            "message": f"Currently authenticated as {user.name} ({user.email}).",
        }
    finally:
        db.close()


@server.tool()
def logout() -> dict[str, Any]:
    """Log out of the current ChronoNote account and lock all workspace tools."""
    clear_local_session()
    return {
        "success": True,
        "authenticated": False,
        "message": "Successfully logged out of ChronoNote. Workspace tools are now locked.",
    }


# ---------------------------------------------------------------------------
# Workspace Management Tools (Strictly User-Scoped)
# ---------------------------------------------------------------------------


@server.tool()
def list_projects(
    status_filter: str | None = None,
) -> dict[str, Any]:
    """List all projects in your ChronoNote workspace with task counts and progress.
    Requires authentication. Only displays projects belonging to the logged-in user.

    Args:
        status_filter: Optional filter ('planned', 'active', 'on_hold', 'completed', 'archived').
    """
    db = SessionLocal()
    try:
        user = resolve_authenticated_user(db)
        if not user:
            return {"success": False, "authenticated": False, "error": AUTH_REQUIRED_MESSAGE}

        q = db.query(Project).filter(Project.user_id == user.id)

        if status_filter:
            q = q.filter(Project.status == status_filter.strip().lower())
        else:
            q = q.filter(Project.status != "archived")

        projects = q.order_by(
            Project.is_pinned.desc(),
            Project.sidebar_order.asc(),
            Project.id.asc(),
        ).all()

        return {
            "success": True,
            "count": len(projects),
            "user": user.email,
            "projects": [_format_project(p) for p in projects],
        }
    finally:
        db.close()


@server.tool()
def get_project(
    project_id: int | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    """Retrieve complete project details including all tasks, notes, and timeline metrics.
    Only allows access to projects owned by the currently authenticated user.

    Args:
        project_id: The integer ID of the project.
        slug: The unique slug of the project (used if project_id is omitted).
    """
    if not project_id and not slug:
        return {"success": False, "error": "Must provide either project_id or slug."}

    db = SessionLocal()
    try:
        user = resolve_authenticated_user(db)
        if not user:
            return {"success": False, "authenticated": False, "error": AUTH_REQUIRED_MESSAGE}

        q = db.query(Project).filter(Project.user_id == user.id)
        if project_id:
            proj = q.filter(Project.id == project_id).first()
        else:
            proj = q.filter(Project.slug == slug.strip()).first()

        if not proj:
            return {"success": False, "error": f"Project not found or you do not have permission to view it."}

        return {
            "success": True,
            "project": _format_project(proj, include_tasks=True, include_notes=True),
        }
    finally:
        db.close()


@server.tool()
def create_project(
    name: str,
    description: str = "",
    color: str = "#6366f1",
    icon: str = "folder",
    status: str = "active",
    is_pinned: bool = False,
    start_date: str | None = None,
    target_date: str | None = None,
) -> dict[str, Any]:
    """Create a new project in your ChronoNote workspace.
    The created project is strictly owned by the logged-in user.

    Args:
        name: Name of the project (required, e.g. 'Website Redesign', 'Mobile App MVP').
        description: Markdown or text description of the project goals.
        color: Hex color code (e.g. '#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6').
        icon: Lucide icon name (e.g. 'folder', 'rocket', 'target', 'star', 'calendar', 'code', 'zap', 'book').
        status: Project status ('planned', 'active', 'on_hold', 'completed', 'archived'). Default: 'active'.
        is_pinned: If True, pins the project to the top of the left sidebar. Default: False.
        start_date: Start date formatted as 'YYYY-MM-DD' (optional).
        target_date: Target or deadline date formatted as 'YYYY-MM-DD' (optional).
    """
    db = SessionLocal()
    try:
        user = resolve_authenticated_user(db)
        if not user:
            return {"success": False, "authenticated": False, "error": AUTH_REQUIRED_MESSAGE}

        base_slug = slugify(name)
        unique_slug = _unique_project_slug(db, base_slug)

        parsed_start = _parse_date(start_date)
        parsed_target = _parse_date(target_date)
        max_order = db.query(Project).filter(Project.user_id == user.id).count()

        proj = Project(
            user_id=user.id,
            name=name.strip(),
            slug=unique_slug,
            description=description.strip(),
            color=color or "#6366f1",
            icon=icon or "folder",
            status=status.strip().lower() if status else "active",
            is_pinned=bool(is_pinned),
            sidebar_order=max_order,
            start_date=parsed_start,
            target_date=parsed_target,
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)

        try:
            ws_manager.emit_from_sync("project.created", {"id": proj.id, "name": proj.name, "user_id": user.id})
        except Exception:
            pass

        return {
            "success": True,
            "message": f"Project '{proj.name}' created for {user.email} with slug '{proj.slug}'.",
            "project": _format_project(proj),
        }
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


@server.tool()
def create_project_with_tasks(
    name: str,
    description: str = "",
    tasks: list[dict[str, Any]] | None = None,
    color: str = "#6366f1",
    icon: str = "folder",
    status: str = "active",
    is_pinned: bool = False,
    start_date: str | None = None,
    target_date: str | None = None,
    initial_note: str | None = None,
) -> dict[str, Any]:
    """Create a new project in your ChronoNote workspace along with tasks and a brief note.
    Strictly isolated to your logged-in account.

    Args:
        name: Project title (e.g. 'Q1 Marketing Sprint', 'API Migration').
        description: Description of the project goals.
        tasks: List of task dicts (title, description, status, priority, due_date, is_milestone).
        color: Hex color (default '#6366f1').
        icon: Lucide icon name (default 'folder').
        status: 'planned' | 'active' | 'on_hold' | 'completed' (default 'active').
        is_pinned: Whether to pin project in sidebar (default False).
        start_date: Project start date 'YYYY-MM-DD' (optional).
        target_date: Project target date 'YYYY-MM-DD' (optional).
        initial_note: Optional Markdown text to create as a project brief note.
    """
    db = SessionLocal()
    try:
        user = resolve_authenticated_user(db)
        if not user:
            return {"success": False, "authenticated": False, "error": AUTH_REQUIRED_MESSAGE}

        base_slug = slugify(name)
        unique_slug = _unique_project_slug(db, base_slug)

        parsed_start = _parse_date(start_date)
        parsed_target = _parse_date(target_date)
        max_order = db.query(Project).filter(Project.user_id == user.id).count()

        proj = Project(
            user_id=user.id,
            name=name.strip(),
            slug=unique_slug,
            description=description.strip(),
            color=color or "#6366f1",
            icon=icon or "folder",
            status=status.strip().lower() if status else "active",
            is_pinned=bool(is_pinned),
            sidebar_order=max_order,
            start_date=parsed_start,
            target_date=parsed_target,
        )
        db.add(proj)
        db.flush()

        created_tasks = []
        if tasks:
            for item in tasks:
                t_title = str(item.get("title", "")).strip()
                if not t_title:
                    continue
                t_stat = item.get("status", "todo").strip().lower()
                t_prio = item.get("priority", "medium").strip().lower()
                t_prog = int(item.get("progress", 100 if t_stat == "done" else 0))
                t_milestone = bool(item.get("is_milestone", False))
                t_sdate = _parse_date(item.get("start_date")) or parsed_start
                t_ddate = _parse_date(item.get("due_date")) or parsed_target

                task_obj = Task(
                    project_id=proj.id,
                    title=t_title,
                    description=item.get("description", "").strip(),
                    status=t_stat if t_stat in ["todo", "in_progress", "review", "done"] else "todo",
                    priority=t_prio if t_prio in ["low", "medium", "high", "urgent"] else "medium",
                    color=proj.color or "#0891b2",
                    start_date=t_sdate,
                    due_date=t_ddate,
                    is_milestone=t_milestone,
                    progress=max(0, min(100, t_prog)),
                )
                db.add(task_obj)
                created_tasks.append(task_obj)

        if initial_note:
            note_slug = f"{unique_slug}-overview"
            counter = 2
            cand_slug = note_slug
            while db.query(Note).filter(Note.slug == cand_slug).first():
                cand_slug = f"{note_slug}-{counter}"
                counter += 1

            note_obj = Note(
                user_id=user.id,
                project_id=proj.id,
                title=f"{proj.name} — Overview & Brief",
                slug=cand_slug,
                content_md=initial_note,
                is_pinned=False,
                is_daily_note=False,
                note_date=date.today(),
            )
            db.add(note_obj)
            db.flush()
            _sync_note(db, note_obj)

        db.commit()
        db.refresh(proj)

        try:
            ws_manager.emit_from_sync("project.created", {"id": proj.id, "name": proj.name, "user_id": user.id})
        except Exception:
            pass

        return {
            "success": True,
            "message": f"Project '{proj.name}' created for {user.email} with {len(created_tasks)} tasks.",
            "project": _format_project(proj, include_tasks=True, include_notes=True),
        }
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


@server.tool()
def create_task(
    project_id: int,
    title: str,
    description: str = "",
    status: str = "todo",
    priority: str = "medium",
    color: str = "#0891b2",
    start_date: str | None = None,
    due_date: str | None = None,
    is_milestone: bool = False,
    depends_on_id: int | None = None,
    progress: int = 0,
) -> dict[str, Any]:
    """Add a new task or milestone to an existing ChronoNote project.
    Verifies that you own the project before adding the task.

    Args:
        project_id: Integer ID of the target project.
        title: Task title (e.g. 'Implement OAuth2 flow').
        description: Detailed task instructions or acceptance criteria.
        status: 'todo' | 'in_progress' | 'review' | 'done'. Default: 'todo'.
        priority: 'low' | 'medium' | 'high' | 'urgent'. Default: 'medium'.
        color: Hex color for the task bar on the timeline view.
        start_date: Start date 'YYYY-MM-DD'.
        due_date: Due date / deadline 'YYYY-MM-DD'.
        is_milestone: If True, renders as a diamond milestone on the timeline.
        depends_on_id: Optional ID of predecessor task (for dependency connector & cascade).
        progress: Percentage complete (0-100).
    """
    db = SessionLocal()
    try:
        user = resolve_authenticated_user(db)
        if not user:
            return {"success": False, "authenticated": False, "error": AUTH_REQUIRED_MESSAGE}

        proj = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
        if not proj:
            return {"success": False, "error": f"Project with ID {project_id} not found or permission denied."}

        parsed_status = status.strip().lower() if status else "todo"
        task_prog = 100 if parsed_status == "done" else max(0, min(100, int(progress)))

        task_obj = Task(
            project_id=project_id,
            title=title.strip(),
            description=description.strip(),
            status=parsed_status if parsed_status in ["todo", "in_progress", "review", "done"] else "todo",
            priority=priority.strip().lower() if priority in ["low", "medium", "high", "urgent"] else "medium",
            color=color or proj.color or "#0891b2",
            start_date=_parse_date(start_date) or proj.start_date,
            due_date=_parse_date(due_date) or proj.target_date,
            is_milestone=bool(is_milestone),
            depends_on_id=depends_on_id,
            progress=task_prog,
        )
        db.add(task_obj)
        db.commit()
        db.refresh(task_obj)

        try:
            ws_manager.emit_from_sync("task.updated", {"task_id": task_obj.id, "project_id": project_id})
        except Exception:
            pass

        return {
            "success": True,
            "message": f"Task '{task_obj.title}' (ID {task_obj.id}) added to project '{proj.name}'.",
            "task": {
                "id": task_obj.id,
                "project_id": task_obj.project_id,
                "title": task_obj.title,
                "status": task_obj.status,
                "priority": task_obj.priority,
                "start_date": task_obj.start_date.isoformat() if task_obj.start_date else None,
                "due_date": task_obj.due_date.isoformat() if task_obj.due_date else None,
                "is_milestone": task_obj.is_milestone,
                "progress": task_obj.progress,
            },
        }
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


@server.tool()
def update_project(
    project_id: int,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
    color: str | None = None,
    icon: str | None = None,
    is_pinned: bool | None = None,
    start_date: str | None = None,
    target_date: str | None = None,
) -> dict[str, Any]:
    """Update metadata, timeline dates, status, or pin state of an existing project.
    Verifies that you own the project.

    Args:
        project_id: ID of the project to update.
        name: New project title.
        description: New description.
        status: New status ('planned', 'active', 'on_hold', 'completed', 'archived').
        color: New hex color code.
        icon: New Lucide icon.
        is_pinned: Set pinned state.
        start_date: New start date 'YYYY-MM-DD'.
        target_date: New deadline date 'YYYY-MM-DD'.
    """
    db = SessionLocal()
    try:
        user = resolve_authenticated_user(db)
        if not user:
            return {"success": False, "authenticated": False, "error": AUTH_REQUIRED_MESSAGE}

        proj = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
        if not proj:
            return {"success": False, "error": f"Project with ID {project_id} not found or permission denied."}

        if name is not None:
            proj.name = name.strip()
        if description is not None:
            proj.description = description.strip()
        if status is not None:
            proj.status = status.strip().lower()
        if color is not None:
            proj.color = color.strip()
        if icon is not None:
            proj.icon = icon.strip()
        if is_pinned is not None:
            proj.is_pinned = bool(is_pinned)
        if start_date is not None:
            proj.start_date = _parse_date(start_date)
        if target_date is not None:
            proj.target_date = _parse_date(target_date)

        db.commit()
        db.refresh(proj)

        try:
            ws_manager.emit_from_sync("project.created", {"id": proj.id, "name": proj.name, "user_id": user.id})
        except Exception:
            pass

        return {
            "success": True,
            "message": f"Project '{proj.name}' updated successfully.",
            "project": _format_project(proj),
        }
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


@server.tool()
def create_project_note(
    project_id: int,
    title: str,
    content: str,
) -> dict[str, Any]:
    """Create a Markdown note linked to a project in ChronoNote.
    Supports #tags, [[WikiLinks]], and inline task directives:
    - [ ] Task title @due(YYYY-MM-DD) @priority(high) @milestone

    Args:
        project_id: The ID of the project to attach the note to.
        title: Note title.
        content: Markdown content.
    """
    db = SessionLocal()
    try:
        user = resolve_authenticated_user(db)
        if not user:
            return {"success": False, "authenticated": False, "error": AUTH_REQUIRED_MESSAGE}

        proj = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
        if not proj:
            return {"success": False, "error": f"Project with ID {project_id} not found or permission denied."}

        note_slug = slugify(title)

        counter = 2
        cand_slug = note_slug
        while db.query(Note).filter(Note.slug == cand_slug).first():
            cand_slug = f"{note_slug}-{counter}"
            counter += 1

        note_obj = Note(
            user_id=user.id,
            project_id=project_id,
            title=title.strip(),
            slug=cand_slug,
            content_md=content,
            is_pinned=False,
            is_daily_note=False,
            note_date=date.today(),
        )
        db.add(note_obj)
        db.flush()
        _sync_note(db, note_obj)

        db.commit()
        db.refresh(note_obj)

        return {
            "success": True,
            "message": f"Note '{note_obj.title}' created and attached to project '{proj.name}'.",
            "note": {
                "id": note_obj.id,
                "project_id": note_obj.project_id,
                "title": note_obj.title,
                "slug": note_obj.slug,
            },
        }
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
    finally:
        db.close()


def main():
    """Run the MCP server over standard input/output (stdio)."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
