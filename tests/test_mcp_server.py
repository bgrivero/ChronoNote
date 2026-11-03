import pytest
from backend.database import SessionLocal
from backend.models import User
from backend.services.auth_service import hash_password
from backend.services.mcp_auth import clear_local_session, generate_mcp_code
from backend.mcp_server import (
    connect_with_code,
    create_project,
    create_project_note,
    create_project_with_tasks,
    create_task,
    get_project,
    list_projects,
    login,
    logout,
    server,
    update_project,
    whoami,
)


@pytest.fixture(autouse=True)
def reset_mcp_auth():
    clear_local_session()
    yield
    clear_local_session()


@pytest.fixture
def auth_users():
    db = SessionLocal()
    # Create User A with password
    u1 = db.query(User).filter(User.email == "alice@example.com").first()
    if not u1:
        h1, s1 = hash_password("AliceSecret123")
        u1 = User(email="alice@example.com", name="Alice", password_hash=h1, salt=s1)
        db.add(u1)

    # Create User B with password
    u2 = db.query(User).filter(User.email == "bob@example.com").first()
    if not u2:
        h2, s2 = hash_password("BobSecret456")
        u2 = User(email="bob@example.com", name="Bob", password_hash=h2, salt=s2)
        db.add(u2)

    db.commit()
    db.refresh(u1)
    db.refresh(u2)
    user_ids = (u1.id, u2.id)
    db.close()
    return user_ids


@pytest.mark.anyio
async def test_mcp_server_tool_registration():
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    assert "login" in tool_names
    assert "connect_with_code" in tool_names
    assert "connect_with_token" in tool_names
    assert "whoami" in tool_names
    assert "logout" in tool_names
    assert "create_project" in tool_names
    assert "create_project_with_tasks" in tool_names
    assert "list_projects" in tool_names
    assert "get_project" in tool_names
    assert "create_task" in tool_names
    assert "update_project" in tool_names
    assert "create_project_note" in tool_names


def test_mcp_requires_authentication():
    # Attempting to list or create projects without logging in must fail
    res = list_projects()
    assert res["success"] is False
    assert res["authenticated"] is False
    assert "Authentication required" in res["error"]

    c_res = create_project(name="Unauthorized Project")
    assert c_res["success"] is False
    assert c_res["authenticated"] is False

    w_res = whoami()
    assert w_res["authenticated"] is False


def test_mcp_login_flow(auth_users):
    # Wrong password fails
    wrong = login(email="alice@example.com", password="WrongPassword")
    assert wrong["success"] is False
    assert wrong["authenticated"] is False

    # Correct login succeeds
    success = login(email="alice@example.com", password="AliceSecret123")
    assert success["success"] is True
    assert success["authenticated"] is True
    assert success["user"]["email"] == "alice@example.com"

    # whoami shows Alice
    w = whoami()
    assert w["authenticated"] is True
    assert w["user"]["email"] == "alice@example.com"

    # Alice creates a project
    p = create_project(name="Alice Secret App")
    assert p["success"] is True
    assert p["project"]["name"] == "Alice Secret App"
    p_id = p["project"]["id"]

    # Projects list contains Alice's project
    projs = list_projects()
    assert projs["success"] is True
    assert any(item["id"] == p_id for item in projs["projects"])

    # Logout locks workspace again
    logout()
    locked = list_projects()
    assert locked["success"] is False
    assert locked["authenticated"] is False


def test_mcp_connect_with_code_and_user_isolation(auth_users):
    alice_id, bob_id = auth_users

    # 1. Generate code for Bob
    code = generate_mcp_code(bob_id, "bob@example.com", "Bob")

    # Connect Claude as Bob using code
    conn = connect_with_code(code)
    assert conn["success"] is True
    assert conn["user"]["email"] == "bob@example.com"

    # Bob creates a project
    bp = create_project_with_tasks(
        name="Bob Personal Task Tracker",
        tasks=[{"title": "Subtask 1", "status": "todo"}],
    )
    assert bp["success"] is True
    bob_proj_id = bp["project"]["id"]

    # 2. Switch user to Alice
    logout()
    login(email="alice@example.com", password="AliceSecret123")

    # Alice's project list must NOT contain Bob's project
    alice_projs = list_projects()
    assert alice_projs["success"] is True
    assert not any(item["id"] == bob_proj_id for item in alice_projs["projects"])

    # Alice cannot get Bob's project
    forbidden = get_project(project_id=bob_proj_id)
    assert forbidden["success"] is False
