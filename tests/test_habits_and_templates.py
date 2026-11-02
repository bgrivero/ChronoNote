from datetime import date, timedelta
import pytest
from backend.services.markdown_parser import parse_markdown_note


def test_markdown_parser_extracts_habits():
    content = """---
date: 2026-11-02
habits:
  hydration: 2500ml
  meditation: true
---

### Daily Checklist
- [x] Morning Workout @habit(workout) @val(45m)
- [ ] Read 20 pages @habit(reading, Book Reading) @val(20)
- [x] Evening Stretch @habit(stretch)
"""
    parsed = parse_markdown_note(content)
    slugs = {h.slug: h for h in parsed.habits}

    assert "workout" in slugs
    assert slugs["workout"].completed is True
    assert slugs["workout"].value == "45m"

    assert "reading" in slugs
    assert slugs["reading"].name == "Book Reading"
    assert slugs["reading"].completed is False
    assert slugs["reading"].value == "20"

    assert "stretch" in slugs
    assert slugs["stretch"].completed is True

    # Frontmatter habits
    assert "hydration" in slugs
    assert slugs["hydration"].completed is True
    assert slugs["hydration"].value == "2500ml"

    assert "meditation" in slugs
    assert slugs["meditation"].completed is True


def test_habits_crud_and_daily_journal_sync(client):
    # 1. Create a habit
    res = client.post(
        "/api/habits",
        json={
            "name": "Morning Run",
            "slug": "morning-run",
            "icon": "activity",
            "color": "#10b981",
        },
    )
    assert res.status_code == 201
    habit_data = res.json()
    habit_id = habit_data["id"]
    assert habit_data["slug"] == "morning-run"

    # 2. Upsert a daily journal that includes this habit
    today_iso = date.today().isoformat()
    journal_content = f"""# Daily Log
- [x] Run 5k @habit(morning-run) @val(5km)
- [ ] Evening Reading @habit(reading)
"""
    res_j = client.put(
        f"/api/journal/{today_iso}",
        json={"title": f"Journal — {today_iso}", "content_md": journal_content},
    )
    assert res_j.status_code == 200

    # 3. Check habits list: morning-run should now have completions and active streak
    res_h = client.get("/api/habits")
    assert res_h.status_code == 200
    habits = res_h.json()
    run_habit = next(h for h in habits if h["slug"] == "morning-run")
    assert run_habit["total_completions"] >= 1
    assert run_habit["current_streak"] >= 1

    # 4. Check auto-created 'reading' habit from markdown
    reading_habit = next(h for h in habits if h["slug"] == "reading")
    assert reading_habit["name"] == "Evening Reading"

    # 5. Toggle habit completion via API and verify bidirectional markdown sync
    toggle_res = client.post(
        f"/api/habits/{habit_id}/toggle",
        json={"log_date": today_iso, "completed": False},
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["completed"] is False

    # Verify daily journal note has updated checkbox to [ ]
    updated_j = client.get(f"/api/journal/{today_iso}")
    assert updated_j.status_code == 200
    assert "- [ ] Run 5k @habit(morning-run)" in updated_j.json()["content_md"]


def test_habit_analytics_and_heatmap(client):
    today = date.today()
    # Create habit
    h_res = client.post(
        "/api/habits",
        json={"name": "Code Review", "slug": "code-review"},
    )
    h_id = h_res.json()["id"]

    # Log 3 consecutive days: today, yesterday, 2 days ago
    for offset in (0, 1, 2):
        d_iso = (today - timedelta(days=offset)).isoformat()
        client.post(
            f"/api/habits/{h_id}/toggle",
            json={"log_date": d_iso, "completed": True},
        )

    # Fetch habit analytics
    res = client.get("/api/analytics/habits?days_count=30")
    assert res.status_code == 200
    analytics = res.json()

    assert "days" in analytics
    assert len(analytics["days"]) == 30
    assert "overall_stats" in analytics
    assert analytics["overall_stats"]["best_current_streak"] >= 3

    # Check today's heatmap day record
    today_record = next(d for d in analytics["days"] if d["date"] == today.isoformat())
    assert today_record["habits"]["code-review"] is True
    assert today_record["completed_count"] >= 1


def test_journal_templates_and_rendering(client):
    # 1. Fetch default templates
    res = client.get("/api/templates")
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) >= 3
    default_tpl = next(t for t in templates if t["is_default"])
    assert "Reflection" in default_tpl["name"]

    # 2. Render journal template for a date
    render_res = client.get("/api/journal/template?target_date=2026-11-02")
    if render_res.status_code != 200:
        print("DEBUG RENDER_RES:", render_res.json())
    assert render_res.status_code == 200
    data = render_res.json()
    assert "2026-11-02" in data["content_md"]
    assert "Monday" in data["content_md"]
    assert "@habit(" in data["content_md"]

    # 3. Create custom template
    create_res = client.post(
        "/api/templates",
        json={
            "name": "Custom Focus Sprint",
            "description": "Morning focus blocks",
            "content_md": "# Focus on {{date}}\n- [ ] Deep work 90m",
            "is_default": False,
        },
    )
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # 4. Update custom template
    update_res = client.put(
        f"/api/templates/{created_id}",
        json={
            "name": "Deep Work Sprint",
            "content_md": "# Deep Work — {{date}}\n- [ ] 2x 90m blocks",
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Deep Work Sprint"

    # 5. Delete custom template
    del_res = client.delete(f"/api/templates/{created_id}")
    assert del_res.status_code == 200
