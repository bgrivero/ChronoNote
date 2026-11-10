import datetime
from backend.models import Habit, Project, Task


def test_create_study_session_with_project_and_auto_journal(client):
    # 1. Create a project
    proj_res = client.post("/api/projects", json={"name": "Neuroscience 201", "color": "#10b981"})
    assert proj_res.status_code == 201
    proj = proj_res.json()

    # 2. Create a study session bound to the project
    session_res = client.post(
        "/api/study/sessions",
        json={
            "project_id": proj["id"],
            "duration_minutes": 25,
            "session_type": "focus",
            "intention": "Review synaptic transmission slides",
            "auto_log_to_journal": True,
        },
    )
    assert session_res.status_code == 201
    session_data = session_res.json()
    assert session_data["project_name"] == "Neuroscience 201"
    assert session_data["duration_minutes"] == 25
    assert session_data["intention"] == "Review synaptic transmission slides"

    # 3. Verify that today's journal note has the auto-logged bullet
    today_str = datetime.date.today().isoformat()
    journal_res = client.get(f"/api/notes?is_daily_note=true")
    assert journal_res.status_code == 200
    notes = journal_res.json()
    today_notes = [n for n in notes if n["note_date"] == today_str]
    assert len(today_notes) >= 1
    today_note = today_notes[0]
    assert "Focus (25m) on [[Neuroscience 201]]" in today_note["content_md"]
    assert "Review synaptic transmission slides" in today_note["content_md"]


def test_study_session_syncs_habit_and_updates_stats(client, db_session):
    # Create a habit with slug "study"
    habit = Habit(slug="study", name="Daily Deep Study", color="#6366f1", target_days_per_week=5)
    db_session.add(habit)
    db_session.commit()

    # Create project and task
    proj_res = client.post("/api/projects", json={"name": "Algorithms", "color": "#f59e0b"}).json()
    task_res = client.post(
        "/api/tasks",
        json={"project_id": proj_res["id"], "title": "Graph Traversal Practice"},
    ).json()

    # Create a completed focus session
    res = client.post(
        "/api/study/sessions",
        json={
            "project_id": proj_res["id"],
            "task_id": task_res["id"],
            "duration_minutes": 50,
            "session_type": "focus",
            "intention": "Solve Dijkstra and Bellman-Ford",
            "sync_habit_slug": "study",
        },
    )
    assert res.status_code == 201
    created_session = res.json()
    assert created_session["task_title"] == "Graph Traversal Practice"

    # Check study stats
    stats_res = client.get("/api/study/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_focus_minutes"] >= 50
    assert stats["today_sessions_count"] >= 1
    assert stats["current_streak_days"] >= 1

    # Verify project breakdown contains Algorithms
    algo_entry = next((p for p in stats["project_breakdown"] if p["project_name"] == "Algorithms"), None)
    assert algo_entry is not None
    assert algo_entry["minutes"] >= 50
    assert algo_entry["session_count"] >= 1

    # Check habit logs
    habits_res = client.get("/api/habits")
    assert habits_res.status_code == 200

    # Delete session
    del_res = client.delete(f"/api/study/sessions/{created_session['id']}")
    assert del_res.status_code == 200

def test_create_study_session_with_notes_and_multiple_sessions_logged(client):
    # Create project
    proj_res = client.post("/api/projects", json={"name": "Quantum Computing", "color": "#8b5cf6"}).json()

    # Create session 1 with notes
    res1 = client.post(
        "/api/study/sessions",
        json={
            "project_id": proj_res["id"],
            "duration_minutes": 25,
            "session_type": "focus",
            "intention": "Study Grover Search Algorithm",
            "notes": "Key Takeaway: Quadratic speedup\nQuestion: Error correction overhead",
            "auto_log_to_journal": True,
        },
    )
    assert res1.status_code == 201

    # Create session 2 with same project & intention (e.g. 2nd Pomodoro cycle)
    res2 = client.post(
        "/api/study/sessions",
        json={
            "project_id": proj_res["id"],
            "duration_minutes": 25,
            "session_type": "focus",
            "intention": "Study Grover Search Algorithm",
            "notes": "Reviewed oracle phase inversion",
            "auto_log_to_journal": True,
        },
    )
    assert res2.status_code == 201

    # Verify journal has both sessions and notes
    today_str = datetime.date.today().isoformat()
    journal_res = client.get("/api/notes?is_daily_note=true")
    assert journal_res.status_code == 200
    today_note = next(n for n in journal_res.json() if n["note_date"] == today_str)
    content = today_note["content_md"]

    assert content.count("Focus (25m) on [[Quantum Computing]]") == 2
    assert "> Key Takeaway: Quadratic speedup" in content
    assert "> Question: Error correction overhead" in content
    assert "> Reviewed oracle phase inversion" in content


def test_authenticated_user_study_session_isolation(client):
    # Register user
    auth_res = client.post(
        "/api/auth/register",
        json={"email": "pomouser@example.com", "name": "Pomo User", "password": "Password123!"},
    )
    assert auth_res.status_code == 200
    token = auth_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create project under authenticated user
    proj_res = client.post("/api/projects", json={"name": "Robotics Lab", "color": "#06b6d4"}, headers=headers)
    assert proj_res.status_code == 201
    proj_id = proj_res.json()["id"]

    # Create study session with auth header
    session_res = client.post(
        "/api/study/sessions",
        json={
            "project_id": proj_id,
            "duration_minutes": 30,
            "session_type": "focus",
            "intention": "Calibrate inverse kinematics",
            "notes": "Checked Jacobian determinant",
            "auto_log_to_journal": True,
        },
        headers=headers,
    )
    assert session_res.status_code == 201
    assert session_res.json()["project_name"] == "Robotics Lab"

    # Verify user's daily journal has the entry
    today_str = datetime.date.today().isoformat()
    journal_res = client.get(f"/api/journal/{today_str}", headers=headers)
    assert journal_res.status_code == 200
    journal_data = journal_res.json()
    assert "Focus (30m) on [[Robotics Lab]]" in journal_data["content_md"]
    assert "Checked Jacobian determinant" in journal_data["content_md"]
