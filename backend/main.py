from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
from typing import Any
from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, inspect, or_, text
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import ACTIVE_DB_DIALECT, Base, compile_postgres_ddl, engine, get_db
from backend.models import (
    Habit,
    HabitLog,
    JournalSecret,
    JournalTemplate,
    Note,
    NoteLink,
    Project,
    Sticker,
    StickerPlacement,
    StudySession,
    Task,
    User,
)
from backend.schemas import (
    AccountProfileUpdateRequest,
    AuthConfigOut,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthSessionOut,
    BacklinkItem,
    CriticalPathOut,
    GoogleAuthRequest,
    GraphEdge,
    GraphNode,
    HabitAnalyticsOut,
    HabitCreate,
    HabitHeatmapDay,
    HabitLogOut,
    HabitOut,
    HabitToggleRequest,
    HabitUpdate,
    ImageUploadRequest,
    ImageUploadResponse,
    JournalLockStatusOut,
    JournalSetPasswordRequest,
    JournalUnlockRequest,
    JournalUnlockResponse,
    JournalUpsertRequest,
    KanbanBoardResponse,
    KanbanColumn,
    KanbanMoveRequest,
    KnowledgeGraphResponse,
    NoteCreate,
    NoteOut,
    NoteUpdate,
    OcrVisionRequest,
    OcrVisionResponse,
    ProjectCreate,
    ProjectKanbanBoardResponse,
    ProjectKanbanColumn,
    ProjectKanbanMoveRequest,
    ProjectOut,
    ProjectUpdate,
    SearchResultItem,
    SidebarProjectItem,
    SidebarReorderRequest,
    StickerCreate,
    StickerOut,
    StickerPlacementCreate,
    StickerPlacementOut,
    StickerPlacementUpdate,
    StudySessionCreate,
    StudySessionOut,
    StudyStatsOut,
    TaskCreate,
    TaskOut,
    TaskUpdate,
    TemplateCreate,
    TemplateOut,
    TemplateRenderedOut,
    TemplateUpdate,
    TimelineDependencyEdge,
    TimelineNotePin,
    TimelineResponse,
    TimelineSwimlane,
    UserOut,
    WikiLinkItem,
)
from backend.services.auth_service import (
    create_journal_session_token,
    create_session_token,
    get_allowed_emails,
    hash_password,
    is_email_allowed,
    verify_google_id_token,
    verify_journal_session_token,
    verify_password,
    verify_session_token,
)
from backend.services.dependency_scheduler import (
    cascade_dependent_tasks,
    compute_critical_path,
    validate_no_dependency_cycle,
)
from backend.services.markdown_parser import parse_markdown_note, slugify
from backend.services.ws_manager import ws_manager

Base.metadata.create_all(bind=engine)


def _ensure_task_color_column() -> None:
    try:
        insp = inspect(engine)
        table_names = set(insp.get_table_names())
        if "tasks" in table_names:
            cols = {c["name"] for c in insp.get_columns("tasks")}
            if "color" not in cols:
                with engine.begin() as conn:
                    conn.execute(
                        text("ALTER TABLE tasks ADD COLUMN color VARCHAR(20) DEFAULT '#0891b2'")
                    )
            if "user_id" not in cols:
                with engine.begin() as conn:
                    conn.execute(
                        text("ALTER TABLE tasks ADD COLUMN user_id INTEGER NULL")
                    )
            if engine.dialect.name == "postgresql":
                with engine.begin() as conn:
                    try:
                        conn.execute(
                            text("ALTER TABLE tasks ALTER COLUMN project_id DROP NOT NULL")
                        )
                    except Exception:
                        pass
        if "projects" in table_names:
            cols = {c["name"] for c in insp.get_columns("projects")}
            if "user_id" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN user_id INTEGER NULL"))
        if "notes" in table_names:
            cols = {c["name"] for c in insp.get_columns("notes")}
            if "user_id" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE notes ADD COLUMN user_id INTEGER NULL"))
        if "users" in table_names:
            cols = {c["name"] for c in insp.get_columns("users")}
            if "password_hash" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(128) NULL"))
            if "salt" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN salt VARCHAR(64) NULL"))
        if "journal_secrets" not in table_names:
            Base.metadata.create_all(bind=engine)
    except Exception:
        pass


_ensure_task_color_column()

app = FastAPI(
    title="ChronoNote API",
    description="Unified Markdown Note-Taking, Project Timeline, Kanban & Knowledge Graph API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _unique_project_slug(db: Session, base_slug: str, exclude_id: int | None = None) -> str:
    candidate = base_slug
    counter = 2
    while True:
        q = db.query(Project).filter(Project.slug == candidate)
        if exclude_id is not None:
            q = q.filter(Project.id != exclude_id)
        if not q.first():
            return candidate
        candidate = f"{base_slug}-{counter}"
        counter += 1


def _unique_note_slug(db: Session, base_slug: str, exclude_id: int | None = None) -> str:
    candidate = base_slug
    counter = 2
    while True:
        q = db.query(Note).filter(Note.slug == candidate)
        if exclude_id is not None:
            q = q.filter(Note.id != exclude_id)
        if not q.first():
            return candidate
        candidate = f"{base_slug}-{counter}"
        counter += 1


def _compute_sidebar_project_item(
    project: Project,
    reference_date: date | None = None,
) -> SidebarProjectItem:
    today = reference_date or date.today()
    tasks = project.tasks or []
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == "done" or t.progress == 100)
    overdue_tasks = sum(
        1
        for t in tasks
        if t.due_date is not None and t.due_date < today and t.status != "done"
    )
    progress_pct = round((completed_tasks / total_tasks) * 100.0, 1) if total_tasks > 0 else 0.0
    note_count = len(project.notes or [])

    return SidebarProjectItem(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        color=project.color,
        icon=project.icon,
        status=project.status,
        is_pinned=project.is_pinned,
        sidebar_order=project.sidebar_order,
        start_date=project.start_date,
        target_date=project.target_date,
        created_at=project.created_at,
        updated_at=project.updated_at,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        overdue_tasks=overdue_tasks,
        progress_pct=progress_pct,
        note_count=note_count,
    )


def _serialize_task(task: Task, cascaded_ids: list[int] | None = None) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.cascaded_task_ids = cascaded_ids or []
    return out


def _sync_note_metadata_and_tasks(
    db: Session,
    note: Note,
    sync_inline_tasks: bool = True,
) -> list[int]:
    """Parse Markdown note, update frontmatter/tags/wikilinks, and sync inline tasks."""
    parsed = parse_markdown_note(note.content_md)
    note.frontmatter_json = json.dumps(parsed.frontmatter)
    note.tags_json = json.dumps(parsed.tags)
    db.flush()

    # Resolve any previously unresolved links targeting this note's slug
    db.query(NoteLink).filter(
        NoteLink.target_slug == note.slug,
        NoteLink.target_note_id.is_(None),
    ).update({"target_note_id": note.id}, synchronize_session=False)

    # Rebuild outgoing WikiLinks for this note
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

    synced_task_ids: list[int] = []
    if sync_inline_tasks:
        existing_tasks = (
            db.query(Task)
            .filter(Task.source_note_id == note.id)
            .all()
        )
        existing_by_title = {t.title: t for t in existing_tasks}
        seen_titles: set[str] = set()

        for item in parsed.inline_tasks:
            seen_titles.add(item.title)
            if item.title in existing_by_title:
                t_obj = existing_by_title[item.title]
                t_obj.status = item.status
                t_obj.progress = item.progress
                t_obj.priority = item.priority
                t_obj.start_date = item.start_date or t_obj.start_date or note.note_date
                t_obj.due_date = item.due_date or t_obj.due_date
                t_obj.is_milestone = item.is_milestone
                if note.project_id is not None:
                    t_obj.project_id = note.project_id
                t_obj.user_id = note.user_id
                db.flush()
                synced_task_ids.append(t_obj.id)
            else:
                new_task = Task(
                    user_id=note.user_id,
                    project_id=note.project_id,
                    source_note_id=note.id,
                    title=item.title,
                    description=f"Synced from note [[{note.title}]]",
                    status=item.status,
                    priority=item.priority,
                    start_date=item.start_date or note.note_date,
                    due_date=item.due_date or (note.note_date if note.is_daily_note else None),
                    is_milestone=item.is_milestone,
                    progress=item.progress,
                )
                db.add(new_task)
                db.flush()
                synced_task_ids.append(new_task.id)

        for title_key, old_task in existing_by_title.items():
            if title_key not in seen_titles:
                db.delete(old_task)

    # Sync habits if note has an associated date (daily note or frontmatter date)
    note_dt = note.note_date
    if not note_dt and "date" in parsed.frontmatter:
        try:
            note_dt = date.fromisoformat(str(parsed.frontmatter["date"]))
        except (ValueError, TypeError):
            pass

    if note_dt and parsed.habits:
        for h in parsed.habits:
            h_query = db.query(Habit).filter(Habit.slug == h.slug)
            if note.user_id:
                h_query = h_query.filter(Habit.user_id == note.user_id)
            else:
                h_query = h_query.filter(Habit.user_id.is_(None))
            habit_obj = h_query.first()
            if not habit_obj:
                habit_obj = Habit(
                    user_id=note.user_id,
                    slug=h.slug,
                    name=h.name,
                    icon="check",
                    color="#10b981",
                )
                db.add(habit_obj)
                db.flush()

            log_query = db.query(HabitLog).filter(
                HabitLog.habit_id == habit_obj.id,
                HabitLog.log_date == note_dt,
            )
            if note.user_id:
                log_query = log_query.filter(HabitLog.user_id == note.user_id)
            else:
                log_query = log_query.filter(HabitLog.user_id.is_(None))
            h_log = log_query.first()
            if h_log:
                h_log.completed = h.completed
                h_log.value = h.value
                h_log.note_id = note.id
            else:
                h_log = HabitLog(
                    habit_id=habit_obj.id,
                    user_id=note.user_id,
                    note_id=note.id,
                    log_date=note_dt,
                    completed=h.completed,
                    value=h.value,
                )
                db.add(h_log)

    db.flush()
    return synced_task_ids


def _serialize_note(db: Session, note: Note, synced_task_ids: list[int] | None = None) -> NoteOut:
    outgoing_rows = db.query(NoteLink).filter(NoteLink.source_note_id == note.id).all()
    incoming_rows = (
        db.query(NoteLink)
        .filter(or_(NoteLink.target_note_id == note.id, NoteLink.target_slug == note.slug))
        .all()
    )

    outgoing_links = [
        WikiLinkItem(
            target_slug=row.target_slug,
            target_note_id=row.target_note_id,
            display_text=row.display_text,
            context_snippet=row.context_snippet,
        )
        for row in outgoing_rows
    ]

    backlinks: list[BacklinkItem] = []
    for row in incoming_rows:
        src = db.query(Note).filter(Note.id == row.source_note_id).first()
        if src and src.id != note.id:
            backlinks.append(
                BacklinkItem(
                    source_note_id=src.id,
                    source_title=src.title,
                    source_slug=src.slug,
                    context_snippet=row.context_snippet,
                )
            )

    if synced_task_ids is None:
        synced_task_ids = [
            t.id for t in db.query(Task).filter(Task.source_note_id == note.id).all()
        ]

    return NoteOut(
        id=note.id,
        project_id=note.project_id,
        title=note.title,
        slug=note.slug,
        content_md=note.content_md,
        frontmatter=json.loads(note.frontmatter_json or "{}"),
        tags=json.loads(note.tags_json or "[]"),
        is_pinned=note.is_pinned,
        is_daily_note=note.is_daily_note,
        note_date=note.note_date,
        outgoing_links=outgoing_links,
        backlinks=backlinks,
        synced_task_ids=synced_task_ids,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def _scope_habits(query, user: User | None):
    if user:
        return query.filter(Habit.user_id == user.id)
    return query.filter(Habit.user_id.is_(None))


def _calculate_habit_metrics(
    db: Session,
    habit: Habit,
    user: User | None = None,
    today_dt: date | None = None,
) -> dict[str, Any]:
    today_dt = today_dt or date.today()
    q = db.query(HabitLog).filter(
        HabitLog.habit_id == habit.id,
        HabitLog.completed.is_(True),
    )
    if user:
        q = q.filter(HabitLog.user_id == user.id)
    elif habit.user_id:
        q = q.filter(HabitLog.user_id == habit.user_id)
    else:
        q = q.filter(HabitLog.user_id.is_(None))

    logs = q.all()
    completed_dates = {log.log_date for log in logs}

    # Current streak calculation: consecutive days up to today or yesterday
    current_streak = 0
    check_day = today_dt
    if check_day not in completed_dates:
        check_day = today_dt - timedelta(days=1)

    while check_day in completed_dates:
        current_streak += 1
        check_day -= timedelta(days=1)

    # Longest streak calculation
    longest_streak = 0
    if completed_dates:
        sorted_dates = sorted(list(completed_dates))
        current_run = 1
        longest_streak = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                current_run += 1
            else:
                current_run = 1
            if current_run > longest_streak:
                longest_streak = current_run

    # 30-day completion rate
    thirty_days_ago = today_dt - timedelta(days=29)
    recent_count = sum(1 for d in completed_dates if thirty_days_ago <= d <= today_dt)
    rate_30d = round((recent_count / 30.0) * 100, 1)

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_completions": len(completed_dates),
        "completion_rate_30d": rate_30d,
    }


