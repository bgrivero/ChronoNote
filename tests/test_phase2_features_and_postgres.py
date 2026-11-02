from pathlib import Path


def test_postgres_ddl_compilation_and_migration_parity(client):
    res = client.get("/api/schema/postgres")
    assert res.status_code == 200
    payload = res.json()
    assert payload["dialect"] == "postgresql"
    ddl = payload["ddl"]

    # Verify native PostgreSQL types and tables are generated cleanly
    assert "CREATE TABLE projects" in ddl
    assert "CREATE TABLE notes" in ddl
    assert "CREATE TABLE tasks" in ddl
    assert "CREATE TABLE note_links" in ddl
    assert "TIMESTAMP WITH TIME ZONE" in ddl
    assert "ON DELETE CASCADE" in ddl

    # Verify SQL migration file exists and matches the 4 core tables
    sql_path = Path(__file__).resolve().parent.parent / "migrations" / "001_postgres_schema.sql"
    assert sql_path.exists()
    sql_text = sql_path.read_text(encoding="utf-8")
    for tbl in ("projects", "notes", "tasks", "note_links"):
        assert f"CREATE TABLE IF NOT EXISTS {tbl}" in sql_text


def test_auto_cascading_dependency_scheduling_and_cycle_detection(client):
    proj = client.post("/api/projects", json={"name": "Cascade Engine"}).json()

    # Task A: Nov 1 -> Nov 3 (3 days)
    t_a = client.post(
        "/api/tasks",
        json={
            "project_id": proj["id"],
            "title": "Task A (Foundation)",
            "start_date": "2026-11-01",
            "due_date": "2026-11-03",
        },
    ).json()

    # Task B depends on Task A: Nov 4 -> Nov 6 (2 days difference = 3 days inclusive)
    t_b = client.post(
        "/api/tasks",
        json={
            "project_id": proj["id"],
            "title": "Task B (API Layer)",
            "start_date": "2026-11-04",
            "due_date": "2026-11-06",
            "depends_on_id": t_a["id"],
        },
    ).json()

    # Task C depends on Task B: Nov 7 -> Nov 8 (1 day difference)
    t_c = client.post(
        "/api/tasks",
        json={
            "project_id": proj["id"],
            "title": "Task C (Integration)",
            "start_date": "2026-11-07",
            "due_date": "2026-11-08",
            "depends_on_id": t_b["id"],
        },
    ).json()

    # Slip Task A's due_date to 2026-11-08
    slip_res = client.patch(
        f"/api/tasks/{t_a['id']}",
        json={"due_date": "2026-11-08", "cascade_dependencies": True},
    )
    assert slip_res.status_code == 200
    slipped_a = slip_res.json()
    assert slipped_a["cascaded_task_ids"] == [t_b["id"], t_c["id"]]

    # Verify Task B shifted to 2026-11-09 -> 2026-11-11 and Task C shifted to 2026-11-12 -> 2026-11-13
    tasks = {
        t["id"]: t
        for t in client.get("/api/tasks", params={"project_id": proj["id"]}).json()
    }
    assert tasks[t_b["id"]]["start_date"] == "2026-11-09"
    assert tasks[t_b["id"]]["due_date"] == "2026-11-11"
    assert tasks[t_c["id"]]["start_date"] == "2026-11-12"
    assert tasks[t_c["id"]]["due_date"] == "2026-11-13"

    # Attempt to create a cycle: Task A depends on Task C -> must fail with 400
    cycle_res = client.patch(
        f"/api/tasks/{t_a['id']}",
        json={"depends_on_id": t_c["id"]},
    )
    assert cycle_res.status_code == 400
    assert "Circular dependency" in cycle_res.json()["detail"]


