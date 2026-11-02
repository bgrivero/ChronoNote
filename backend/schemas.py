from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


ProjectStatus = Literal["planned", "active", "on_hold", "completed", "archived"]
TaskStatus = Literal["todo", "in_progress", "review", "done"]
TaskPriority = Literal["low", "medium", "high", "urgent"]


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=140)
    description: str = ""
    color: str = "#6366f1"
    icon: str = "folder"
    status: ProjectStatus = "active"
    is_pinned: bool = False
    sidebar_order: int = 0
    start_date: date | None = None
    target_date: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    color: str | None = None
    icon: str | None = None
    status: ProjectStatus | None = None
    is_pinned: bool | None = None
    sidebar_order: int | None = None
    start_date: date | None = None
    target_date: date | None = None


class SidebarReorderRequest(BaseModel):
    ordered_project_ids: list[int]


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str
    color: str
    icon: str
    status: str
    is_pinned: bool
    sidebar_order: int
    start_date: date | None
    target_date: date | None
    created_at: datetime
    updated_at: datetime


class SidebarProjectItem(ProjectOut):
    total_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = 0
    progress_pct: float = 0.0
    note_count: int = 0


class TaskCreate(BaseModel):
    project_id: int
    source_note_id: int | None = None
    title: str = Field(..., min_length=1, max_length=240)
    description: str = ""
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    color: str = "#0891b2"
    start_date: date | None = None
    due_date: date | None = None
    is_milestone: bool = False
    depends_on_id: int | None = None
    progress: int = Field(default=0, ge=0, le=100)
    cascade_dependencies: bool = True


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    color: str | None = None
    start_date: date | None = None
    due_date: date | None = None
    is_milestone: bool | None = None
    depends_on_id: int | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    cascade_dependencies: bool = True


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    source_note_id: int | None
    title: str
    description: str
    status: str
    priority: str
    color: str = "#0891b2"
    start_date: date | None
    due_date: date | None
    is_milestone: bool
    depends_on_id: int | None
    progress: int
    cascaded_task_ids: list[int] = []
    created_at: datetime
    updated_at: datetime


class CriticalPathOut(BaseModel):
    project_id: int
    critical_path_task_ids: list[int]
    total_duration_days: int


class WikiLinkItem(BaseModel):
    target_slug: str
    target_note_id: int | None
    display_text: str
    context_snippet: str


class BacklinkItem(BaseModel):
    source_note_id: int
    source_title: str
    source_slug: str
    context_snippet: str


class NoteCreate(BaseModel):
    project_id: int | None = None
    title: str = Field(..., min_length=1, max_length=200)
    slug: str | None = None
    content_md: str = ""
    is_pinned: bool = False
    is_daily_note: bool = False
    note_date: date | None = None
    sync_inline_tasks: bool = True


class NoteUpdate(BaseModel):
    project_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content_md: str | None = None
    is_pinned: bool | None = None
    note_date: date | None = None
    sync_inline_tasks: bool = True


class NoteOut(BaseModel):
    id: int
    project_id: int | None
    title: str
    slug: str
    content_md: str
    frontmatter: dict[str, Any]
    tags: list[str]
    is_pinned: bool
    is_daily_note: bool
    note_date: date | None
    outgoing_links: list[WikiLinkItem] = []
    backlinks: list[BacklinkItem] = []
    synced_task_ids: list[int] = []
    created_at: datetime
    updated_at: datetime


class TimelineNotePin(BaseModel):
    note_id: int
    title: str
    slug: str
    note_date: date
    is_daily_note: bool
    tags: list[str]


class TimelineDependencyEdge(BaseModel):
    from_task_id: int
    to_task_id: int
    project_id: int


class TimelineSwimlane(BaseModel):
    project: SidebarProjectItem
    tasks: list[TaskOut]
    milestones: list[TaskOut]
    note_pins: list[TimelineNotePin]
    critical_path_task_ids: list[int] = []
    critical_path_days: int = 0


class TimelineResponse(BaseModel):
    window_start: date
    window_end: date
    total_days: int
    swimlanes: list[TimelineSwimlane]
    daily_notes: list[TimelineNotePin]
    dependencies: list[TimelineDependencyEdge]