def _serialize_habit(
    db: Session,
    habit: Habit,
    user: User | None = None,
    today_dt: date | None = None,
) -> HabitOut:
    metrics = _calculate_habit_metrics(db, habit, user, today_dt)
    return HabitOut(
        id=habit.id,
        slug=habit.slug,
        name=habit.name,
        description=habit.description or "",
        icon=habit.icon or "check",
        color=habit.color or "#10b981",
        target_days_per_week=habit.target_days_per_week or 7,
        archived=habit.archived,
        current_streak=metrics["current_streak"],
        longest_streak=metrics["longest_streak"],
        total_completions=metrics["total_completions"],
        completion_rate_30d=metrics["completion_rate_30d"],
        created_at=habit.created_at,
        updated_at=habit.updated_at,
    )


DEFAULT_TEMPLATES = [
    {
        "name": "Daily Reflection & Habits",
        "description": "Standard daily journal with habit check-in, notes, and evening reflection.",
        "is_default": True,
        "content_md": """---
date: {{date}}
day: {{day_of_week}}
tags: [journal, daily]
---

### Daily Habits
{{habits_checklist}}

### Notes & Observations
- 

### Evening Reflection
- Highlight of the day: 
- One lesson or realization: 
- Focus for tomorrow: 
""",
    },
    {
        "name": "Minimal Habit Check-in",
        "description": "Clean, low-pressure checklist focused purely on daily momentum.",
        "is_default": False,
        "content_md": """---
date: {{date}}
tags: [journal, habits]
---

### Daily Habits
{{habits_checklist}}

### Quick Log
- 
""",
    },
    {
        "name": "Weekly Review & Retrospective",
        "description": "End-of-week reflection to review completed tasks, habit consistency, and upcoming goals.",
        "is_default": False,
        "content_md": """---
date: {{date}}
tags: [journal, weekly-review]
---

## Weekly Review (Week ending {{date}})

### Highlights & Accomplishments
- 

### Habit Consistency & Energy
- What felt easy this week?
- What caused friction or distraction?

### Top Priorities for Next Week
1. 
2. 
3. 
""",
    },
]


def _ensure_default_templates(db: Session, user: User | None = None) -> list[JournalTemplate]:
    q = db.query(JournalTemplate)
    if user:
        q = q.filter(JournalTemplate.user_id == user.id)
    else:
        q = q.filter(JournalTemplate.user_id.is_(None))
    existing = q.all()
    if existing:
        return existing

    created: list[JournalTemplate] = []
    for tpl in DEFAULT_TEMPLATES:
        row = JournalTemplate(
            user_id=user.id if user else None,
            name=tpl["name"],
            description=tpl["description"],
            content_md=tpl["content_md"],
            is_default=tpl["is_default"],
        )
        db.add(row)
        created.append(row)
    db.commit()
    return created


def _render_journal_template(
    template_content: str,
    target_dt: date,
    habits: list[Habit],
) -> str:
    rendered = template_content.replace("{{date}}", target_dt.isoformat())
    rendered = rendered.replace("{{day_of_week}}", target_dt.strftime("%A"))
    rendered = rendered.replace("{{year}}", str(target_dt.year))
    rendered = rendered.replace("{{month}}", target_dt.strftime("%B"))

    active_habits = [h for h in habits if not h.archived]
    if active_habits:
        checklist_lines = [
            f"- [ ] {h.name} @habit({h.slug})"
            for h in active_habits
        ]
        checklist_str = "\n".join(checklist_lines)
    else:
        checklist_str = (
            "- [ ] Morning Routine @habit(morning-routine)\n"
            "- [ ] Deep Work Block @habit(deep-work)\n"
            "- [ ] Reading / Learning @habit(reading)"
        )

    rendered = rendered.replace("{{habits_checklist}}", checklist_str)
    return rendered



@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "ChronoNote API",
        "version": "2.0.0",
        "database_dialect": ACTIVE_DB_DIALECT,
    }


@app.get("/api/schema/postgres")
def get_postgres_ddl_schema():
    """Return compiled PostgreSQL 16 DDL statements for all ChronoNote tables & indexes."""
    return {
        "dialect": "postgresql",
        "ddl": compile_postgres_ddl(),
    }


# ---------------------------------------------------------------------------
# Google Authentication & Personal Session Endpoints
# ---------------------------------------------------------------------------


def get_optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    raw_token = authorization.split(" ", 1)[1].strip()
    claims = verify_session_token(raw_token)
    if not claims:
        return None
    try:
        uid = int(claims["sub"])
    except (KeyError, ValueError, TypeError):
        return None
    return db.query(User).filter(User.id == uid).first()


def _scope_projects(q, user: User | None):
    if user is not None:
        return q.filter(Project.user_id == user.id)
    return q.filter(Project.user_id.is_(None))


def _scope_notes(q, user: User | None):
    if user is not None:
        return q.filter(Note.user_id == user.id)
    return q.filter(Note.user_id.is_(None))


def _ensure_user_workspace_initialized(db: Session, user: User) -> None:
    """
    Ensure a newly authenticated user has their own persistent workspace in the database.
    If they are the first user and unclaimed (user_id IS NULL) rows exist, claim them;
    otherwise seed a fresh starter project and journal entry scoped to user.id.
    """
    existing_count = db.query(Project).filter(Project.user_id == user.id).count()
    existing_notes = db.query(Note).filter(Note.user_id == user.id).count()
    if existing_count > 0 or existing_notes > 0:
        return

    other_users_with_data = (
        db.query(Project).filter(Project.user_id.is_not(None), Project.user_id != user.id).count()
    )
    unclaimed_projects = db.query(Project).filter(Project.user_id.is_(None)).count()
    unclaimed_notes = db.query(Note).filter(Note.user_id.is_(None)).count()

    if other_users_with_data == 0 and (unclaimed_projects > 0 or unclaimed_notes > 0):
        db.query(Project).filter(Project.user_id.is_(None)).update(
            {"user_id": user.id}, synchronize_session=False
        )
        db.query(Note).filter(Note.user_id.is_(None)).update(
            {"user_id": user.id}, synchronize_session=False
        )
        db.commit()
        return

    # Otherwise create a personal starter project for this user account
    starter_slug = _unique_project_slug(db, f"personal-roadmap-{user.id}")
    starter_proj = Project(
        user_id=user.id,
        name="Personal Goals & Projects",
        slug=starter_slug,
        description=f"{user.name or user.email}'s synced workspace",
        color="#b85423",
        status="active",
        is_pinned=True,
        sidebar_order=0,
        start_date=date(2026, 11, 1),
        target_date=date(2026, 11, 30),
    )
    db.add(starter_proj)
    db.flush()

    db.add(
        Task(
            project_id=starter_proj.id,
            title="Write first daily journal entry",
            status="todo",
            color="#2c666e",
            start_date=date(2026, 11, 1),
            due_date=date(2026, 11, 5),
        )
    )
    db.commit()


@app.get("/api/auth/config", response_model=AuthConfigOut)
def get_auth_config():
    return AuthConfigOut(
        google_client_id=settings.GOOGLE_CLIENT_ID,
        auth_required=settings.AUTH_REQUIRED,
        has_allowlist=bool(get_allowed_emails()),
        has_server_ocr_key=bool((settings.GEMINI_API_KEY or "").strip()),
    )