def test_critical_path_computation(client):
    proj = client.post("/api/projects", json={"name": "Critical Path Project"}).json()

    # Chain 1: 4 days + 3 days = 7 days total
    t1 = client.post(
        "/api/tasks",
        json={
            "project_id": proj["id"],
            "title": "Chain 1 Step 1",
            "start_date": "2026-11-01",
            "due_date": "2026-11-04",
        },
    ).json()
    t2 = client.post(
        "/api/tasks",
        json={
            "project_id": proj["id"],
            "title": "Chain 1 Step 2",
            "start_date": "2026-11-05",
            "due_date": "2026-11-07",
            "depends_on_id": t1["id"],
        },
    ).json()

    # Short standalone task: 2 days
    client.post(
        "/api/tasks",
        json={
            "project_id": proj["id"],
            "title": "Short Side Task",
            "start_date": "2026-11-01",
            "due_date": "2026-11-02",
        },
    )

    cp_res = client.get(f"/api/projects/{proj['id']}/critical-path")
    assert cp_res.status_code == 200
    cp = cp_res.json()
    assert cp["critical_path_task_ids"] == [t1["id"], t2["id"]]
    assert cp["total_duration_days"] == 7


def test_kanban_board_columns_and_card_movement(client):
    proj = client.post("/api/projects", json={"name": "Kanban Flow"}).json()
    task = client.post(
        "/api/tasks",
        json={
            "project_id": proj["id"],
            "title": "Implement Kanban Drag",
            "status": "todo",
        },
    ).json()

    board = client.get("/api/kanban", params={"project_id": proj["id"]}).json()
    assert board["total_tasks"] == 1
    todo_col = next(c for c in board["columns"] if c["status"] == "todo")
    assert todo_col["count"] == 1

    # Move card to in_progress
    moved = client.patch(
        "/api/kanban/move",
        json={"task_id": task["id"], "target_status": "in_progress"},
    ).json()
    assert moved["status"] == "in_progress"
    assert moved["progress"] == 50

    # Move card to done
    moved_done = client.patch(
        "/api/kanban/move",
        json={"task_id": task["id"], "target_status": "done"},
    ).json()
    assert moved_done["status"] == "done"
    assert moved_done["progress"] == 100


def test_knowledge_graph_nodes_and_edges(client):
    proj = client.post("/api/projects", json={"name": "Graph Project"}).json()
    client.post(
        "/api/notes",
        json={
            "project_id": proj["id"],
            "title": "Graph Root Note",
            "content_md": "Linking to [[Future Spec]] with #graph and #vue3.",
        },
    )

    graph_res = client.get("/api/graph")
    assert graph_res.status_code == 200
    graph = graph_res.json()

    node_kinds = {n["kind"] for n in graph["nodes"]}
    assert {"project", "note", "tag"}.issubset(node_kinds)

    edge_relations = {e["relation"] for e in graph["edges"]}
    assert edge_relations == {"belongs_to", "tagged", "wikilink"}


def test_realtime_websocket_collaboration_and_broadcast(client):
    with client.websocket_connect("/ws/workspace") as ws:
        hello = ws.receive_json()
        assert hello["event"] == "workspace.connected"
        assert hello["payload"]["active_clients"] >= 1

        ws.send_json({"action": "ping", "payload": {"cursor": "editor"}})
        pong = ws.receive_json()
        assert pong["event"] == "pong"
        assert pong["payload"]["cursor"] == "editor"

        # Trigger a REST mutation while WebSocket is connected and verify broadcast
        client.post("/api/projects", json={"name": "Live Broadcast Project"})
        broadcast_msg = ws.receive_json()
        assert broadcast_msg["event"] == "project.created"
        assert broadcast_msg["payload"]["name"] == "Live Broadcast Project"


def test_demo_workspace_seeder(client):
    res1 = client.post("/api/seed")
    assert res1.status_code == 200
    assert res1.json()["status"] == "seeded"

    # Calling again is idempotent
    res2 = client.post("/api/seed")
    assert res2.status_code == 200
    assert res2.json()["status"] == "already_seeded"


