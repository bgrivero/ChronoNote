def test_timeline_swimlanes_dependencies_and_note_pins(client):
    proj_alpha = client.post(
        "/api/projects",
        json={
            "name": "Alpha Platform",
            "color": "#8b5cf6",
            "is_pinned": True,
            "sidebar_order": 0,
            "start_date": "2026-11-01",
            "target_date": "2026-11-30",
        },
    ).json()

    # Create a regular task and a dependent milestone
    t1 = client.post(
        "/api/tasks",
        json={
            "project_id": proj_alpha["id"],
            "title": "Implement Timeline Grid",
            "status": "in_progress",
            "priority": "high",
            "start_date": "2026-11-02",
            "due_date": "2026-11-09",
            "progress": 60,
        },
    ).json()

    t2 = client.post(
        "/api/tasks",
        json={
            "project_id": proj_alpha["id"],
            "title": "Alpha Milestone Review",
            "status": "todo",
            "priority": "urgent",
            "start_date": "2026-11-10",
            "due_date": "2026-11-10",
            "is_milestone": True,
            "depends_on_id": t1["id"],
        },
    ).json()

    # Task outside the queried window (December)
    client.post(
        "/api/tasks",
        json={
            "project_id": proj_alpha["id"],
            "title": "December Post-Launch Audit",
            "status": "todo",
            "start_date": "2026-12-15",
            "due_date": "2026-12-20",
        },
    )

    # Create a project note and a daily note inside the November window
    client.post(
        "/api/notes",
        json={
            "project_id": proj_alpha["id"],
            "title": "Architecture Decision Record",
            "note_date": "2026-11-04",
            "content_md": "Decided on #fastapi and #vue3 with SVG dependency arrows.",
            "sync_inline_tasks": False,
        },
    )
    client.post("/api/notes/daily/2026-11-05")

    res = client.get(
        "/api/timeline",
        params={"start_date": "2026-11-01", "end_date": "2026-11-15"},
    )
    assert res.status_code == 200
    timeline = res.json()

    assert timeline["window_start"] == "2026-11-01"
    assert timeline["window_end"] == "2026-11-15"
    assert timeline["total_days"] == 15
    assert len(timeline["swimlanes"]) == 1

    lane = timeline["swimlanes"][0]
    assert lane["project"]["name"] == "Alpha Platform"
    assert len(lane["tasks"]) == 1
    assert lane["tasks"][0]["title"] == "Implement Timeline Grid"
    assert len(lane["milestones"]) == 1
    assert lane["milestones"][0]["id"] == t2["id"]
    assert len(lane["note_pins"]) == 1
    assert lane["note_pins"][0]["title"] == "Architecture Decision Record"

    assert len(timeline["daily_notes"]) == 1
    assert timeline["daily_notes"][0]["note_date"] == "2026-11-05"

    assert len(timeline["dependencies"]) == 1
    dep = timeline["dependencies"][0]
    assert dep["from_task_id"] == t1["id"]
    assert dep["to_task_id"] == t2["id"]


def test_timeline_rejects_invalid_date_window(client):
    res = client.get(
        "/api/timeline",
        params={"start_date": "2026-11-20", "end_date": "2026-11-01"},
    )
    assert res.status_code == 400


def test_unified_command_palette_search(client):
    proj = client.post(
        "/api/projects",
        json={"name": "Nebula Sync Engine", "description": "Offline-first sync"},
    ).json()
    client.post(
        "/api/notes",
        json={
            "project_id": proj["id"],
            "title": "Nebula CRDT Research",
            "content_md": "Exploring Yjs and #nebula conflict resolution.",
        },
    )
    client.post(
        "/api/tasks",
        json={
            "project_id": proj["id"],
            "title": "Benchmark Nebula WebSockets",
        },
    )

    res = client.get("/api/search", params={"q": "nebula"})
    assert res.status_code == 200
    items = res.json()
    kinds = {item["kind"] for item in items}
    assert kinds == {"project", "note", "task"}