class KanbanColumn(BaseModel):
    status: TaskStatus
    label: str
    count: int
    tasks: list[TaskOut]


class KanbanBoardResponse(BaseModel):
    project_id: int | None = None
    total_tasks: int
    columns: list[KanbanColumn]


class KanbanMoveRequest(BaseModel):
    task_id: int
    target_status: TaskStatus
    progress: int | None = Field(default=None, ge=0, le=100)


class ProjectKanbanColumn(BaseModel):
    status: ProjectStatus
    label: str
    count: int
    projects: list[SidebarProjectItem]


class ProjectKanbanBoardResponse(BaseModel):
    total_projects: int
    columns: list[ProjectKanbanColumn]


class ProjectKanbanMoveRequest(BaseModel):
    project_id: int
    target_status: ProjectStatus
    sidebar_order: int | None = None
    ordered_project_ids: list[int] | None = None


class GraphNode(BaseModel):
    id: str
    kind: Literal["project", "note", "tag"]
    label: str
    color: str
    entity_id: int | None = None
    slug: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: Literal["wikilink", "belongs_to", "tagged"]
    label: str = ""


class KnowledgeGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class SearchResultItem(BaseModel):
    kind: Literal["project", "note", "task"]
    id: int
    title: str
    subtitle: str
    project_id: int | None = None
    slug: str | None = None
    matched_tags: list[str] = []


class GoogleAuthRequest(BaseModel):
    credential: str | None = None
    email: str | None = None
    name: str | None = None
    picture: str | None = None


class AuthRegisterRequest(BaseModel):
    email: str
    name: str | None = None
    password: str | None = None


class AuthLoginRequest(BaseModel):
    email: str
    password: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    picture: str
    created_at: datetime
    last_login_at: datetime


class AuthSessionOut(BaseModel):
    token: str
    user: UserOut
    expires_at: str


class AuthConfigOut(BaseModel):
    google_client_id: str
    auth_required: bool
    has_allowlist: bool
    has_server_ocr_key: bool = False


class JournalUpsertRequest(BaseModel):
    title: str | None = None
    content_md: str = ""
    project_id: int | None = None
    sync_inline_tasks: bool = True


class JournalLockStatusOut(BaseModel):
    has_password: bool
    is_unlocked: bool


class JournalSetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=1)
    current_password: str | None = None


class JournalUnlockRequest(BaseModel):
    password: str


class JournalUnlockResponse(BaseModel):
    success: bool
    journal_token: str
    message: str = "Journal unlocked"


class OcrVisionRequest(BaseModel):
    image_base64: str = Field(..., min_length=10)
    mime_type: str = "image/png"
    gemini_api_key: str | None = None


class OcrVisionResponse(BaseModel):
    text: str
    engine: str = "gemini-vision"


class HabitCreate(BaseModel):
    slug: str | None = Field(default=None, max_length=100)
    name: str = Field(..., min_length=1, max_length=140)
    description: str = ""
    icon: str = "check"
    color: str = "#10b981"
    target_days_per_week: int = Field(default=7, ge=1, le=7)


class HabitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=140)
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    target_days_per_week: int | None = Field(default=None, ge=1, le=7)
    archived: bool | None = None


class HabitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    icon: str
    color: str
    target_days_per_week: int
    archived: bool
    current_streak: int = 0
    longest_streak: int = 0
    total_completions: int = 0
    completion_rate_30d: float = 0.0
    created_at: datetime
    updated_at: datetime


class HabitToggleRequest(BaseModel):
    log_date: date | None = None
    completed: bool | None = None
    value: str | None = None


class HabitLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    habit_id: int
    log_date: date
    completed: bool
    value: str | None = None


class HabitHeatmapDay(BaseModel):
    date: str
    total_habits: int
    completed_count: int
    rate: float
    habits: dict[str, bool]


class HabitAnalyticsOut(BaseModel):
    days: list[HabitHeatmapDay]
    overall_stats: dict[str, Any]
    habit_streaks: list[dict[str, Any]]


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = ""
    content_md: str
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    content_md: str | None = None
    is_default: bool | None = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    content_md: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class TemplateRenderedOut(BaseModel):
    content_md: str
    template_name: str

