"""One-step database initializer for ChronoNote (PostgreSQL 16 + fallback)."""

from urllib.parse import urlparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from backend.config import settings
from backend.database import Base, build_engine
import backend.models  # noqa: F401 - register models on Base.metadata


def ensure_postgres_database_exists(db_url: str) -> bool:
    if not db_url.startswith("postgresql"):
        return False

    parsed = urlparse(db_url.replace("postgresql+psycopg2://", "postgresql://"))
    dbname = (parsed.path or "/chrononote").lstrip("/") or "chrononote"
    user = parsed.username or "postgres"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname="postgres",
            connect_timeout=3,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        exists = cur.fetchone() is not None
        if not exists:
            cur.execute(f'CREATE DATABASE "{dbname}"')
            print(f"[OK] Created PostgreSQL database '{dbname}' on {host}:{port}.")
        else:
            print(f"[OK] PostgreSQL database '{dbname}' already exists on {host}:{port}.")
        cur.close()
        conn.close()
        return True
    except Exception as exc:
        print(f"[INFO] Could not connect to PostgreSQL on {host}:{port} ({exc.__class__.__name__}: {exc})")
        print("       Update DATABASE_URL in .env with your PostgreSQL password to use Postgres.")
        return False


def main() -> None:
    pg_ready = ensure_postgres_database_exists(settings.DATABASE_URL)
    eng, dialect = build_engine(allow_fallback=not pg_ready)
    Base.metadata.create_all(bind=eng)
    print(f"[OK] ChronoNote schema initialized successfully using dialect: {dialect.upper()}")


if __name__ == "__main__":
    main()
