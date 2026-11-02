import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.schema import CreateIndex, CreateTable

from backend.config import settings

logger = logging.getLogger("chrononote.db")

Base = declarative_base()


def build_engine(database_url: str | None = None, allow_fallback: bool | None = None) -> tuple[Engine, str]:
    """Create a SQLAlchemy Engine targeting PostgreSQL by default, with optional SQLite fallback."""
    target_url = (database_url or settings.DATABASE_URL).strip()
    fallback = settings.AUTO_FALLBACK_SQLITE if allow_fallback is None else allow_fallback

    # Normalize legacy postgres:// scheme to postgresql://
    if target_url.startswith("postgres://"):
        target_url = target_url.replace("postgres://", "postgresql://", 1)

    if target_url.startswith("postgresql"):
        try:
            pg_engine = create_engine(
                target_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                connect_args={"connect_timeout": 10},
            )
            if not fallback:
                return pg_engine, "postgresql"

            with pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return pg_engine, "postgresql"
        except Exception as exc:
            if not fallback:
                raise
            logger.warning(
                "PostgreSQL at %s unreachable or awaiting credentials (%s); using fallback %s",
                target_url,
                exc.__class__.__name__,
                settings.SQLITE_FALLBACK_URL,
            )
            target_url = settings.SQLITE_FALLBACK_URL

    sqlite_engine = create_engine(
        target_url,
        connect_args={"check_same_thread": False} if target_url.startswith("sqlite") else {},
    )
    if target_url.startswith("sqlite"):
        @event.listens_for(sqlite_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return sqlite_engine, "sqlite"


engine, ACTIVE_DB_DIALECT = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def compile_postgres_ddl() -> str:
    """Compile all SQLAlchemy ORM tables and indexes into native PostgreSQL DDL statements."""
    pg_dialect = postgresql.dialect()
    statements: list[str] = []
    for table in Base.metadata.sorted_tables:
        create_tbl = str(CreateTable(table).compile(dialect=pg_dialect)).strip()
        statements.append(f"{create_tbl};")
        for idx in table.indexes:
            create_idx = str(CreateIndex(idx).compile(dialect=pg_dialect)).strip()
            statements.append(f"{create_idx};")
    return "\n\n".join(statements)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
