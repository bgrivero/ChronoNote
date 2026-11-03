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
