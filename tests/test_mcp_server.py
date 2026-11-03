import pytest
from backend.mcp_server import (
    create_project,
    create_project_note,
    create_project_with_tasks,
    create_task,
    get_project,
    list_projects,
    server,
    update_project,
)


@pytest.mark.anyio
async def test_mcp_server_tool_registration():
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    assert "create_project" in tool_names
    assert "create_project_with_tasks" in tool_names
    assert "list_projects" in tool_names
    assert "get_project" in tool_names
    assert "create_task" in tool_names
    assert "update_project" in tool_names
    assert "create_project_note" in tool_names


def test_mcp_create_project_and_list():
    res = create_project(
        name="AI MCP Agent Project",
        description="Autonomous agent integration via Model Context Protocol",
        color="#8b5cf6",
        icon="rocket",
        status="active",
        is_pinned=True,
        start_date="2026-11-05",
        target_date="2026-11-20",
    )
    assert res["success"] is True
    proj = res["project"]
    assert proj["name"] == "AI MCP Agent Project"
    assert proj["is_pinned"] is True
    assert proj["icon"] == "rocket"
    proj_id = proj["id"]

    # Verify in list
    listing = list_projects()
    assert listing["success"] is True
    found = any(p["id"] == proj_id for p in listing["projects"])
    assert found is True


def test_mcp_create_project_with_tasks_and_notes():
    res = create_project_with_tasks(
        name="Mobile App Launch",
        description="Comprehensive mobile client delivery",
        color="#0ea5e9",
        icon="target",
        status="active",
        tasks=[
            {
                "title": "Design Figma prototype",
                "status": "done",
                "priority": "high",
                "start_date": "2026-11-01",
                "due_date": "2026-11-05",
            },
            {
                "title": "Develop Swift iOS client",
                "status": "in_progress",
                "priority": "urgent",
                "start_date": "2026-11-06",
                "due_date": "2026-11-15",
            },
            {
                "title": "App Store submission",
                "status": "todo",
                "priority": "high",
                "is_milestone": True,
                "due_date": "2026-11-25",
            },
        ],
        initial_note="# Mobile Launch Roadmap\n\nDeliverables:\n- [[iOS]] release\n- [[Android]] beta\n#mobile #release",
    )
    assert res["success"] is True
    proj = res["project"]
    assert proj["total_tasks"] == 3
    assert proj["completed_tasks"] == 1
    assert proj["progress_pct"] == 33.3
    assert proj["note_count"] == 1
    assert len(proj["tasks"]) == 3
    assert len(proj["notes"]) == 1

    # Verify get_project
    details = get_project(project_id=proj["id"])
    assert details["success"] is True
    assert details["project"]["name"] == "Mobile App Launch"


def test_mcp_create_task_and_update_project():
    proj_res = create_project(name="DevOps Infrastructure")
    proj_id = proj_res["project"]["id"]

    # Add task
    task_res = create_task(
        project_id=proj_id,
        title="Setup GitHub Actions CI/CD",
        priority="high",
        status="in_progress",
        progress=50,
    )
    assert task_res["success"] is True
    assert task_res["task"]["title"] == "Setup GitHub Actions CI/CD"
    assert task_res["task"]["progress"] == 50

    # Add note
    note_res = create_project_note(
        project_id=proj_id,
        title="CI Architecture",
        content="## CI Pipeline\n- [ ] Add lint check @due(2026-11-10)\n#devops #ci",
    )
    assert note_res["success"] is True
    assert note_res["note"]["title"] == "CI Architecture"

    # Update project
    upd_res = update_project(
        project_id=proj_id,
        status="completed",
        is_pinned=True,
    )
    assert upd_res["success"] is True
    assert upd_res["project"]["status"] == "completed"
    assert upd_res["project"]["is_pinned"] is True
