import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from typing import Any
import httpx

from backend.config import settings


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(encoded + padding)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash password with PBKDF2 HMAC SHA-256."""
    import secrets
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000,
    ).hex()
    return hashed, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify password against stored PBKDF2 hash."""
    expected_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(expected_hash, hashed)


def create_journal_session_token(
    user_id: int | None = None,
    expires_hours: int = 24,
) -> str:
    """Create a temporary signed token allowing journal access for this session."""
    exp_dt = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = {
        "scope": "journal",
        "sub": str(user_id) if user_id is not None else "anonymous",
        "exp": int(exp_dt.timestamp()),
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        f"journal:{payload_b64}".encode("ascii"),
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{payload_b64}.{sig_b64}"


def verify_journal_session_token(token: str, user_id: int | None = None) -> bool:
    """Verify a journal session token."""
    if not token or "." not in token:
        return False
    parts = token.split(".")
    if len(parts) != 2:
        return False
    payload_b64, sig_b64 = parts
    expected_sig = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        f"journal:{payload_b64}".encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        return False
    if not hmac.compare_digest(expected_sig, actual_sig):
        return False
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        return False
    if payload.get("scope") != "journal":
        return False
    exp = payload.get("exp", 0)
    if int(datetime.now(timezone.utc).timestamp()) > int(exp):
        return False
    expected_sub = str(user_id) if user_id is not None else "anonymous"
    # Allow token if sub matches or if sub is anonymous and user_id is None
    return payload.get("sub") == expected_sub


def get_allowed_emails() -> set[str]:
    raw = (settings.ALLOWED_GOOGLE_EMAILS or "").strip()
    if not raw:
        return set()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def is_email_allowed(email: str) -> bool:
    allowed = get_allowed_emails()
    if not allowed:
        return True
    return email.strip().lower() in allowed


def create_session_token(
    user_id: int,
    email: str,
    name: str = "",
    expires_days: int = 30,
) -> tuple[str, str]:
    exp_dt = datetime.now(timezone.utc) + timedelta(days=expires_days)
    payload = {
        "sub": str(user_id),
        "email": email,
        "name": name,
        "exp": int(exp_dt.timestamp()),
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{payload_b64}.{sig_b64}", exp_dt.isoformat()


def verify_session_token(token: str) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    parts = token.split(".")
    if len(parts) != 2:
        return None
    payload_b64, sig_b64 = parts
    expected_sig = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        return None
    if not hmac.compare_digest(expected_sig, actual_sig):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        return None
    exp = payload.get("exp", 0)
    if int(datetime.now(timezone.utc).timestamp()) > int(exp):
        return None
    return payload


def verify_google_id_token(credential: str) -> dict[str, Any]:
    """
    Verify a Google Identity Services ID token (JWT) against Google's tokeninfo endpoint.
    In non-production environments, also supports structured dev/test JWTs for automated testing.
    """
    # Check if this is a test/dev mock credential in non-production
    if credential.startswith("dev-google-jwt:") and settings.APP_ENV != "production":
        try:
            raw_json = _b64url_decode(credential.split(":", 1)[1]).decode("utf-8")
            data = json.loads(raw_json)
            return {
                "sub": data.get("sub") or f"google-{data.get('email', 'user')}",
                "email": data["email"],
                "name": data.get("name", data["email"].split("@")[0]),
                "picture": data.get("picture", ""),
                "email_verified": True,
            }
        except Exception as exc:
            raise ValueError("Invalid dev Google token") from exc

    # Verify real Google ID token via Google OAuth2 tokeninfo endpoint
    try:
        resp = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": credential},
            timeout=8.0,
        )
    except Exception as exc:
        raise ValueError("Unable to reach Google token verification service") from exc

    if resp.status_code != 200:
        raise ValueError("Invalid or expired Google ID token")

    info = resp.json()
    if settings.GOOGLE_CLIENT_ID and info.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise ValueError("Google ID token audience mismatch")

    if str(info.get("email_verified", "")).lower() not in ("true", "1"):
        raise ValueError("Google account email is not verified")

    return {
        "sub": info.get("sub", ""),
        "email": info.get("email", ""),
        "name": info.get("name", info.get("email", "").split("@")[0]),
        "picture": info.get("picture", ""),
        "email_verified": True,
    }
