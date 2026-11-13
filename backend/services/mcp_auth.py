"""ChronoNote MCP Authentication & Session Service
Handles user login, 6-digit connection codes, session token verification,
and session persistence for MCP clients (Claude Desktop, Claude Code, etc.).
"""

from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import SessionLocal, engine
from backend.models import McpConnectionCode, User
from backend.services.auth_service import (
    create_session_token,
    verify_password,
    verify_session_token,
)

# In-memory store for 6-digit connection codes: code -> metadata
# code: {"user_id": int, "email": str, "name": str, "expires_at": float}
_MCP_CODES: dict[str, dict[str, Any]] = {}

# In-memory active user for this process session
_active_user_id: int | None = None

# Local persistent session file path
_SESSION_FILE = Path(os.getenv("USERPROFILE", ".")) / ".chrononote_mcp_session.json"


def _ensure_mcp_codes_table() -> None:
    try:
        McpConnectionCode.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        pass


def generate_mcp_code(user_id: int, email: str, name: str = "", ttl_seconds: int = 900) -> str:
    """Generate a 6-digit temporary connection code for an authenticated user."""
    now = int(time.time())
    expires_at = now + int(ttl_seconds)
    code = f"{secrets.randbelow(900000) + 100000}"

    # Persist in DB so separate processes (e.g. FastAPI web server + stdio run_mcp.py) share codes
    _ensure_mcp_codes_table()
    db = SessionLocal()
    try:
        db.query(McpConnectionCode).filter(McpConnectionCode.expires_at < now).delete()
        row = McpConnectionCode(
            code=code,
            user_id=user_id,
            email=email,
            name=name or "",
            expires_at=expires_at,
        )
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        # Fallback to in-memory if DB insert fails (e.g., transient test setup)
        expired = [k for k, v in _MCP_CODES.items() if now > v.get("expires_at", 0)]
        for k in expired:
            _MCP_CODES.pop(k, None)
        _MCP_CODES[code] = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "expires_at": float(expires_at),
        }
    finally:
        db.close()

    return code


def verify_and_consume_code(code: str) -> dict[str, Any] | None:
    """Validate and consume a 6-digit connection code (single use)."""
    cleaned = code.strip().replace(" ", "").replace("-", "")
    now = int(time.time())

    _ensure_mcp_codes_table()
    db = SessionLocal()
    try:
        row = db.query(McpConnectionCode).filter(McpConnectionCode.code == cleaned).first()
        if row:
            entry = {
                "user_id": row.user_id,
                "email": row.email,
                "name": row.name,
                "expires_at": row.expires_at,
            }
            is_valid = now <= row.expires_at
            db.delete(row)
            db.commit()
            return entry if is_valid else None
    except Exception:
        db.rollback()
    finally:
        db.close()

    entry = _MCP_CODES.get(cleaned)
    if not entry:
        return None
    if time.time() > entry.get("expires_at", 0):
        _MCP_CODES.pop(cleaned, None)
        return None

    _MCP_CODES.pop(cleaned, None)
    return entry


def save_local_session(token: str, user_id: int, email: str) -> None:
    """Persist session token locally so the user stays logged in across Claude Desktop restarts."""
    try:
        data = {
            "token": token,
            "user_id": user_id,
            "email": email,
            "saved_at": time.time(),
        }
        _SESSION_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def load_local_session() -> str | None:
    """Load persistent session token if valid."""
    try:
        if _SESSION_FILE.is_file():
            data = json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
            token = data.get("token")
            if token:
                claims = verify_session_token(token)
                if claims:
                    return token
    except Exception:
        pass
    return None


def clear_local_session() -> None:
    """Delete persistent session file upon logout."""
    global _active_user_id
    _active_user_id = None
    try:
        if _SESSION_FILE.is_file():
            _SESSION_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def set_active_user_id(uid: int | None) -> None:
    global _active_user_id
    _active_user_id = uid


def get_active_user_id() -> int | None:
    return _active_user_id


def resolve_authenticated_user(db: Session, token: str | None = None) -> User | None:
    """Resolve the currently authenticated user for an MCP call.
    Checks:
    1. Explicit token (if provided in tool call or header)
    2. Active session in-memory (_active_user_id)
    3. Persistent local session file (~/.chrononote_mcp_session.json)
    4. Environment variable CHRONONOTE_SESSION_TOKEN
    """
    global _active_user_id

    # 1. Check explicit token
    target_token = token or os.getenv("CHRONONOTE_SESSION_TOKEN")
    if target_token:
        claims = verify_session_token(target_token)
        if claims and claims.get("sub"):
            try:
                uid = int(claims["sub"])
                user = db.query(User).filter(User.id == uid).first()
                if user:
                    _active_user_id = user.id
                    return user
            except (ValueError, TypeError):
                pass

    # 2. Check in-memory active user
    if _active_user_id is not None:
        user = db.query(User).filter(User.id == _active_user_id).first()
        if user:
            return user
        _active_user_id = None

    # 3. Check persistent session file
    saved_token = load_local_session()
    if saved_token:
        claims = verify_session_token(saved_token)
        if claims and claims.get("sub"):
            try:
                uid = int(claims["sub"])
                user = db.query(User).filter(User.id == uid).first()
                if user:
                    _active_user_id = user.id
                    return user
            except (ValueError, TypeError):
                pass

    return None