@app.post("/api/auth/google", response_model=AuthSessionOut)
def authenticate_with_google(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db),
):
    if payload.credential:
        try:
            verified = verify_google_id_token(payload.credential)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        email = verified["email"]
        name = verified["name"]
        picture = verified.get("picture", "")
        google_sub = verified.get("sub")
    else:
        # Personal quick-login when GOOGLE_CLIENT_ID is not yet configured in local/personal setup
        if settings.APP_ENV == "production" and settings.GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=400, detail="Google credential token is required")
        email = (payload.email or "").strip().lower()
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="Valid Google email address is required")
        name = (payload.name or email.split("@")[0]).strip()
        picture = payload.picture or ""
        google_sub = f"local-{email}"

    if not is_email_allowed(email):
        raise HTTPException(
            status_code=403,
            detail="This Google account is not authorized to access this personal workspace",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user and google_sub:
        user = db.query(User).filter(User.google_sub == google_sub).first()

    if user:
        user.name = name or user.name
        if picture:
            user.picture = picture
        if google_sub:
            user.google_sub = google_sub
        user.last_login_at = datetime.now(timezone.utc)
    else:
        user = User(
            email=email,
            name=name,
            picture=picture,
            google_sub=google_sub,
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    _ensure_user_workspace_initialized(db, user)

    token, expires_at = create_session_token(user.id, user.email, user.name)
    return AuthSessionOut(
        token=token,
        user=UserOut.model_validate(user),
        expires_at=expires_at,
    )


@app.post("/api/auth/register", response_model=AuthSessionOut)
def register_account(
    payload: AuthRegisterRequest,
    db: Session = Depends(get_db),
):
    email = (payload.email or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not payload.password or len(payload.password.strip()) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password is required and must be at least 6 characters",
        )
    if not is_email_allowed(email):
        raise HTTPException(
            status_code=403,
            detail="This email is not authorized to register on this personal instance",
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists. Please sign in instead.",
        )

    name = (payload.name or email.split("@")[0]).strip()
    pwd_hash, salt_val = hash_password(payload.password.strip())

    user = User(
        email=email,
        name=name,
        picture="",
        password_hash=pwd_hash,
        salt=salt_val,
        google_sub=f"local-{email}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _ensure_user_workspace_initialized(db, user)

    token, expires_at = create_session_token(user.id, user.email, user.name)
    return AuthSessionOut(
        token=token,
        user=UserOut.model_validate(user),
        expires_at=expires_at,
    )


@app.post("/api/auth/login", response_model=AuthSessionOut)
def login_account(
    payload: AuthLoginRequest,
    db: Session = Depends(get_db),
):
    email = (payload.email or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not payload.password or not payload.password.strip():
        raise HTTPException(status_code=400, detail="Password is required")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account found with this email. Please register first.",
        )

    if not user.password_hash or not user.salt:
        raise HTTPException(
            status_code=401,
            detail="This account does not have a local password set. Please sign in via Google.",
        )

    if not verify_password(payload.password.strip(), user.password_hash, user.salt):
        raise HTTPException(status_code=401, detail="Incorrect email or password. Please try again.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    _ensure_user_workspace_initialized(db, user)

    token, expires_at = create_session_token(user.id, user.email, user.name)
    return AuthSessionOut(
        token=token,
        user=UserOut.model_validate(user),
        expires_at=expires_at,
    )


@app.get("/api/auth/me", response_model=UserOut)
def get_current_authenticated_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer session token")
    raw_token = authorization.split(" ", 1)[1].strip()
    claims = verify_session_token(raw_token)
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    user = db.query(User).filter(User.id == int(claims["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User account not found")
    return UserOut.model_validate(user)


SPECIAL_PASSWORD_CHARS = set("!@#$%^&*()_+-=[]{};':\",.<>/?~`|\\")


def validate_strict_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    if len(password) > 128:
        raise HTTPException(status_code=400, detail="Password cannot exceed 128 characters")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter (A-Z)")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter (a-z)")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one numeric digit (0-9)")
    if not any(c in SPECIAL_PASSWORD_CHARS for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character (!@#$%^&*...)")


@app.patch("/api/auth/profile", response_model=AuthSessionOut)
def update_user_account_profile(
    payload: AccountProfileUpdateRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer session token")
    raw_token = authorization.split(" ", 1)[1].strip()
    claims = verify_session_token(raw_token)
    if not claims or not claims.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    try:
        user_id = int(claims["sub"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token claims")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User account not found")

    # 1. Update Name/Username if provided
    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        if len(clean_name) > 120:
            raise HTTPException(status_code=400, detail="Username cannot exceed 120 characters")
        user.name = clean_name

    # 2. Update Email if provided
    if payload.email is not None:
        clean_email = payload.email.strip().lower()
        if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
            raise HTTPException(status_code=400, detail="A valid email address is required")
        if not is_email_allowed(clean_email):
            raise HTTPException(status_code=403, detail="Email is not in the allowed list")
        if clean_email != user.email:
            existing_email = db.query(User).filter(User.email == clean_email, User.id != user.id).first()
            if existing_email:
                raise HTTPException(status_code=409, detail="This email is already in use by another account")
            user.email = clean_email

    # 3. Update Password if requested (STRICT!)
    if payload.new_password:
        new_pwd = payload.new_password.strip()
        validate_strict_password(new_pwd)

        if payload.confirm_password is not None and payload.confirm_password.strip() != new_pwd:
            raise HTTPException(status_code=400, detail="Password confirmation does not match")

        # If account has existing password, require and verify current_password
        if user.password_hash and user.salt:
            if not payload.current_password or not payload.current_password.strip():
                raise HTTPException(status_code=400, detail="Current password is required to change password")
            if not verify_password(payload.current_password.strip(), user.password_hash, user.salt):
                raise HTTPException(status_code=401, detail="Current password is incorrect")
            if verify_password(new_pwd, user.password_hash, user.salt):
                raise HTTPException(status_code=400, detail="New password cannot be the same as current password")

        new_hash, new_salt = hash_password(new_pwd)
        user.password_hash = new_hash
        user.salt = new_salt

    db.commit()
    db.refresh(user)

    new_token, expires_at = create_session_token(
        user_id=user.id,
        email=user.email,
        name=user.name,
    )
    return AuthSessionOut(
        token=new_token,
        user=UserOut.model_validate(user),
        expires_at=expires_at,
    )


@app.get("/api/auth/mcp-code")
def get_mcp_connection_code(
    token: str | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Generate a temporary 6-digit connection code strictly for the authenticated user."""
    if not user and token:
        claims = verify_session_token(token.strip())
        if claims and claims.get("sub"):
            try:
                user = db.query(User).filter(User.id == int(claims["sub"])).first()
            except Exception:
                pass

    if not user:
        raise HTTPException(
            status_code=401,
            detail="You must be logged in to ChronoNote to generate an MCP connection code. Please log in first.",
        )

    from backend.services.mcp_auth import generate_mcp_code
    code = generate_mcp_code(user.id, user.email, user.name)
    return {
        "success": True,
        "code": code,
        "email": user.email,
        "name": user.name,
        "expires_in_seconds": 900,
        "instructions": f"In Claude, tell it: Connect to ChronoNote with code {code}",
    }


@app.post("/api/user/reset")
def reset_user_workspace_data(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    Permanently clear all user workspace data:
    projects, tasks, notes, journal entries, habits, habit logs, custom templates.
    """
    if user:
        # Delete user's habit logs & habits
        db.query(HabitLog).filter(HabitLog.user_id == user.id).delete(synchronize_session=False)
        db.query(Habit).filter(Habit.user_id == user.id).delete(synchronize_session=False)

        # Delete user's notes and links
        user_notes = db.query(Note.id).filter(Note.user_id == user.id).all()
        user_note_ids = [n[0] for n in user_notes]
        if user_note_ids:
            db.query(NoteLink).filter(
                (NoteLink.source_note_id.in_(user_note_ids)) | (NoteLink.target_note_id.in_(user_note_ids))
            ).delete(synchronize_session=False)
            db.query(Task).filter(Task.source_note_id.in_(user_note_ids)).update(
                {"source_note_id": None}, synchronize_session=False
            )

        # Delete user's projects and tasks
        user_projects = db.query(Project.id).filter(Project.user_id == user.id).all()
        user_proj_ids = [p[0] for p in user_projects]
        if user_proj_ids:
            db.query(Task).filter(Task.project_id.in_(user_proj_ids)).delete(synchronize_session=False)
            db.query(Note).filter(Note.project_id.in_(user_proj_ids)).delete(synchronize_session=False)
            db.query(Project).filter(Project.id.in_(user_proj_ids)).delete(synchronize_session=False)

        db.query(Note).filter(Note.user_id == user.id).delete(synchronize_session=False)
        db.query(JournalTemplate).filter(JournalTemplate.user_id == user.id).delete(synchronize_session=False)
        db.query(JournalSecret).filter(JournalSecret.user_id == user.id).delete(synchronize_session=False)
        db.commit()

        # Re-seed clean default templates
        _ensure_default_templates(db, user)
    else:
        # Anonymous / local data wipe
        db.query(HabitLog).filter(HabitLog.user_id.is_(None)).delete(synchronize_session=False)
        db.query(Habit).filter(Habit.user_id.is_(None)).delete(synchronize_session=False)

        anon_notes = db.query(Note.id).filter(Note.user_id.is_(None)).all()
        anon_note_ids = [n[0] for n in anon_notes]
        if anon_note_ids:
            db.query(NoteLink).filter(
                (NoteLink.source_note_id.in_(anon_note_ids)) | (NoteLink.target_note_id.in_(anon_note_ids))
            ).delete(synchronize_session=False)
            db.query(Task).filter(Task.source_note_id.in_(anon_note_ids)).update(
                {"source_note_id": None}, synchronize_session=False
            )

        anon_projects = db.query(Project.id).filter(Project.user_id.is_(None)).all()
        anon_proj_ids = [p[0] for p in anon_projects]
        if anon_proj_ids:
            db.query(Task).filter(Task.project_id.in_(anon_proj_ids)).delete(synchronize_session=False)
            db.query(Note).filter(Note.project_id.in_(anon_proj_ids)).delete(synchronize_session=False)
            db.query(Project).filter(Project.id.in_(anon_proj_ids)).delete(synchronize_session=False)

        db.query(Note).filter(Note.user_id.is_(None)).delete(synchronize_session=False)
        db.query(JournalTemplate).filter(JournalTemplate.user_id.is_(None)).delete(synchronize_session=False)
        db.query(JournalSecret).filter(JournalSecret.user_id.is_(None)).delete(synchronize_session=False)
        db.commit()

        _ensure_default_templates(db, None)

    return {"message": "All workspace data cleared successfully", "reset": True}


@app.post("/api/ocr", response_model=OcrVisionResponse)
def transcribe_handwritten_image_ocr(payload: OcrVisionRequest):
    """
    High-accuracy handwritten journal transcription using Gemini 2.5 Flash Vision API.
    """
    import httpx

    api_key = (payload.gemini_api_key or settings.GEMINI_API_KEY or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="No Gemini Vision API key configured. Provide a key or use the enhanced browser OCR scanner.",
        )

    raw_b64 = payload.image_base64.strip()
    if "," in raw_b64 and raw_b64.startswith("data:"):
        raw_b64 = raw_b64.split(",", 1)[1]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt_text = (
        "Transcribe all handwritten or printed text from this journal page accurately into clean Markdown. "
        "Preserve line breaks, paragraphs, bullet points (- ), and checkboxes (- [ ] or - [x]). "
        "Output ONLY the transcribed text without any introductory or concluding commentary."
    )
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text},
                    {
                        "inline_data": {
                            "mime_type": payload.mime_type or "image/jpeg",
                            "data": raw_b64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1},
    }

    try:
        resp = httpx.post(url, json=body, timeout=25.0)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vision OCR request failed: {exc}") from exc

    if resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail="Gemini Vision API rejected the request. Check your Gemini API key.",
        )

    data = resp.json()
    try:
        candidates = data.get("candidates") or []
        parts = candidates[0]["content"]["parts"]
        extracted = "\n".join(p.get("text", "") for p in parts if "text" in p).strip()
    except Exception:
        extracted = ""

    return OcrVisionResponse(text=extracted, engine="gemini-vision")


# ---------------------------------------------------------------------------
# Left Sidebar & Projects Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/sidebar/projects", response_model=list[SidebarProjectItem])
def get_sidebar_projects(
    status_filter: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    reference_date: date | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = _scope_projects(db.query(Project), user)
    if status_filter:
        q = q.filter(Project.status == status_filter)
    elif not include_archived:
        q = q.filter(Project.status != "archived")

    projects = q.order_by(
        Project.is_pinned.desc(),
        Project.sidebar_order.asc(),
        Project.id.asc(),
    ).all()
    return [_compute_sidebar_project_item(p, reference_date=reference_date) for p in projects]


@app.patch("/api/sidebar/projects/reorder", response_model=list[SidebarProjectItem])
def reorder_sidebar_projects(
    payload: SidebarReorderRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    for index, pid in enumerate(payload.ordered_project_ids):
        proj = _scope_projects(db.query(Project), user).filter(Project.id == pid).first()
        if proj:
            proj.sidebar_order = index
    db.commit()
    ws_manager.emit_from_sync(
        "sidebar.reordered", {"ordered_project_ids": payload.ordered_project_ids}
    )
    return get_sidebar_projects(
        status_filter=None,
        include_archived=False,
        reference_date=None,
        user=user,
        db=db,
    )


@app.post("/api/projects", response_model=SidebarProjectItem, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    base_slug = slugify(payload.slug or payload.name)
    unique_slug = _unique_project_slug(db, base_slug)

    proj = Project(
        user_id=user.id if user else None,
        name=payload.name,
        slug=unique_slug,
        description=payload.description,
        color=payload.color,
        icon=payload.icon,
        status=payload.status,
        is_pinned=payload.is_pinned,
        sidebar_order=payload.sidebar_order,
        start_date=payload.start_date,
        target_date=payload.target_date,
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    item = _compute_sidebar_project_item(proj)
    ws_manager.emit_from_sync("project.created", {"id": proj.id, "name": proj.name})
    return item


@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return (
        _scope_projects(db.query(Project), user)
        .order_by(Project.is_pinned.desc(), Project.sidebar_order.asc(), Project.id.asc())
        .all()
    )


PROJECT_KANBAN_COLUMNS: list[tuple[str, str]] = [
    ("planned", "Planned"),
    ("active", "Active"),
    ("on_hold", "On Hold"),
    ("completed", "Completed"),
]


@app.get("/api/projects-kanban", response_model=ProjectKanbanBoardResponse)
def get_projects_kanban_board(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    projects = (
        _scope_projects(db.query(Project), user)
        .filter(Project.status != "archived")
        .order_by(Project.sidebar_order.asc(), Project.is_pinned.desc(), Project.id.asc())
        .all()
    )
    grouped: dict[str, list[SidebarProjectItem]] = {
        col_key: [] for col_key, _ in PROJECT_KANBAN_COLUMNS
    }
    for proj in projects:
        bucket = proj.status if proj.status in grouped else "planned"
        grouped[bucket].append(_compute_sidebar_project_item(proj))

    columns = [
        ProjectKanbanColumn(
            status=col_key,  # type: ignore[arg-type]
            label=col_label,
            count=len(grouped[col_key]),
            projects=grouped[col_key],
        )
        for col_key, col_label in PROJECT_KANBAN_COLUMNS
    ]
    return ProjectKanbanBoardResponse(
        total_projects=len(projects),
        columns=columns,
    )


@app.patch("/api/projects-kanban/move", response_model=SidebarProjectItem)
def move_project_kanban_card(
    payload: ProjectKanbanMoveRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    proj = _scope_projects(db.query(Project), user).filter(Project.id == payload.project_id).first()
    if not proj:
        proj = db.query(Project).filter(Project.id == payload.project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    proj.status = payload.target_status
    if payload.sidebar_order is not None:
        proj.sidebar_order = payload.sidebar_order

    if payload.ordered_project_ids:
        for index, pid in enumerate(payload.ordered_project_ids):
            target = db.query(Project).filter(Project.id == pid).first()
            if target:
                target.sidebar_order = index

    db.commit()
    db.refresh(proj)
    item = _compute_sidebar_project_item(proj)
    ws_manager.emit_from_sync(
        "project.kanban_moved",
        {
            "project_id": proj.id,
            "target_status": proj.status,
            "sidebar_order": proj.sidebar_order,
        },
    )
    return item


@app.get("/api/projects/{project_id}", response_model=SidebarProjectItem)
def get_project(project_id: int, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return _compute_sidebar_project_item(proj)


@app.get("/api/projects/{project_id}/critical-path", response_model=CriticalPathOut)
def get_project_critical_path(project_id: int, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    cp_ids, cp_days = compute_critical_path(proj.tasks or [])
    return CriticalPathOut(
        project_id=proj.id,
        critical_path_task_ids=cp_ids,
        total_duration_days=cp_days,
    )


@app.patch("/api/projects/{project_id}", response_model=SidebarProjectItem)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"]:
        proj.name = update_data["name"].strip()
        base_slug = slugify(proj.name)
        proj.slug = _unique_project_slug(db, base_slug, exclude_id=proj.id)

    for field, val in update_data.items():
        if field != "name":
            setattr(proj, field, val)

    db.commit()
    db.refresh(proj)
    item = _compute_sidebar_project_item(proj)
    ws_manager.emit_from_sync("project.updated", {"id": proj.id, "name": proj.name})
    return item


@app.delete("/api/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Safely detach notes so notes are preserved
    db.query(Note).filter(Note.project_id == project_id).update({Note.project_id: None})

    # Clear task dependencies and delete tasks
    db.query(Task).filter(Task.project_id == project_id).update({Task.depends_on_id: None})
    db.query(Task).filter(Task.project_id == project_id).delete(synchronize_session=False)

    db.delete(proj)
    db.commit()
    ws_manager.emit_from_sync("project.deleted", {"id": project_id})
    return None


# ---------------------------------------------------------------------------
# Tasks, Milestones & Auto-Cascading Dependency Scheduling
# ---------------------------------------------------------------------------


@app.post("/api/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    task_user_id = user.id if user else None
    if payload.project_id is not None:
        proj = db.query(Project).filter(Project.id == payload.project_id).first()
        if not proj:
            raise HTTPException(status_code=404, detail="Parent project not found")
        if proj.user_id:
            task_user_id = proj.user_id

    if payload.depends_on_id is not None:
        dep = db.query(Task).filter(Task.id == payload.depends_on_id).first()
        if not dep:
            raise HTTPException(status_code=404, detail="Dependency task not found")
        try:
            validate_no_dependency_cycle(db, None, payload.depends_on_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    progress = 100 if payload.status == "done" else payload.progress
    task = Task(
        user_id=task_user_id,
        project_id=payload.project_id,
        source_note_id=payload.source_note_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        color=payload.color,
        start_date=payload.start_date,
        due_date=payload.due_date,
        is_milestone=payload.is_milestone,
        depends_on_id=payload.depends_on_id,
        progress=progress,
    )
    db.add(task)
    db.flush()

    # If creating a task that depends on an earlier task, auto-align start_date if needed
    cascaded_ids: list[int] = []
    if payload.cascade_dependencies and task.depends_on_id is not None:
        parent = db.query(Task).filter(Task.id == task.depends_on_id).first()
        if parent:
            cascaded = cascade_dependent_tasks(db, parent)
            cascaded_ids = [c.id for c in cascaded]

    db.commit()
    db.refresh(task)
    ws_manager.emit_from_sync(
        "task.created",
        {"id": task.id, "project_id": task.project_id, "title": task.title},
    )
    return _serialize_task(task, cascaded_ids=cascaded_ids)


@app.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(
    project_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None),
    standalone_only: bool = Query(default=False),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.query(Task).outerjoin(Project, Task.project_id == Project.id)
    if user is not None:
        q = q.filter(or_(Task.user_id == user.id, Project.user_id == user.id))
    else:
        q = q.filter(and_(Task.user_id.is_(None), Project.user_id.is_(None)))

    if standalone_only:
        q = q.filter(Task.project_id.is_(None))
    elif project_id is not None:
        q = q.filter(Task.project_id == project_id)

    if status_filter is not None:
        if status_filter == "overdue":
            today = date.today()
            q = q.filter(Task.due_date.isnot(None), Task.due_date < today, Task.status != "done")
        else:
            q = q.filter(Task.status == status_filter)

    rows = q.order_by(Task.start_date.asc(), Task.due_date.asc(), Task.id.asc()).all()
    return [_serialize_task(r) for r in rows]


@app.patch("/api/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = payload.model_dump(exclude_unset=True)
    cascade_flag = update_data.pop("cascade_dependencies", True)

    if "depends_on_id" in update_data and update_data["depends_on_id"] is not None:
        dep = db.query(Task).filter(Task.id == update_data["depends_on_id"]).first()
        if not dep:
            raise HTTPException(status_code=404, detail="Dependency task not found")
        try:
            validate_no_dependency_cycle(db, task.id, update_data["depends_on_id"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if "status" in update_data and update_data["status"] == "done" and "progress" not in update_data:
        update_data["progress"] = 100

    for field, val in update_data.items():
        setattr(task, field, val)
    db.flush()

    cascaded_ids: list[int] = []
    if cascade_flag:
        cascaded = cascade_dependent_tasks(db, task)
        cascaded_ids = [c.id for c in cascaded]

    db.commit()
    db.refresh(task)
    ws_manager.emit_from_sync(
        "task.updated",
        {
            "id": task.id,
            "project_id": task.project_id,
            "status": task.status,
            "start_date": task.start_date.isoformat() if task.start_date else None,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "cascaded_task_ids": cascaded_ids,
        },
    )
    return _serialize_task(task, cascaded_ids=cascaded_ids)


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    ws_manager.emit_from_sync("task.deleted", {"id": task_id})
    return None


# ---------------------------------------------------------------------------
# Kanban Board View Endpoints
# ---------------------------------------------------------------------------

KANBAN_COLUMNS: list[tuple[str, str]] = [
    ("todo", "To Do"),
    ("in_progress", "In Progress"),
    ("review", "In Review"),
    ("done", "Done"),
]

DEFAULT_PROGRESS_BY_STATUS = {
    "todo": 0,
    "in_progress": 50,
    "review": 85,
    "done": 100,
}


@app.get("/api/kanban", response_model=KanbanBoardResponse)
def get_kanban_board(
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Task)
    if project_id is not None:
        q = q.filter(Task.project_id == project_id)
    tasks = q.order_by(Task.due_date.asc(), Task.id.asc()).all()

    grouped: dict[str, list[TaskOut]] = {col_key: [] for col_key, _ in KANBAN_COLUMNS}
    for t in tasks:
        bucket = t.status if t.status in grouped else "todo"
        grouped[bucket].append(_serialize_task(t))

    columns = [
        KanbanColumn(
            status=col_key,  # type: ignore[arg-type]
            label=col_label,
            count=len(grouped[col_key]),
            tasks=grouped[col_key],
        )
        for col_key, col_label in KANBAN_COLUMNS
    ]
    return KanbanBoardResponse(
        project_id=project_id,
        total_tasks=len(tasks),
        columns=columns,
    )


@app.patch("/api/kanban/move", response_model=TaskOut)
def move_kanban_card(payload: KanbanMoveRequest, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == payload.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = payload.target_status
    if payload.progress is not None:
        task.progress = payload.progress
    else:
        task.progress = DEFAULT_PROGRESS_BY_STATUS.get(payload.target_status, task.progress)

    db.commit()
    db.refresh(task)
    ws_manager.emit_from_sync(
        "kanban.moved",
        {"task_id": task.id, "target_status": task.status, "progress": task.progress},
    )
    return _serialize_task(task)


# ---------------------------------------------------------------------------
# Markdown Notes Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if payload.project_id is not None:
        proj = db.query(Project).filter(Project.id == payload.project_id).first()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

    base_slug = slugify(payload.slug or payload.title)
    unique_slug = _unique_note_slug(db, base_slug)

    note = Note(
        user_id=user.id if user else None,
        project_id=payload.project_id,
        title=payload.title,
        slug=unique_slug,
        content_md=payload.content_md,
        is_pinned=payload.is_pinned,
        is_daily_note=payload.is_daily_note,
        note_date=payload.note_date or date.today(),
    )
    db.add(note)
    db.flush()

    synced_ids = _sync_note_metadata_and_tasks(
        db, note, sync_inline_tasks=payload.sync_inline_tasks
    )
    db.commit()
    db.refresh(note)
    out = _serialize_note(db, note, synced_task_ids=synced_ids)
    ws_manager.emit_from_sync(
        "note.synced",
        {"id": note.id, "slug": note.slug, "synced_task_ids": synced_ids},
    )
    return out


@app.get("/api/notes", response_model=list[NoteOut])
def list_notes(
    project_id: int | None = Query(default=None),
    tag: str | None = Query(default=None),
    daily_only: bool = Query(default=False),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = _scope_notes(db.query(Note), user)
    if project_id is not None:
        q = q.filter(Note.project_id == project_id)
    if daily_only:
        q = q.filter(Note.is_daily_note.is_(True))

    notes = q.order_by(Note.is_pinned.desc(), Note.note_date.desc(), Note.id.desc()).all()
    serialized = [_serialize_note(db, n) for n in notes]
    if tag:
        clean_tag = tag.lstrip("#").lower()
        serialized = [n for n in serialized if clean_tag in n.tags]
    return serialized


@app.get("/api/notes/{note_id}", response_model=NoteOut)
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return _serialize_note(db, note)


@app.put("/api/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: int, payload: NoteUpdate, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    update_data = payload.model_dump(exclude_unset=True)
    sync_flag = update_data.pop("sync_inline_tasks", True)

    if "title" in update_data and update_data["title"] is not None:
        note.title = update_data["title"]

    for field in ("project_id", "content_md", "is_pinned", "note_date"):
        if field in update_data:
            setattr(note, field, update_data[field])

    synced_ids = _sync_note_metadata_and_tasks(db, note, sync_inline_tasks=sync_flag)
    db.commit()
    db.refresh(note)
    out = _serialize_note(db, note, synced_task_ids=synced_ids)
    ws_manager.emit_from_sync(
        "note.synced",
        {"id": note.id, "slug": note.slug, "synced_task_ids": synced_ids},
    )
    return out


@app.delete("/api/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    ws_manager.emit_from_sync("note.deleted", {"id": note_id})
    return None


@app.post("/api/notes/daily/{note_date}", response_model=NoteOut)
def get_or_create_daily_note(
    note_date: date,
    project_id: int | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    existing = (
        _scope_notes(db.query(Note), user)
        .filter(Note.is_daily_note.is_(True), Note.note_date == note_date)
        .first()
    )
    if existing:
        return _serialize_note(db, existing)

    title = f"Daily Note - {note_date.isoformat()}"
    slug = _unique_note_slug(db, f"daily-{note_date.isoformat()}")
    template_md = (
        f"---\ndate: {note_date.isoformat()}\ntags: [daily]\n---\n\n"
        f"# {title}\n\n## Focus Today\n- [ ] Review timeline milestones @due({note_date.isoformat()})\n\n"
        f"## Meeting & Project Notes\n"
    )
    note = Note(
        user_id=user.id if user else None,
        project_id=project_id,
        title=title,
        slug=slug,
        content_md=template_md,
        is_pinned=False,
        is_daily_note=True,
        note_date=note_date,
    )
    db.add(note)
    db.flush()
    synced_ids = _sync_note_metadata_and_tasks(db, note, sync_inline_tasks=True)
    db.commit()
    db.refresh(note)
    return _serialize_note(db, note, synced_task_ids=synced_ids)


def _scope_journal_secret(q, user: User | None):
    if user is not None:
        return q.filter(JournalSecret.user_id == user.id)
    return q.filter(JournalSecret.user_id.is_(None))


def _check_journal_access(
    db: Session,
    user: User | None,
    x_journal_token: str | None = None,
) -> bool:
    """Return True if journal access is permitted (either no password set or valid session token provided)."""
    secret = _scope_journal_secret(db.query(JournalSecret), user).first()
    if not secret:
        return True
    if not x_journal_token:
        return False
    return verify_journal_session_token(x_journal_token, user.id if user else None)


@app.get("/api/journal/lock-status", response_model=JournalLockStatusOut)
def get_journal_lock_status(
    x_journal_token: str | None = Header(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    secret = _scope_journal_secret(db.query(JournalSecret), user).first()
    if not secret:
        return JournalLockStatusOut(has_password=False, is_unlocked=True)
    is_unlocked = verify_journal_session_token(x_journal_token or "", user.id if user else None)
    return JournalLockStatusOut(has_password=True, is_unlocked=is_unlocked)


@app.post("/api/journal/unlock", response_model=JournalUnlockResponse)
def unlock_journal(
    payload: JournalUnlockRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    secret = _scope_journal_secret(db.query(JournalSecret), user).first()
    if not secret:
        token = create_journal_session_token(user.id if user else None)
        return JournalUnlockResponse(success=True, journal_token=token, message="No password required")
    if not verify_password(payload.password, secret.password_hash, secret.salt):
        raise HTTPException(status_code=401, detail="Incorrect journal password")
    token = create_journal_session_token(user.id if user else None)
    return JournalUnlockResponse(success=True, journal_token=token, message="Journal unlocked")


@app.post("/api/journal/password", response_model=JournalUnlockResponse)
def set_or_change_journal_password(
    payload: JournalSetPasswordRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if not payload.password or len(payload.password.strip()) < 1:
        raise HTTPException(status_code=400, detail="Password cannot be empty")
    secret = _scope_journal_secret(db.query(JournalSecret), user).first()
    if secret:
        if not payload.current_password or not verify_password(payload.current_password, secret.password_hash, secret.salt):
            raise HTTPException(status_code=401, detail="Current journal password is incorrect")
        new_hash, new_salt = hash_password(payload.password)
        secret.password_hash = new_hash
        secret.salt = new_salt
    else:
        new_hash, new_salt = hash_password(payload.password)
        secret = JournalSecret(
            user_id=user.id if user else None,
            password_hash=new_hash,
            salt=new_salt,
        )
        db.add(secret)
    db.commit()
    token = create_journal_session_token(user.id if user else None)
    return JournalUnlockResponse(success=True, journal_token=token, message="Journal password updated")


@app.get("/api/journal", response_model=list[NoteOut])
def list_daily_journal_entries(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    x_journal_token: str | None = Header(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if not _check_journal_access(db, user, x_journal_token):
        raise HTTPException(status_code=403, detail="Journal is locked. Password required.")
    q = _scope_notes(db.query(Note), user).filter(Note.is_daily_note.is_(True))
    if year is not None and month is not None:
        start_d = date(year, month, 1)
        if month == 12:
            end_d = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_d = date(year, month + 1, 1) - timedelta(days=1)
        q = q.filter(Note.note_date >= start_d, Note.note_date <= end_d)
    elif year is not None:
        q = q.filter(
            Note.note_date >= date(year, 1, 1),
            Note.note_date <= date(year, 12, 31),
        )
    rows = q.order_by(Note.note_date.desc(), Note.id.desc()).all()
    return [_serialize_note(db, r) for r in rows]


@app.get("/api/journal/template", response_model=TemplateRenderedOut)
def get_rendered_journal_template(
    template_id: int | None = Query(default=None),
    target_date: str | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    target_dt = date.today()
    if target_date:
        try:
            target_dt = date.fromisoformat(target_date)
        except (ValueError, TypeError):
            pass
    templates = _ensure_default_templates(db, user)
    selected_tpl: JournalTemplate | None = None
    if template_id is not None:
        selected_tpl = next((t for t in templates if t.id == template_id), None)
    if not selected_tpl:
        selected_tpl = next(
            (t for t in templates if t.is_default),
            templates[0] if templates else None,
        )

    if not selected_tpl:
        raise HTTPException(status_code=404, detail="No templates found")

    habits = _scope_habits(db.query(Habit), user).filter(Habit.archived.is_(False)).all()
    rendered = _render_journal_template(selected_tpl.content_md, target_dt, habits)

    return TemplateRenderedOut(
        content_md=rendered,
        template_name=selected_tpl.name,
    )


@app.get("/api/journal/{note_date}", response_model=NoteOut)
def get_daily_journal_entry(
    note_date: date,
    x_journal_token: str | None = Header(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if not _check_journal_access(db, user, x_journal_token):
        raise HTTPException(status_code=403, detail="Journal is locked. Password required.")
    existing = (
        _scope_notes(db.query(Note), user)
        .filter(Note.is_daily_note.is_(True), Note.note_date == note_date)
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="No journal entry for this date yet")
    return _serialize_note(db, existing)


@app.put("/api/journal/{note_date}", response_model=NoteOut)
def upsert_daily_journal_entry(
    note_date: date,
    payload: JournalUpsertRequest,
    x_journal_token: str | None = Header(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if not _check_journal_access(db, user, x_journal_token):
        raise HTTPException(status_code=403, detail="Journal is locked. Password required.")
    existing = (
        _scope_notes(db.query(Note), user)
        .filter(Note.is_daily_note.is_(True), Note.note_date == note_date)
        .first()
    )
    default_title = f"Journal — {note_date.isoformat()}"
    if existing:
        if payload.title is not None and payload.title.strip():
            existing.title = payload.title.strip()
        existing.content_md = payload.content_md
        if payload.project_id is not None:
            existing.project_id = payload.project_id
        note = existing
    else:
        title = (payload.title or default_title).strip() or default_title
        slug = _unique_note_slug(db, f"journal-{note_date.isoformat()}")
        note = Note(
            user_id=user.id if user else None,
            project_id=payload.project_id,
            title=title,
            slug=slug,
            content_md=payload.content_md,
            is_pinned=False,
            is_daily_note=True,
            note_date=note_date,
        )
        db.add(note)
        db.flush()

    synced_ids = _sync_note_metadata_and_tasks(
        db, note, sync_inline_tasks=payload.sync_inline_tasks
    )
    db.commit()
    db.refresh(note)
    out = _serialize_note(db, note, synced_task_ids=synced_ids)
    ws_manager.emit_from_sync(
        "note.synced",
        {"id": note.id, "slug": note.slug, "synced_task_ids": synced_ids},
    )
    return out


# ---------------------------------------------------------------------------
# Habits, Habit Logs & Analytics Endpoints (Phase 1)
# ---------------------------------------------------------------------------


@app.get("/api/habits", response_model=list[HabitOut])
def list_habits(
    include_archived: bool = Query(default=False),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = _scope_habits(db.query(Habit), user)
    if not include_archived:
        q = q.filter(Habit.archived.is_(False))
    rows = q.order_by(Habit.id.asc()).all()
    return [_serialize_habit(db, r, user) for r in rows]


@app.post("/api/habits", response_model=HabitOut, status_code=201)
def create_habit(
    payload: HabitCreate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    slug_val = slugify(payload.slug or payload.name)
    existing = _scope_habits(db.query(Habit), user).filter(Habit.slug == slug_val).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A habit with slug '{slug_val}' already exists.",
        )

    habit = Habit(
        user_id=user.id if user else None,
        slug=slug_val,
        name=payload.name.strip(),
        description=payload.description.strip(),
        icon=payload.icon.strip() or "check",
        color=payload.color.strip() or "#10b981",
        target_days_per_week=payload.target_days_per_week,
        archived=False,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    ws_manager.emit_from_sync(
        "habit.created",
        {"id": habit.id, "slug": habit.slug, "name": habit.name},
    )
    return _serialize_habit(db, habit, user)


@app.patch("/api/habits/{habit_id}", response_model=HabitOut)
def update_habit(
    habit_id: int,
    payload: HabitUpdate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    habit = _scope_habits(db.query(Habit), user).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    if payload.name is not None:
        habit.name = payload.name.strip()
    if payload.slug is not None and payload.slug.strip():
        new_slug = slugify(payload.slug.strip())
        existing = db.query(Habit).filter(Habit.slug == new_slug, Habit.id != habit.id).first()
        if not existing:
            habit.slug = new_slug
    if payload.description is not None:
        habit.description = payload.description.strip()
    if payload.icon is not None:
        habit.icon = payload.icon.strip()
    if payload.color is not None:
        habit.color = payload.color.strip()
    if payload.target_days_per_week is not None:
        habit.target_days_per_week = payload.target_days_per_week
    if payload.archived is not None:
        habit.archived = payload.archived

    db.commit()
    db.refresh(habit)
    ws_manager.emit_from_sync("habit.updated", {"id": habit.id, "slug": habit.slug})
    return _serialize_habit(db, habit, user)


@app.delete("/api/habits/{habit_id}")
def delete_habit(
    habit_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    habit = _scope_habits(db.query(Habit), user).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    db.delete(habit)
    db.commit()
    ws_manager.emit_from_sync("habit.deleted", {"id": habit_id})
    return {"status": "deleted", "id": habit_id}


@app.post("/api/habits/{habit_id}/toggle", response_model=HabitLogOut)
def toggle_habit(
    habit_id: int,
    payload: HabitToggleRequest | None = None,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    habit = _scope_habits(db.query(Habit), user).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    target_date = (payload.log_date if payload and payload.log_date else None) or date.today()
    log_q = db.query(HabitLog).filter(
        HabitLog.habit_id == habit.id,
        HabitLog.log_date == target_date,
    )
    if user:
        log_q = log_q.filter(HabitLog.user_id == user.id)
    else:
        log_q = log_q.filter(HabitLog.user_id.is_(None))

    habit_log = log_q.first()
    new_completed = (
        payload.completed
        if payload and payload.completed is not None
        else (not habit_log.completed if habit_log else True)
    )
    val = (
        payload.value
        if payload and payload.value is not None
        else (habit_log.value if habit_log else None)
    )

    note = (
        _scope_notes(db.query(Note), user)
        .filter(Note.is_daily_note.is_(True), Note.note_date == target_date)
        .first()
    )
    note_id = note.id if note else None

    if habit_log:
        habit_log.completed = new_completed
        habit_log.value = val
        if note_id:
            habit_log.note_id = note_id
    else:
        habit_log = HabitLog(
            habit_id=habit.id,
            user_id=user.id if user else None,
            note_id=note_id,
            log_date=target_date,
            completed=new_completed,
            value=val,
        )
        db.add(habit_log)

    if note and note.content_md:
        pattern = re.compile(
            rf"^([ \t]*[-*][ \t]+\[)([ xX])(\][ \t]+.*@habit\({re.escape(habit.slug)}[,\)].*)$",
            re.MULTILINE | re.IGNORECASE,
        )
        new_mark = "x" if new_completed else " "
        updated_content = pattern.sub(rf"\g<1>{new_mark}\g<3>", note.content_md)
        if updated_content != note.content_md:
            note.content_md = updated_content
            db.flush()

    db.commit()
    db.refresh(habit_log)
    ws_manager.emit_from_sync(
        "habit.toggled",
        {
            "habit_id": habit.id,
            "slug": habit.slug,
            "log_date": target_date.isoformat(),
            "completed": new_completed,
        },
    )
    return habit_log


@app.get("/api/analytics/habits", response_model=HabitAnalyticsOut)
def get_habit_analytics(
    days_count: int = Query(default=364, ge=7, le=730),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    start_date = today - timedelta(days=days_count - 1)

    habits = _scope_habits(db.query(Habit), user).filter(Habit.archived.is_(False)).all()
    habit_ids = [h.id for h in habits]
    habit_slug_map = {h.id: h.slug for h in habits}

    if habit_ids:
        logs_q = db.query(HabitLog).filter(
            HabitLog.habit_id.in_(habit_ids),
            HabitLog.log_date >= start_date,
            HabitLog.log_date <= today,
            HabitLog.completed.is_(True),
        )
        if user:
            logs_q = logs_q.filter(HabitLog.user_id == user.id)
        else:
            logs_q = logs_q.filter(HabitLog.user_id.is_(None))
        logs = logs_q.all()
    else:
        logs = []

    day_logs_map: dict[str, set[str]] = {}
    for log in logs:
        iso_str = log.log_date.isoformat()
        slug = habit_slug_map.get(log.habit_id)
        if slug:
            day_logs_map.setdefault(iso_str, set()).add(slug)

    total_h = len(habits)
    days_out: list[HabitHeatmapDay] = []
    curr = start_date
    total_rate_sum = 0.0

    while curr <= today:
        iso = curr.isoformat()
        completed_slugs = day_logs_map.get(iso, set())
        completed_count = len(completed_slugs)
        rate = round(completed_count / total_h, 3) if total_h > 0 else 0.0
        total_rate_sum += rate
        h_status = {h.slug: (h.slug in completed_slugs) for h in habits}

        days_out.append(
            HabitHeatmapDay(
                date=iso,
                total_habits=total_h,
                completed_count=completed_count,
                rate=rate,
                habits=h_status,
            )
        )
        curr += timedelta(days=1)

    habit_streaks = [_serialize_habit(db, h, user, today).model_dump() for h in habits]
    best_streak = max([h["current_streak"] for h in habit_streaks], default=0)
    best_longest = max([h["longest_streak"] for h in habit_streaks], default=0)
    today_completed = len(day_logs_map.get(today.isoformat(), set()))

    overall_stats = {
        "total_habits": total_h,
        "today_completed": today_completed,
        "best_current_streak": best_streak,
        "best_longest_streak": best_longest,
        "average_completion_rate": (
            round((total_rate_sum / len(days_out)) * 100, 1) if days_out else 0.0
        ),
    }

    return HabitAnalyticsOut(
        days=days_out,
        overall_stats=overall_stats,
        habit_streaks=habit_streaks,
    )


# ---------------------------------------------------------------------------
# Journal Templates Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/templates", response_model=list[TemplateOut])
def list_journal_templates(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    rows = _ensure_default_templates(db, user)
    return rows


@app.post("/api/templates", response_model=TemplateOut, status_code=201)
def create_journal_template(
    payload: TemplateCreate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if payload.is_default:
        q = db.query(JournalTemplate)
        if user:
            q = q.filter(JournalTemplate.user_id == user.id)
        else:
            q = q.filter(JournalTemplate.user_id.is_(None))
        q.update({"is_default": False})

    tpl = JournalTemplate(
        user_id=user.id if user else None,
        name=payload.name.strip(),
        description=payload.description.strip(),
        content_md=payload.content_md,
        is_default=payload.is_default,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@app.put("/api/templates/{template_id}", response_model=TemplateOut)
def update_journal_template(
    template_id: int,
    payload: TemplateUpdate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.query(JournalTemplate).filter(JournalTemplate.id == template_id)
    if user:
        q = q.filter(JournalTemplate.user_id == user.id)
    else:
        q = q.filter(JournalTemplate.user_id.is_(None))
    tpl = q.first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    if payload.is_default is True:
        def_q = db.query(JournalTemplate)
        if user:
            def_q = def_q.filter(JournalTemplate.user_id == user.id)
        else:
            def_q = def_q.filter(JournalTemplate.user_id.is_(None))
        def_q.update({"is_default": False})
        tpl.is_default = True
    elif payload.is_default is False:
        tpl.is_default = False

    if payload.name is not None:
        tpl.name = payload.name.strip()
    if payload.description is not None:
        tpl.description = payload.description.strip()
    if payload.content_md is not None:
        tpl.content_md = payload.content_md

    db.commit()
    db.refresh(tpl)
    return tpl


@app.delete("/api/templates/{template_id}")
def delete_journal_template(
    template_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.query(JournalTemplate).filter(JournalTemplate.id == template_id)
    if user:
        q = q.filter(JournalTemplate.user_id == user.id)
    else:
        q = q.filter(JournalTemplate.user_id.is_(None))
    tpl = q.first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(tpl)
    db.commit()
    return {"message": "Template deleted successfully", "id": template_id}


# ---------------------------------------------------------------------------
# Study Mode & Pomodoro Endpoints
# ---------------------------------------------------------------------------


def _serialize_study_session(session: StudySession) -> StudySessionOut:
    return StudySessionOut(
        id=session.id,
        user_id=session.user_id,
        project_id=session.project_id,
        task_id=session.task_id,
        note_id=session.note_id,
        duration_minutes=session.duration_minutes,
        session_type=session.session_type,
        intention=session.intention,
        notes=session.notes,
        session_date=session.session_date,
        completed=session.completed,
        created_at=session.created_at,
        project_name=session.project.name if session.project else None,
        project_color=session.project.color if session.project else None,
        task_title=session.task.title if session.task else None,
    )


@app.post("/api/study/sessions", response_model=StudySessionOut, status_code=201)
def create_study_session(
    payload: StudySessionCreate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    s_date = payload.session_date or date.today()
    project = None
    if payload.project_id:
        pq = db.query(Project).filter(Project.id == payload.project_id)
        if user:
            pq = pq.filter(Project.user_id == user.id)
        else:
            pq = pq.filter(Project.user_id.is_(None))
        project = pq.first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    task = None
    if payload.task_id:
        tq = db.query(Task).filter(Task.id == payload.task_id)
        task = tq.first()

    note = None
    if payload.note_id:
        nq = db.query(Note).filter(Note.id == payload.note_id)
        if user:
            nq = nq.filter(Note.user_id == user.id)
        else:
            nq = nq.filter(Note.user_id.is_(None))
        note = nq.first()

    session = StudySession(
        user_id=user.id if user else None,
        project_id=project.id if project else None,
        task_id=task.id if task else None,
        note_id=note.id if note else None,
        duration_minutes=payload.duration_minutes,
        session_type=payload.session_type,
        intention=payload.intention.strip(),
        notes=payload.notes.strip(),
        session_date=s_date,
        completed=payload.completed,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Auto-log to daily journal if requested
    if payload.auto_log_to_journal and payload.completed and payload.session_type == "focus":
        dn_q = db.query(Note).filter(Note.is_daily_note == True, Note.note_date == s_date)
        if user:
            dn_q = dn_q.filter(Note.user_id == user.id)
        else:
            dn_q = dn_q.filter(Note.user_id.is_(None))
        daily_note = dn_q.first()
        if not daily_note:
            d_str = s_date.isoformat()
            daily_note = Note(
                user_id=user.id if user else None,
                title=f"Journal - {d_str}",
                slug=slugify(f"journal-{d_str}-{user.id if user else 'demo'}"),
                content_md=f"# Journal — {d_str}\n\n",
                is_daily_note=True,
                note_date=s_date,
            )
            db.add(daily_note)
            db.commit()
            db.refresh(daily_note)

        proj_label = f"[[{project.name}]]" if project else "Study Session"
        task_label = f" ({task.title})" if task else ""
        intent_label = f": {payload.intention.strip()}" if payload.intention.strip() else ""
        bullet = f"- [x] 🍅 Focus ({payload.duration_minutes}m) on {proj_label}{task_label}{intent_label}"

        if bullet not in (daily_note.content_md or ""):
            new_content = (daily_note.content_md or "").rstrip() + f"\n{bullet}\n"
            daily_note.content_md = new_content
            parsed = parse_markdown_note(new_content)
            daily_note.frontmatter_json = json.dumps(parsed.frontmatter)
            daily_note.tags_json = json.dumps(parsed.tags)
            db.commit()

    # Sync habit if slug matches
    target_slug = payload.sync_habit_slug or "study"
    hq = db.query(Habit).filter(
        Habit.archived == False,
        (Habit.slug == target_slug) | (Habit.slug == "deep-work") | (Habit.slug == "focus"),
    )
    if user:
        hq = hq.filter(Habit.user_id == user.id)
    else:
        hq = hq.filter(Habit.user_id.is_(None))
    matched_habit = hq.first()
    if matched_habit and payload.completed and payload.session_type == "focus":
        log_q = db.query(HabitLog).filter(
            HabitLog.habit_id == matched_habit.id,
            HabitLog.log_date == s_date,
        )
        if user:
            log_q = log_q.filter(HabitLog.user_id == user.id)
        else:
            log_q = log_q.filter(HabitLog.user_id.is_(None))
        h_log = log_q.first()
        if not h_log:
            h_log = HabitLog(
                habit_id=matched_habit.id,
                user_id=user.id if user else None,
                log_date=s_date,
                completed=True,
                value=f"{payload.duration_minutes}m",
            )
            db.add(h_log)
            db.commit()

    return _serialize_study_session(session)


@app.get("/api/study/sessions", response_model=list[StudySessionOut])
def list_study_sessions(
    project_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.query(StudySession)
    if user:
        q = q.filter(StudySession.user_id == user.id)
    else:
        q = q.filter(StudySession.user_id.is_(None))
    if project_id is not None:
        q = q.filter(StudySession.project_id == project_id)
    rows = q.order_by(StudySession.created_at.desc()).limit(limit).all()
    return [_serialize_study_session(r) for r in rows]


@app.get("/api/study/stats", response_model=StudyStatsOut)
def get_study_stats(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.query(StudySession).filter(
        StudySession.completed == True,
        StudySession.session_type == "focus",
    )
    if user:
        q = q.filter(StudySession.user_id == user.id)
    else:
        q = q.filter(StudySession.user_id.is_(None))
    all_sessions = q.order_by(StudySession.created_at.desc()).all()

    today = date.today()
    total_minutes = sum(s.duration_minutes for s in all_sessions)
    today_sessions = [s for s in all_sessions if s.session_date == today]
    today_minutes = sum(s.duration_minutes for s in today_sessions)
    today_count = len(today_sessions)

    # Project breakdown
    proj_map: dict[int | None, dict[str, Any]] = {}
    for s in all_sessions:
        pid = s.project_id
        if pid not in proj_map:
            p_name = s.project.name if s.project else "General Study"
            p_color = s.project.color if s.project else "#6366f1"
            proj_map[pid] = {
                "project_id": pid,
                "project_name": p_name,
                "project_color": p_color,
                "minutes": 0,
                "session_count": 0,
            }
        proj_map[pid]["minutes"] += s.duration_minutes
        proj_map[pid]["session_count"] += 1

    project_breakdown = sorted(proj_map.values(), key=lambda x: x["minutes"], reverse=True)

    # Streak calculation
    active_dates = {s.session_date for s in all_sessions}
    streak = 0
    check_date = today
    while check_date in active_dates:
        streak += 1
        check_date = check_date - timedelta(days=1)

    recent_serialized = [_serialize_study_session(s) for s in all_sessions[:10]]

    return StudyStatsOut(
        total_focus_minutes=total_minutes,
        today_focus_minutes=today_minutes,
        today_sessions_count=today_count,
        current_streak_days=streak,
        project_breakdown=project_breakdown,
        recent_sessions=recent_serialized,
    )


@app.delete("/api/study/sessions/{session_id}")
def delete_study_session(
    session_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.query(StudySession).filter(StudySession.id == session_id)
    if user:
        q = q.filter(StudySession.user_id == user.id)
    else:
        q = q.filter(StudySession.user_id.is_(None))
    session = q.first()
    if not session:
        raise HTTPException(status_code=404, detail="Study session not found")
    db.delete(session)
    db.commit()
    return {"message": "Study session deleted successfully", "id": session_id}


# ---------------------------------------------------------------------------
# Custom Stickers & Placements (Calendar & Notes)
# ---------------------------------------------------------------------------

PRESET_STICKERS = [
    {
        "name": "Coffee Cup",
        "category": "lifestyle",
        "image_url": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='46' fill='%23fef3c7' stroke='%23d97706' stroke-width='4'/><text x='50' y='64' font-size='46' text-anchor='middle'>☕</text></svg>",
    },
    {
        "name": "Gold Star",
        "category": "achievement",
        "image_url": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='46' fill='%23fef9c3' stroke='%23eab308' stroke-width='4'/><text x='50' y='64' font-size='46' text-anchor='middle'>⭐</text></svg>",
    },
    {
        "name": "Study Books",
        "category": "study",
        "image_url": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='46' fill='%23e0e7ff' stroke='%236366f1' stroke-width='4'/><text x='50' y='64' font-size='46' text-anchor='middle'>📚</text></svg>",
    },
    {
        "name": "Deep Focus",
        "category": "study",
        "image_url": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='46' fill='%23fee2e2' stroke='%23ef4444' stroke-width='4'/><text x='50' y='64' font-size='46' text-anchor='middle'>🍅</text></svg>",
    },
    {
        "name": "Nature Leaf",
        "category": "lifestyle",
        "image_url": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='46' fill='%23dcfce7' stroke='%2316a34a' stroke-width='4'/><text x='50' y='64' font-size='46' text-anchor='middle'>🌿</text></svg>",
    },
    {
        "name": "Milestone Trophy",
        "category": "achievement",
        "image_url": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='46' fill='%23ffedd5' stroke='%23ea580c' stroke-width='4'/><text x='50' y='64' font-size='46' text-anchor='middle'>🏆</text></svg>",
    },
    {
        "name": "Inspiration Light",
        "category": "study",
        "image_url": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='46' fill='%23fef08a' stroke='%23ca8a04' stroke-width='4'/><text x='50' y='64' font-size='46' text-anchor='middle'>💡</text></svg>",
    },
    {
        "name": "Target Goal",
        "category": "achievement",
        "image_url": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='46' fill='%23fce7f3' stroke='%23db2777' stroke-width='4'/><text x='50' y='64' font-size='46' text-anchor='middle'>🎯</text></svg>",
    },
]


def _ensure_default_stickers(db: Session, user: User | None) -> list[Sticker]:
    q = db.query(Sticker)
    if user:
        q = q.filter(Sticker.user_id == user.id)
    else:
        q = q.filter(Sticker.user_id.is_(None))
    existing = q.all()
    if existing:
        return existing

    created = []
    for s_info in PRESET_STICKERS:
        stk = Sticker(
            user_id=user.id if user else None,
            name=s_info["name"],
            category=s_info["category"],
            image_url=s_info["image_url"],
        )
        db.add(stk)
        created.append(stk)
    db.commit()
    for stk in created:
        db.refresh(stk)
    return created


@app.get("/api/stickers", response_model=list[StickerOut])
def list_stickers(
    category: str | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    stickers = _ensure_default_stickers(db, user)
    if category:
        stickers = [s for s in stickers if s.category == category]
    return stickers


@app.post("/api/stickers", response_model=StickerOut, status_code=201)
def upload_sticker(
    payload: StickerCreate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    stk = Sticker(
        user_id=user.id if user else None,
        name=payload.name.strip(),
        category=payload.category.strip() or "custom",
        image_url=payload.image_url.strip(),
    )
    db.add(stk)
    db.commit()
    db.refresh(stk)
    return stk


@app.delete("/api/stickers/{sticker_id}")
def delete_sticker(
    sticker_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.query(Sticker).filter(Sticker.id == sticker_id)
    if user:
        q = q.filter(Sticker.user_id == user.id)
    else:
        q = q.filter(Sticker.user_id.is_(None))
    stk = q.first()
    if not stk:
        raise HTTPException(status_code=404, detail="Sticker not found")
    db.delete(stk)
    db.commit()
    return {"message": "Sticker deleted successfully", "id": sticker_id}


@app.get("/api/stickers/placements", response_model=list[StickerPlacementOut])
def list_sticker_placements(
    target_type: str | None = Query(default=None),
    target_key: str | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.query(StickerPlacement)
    if user:
        q = q.filter(StickerPlacement.user_id == user.id)
    else:
        q = q.filter(StickerPlacement.user_id.is_(None))
    if target_type:
        q = q.filter(StickerPlacement.target_type == target_type)
    if target_key:
        q = q.filter(StickerPlacement.target_key == target_key)
    return q.order_by(StickerPlacement.created_at.asc()).all()


@app.post("/api/stickers/placements", response_model=StickerPlacementOut, status_code=201)
def create_sticker_placement(
    payload: StickerPlacementCreate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    placement = StickerPlacement(
        user_id=user.id if user else None,
        sticker_id=payload.sticker_id,
        sticker_name=payload.sticker_name,
        image_url=payload.image_url,
        target_type=payload.target_type,
        target_key=payload.target_key,
        pos_x=payload.pos_x,
        pos_y=payload.pos_y,
        rotation_deg=payload.rotation_deg,
        scale=payload.scale,
    )
    db.add(placement)
    db.commit()
    db.refresh(placement)
    return placement


@app.patch("/api/stickers/placements/{placement_id}", response_model=StickerPlacementOut)
def update_sticker_placement(
    placement_id: int,
    payload: StickerPlacementUpdate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.query(StickerPlacement).filter(StickerPlacement.id == placement_id)
    if user:
        q = q.filter(StickerPlacement.user_id == user.id)
    else:
        q = q.filter(StickerPlacement.user_id.is_(None))
    placement = q.first()
    if not placement:
        raise HTTPException(status_code=404, detail="Sticker placement not found")

    if payload.pos_x is not None:
        placement.pos_x = payload.pos_x
    if payload.pos_y is not None:
        placement.pos_y = payload.pos_y
    if payload.rotation_deg is not None:
        placement.rotation_deg = payload.rotation_deg
    if payload.scale is not None:
        placement.scale = payload.scale

    db.commit()
    db.refresh(placement)
    return placement


@app.delete("/api/stickers/placements/{placement_id}")
def delete_sticker_placement(
    placement_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    q = db.query(StickerPlacement).filter(StickerPlacement.id == placement_id)
    if user:
        q = q.filter(StickerPlacement.user_id == user.id)
    else:
        q = q.filter(StickerPlacement.user_id.is_(None))
    placement = q.first()
    if not placement:
        raise HTTPException(status_code=404, detail="Sticker placement not found")
    db.delete(placement)
    db.commit()
    return {"message": "Sticker placement removed", "id": placement_id}


# ---------------------------------------------------------------------------
# Docs-Style Uploadable Images Engine (Inline, Wrap, Above Text / Draggable)
# ---------------------------------------------------------------------------

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/uploads/images", response_model=ImageUploadResponse)
def upload_journal_image(
    payload: ImageUploadRequest,
    user: User | None = Depends(get_optional_user),
):
    """Save an image uploaded for notes/journal and return its URL and layout mode."""
    clean_filename = re.sub(r"[^a-zA-Z0-9_\.-]", "_", payload.filename) or "image.png"
    timestamp_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
    stored_filename = f"{timestamp_prefix}_{clean_filename}"
    file_path = UPLOADS_DIR / stored_filename

    raw_data = payload.image_data.strip()
    if raw_data.startswith("data:") and ";base64," in raw_data:
        _, b64_str = raw_data.split(";base64,", 1)
        import base64
        try:
            file_bytes = base64.b64decode(b64_str)
            file_path.write_bytes(file_bytes)
            url = f"/api/uploads/images/{stored_filename}"
        except Exception:
            url = raw_data
    else:
        url = raw_data

    return ImageUploadResponse(
        url=url,
        filename=payload.filename,
        mode=payload.mode or "inline",
        pos_x=50,
        pos_y=20,
        width=320,
    )


@app.get("/api/uploads/images/{filename}")
def serve_uploaded_image(filename: str):
    clean_filename = Path(filename).name
    target = UPLOADS_DIR / clean_filename
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path=str(target))





# ---------------------------------------------------------------------------
# Knowledge Graph View Endpoint (Projects + Notes + Tags + WikiLinks)
# ---------------------------------------------------------------------------


@app.get("/api/graph", response_model=KnowledgeGraphResponse)
def get_knowledge_graph(
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    seen_node_ids: set[str] = set()

    proj_q = db.query(Project)
    if project_id is not None:
        proj_q = proj_q.filter(Project.id == project_id)
    projects = proj_q.all()

    for p in projects:
        pid_str = f"project:{p.id}"
        seen_node_ids.add(pid_str)
        nodes.append(
            GraphNode(
                id=pid_str,
                kind="project",
                label=p.name,
                color=p.color,
                entity_id=p.id,
                slug=p.slug,
            )
        )

    note_q = db.query(Note)
    if project_id is not None:
        note_q = note_q.filter(Note.project_id == project_id)
    notes = note_q.all()

    slug_to_note_node: dict[str, str] = {}
    for n in notes:
        nid_str = f"note:{n.id}"
        seen_node_ids.add(nid_str)
        slug_to_note_node[n.slug] = nid_str
        nodes.append(
            GraphNode(
                id=nid_str,
                kind="note",
                label=n.title,
                color="#38bdf8" if not n.is_daily_note else "#f59e0b",
                entity_id=n.id,
                slug=n.slug,
            )
        )
        if n.project_id is not None and f"project:{n.project_id}" in seen_node_ids:
            edges.append(
                GraphEdge(
                    source=nid_str,
                    target=f"project:{n.project_id}",
                    relation="belongs_to",
                    label="project",
                )
            )
        for tag in json.loads(n.tags_json or "[]"):
            tid_str = f"tag:{tag}"
            if tid_str not in seen_node_ids:
                seen_node_ids.add(tid_str)
                nodes.append(
                    GraphNode(
                        id=tid_str,
                        kind="tag",
                        label=f"#{tag}",
                        color="#a855f7",
                        slug=tag,
                    )
                )
            edges.append(
                GraphEdge(
                    source=nid_str,
                    target=tid_str,
                    relation="tagged",
                    label=f"#{tag}",
                )
            )

    links = db.query(NoteLink).all()
    for link in links:
        src_str = f"note:{link.source_note_id}"
        if src_str not in seen_node_ids:
            continue
        if link.target_note_id and f"note:{link.target_note_id}" in seen_node_ids:
            dst_str = f"note:{link.target_note_id}"
        elif link.target_slug in slug_to_note_node:
            dst_str = slug_to_note_node[link.target_slug]
        else:
            # Represent unresolved forward WikiLink as a ghost note node
            dst_str = f"note_slug:{link.target_slug}"
            if dst_str not in seen_node_ids:
                seen_node_ids.add(dst_str)
                nodes.append(
                    GraphNode(
                        id=dst_str,
                        kind="note",
                        label=link.display_text,
                        color="#64748b",
                        slug=link.target_slug,
                    )
                )
        edges.append(
            GraphEdge(
                source=src_str,
                target=dst_str,
                relation="wikilink",
                label=link.display_text,
            )
        )

    return KnowledgeGraphResponse(nodes=nodes, edges=edges)


# ---------------------------------------------------------------------------
# Unified Timeline View Endpoint (Projects Left Sidebar + Swimlanes + Critical Path)
# ---------------------------------------------------------------------------


def _overlaps_window(
    item_start: date | None,
    item_end: date | None,
    window_start: date,
    window_end: date,
) -> bool:
    eff_start = item_start or item_end
    eff_end = item_end or item_start
    if eff_start is None or eff_end is None:
        return True
    return eff_start <= window_end and eff_end >= window_start


@app.get("/api/timeline", response_model=TimelineResponse)
def get_timeline_view(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    project_ids: list[int] | None = Query(default=None),
    pinned_only: bool = Query(default=False),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    win_start = start_date or (date.today() - timedelta(days=7))
    win_end = end_date or (win_start + timedelta(days=30))
    if win_end < win_start:
        raise HTTPException(status_code=400, detail="end_date must be >= start_date")

    total_days = (win_end - win_start).days + 1

    proj_query = db.query(Project)
    if not include_archived:
        proj_query = proj_query.filter(Project.status != "archived")
    if pinned_only:
        proj_query = proj_query.filter(Project.is_pinned.is_(True))
    if project_ids:
        proj_query = proj_query.filter(Project.id.in_(project_ids))

    projects = proj_query.order_by(
        Project.is_pinned.desc(),
        Project.sidebar_order.asc(),
        Project.id.asc(),
    ).all()

    swimlanes: list[TimelineSwimlane] = []
    dependencies: list[TimelineDependencyEdge] = []

    for proj in projects:
        sidebar_item = _compute_sidebar_project_item(proj, reference_date=win_start)
        regular_tasks: list[TaskOut] = []
        milestones: list[TaskOut] = []

        cp_ids, cp_days = compute_critical_path(proj.tasks or [])

        sorted_tasks = sorted(
            proj.tasks,
            key=lambda t: (
                t.start_date or t.due_date or date.max,
                t.due_date or date.max,
                t.id,
            ),
        )
        for t in sorted_tasks:
            if _overlaps_window(t.start_date, t.due_date, win_start, win_end):
                t_out = _serialize_task(t)
                if t.is_milestone:
                    milestones.append(t_out)
                else:
                    regular_tasks.append(t_out)

            if t.depends_on_id is not None:
                dependencies.append(
                    TimelineDependencyEdge(
                        from_task_id=t.depends_on_id,
                        to_task_id=t.id,
                        project_id=proj.id,
                    )
                )

        note_pins: list[TimelineNotePin] = []
        for n in proj.notes:
            if n.note_date and win_start <= n.note_date <= win_end:
                note_pins.append(
                    TimelineNotePin(
                        note_id=n.id,
                        title=n.title,
                        slug=n.slug,
                        note_date=n.note_date,
                        is_daily_note=n.is_daily_note,
                        tags=json.loads(n.tags_json or "[]"),
                    )
                )

        swimlanes.append(
            TimelineSwimlane(
                project=sidebar_item,
                tasks=regular_tasks,
                milestones=milestones,
                note_pins=note_pins,
                critical_path_task_ids=cp_ids,
                critical_path_days=cp_days,
            )
        )

    daily_note_rows = (
        db.query(Note)
        .filter(
            Note.is_daily_note.is_(True),
            Note.note_date >= win_start,
            Note.note_date <= win_end,
        )
        .order_by(Note.note_date.asc())
        .all()
    )
    daily_notes = [
        TimelineNotePin(
            note_id=n.id,
            title=n.title,
            slug=n.slug,
            note_date=n.note_date,
            is_daily_note=True,
            tags=json.loads(n.tags_json or "[]"),
        )
        for n in daily_note_rows
        if n.note_date is not None
    ]

    return TimelineResponse(
        window_start=win_start,
        window_end=win_end,
        total_days=total_days,
        swimlanes=swimlanes,
        daily_notes=daily_notes,
        dependencies=dependencies,
    )


# ---------------------------------------------------------------------------
# Unified Search (Command Palette Ctrl+K)
# ---------------------------------------------------------------------------


@app.get("/api/search", response_model=list[SearchResultItem])
def unified_search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    term = q.strip().lower()
    like_pattern = f"%{term}%"
    results: list[SearchResultItem] = []

    for p in db.query(Project).filter(
        or_(Project.name.ilike(like_pattern), Project.description.ilike(like_pattern))
    ).all():
        results.append(
            SearchResultItem(
                kind="project",
                id=p.id,
                title=p.name,
                subtitle=f"Project ({p.status})",
                project_id=p.id,
                slug=p.slug,
            )
        )

    for n in db.query(Note).filter(
        or_(
            Note.title.ilike(like_pattern),
            Note.content_md.ilike(like_pattern),
            Note.tags_json.ilike(like_pattern),
        )
    ).all():
        tags = json.loads(n.tags_json or "[]")
        results.append(
            SearchResultItem(
                kind="note",
                id=n.id,
                title=n.title,
                subtitle=f"Markdown Note ({n.note_date.isoformat() if n.note_date else 'undated'})",
                project_id=n.project_id,
                slug=n.slug,
                matched_tags=tags,
            )
        )

    for t in db.query(Task).filter(
        or_(Task.title.ilike(like_pattern), Task.description.ilike(like_pattern))
    ).all():
        results.append(
            SearchResultItem(
                kind="task",
                id=t.id,
                title=t.title,
                subtitle=f"Task ({t.status}, priority: {t.priority})",
                project_id=t.project_id,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Real-Time Collaboration WebSocket & Event Stream
# ---------------------------------------------------------------------------


@app.get("/api/ws/events")
def get_recent_ws_events():
    return {"events": list(ws_manager.recent_events)}


@app.websocket("/ws/workspace")
async def workspace_websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "event": "workspace.connected",
                "payload": {"active_clients": len(ws_manager.active_connections)},
            }
        )
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "ping")
            if action == "ping":
                await websocket.send_json({"event": "pong", "payload": data.get("payload", {})})
            else:
                await ws_manager.broadcast(
                    f"client.{action}",
                    data.get("payload", {}),
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Demo Seed Endpoint (Populates Rich Projects, Tasks, Dependencies & Notes)
# ---------------------------------------------------------------------------


@app.post("/api/seed")
def seed_demo_workspace(db: Session = Depends(get_db)):
    if db.query(Project).count() > 0:
        return {"status": "already_seeded", "projects": db.query(Project).count()}

    p_shared = Project(
        name="Everyone",
        slug="everyone-shared-gates",
        description="Shared release gates, end-to-end integration & demo freeze",
        color="#f97316",
        is_pinned=True,
        sidebar_order=0,
        start_date=date(2026, 11, 1),
        target_date=date(2026, 11, 8),
    )
    p1 = Project(
        name="Core Engine",
        slug="chrononote-core-engine",
        description="FastAPI + PostgreSQL backend & Markdown parser",
        color="#ea580c",
        is_pinned=True,
        sidebar_order=1,
        start_date=date(2026, 11, 1),
        target_date=date(2026, 11, 8),
    )
    p2 = Project(
        name="Roadmap & Timeline UI",
        slug="vue3-timeline-kanban-ui",
        description="Left sidebar, day-column matrix, Kanban & SVG graph",
        color="#0891b2",
        is_pinned=False,
        sidebar_order=2,
        start_date=date(2026, 11, 1),
        target_date=date(2026, 11, 8),
    )
    p3 = Project(
        name="Markdown & Sync",
        slug="markdown-wikilink-sync",
        description="Bidirectional [[WikiLinks]], YAML frontmatter & live WebSockets",
        color="#06b6d4",
        is_pinned=False,
        sidebar_order=3,
        start_date=date(2026, 11, 1),
        target_date=date(2026, 11, 8),
    )
    db.add_all([p_shared, p1, p2, p3])
    db.flush()

    # Shared / Everyone Gate Tasks
    db.add_all(
        [
            Task(
                project_id=p_shared.id,
                title="Hero case end to end, mocks off",
                description="waits on 6 core tasks",
                status="todo",
                priority="urgent",
                start_date=date(2026, 11, 6),
                due_date=date(2026, 11, 6),
                is_milestone=True,
                progress=0,
            ),
            Task(
                project_id=p_shared.id,
                title="Test-set run, review misses",
                description="mock until A5",
                status="todo",
                priority="high",
                start_date=date(2026, 11, 7),
                due_date=date(2026, 11, 7),
                progress=0,
            ),
            Task(
                project_id=p_shared.id,
                title="Code freeze & v2.0-demo",
                description="after the gate",
                status="todo",
                priority="urgent",
                start_date=date(2026, 11, 8),
                due_date=date(2026, 11, 8),
                is_milestone=True,
                progress=0,
            ),
        ]
    )

    # Core Engine Tasks
    t1 = Task(
        project_id=p1.id,
        title="PostgreSQL 16 schema, two seeds, hero case",
        description="migrations/001_postgres_schema.sql",
        status="done",
        priority="high",
        start_date=date(2026, 11, 1),
        due_date=date(2026, 11, 2),
        progress=100,
    )
    db.add(t1)
    db.flush()

    t2 = Task(
        project_id=p1.id,
        title="Fast-path seed-db & connection pooling",
        description="pool_pre_ping enabled",
        status="todo",
        priority="medium",
        start_date=date(2026, 11, 2),
        due_date=date(2026, 11, 2),
        progress=0,
    )
    t3 = Task(
        project_id=p1.id,
        title="Entities and dependency cycle check",
        description="validate_no_dependency_cycle",
        status="todo",
        priority="high",
        start_date=date(2026, 11, 3),
        due_date=date(2026, 11, 3),
        depends_on_id=t1.id,
        progress=0,
    )
    db.add_all([t2, t3])
    db.flush()

    t4 = Task(
        project_id=p1.id,
        title="Auto-cascading timeline scheduler",
        description="cascade_dependent_tasks",
        status="todo",
        priority="urgent",
        start_date=date(2026, 11, 4),
        due_date=date(2026, 11, 5),
        depends_on_id=t3.id,
        progress=0,
    )
    t5 = Task(
        project_id=p1.id,
        title="Critical path & evaluation harness",
        description="B1-B4 done ✓",
        status="todo",
        priority="high",
        start_date=date(2026, 11, 6),
        due_date=date(2026, 11, 7),
        depends_on_id=t4.id,
        progress=0,
    )
    db.add_all([t4, t5])

    # Roadmap & Timeline UI Tasks
    db.add_all(
        [
            Task(
                project_id=p2.id,
                title="Warm editorial light theme (Orange + Cyan)",
                status="done",
                priority="high",
                start_date=date(2026, 11, 1),
                due_date=date(2026, 11, 1),
                progress=100,
            ),
            Task(
                project_id=p2.id,
                title="KPI summary cards & status pills",
                status="done",
                priority="high",
                start_date=date(2026, 11, 2),
                due_date=date(2026, 11, 2),
                progress=100,
            ),
            Task(
                project_id=p2.id,
                title="Day-column matrix & sub-row card packing",
                status="done",
                priority="urgent",
                start_date=date(2026, 11, 3),
                due_date=date(2026, 11, 4),
                progress=100,
            ),
            Task(
                project_id=p2.id,
                title="Kanban board & SVG knowledge graph",
                status="done",
                priority="medium",
                start_date=date(2026, 11, 5),
                due_date=date(2026, 11, 6),
                progress=100,
            ),
        ]
    )

    note1 = Note(
        project_id=p1.id,
        title="Architecture Spec",
        slug="architecture-spec",
        note_date=date(2026, 11, 2),
        content_md=(
            "---\nowner: bryce\ntags: [postgres, fastapi, architecture]\n---\n"
            "# Architecture Spec\n\nLinked to [[UI Design System|Vue 3 UI Spec]].\n\n"
            "## Action Items\n"
            "- [ ] Benchmark PostgreSQL connection pooling @start(2026-11-06) @due(2026-11-07) @priority(high)\n"
        ),
    )
    note2 = Note(
        project_id=p3.id,
        title="UI Design System",
        slug="ui-design-system",
        note_date=date(2026, 11, 4),
        content_md=(
            "---\nowner: bryce\ntags: [vue3, timeline, kanban]\n---\n"
            "# UI Design System\n\nBuilds upon [[Architecture Spec]].\n\n"
            "- [x] Orange primary & Cyan secondary editorial theme @start(2026-11-01) @due(2026-11-02) @priority(high)\n"
            "- [ ] Bidirectional [[WikiLink]] backlinks drawer @start(2026-11-05) @due(2026-11-07) @priority(high)\n"
        ),
    )
    db.add_all([note1, note2])
    db.flush()
    _sync_note_metadata_and_tasks(db, note1, sync_inline_tasks=True)
    _sync_note_metadata_and_tasks(db, note2, sync_inline_tasks=True)
    db.commit()

    return {"status": "seeded", "projects": 4}


# ---------------------------------------------------------------------------
# Mount MCP (Model Context Protocol) SSE Server for Remote / Cloud Access (e.g. Render)
# ---------------------------------------------------------------------------
try:
    from backend.mcp_server import server as mcp_server
    from mcp.server.transport_security import TransportSecuritySettings
    _mcp_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    app.mount("/mcp", mcp_server.sse_app(transport_security=_mcp_security))
except Exception as _exc:
    logger.warning("Could not mount MCP SSE app: %s", _exc)


# ---------------------------------------------------------------------------
# Single-Service Production SPA Static Serving (FastAPI serves frontend/dist)
# ---------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (_FRONTEND_DIST / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
        name="frontend-assets",
    )


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa_or_static(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("ws/") or full_path.startswith("mcp/"):
        raise HTTPException(status_code=404, detail="Not Found")
    if _FRONTEND_DIST.is_dir():
        candidate = (_FRONTEND_DIST / full_path).resolve()
        if candidate.is_file() and str(candidate).startswith(str(_FRONTEND_DIST.resolve())):
            return FileResponse(str(candidate))
        index_html = _FRONTEND_DIST / "index.html"
        if index_html.is_file():
            return FileResponse(str(index_html))
    return {
        "service": "ChronoNote API",
        "status": "running",
        "docs": "/docs",
    }