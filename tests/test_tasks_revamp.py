from datetime import date, timedelta
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db, SessionLocal
from backend.models import Task, Note, User

client = TestClient(app)


def test_create_and_list_standalone_tasks():
    # 1. Create a standalone task without any project_id
    payload = {
        "title": "Buy groceries and ingredients",
        "description": "Milk, eggs, flour",
        "priority": "high",
        "color": "#e11d48",
        "due_date": "2026-11-15",
        "is_milestone": False,
    }
    res = client.post("/api/tasks", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["id"] > 0
    assert created["project_id"] is None
    assert created["title"] == "Buy groceries and ingredients"
    assert created["priority"] == "high"

    # 2. Query standalone tasks
    res_list = client.get("/api/tasks?standalone_only=true")
    assert res_list.status_code == 200
    standalone_tasks = res_list.json()
    assert any(t["id"] == created["id"] for t in standalone_tasks)


def test_overdue_tasks_status_filter():
    yesterday = (date.today() - timedelta(days=2)).isoformat()
    tomorrow = (date.today() + timedelta(days=2)).isoformat()

    # Create an overdue task
    res_overdue = client.post(
        "/api/tasks",
        json={
            "title": "Old overdue chore",
            "due_date": yesterday,
            "status": "todo",
        },
    )
    assert res_overdue.status_code == 201
    overdue_task = res_overdue.json()

    # Create an upcoming task
    res_upcoming = client.post(
        "/api/tasks",
        json={
            "title": "Future chore",
            "due_date": tomorrow,
            "status": "todo",
        },
    )
    assert res_upcoming.status_code == 201
    upcoming_task = res_upcoming.json()

    # Filter by status_filter=overdue
    res = client.get("/api/tasks?status_filter=overdue")
    assert res.status_code == 200
    overdue_list = res.json()
    overdue_ids = [t["id"] for t in overdue_list]

    assert overdue_task["id"] in overdue_ids
    assert upcoming_task["id"] not in overdue_ids


def test_sync_inline_tasks_from_daily_note_without_project():
    # Create a daily note (no project_id) with inline task directives
    content = """---
date: 2026-11-04
---
# Daily Journal — 2026-11-04

- [ ] Call doctor @due(2026-11-04) @priority(high)
- [x] Morning run @due(2026-11-04)
"""
    res = client.post(
        "/api/notes",
        json={
            "title": "Journal — 2026-11-04",
            "content_md": content,
            "is_daily_note": True,
            "note_date": "2026-11-04",
            "sync_inline_tasks": True,
        },
    )
    assert res.status_code == 201
    created_note = res.json()
    assert len(created_note["synced_task_ids"]) == 2

    # Check tasks created from the note
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(Task.source_note_id == created_note["id"]).all()
        assert len(tasks) == 2
        titles = {t.title: t for t in tasks}
        assert "Call doctor" in titles
        assert titles["Call doctor"].project_id is None
        assert titles["Call doctor"].priority == "high"
        assert titles["Call doctor"].status == "todo"
        assert "Morning run" in titles
        assert titles["Morning run"].status == "done"
    finally:
        db.close()


def test_task_deadline_only_create_and_update():
    res_proj = client.post(
        "/api/projects",
        json={"name": "Deadline Project", "start_date": "2026-11-01", "target_date": "2026-11-30"},
    )
    assert res_proj.status_code == 201
    pid = res_proj.json()["id"]

    res_create = client.post(
        "/api/tasks",
        json={
            "project_id": pid,
            "title": "Submit report",
            "start_date": "2026-11-01",
            "due_date": "2026-11-15",
            "deadline_only": True,
        },
    )
    assert res_create.status_code == 201
    created = res_create.json()
    assert created["deadline_only"] is True

    res_patch = client.patch(
        f"/api/tasks/{created['id']}",
        json={"deadline_only": False},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["deadline_only"] is False


def test_overdue_status_filter_excludes_completed_progress_and_archived_or_completed_projects():
    yesterday = (date.today() - timedelta(days=3)).isoformat()

    p_active = client.post(
        "/api/projects",
        json={"name": "Active Proj", "status": "active", "start_date": yesterday, "target_date": yesterday},
    ).json()
    p_archived = client.post(
        "/api/projects",
        json={"name": "Archived Proj", "status": "archived", "start_date": yesterday, "target_date": yesterday},
    ).json()
    p_completed = client.post(
        "/api/projects",
        json={"name": "Completed Proj", "status": "completed", "start_date": yesterday, "target_date": yesterday},
    ).json()

    t_active_overdue = client.post(
        "/api/tasks",
        json={"project_id": p_active["id"], "title": "Real active overdue", "status": "todo", "due_date": yesterday},
    ).json()
    t_progress_100 = client.post(
        "/api/tasks",
        json={
            "project_id": p_active["id"],
            "title": "Done by progress 100",
            "status": "in_progress",
            "progress": 100,
            "due_date": yesterday,
        },
    ).json()
    t_archived_proj = client.post(
        "/api/tasks",
        json={"project_id": p_archived["id"], "title": "Archived proj task", "status": "todo", "due_date": yesterday},
    ).json()
    t_completed_proj = client.post(
        "/api/tasks",
        json={"project_id": p_completed["id"], "title": "Completed proj task", "status": "todo", "due_date": yesterday},
    ).json()
    t_standalone_overdue = client.post(
        "/api/tasks",
        json={"title": "Standalone overdue", "status": "todo", "due_date": yesterday},
    ).json()

    res = client.get("/api/tasks?status_filter=overdue")
    assert res.status_code == 200
    overdue_ids = {t["id"] for t in res.json()}

    assert t_active_overdue["id"] in overdue_ids
    assert t_standalone_overdue["id"] in overdue_ids
    assert t_progress_100["id"] not in overdue_ids
    assert t_archived_proj["id"] not in overdue_ids
    assert t_completed_proj["id"] not in overdue_ids


def test_task_time_blocks_and_project_area_archive_lifecycle():
    # 1. Create a task with start_time / end_time
    created_task = client.post(
        "/api/tasks",
        json={
            "title": "Deep work block",
            "status": "todo",
            "start_date": "2026-11-24",
            "due_date": "2026-11-24",
            "start_time": "09:30",
            "end_time": "11:00",
        },
    )
    assert created_task.status_code == 201
    task_data = created_task.json()
    assert task_data["start_time"] == "09:30"
    assert task_data["end_time"] == "11:00"

    # Update timed block hours and verify persistence
    patched_task = client.patch(
        f"/api/tasks/{task_data['id']}",
        json={"start_time": "13:15", "end_time": "14:45"},
    )
    assert patched_task.status_code == 200
    assert patched_task.json()["start_time"] == "13:15"
    assert patched_task.json()["end_time"] == "14:45"

    # 2. Create project with padded area -> trimmed cleanly
    created_proj = client.post(
        "/api/projects",
        json={
            "name": "Archived System Redesign",
            "status": "active",
            "area": "  Engineering  ",
        },
    )
    assert created_proj.status_code == 201
    proj = created_proj.json()
    assert proj["area"] == "Engineering"

    # Archive project -> listed under status_filter=archived
    archived_res = client.patch(
        f"/api/projects/{proj['id']}",
        json={"status": "archived"},
    )
    assert archived_res.status_code == 200
    assert archived_res.json()["status"] == "archived"

    archived_sidebar = client.get("/api/sidebar/projects?status_filter=archived")
    assert archived_sidebar.status_code == 200
    archived_ids = {p["id"] for p in archived_sidebar.json()}
    assert proj["id"] in archived_ids

    # Restore project -> returns to active list and leaves archive vault
    restored_res = client.patch(
        f"/api/projects/{proj['id']}",
        json={"status": "active"},
    )
    assert restored_res.status_code == 200
    assert restored_res.json()["status"] == "active"

    archived_after = client.get("/api/sidebar/projects?status_filter=archived")
    assert archived_after.status_code == 200
    assert proj["id"] not in {p["id"] for p in archived_after.json()}

