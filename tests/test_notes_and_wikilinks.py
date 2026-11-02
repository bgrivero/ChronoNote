def test_markdown_note_inline_task_sync_to_timeline(client):
    proj = client.post("/api/projects", json={"name": "Mobile App Launch"}).json()

    note_md = """---
author: bryce
tags: [launch, mobile]
---
# Sprint Planning
- [ ] Prepare App Store screenshots @start(2026-11-04) @due(2026-11-08) @priority(high)
- [ ] v1.0 Submission Freeze @start(2026-11-12) @due(2026-11-12) @milestone
"""
    create_res = client.post(
        "/api/notes",
        json={
            "project_id": proj["id"],
            "title": "Sprint Planning Note",
            "note_date": "2026-11-02",
            "content_md": note_md,
            "sync_inline_tasks": True,
        },
    )
    assert create_res.status_code == 201
    note = create_res.json()
    assert note["frontmatter"]["author"] == "bryce"
    assert "launch" in note["tags"]
    assert len(note["synced_task_ids"]) == 2

    # Verify tasks were created on the project
    tasks = client.get("/api/tasks", params={"project_id": proj["id"]}).json()
    assert len(tasks) == 2
    assert tasks[0]["title"] == "Prepare App Store screenshots"
    assert tasks[0]["status"] == "todo"
    assert tasks[0]["priority"] == "high"
    assert tasks[0]["start_date"] == "2026-11-04"
    assert tasks[0]["due_date"] == "2026-11-08"
    assert tasks[1]["title"] == "v1.0 Submission Freeze"
    assert tasks[1]["is_milestone"] is True

    # Now check off the first task in Markdown ([ ] -> [x]) and update the note
    updated_md = note_md.replace("- [ ] Prepare App Store screenshots", "- [x] Prepare App Store screenshots")
    upd_res = client.put(
        f"/api/notes/{note['id']}",
        json={"content_md": updated_md, "sync_inline_tasks": True},
    )
    assert upd_res.status_code == 200

    tasks_after = client.get("/api/tasks", params={"project_id": proj["id"]}).json()
    screenshots_task = next(t for t in tasks_after if t["title"] == "Prepare App Store screenshots")
    assert screenshots_task["status"] == "done"
    assert screenshots_task["progress"] == 100


def test_bidirectional_wikilinks_and_backlinks(client):
    # Create Note A referencing [[Database Architecture]] before Note B even exists
    note_a = client.post(
        "/api/notes",
        json={
            "title": "System Overview",
            "content_md": "See [[Database Architecture|DB Spec]] for schema details.",
        },
    ).json()
    assert len(note_a["outgoing_links"]) == 1
    assert note_a["outgoing_links"][0]["target_slug"] == "database-architecture"
    assert note_a["outgoing_links"][0]["target_note_id"] is None

    # Now create Note B ("Database Architecture") and verify forward reference resolves automatically
    note_b = client.post(
        "/api/notes",
        json={
            "title": "Database Architecture",
            "content_md": "# Database Architecture\nPostgreSQL & SQLite support.",
        },
    ).json()

    assert len(note_b["backlinks"]) == 1
    assert note_b["backlinks"][0]["source_note_id"] == note_a["id"]
    assert note_b["backlinks"][0]["source_title"] == "System Overview"

    # Re-fetch Note A to confirm target_note_id is now populated
    note_a_refreshed = client.get(f"/api/notes/{note_a['id']}").json()
    assert note_a_refreshed["outgoing_links"][0]["target_note_id"] == note_b["id"]


def test_daily_note_idempotent_creation(client):
    res1 = client.post("/api/notes/daily/2026-11-01")
    assert res1.status_code == 200
    n1 = res1.json()
    assert n1["is_daily_note"] is True
    assert n1["note_date"] == "2026-11-01"

    # Calling a second time returns the exact same Daily Note
    res2 = client.post("/api/notes/daily/2026-11-01")
    assert res2.status_code == 200
    assert res2.json()["id"] == n1["id"]
