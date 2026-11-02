from datetime import date, datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), unique=True, index=True, nullable=False)
    name = Column(String(160), nullable=False, default="")
    picture = Column(String(500), default="")
    google_sub = Column(String(120), unique=True, index=True, nullable=True)
    password_hash = Column(String(128), nullable=True)
    salt = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    last_login_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    journal_secrets = relationship("JournalSecret", back_populates="owner", cascade="all, delete-orphan")
    habits = relationship("Habit", back_populates="owner", cascade="all, delete-orphan")
    habit_logs = relationship("HabitLog", back_populates="owner", cascade="all, delete-orphan")
    templates = relationship("JournalTemplate", back_populates="owner", cascade="all, delete-orphan")


class JournalSecret(Base):
    __tablename__ = "journal_secrets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=True, index=True)
    password_hash = Column(String(128), nullable=False)
    salt = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    owner = relationship("User", back_populates="journal_secrets")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(140), unique=True, index=True, nullable=False)
    description = Column(Text, default="")
    color = Column(String(20), default="#6366f1")
    icon = Column(String(40), default="folder")
    status = Column(String(30), default="active", index=True)  # planned, active, on_hold, completed, archived
    is_pinned = Column(Boolean, default=False, index=True)
    sidebar_order = Column(Integer, default=0, index=True)
    start_date = Column(Date, nullable=True)
    target_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    source_note_id = Column(Integer, ForeignKey("notes.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(240), nullable=False)
    description = Column(Text, default="")
    status = Column(String(30), default="todo", index=True)  # todo, in_progress, review, done
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    color = Column(String(20), default="#0891b2")
    start_date = Column(Date, nullable=True, index=True)
    due_date = Column(Date, nullable=True, index=True)
    is_milestone = Column(Boolean, default=False)
    depends_on_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    progress = Column(Integer, default=0)  # 0..100
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project = relationship("Project", back_populates="tasks")
    source_note = relationship("Note", back_populates="extracted_tasks")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    content_md = Column(Text, nullable=False, default="")
    frontmatter_json = Column(Text, default="{}")
    tags_json = Column(Text, default="[]")
    is_pinned = Column(Boolean, default=False)
    is_daily_note = Column(Boolean, default=False, index=True)
    note_date = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    owner = relationship("User", back_populates="notes")
    project = relationship("Project", back_populates="notes")
    extracted_tasks = relationship("Task", back_populates="source_note")
    habit_logs = relationship("HabitLog", back_populates="note")
    outgoing_links = relationship(
        "NoteLink",
        foreign_keys="NoteLink.source_note_id",
        back_populates="source_note",
        cascade="all, delete-orphan",
    )
    incoming_links = relationship(
        "NoteLink",
        foreign_keys="NoteLink.target_note_id",
        back_populates="target_note",
    )


class NoteLink(Base):
    __tablename__ = "note_links"

    id = Column(Integer, primary_key=True, index=True)
    source_note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_note_id = Column(Integer, ForeignKey("notes.id", ondelete="SET NULL"), nullable=True, index=True)
    target_slug = Column(String(220), nullable=False, index=True)
    display_text = Column(String(220), nullable=False)
    context_snippet = Column(String(300), default="")

    source_note = relationship("Note", foreign_keys=[source_note_id], back_populates="outgoing_links")
    target_note = relationship("Note", foreign_keys=[target_note_id], back_populates="incoming_links")


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    slug = Column(String(100), nullable=False, index=True)
    name = Column(String(140), nullable=False)
    description = Column(Text, default="")
    icon = Column(String(40), default="check")
    color = Column(String(20), default="#10b981")
    target_days_per_week = Column(Integer, default=7)
    archived = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    owner = relationship("User", back_populates="habits")
    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="SET NULL"), nullable=True, index=True)
    log_date = Column(Date, nullable=False, index=True)
    completed = Column(Boolean, default=True, index=True)
    value = Column(String(60), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    habit = relationship("Habit", back_populates="logs")
    owner = relationship("User", back_populates="habit_logs")
    note = relationship("Note", back_populates="habit_logs")


class JournalTemplate(Base):
    __tablename__ = "journal_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(String(240), default="")
    content_md = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    owner = relationship("User", back_populates="templates")