def test_daily_journal_upsert_and_month_listing(client):
    # Create/upsert a daily journal entry for 2026-11-05
    put_res = client.put(
        "/api/journal/2026-11-05",
        json={
            "title": "Journal — 2026-11-05",
            "content_md": "Wrote down handwritten thoughts.\n- [ ] Buy fountain pen ink @due(2026-11-06)",
        },
    )
    assert put_res.status_code == 200
    entry = put_res.json()
    assert entry["is_daily_note"] is True
    assert entry["note_date"] == "2026-11-05"
    assert "fountain pen ink" in entry["content_md"]

    # Fetch specific date
    get_res = client.get("/api/journal/2026-11-05")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == entry["id"]

    # List November 2026 journal entries
    list_res = client.get("/api/journal", params={"year": 2026, "month": 11})
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["note_date"] == "2026-11-05"


def test_google_authentication_and_session_verification(client):
    cfg = client.get("/api/auth/config")
    assert cfg.status_code == 200
    assert "auth_required" in cfg.json()

    auth_res = client.post(
        "/api/auth/google",
        json={
            "email": "bryce@example.com",
            "name": "Bryce",
        },
    )
    assert auth_res.status_code == 200
    session = auth_res.json()
    assert session["user"]["email"] == "bryce@example.com"
    assert session["token"]

    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {session['token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "bryce@example.com"


def test_per_user_account_data_persistence_and_isolation(client):
    # Sign in as User A (Alice)
    alice_session = client.post(
        "/api/auth/google",
        json={"email": "alice@example.com", "name": "Alice"},
    ).json()
    alice_headers = {"Authorization": f"Bearer {alice_session['token']}"}

    # Sign in as User B (Bob)
    bob_session = client.post(
        "/api/auth/google",
        json={"email": "bob@example.com", "name": "Bob"},
    ).json()
    bob_headers = {"Authorization": f"Bearer {bob_session['token']}"}

    # Alice creates a project and a daily journal entry on 2026-11-01
    alice_proj = client.post(
        "/api/projects",
        json={"name": "Alice Secret Project"},
        headers=alice_headers,
    ).json()
    client.put(
        "/api/journal/2026-11-01",
        json={"content_md": "Alice private journal notes"},
        headers=alice_headers,
    )

    # Bob creates a project and a daily journal entry on the SAME date 2026-11-01
    bob_proj = client.post(
        "/api/projects",
        json={"name": "Bob Hardware Project"},
        headers=bob_headers,
    ).json()
    client.put(
        "/api/journal/2026-11-01",
        json={"content_md": "Bob private journal notes"},
        headers=bob_headers,
    )

    # Verify Alice only sees Alice's projects and Alice's journal entry across devices
    alice_projects = [
        p["name"]
        for p in client.get("/api/sidebar/projects", headers=alice_headers).json()
    ]
    assert "Alice Secret Project" in alice_projects
    assert "Bob Hardware Project" not in alice_projects

    alice_journal = client.get("/api/journal/2026-11-01", headers=alice_headers).json()
    assert alice_journal["content_md"] == "Alice private journal notes"

    # Verify Bob only sees Bob's projects and Bob's journal entry
    bob_projects = [
        p["name"]
        for p in client.get("/api/sidebar/projects", headers=bob_headers).json()
    ]
    assert "Bob Hardware Project" in bob_projects
    assert "Alice Secret Project" not in bob_projects

    bob_journal = client.get("/api/journal/2026-11-01", headers=bob_headers).json()
    assert bob_journal["content_md"] == "Bob private journal notes"
    assert alice_proj["id"] != bob_proj["id"]


def test_registration_login_and_account_data_isolation(client):
    # 1. Register User 1 (Charlie) with password
    charlie_reg = client.post(
        "/api/auth/register",
        json={"email": "charlie@example.com", "name": "Charlie", "password": "charlie-pass-123"},
    )
    assert charlie_reg.status_code == 200
    charlie_session = charlie_reg.json()
    assert charlie_session["user"]["email"] == "charlie@example.com"
    charlie_headers = {"Authorization": f"Bearer {charlie_session['token']}"}

    # Duplicate registration should fail
    dup_res = client.post(
        "/api/auth/register",
        json={"email": "charlie@example.com", "name": "Charlie", "password": "charlie-pass-123"},
    )
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # Charlie creates a project
    client.post(
        "/api/projects",
        json={"name": "Charlie Roadmap"},
        headers=charlie_headers,
    )

    # 2. Register User 2 (Diana) with password
    diana_reg = client.post(
        "/api/auth/register",
        json={"email": "diana@example.com", "name": "Diana", "password": "diana-pass-456"},
    )
    assert diana_reg.status_code == 200
    diana_headers = {"Authorization": f"Bearer {diana_reg.json()['token']}"}

    # Diana creates a project
    client.post(
        "/api/projects",
        json={"name": "Diana Design Studio"},
        headers=diana_headers,
    )

    # 3. Verify Diana does not see Charlie's data
    diana_projects = [p["name"] for p in client.get("/api/sidebar/projects", headers=diana_headers).json()]
    assert "Diana Design Studio" in diana_projects
    assert "Charlie Roadmap" not in diana_projects

    # 4. Verify Charlie logs in with password and sees only Charlie's data
    login_fail = client.post(
        "/api/auth/login",
        json={"email": "charlie@example.com", "password": "wrong-password"},
    )
    assert login_fail.status_code == 401

    login_ok = client.post(
        "/api/auth/login",
        json={"email": "charlie@example.com", "password": "charlie-pass-123"},
    )
    assert login_ok.status_code == 200
    new_charlie_headers = {"Authorization": f"Bearer {login_ok.json()['token']}"}
    charlie_projects = [p["name"] for p in client.get("/api/sidebar/projects", headers=new_charlie_headers).json()]
    assert "Charlie Roadmap" in charlie_projects
    assert "Diana Design Studio" not in charlie_projects


def test_journal_password_lock_and_session_unlock(client):
    # Initially no password set
    status_res = client.get("/api/journal/lock-status")
    assert status_res.status_code == 200
    assert status_res.json()["has_password"] is False
    assert status_res.json()["is_unlocked"] is True

    # Set journal password
    set_pw_res = client.post(
        "/api/journal/password",
        json={"password": "MySecretJournalPassword123"},
    )
    assert set_pw_res.status_code == 200
    token = set_pw_res.json()["journal_token"]
    assert token

    # Check lock status without token -> locked
    status_locked = client.get("/api/journal/lock-status").json()
    assert status_locked["has_password"] is True
    assert status_locked["is_unlocked"] is False

    # Check lock status with token -> unlocked
    status_unlocked = client.get(
        "/api/journal/lock-status",
        headers={"X-Journal-Token": token},
    ).json()
    assert status_unlocked["has_password"] is True
    assert status_unlocked["is_unlocked"] is True

    # Accessing journal without token returns 403 Forbidden
    denied = client.get("/api/journal")
    assert denied.status_code == 403

    # Incorrect unlock password returns 401
    bad_unlock = client.post("/api/journal/unlock", json={"password": "WrongPassword"})
    assert bad_unlock.status_code == 401

    # Correct unlock password returns session token
    good_unlock = client.post(
        "/api/journal/unlock",
        json={"password": "MySecretJournalPassword123"},
    )
    assert good_unlock.status_code == 200
    session_token = good_unlock.json()["journal_token"]
    assert session_token

    # Reading and writing journal succeeds with session token
    put_res = client.put(
        "/api/journal/2026-11-15",
        json={"content_md": "Encrypted session thoughts"},
        headers={"X-Journal-Token": session_token},
    )
    assert put_res.status_code == 200

    get_res = client.get(
        "/api/journal/2026-11-15",
        headers={"X-Journal-Token": session_token},
    )
    assert get_res.status_code == 200
    assert get_res.json()["content_md"] == "Encrypted session thoughts"

    # Reset workspace data
    reset_res = client.post("/api/user/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["reset"] is True
