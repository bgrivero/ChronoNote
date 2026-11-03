from fastapi.testclient import TestClient

from backend.main import app
from backend.models import User
from backend.services.auth_service import create_session_token, hash_password


def test_account_settings_username_update(client, db_session):
    pwd_hash, salt = hash_password("OldPassword123!")
    user = User(
        email="settings_user@example.com",
        name="Original Name",
        password_hash=pwd_hash,
        salt=salt,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token, _ = create_session_token(user.id, user.email, user.name)
    headers = {"Authorization": f"Bearer {token}"}

    # Update Username
    res = client.patch(
        "/api/auth/profile",
        json={"name": "New Minimal User"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["name"] == "New Minimal User"
    assert data["user"]["has_password"] is True


def test_account_settings_strict_password_rules(client, db_session):
    pwd_hash, salt = hash_password("CurrentPass123!")
    user = User(
        email="strict_user@example.com",
        name="Strict User",
        password_hash=pwd_hash,
        salt=salt,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token, _ = create_session_token(user.id, user.email, user.name)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Reject too short (< 8)
    res = client.patch(
        "/api/auth/profile",
        json={
            "current_password": "CurrentPass123!",
            "new_password": "Sh1!",
            "confirm_password": "Sh1!",
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "at least 8 characters" in res.json()["detail"]

    # 2. Reject no uppercase
    res = client.patch(
        "/api/auth/profile",
        json={
            "current_password": "CurrentPass123!",
            "new_password": "lowercase123!",
            "confirm_password": "lowercase123!",
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "uppercase" in res.json()["detail"].lower()

    # 3. Reject no lowercase
    res = client.patch(
        "/api/auth/profile",
        json={
            "current_password": "CurrentPass123!",
            "new_password": "UPPERCASE123!",
            "confirm_password": "UPPERCASE123!",
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "lowercase" in res.json()["detail"].lower()

    # 4. Reject no number
    res = client.patch(
        "/api/auth/profile",
        json={
            "current_password": "CurrentPass123!",
            "new_password": "NoNumbersHere!",
            "confirm_password": "NoNumbersHere!",
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "digit" in res.json()["detail"].lower() or "number" in res.json()["detail"].lower()

    # 5. Reject no special character
    res = client.patch(
        "/api/auth/profile",
        json={
            "current_password": "CurrentPass123!",
            "new_password": "ValidPassword99",
            "confirm_password": "ValidPassword99",
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "special character" in res.json()["detail"].lower()

    # 6. Reject mismatched confirmation
    res = client.patch(
        "/api/auth/profile",
        json={
            "current_password": "CurrentPass123!",
            "new_password": "StrictPassword123#",
            "confirm_password": "MismatchPassword123#",
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "match" in res.json()["detail"].lower()

    # 7. Reject wrong current password
    res = client.patch(
        "/api/auth/profile",
        json={
            "current_password": "WrongPassword999!",
            "new_password": "StrictPassword123#",
            "confirm_password": "StrictPassword123#",
        },
        headers=headers,
    )
    assert res.status_code == 401
    assert "Current password is incorrect" in res.json()["detail"]

    # 8. Reject new password identical to current password
    res = client.patch(
        "/api/auth/profile",
        json={
            "current_password": "CurrentPass123!",
            "new_password": "CurrentPass123!",
            "confirm_password": "CurrentPass123!",
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "same as current" in res.json()["detail"].lower()

    # 9. Successful strict password update
    res = client.patch(
        "/api/auth/profile",
        json={
            "current_password": "CurrentPass123!",
            "new_password": "StrictPassword123#",
            "confirm_password": "StrictPassword123#",
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert "token" in res.json()
