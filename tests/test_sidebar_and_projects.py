def test_left_sidebar_ordering_and_rollup_metrics(client):
    # Create three projects: one normal, one pinned, one archived
    p1 = client.post(
        "/api/projects",
        json={
            "name": "Backend API",
            "color": "#3b82f6",
            "sidebar_order": 2,
            "start_date": "2026-11-01",
            "target_date": "2026-11-20",
        },
    ).json()
    p2 = client.post(
        "/api/projects",
        json={
            "name": "Vue Timeline UI",
            "color": "#10b981",
            "is_pinned": True,
            "sidebar_order": 5,
            "start_date": "2026-11-03",
            "target_date": "2026-11-25",
        },
    ).json()
    p3 = client.post(
        "/api/projects",
        json={
            "name": "Legacy Migration",
            "status": "archived",
            "sidebar_order": 1,
        },
    ).json()

    # Add tasks to Backend API: 1 done, 1 overdue todo
    client.post(
        "/api/tasks",
        json={
            "project_id": p1["id"],
            "title": "Design schema",
            "status": "done",
            "due_date": "2026-11-02",
        },
    )
    client.post(
        "/api/tasks",
        json={
            "project_id": p1["id"],
            "title": "Write auth middleware",
            "status": "todo",
            "due_date": "2026-11-05",
        },
    )

    # Add a note to Backend API
    client.post(
        "/api/notes",
        json={
            "project_id": p1["id"],
            "title": "API Kickoff",
            "content_md": "Initial notes for #backend",
            "sync_inline_tasks": False,
        },
    )

    # Fetch sidebar projects with reference_date=2026-11-10 so 2026-11-05 is overdue
    res = client.get("/api/sidebar/projects", params={"reference_date": "2026-11-10"})
    assert res.status_code == 200
    items = res.json()

    # Archived project p3 is excluded by default; pinned project p2 comes first
    assert [item["id"] for item in items] == [p2["id"], p1["id"]]

    backend_item = items[1]
    assert backend_item["total_tasks"] == 2
    assert backend_item["completed_tasks"] == 1
    assert backend_item["overdue_tasks"] == 1
    assert backend_item["progress_pct"] == 50.0
    assert backend_item["note_count"] == 1

    # Verify include_archived=true returns all 3
    res_all = client.get("/api/sidebar/projects", params={"include_archived": True})
    assert len(res_all.json()) == 3
    assert p3["id"] in [i["id"] for i in res_all.json()]


def test_sidebar_drag_and_drop_reorder(client):
    a = client.post("/api/projects", json={"name": "Project A", "sidebar_order": 0}).json()
    b = client.post("/api/projects", json={"name": "Project B", "sidebar_order": 1}).json()
    c = client.post("/api/projects", json={"name": "Project C", "sidebar_order": 2}).json()

    reorder_res = client.patch(
        "/api/sidebar/projects/reorder",
        json={"ordered_project_ids": [c["id"], a["id"], b["id"]]},
    )
    assert reorder_res.status_code == 200
    ordered = reorder_res.json()
    assert [p["id"] for p in ordered] == [c["id"], a["id"], b["id"]]
    assert [p["sidebar_order"] for p in ordered] == [0, 1, 2]


def test_projects_kanban_and_pinned_only_timeline(client):
    p_pinned = client.post(
        "/api/projects",
        json={
            "name": "Pinned Calendar Project",
            "status": "active",
            "is_pinned": True,
            "start_date": "2026-10-01",
            "target_date": "2026-12-15",
        },
    ).json()
    p_unpinned = client.post(
        "/api/projects",
        json={
            "name": "Unpinned Planned Project",
            "status": "planned",
            "is_pinned": False,
            "start_date": "2026-11-01",
            "target_date": "2026-11-30",
        },
    ).json()

    kanban_res = client.get("/api/projects-kanban")
    assert kanban_res.status_code == 200
    kb = kanban_res.json()
    assert kb["total_projects"] == 2
    col_counts = {c["status"]: c["count"] for c in kb["columns"]}
    assert col_counts["active"] == 1
    assert col_counts["planned"] == 1

    # Verify timeline with pinned_only=True returns only p_pinned
    tl_pinned = client.get(
        "/api/timeline",
        params={"start_date": "2026-01-01", "end_date": "2026-12-31", "pinned_only": True},
    ).json()
    assert [lane["project"]["id"] for lane in tl_pinned["swimlanes"]] == [p_pinned["id"]]
    assert p_unpinned["id"] not in [lane["project"]["id"] for lane in tl_pinned["swimlanes"]]

    # Drag p_unpinned from 'planned' to 'active' and place it first via /api/projects-kanban/move
    move_res = client.patch(
        "/api/projects-kanban/move",
        json={
            "project_id": p_unpinned["id"],
            "target_status": "active",
            "sidebar_order": 0,
            "ordered_project_ids": [p_unpinned["id"], p_pinned["id"]],
        },
    )
    assert move_res.status_code == 200
    moved_proj = move_res.json()
    assert moved_proj["status"] == "active"
    assert moved_proj["sidebar_order"] == 0

    kb_after = client.get("/api/projects-kanban").json()
    active_col = next(c for c in kb_after["columns"] if c["status"] == "active")
    assert active_col["count"] == 2
    assert [p["id"] for p in active_col["projects"]] == [p_unpinned["id"], p_pinned["id"]]


def test_project_update_and_delete(client):
    # Create project
    proj = client.post(
        "/api/projects",
        json={
            "name": "Initial Name",
            "description": "Initial Description",
            "color": "#6366f1",
            "start_date": "2026-11-01",
            "target_date": "2026-11-15",
        },
    ).json()
    proj_id = proj["id"]

    # Add task and note
    task = client.post(
        "/api/tasks",
        json={"project_id": proj_id, "title": "Subtask 1"},
    ).json()
    note = client.post(
        "/api/notes",
        json={"project_id": proj_id, "title": "Project Note", "content_md": "Hello"},
    ).json()

    # Update project name and description
    patch_res = client.patch(
        f"/api/projects/{proj_id}",
        json={"name": "Renamed Project", "description": "Updated Goals", "color": "#10b981"},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["name"] == "Renamed Project"
    assert updated["color"] == "#10b981"

    # Delete project
    del_res = client.delete(f"/api/projects/{proj_id}")
    assert del_res.status_code == 204

    # Verify project is gone
    get_res = client.get(f"/api/projects/{proj_id}/critical-path")
    assert get_res.status_code == 404

    # Verify note is preserved with detached project_id
    note_res = client.get(f"/api/notes/{note['id']}")
    assert note_res.status_code == 200
    assert note_res.json()["project_id"] is None

