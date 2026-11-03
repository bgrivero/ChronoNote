# ChronoNote v2.0 — Unified Markdown Note-Taking, Project Timeline, Kanban & Knowledge Graph Specification

## 1. Product Vision & Overview

**ChronoNote** is a full-stack knowledge base and project management workspace built with **FastAPI**, **PostgreSQL 16** (with SQLAlchemy 2.0 + automatic dev/test SQLite fallback), and **Vue 3** (Composition API + Pinia).

### Core Capabilities (All Implemented & Tested)
1. **Left Sidebar (Project Navigator & Rollup Hub)**:
   - Pinned and active projects ordered by `is_pinned DESC, sidebar_order ASC`.
   - Live rollup metrics (`total_tasks`, `completed_tasks`, `overdue_tasks`, `progress_pct`, `note_count`).
   - Drag-and-drop project reordering (`PATCH /api/sidebar/projects/reorder`).
2. **Multi-View Workspace Switcher (`Timeline` | `Kanban` | `Knowledge Graph`)**:
   - **Timeline View (`GET /api/timeline`)**: Horizontal project swimlanes aligned with the Left Sidebar, task duration bars, milestone diamonds (`◆`), SVG cubic Bezier dependency connectors, **Critical Path highlighting**, **Daily Note header strip (`📅`)**, and **Project Note Pins (`📝`)**.
   - **Kanban Board View (`GET /api/kanban` & `PATCH /api/kanban/move`)**: 4-column workflow (`To Do`, `In Progress`, `In Review`, `Done`) with automatic progress percentage updates (`0%`, `50%`, `85%`, `100%`).
   - **Knowledge Graph View (`GET /api/graph`)**: Networked graph of Projects, Markdown Notes, `#tags`, and `[[WikiLinks]]` rendered in an interactive SVG radial layout.
3. **Auto-Cascading Task Dependency Scheduler & Cycle Detection**:
   - Shifting a predecessor task's `due_date` forward automatically cascades all transitive downstream dependent tasks (`depends_on_id`), preserving their durations (`backend/services/dependency_scheduler.py`).
   - Circular dependency detection rejects cycles (`A -> B -> A`) with `400 Bad Request`.
   - Critical Path calculation (`GET /api/projects/{id}/critical-path`) computes the longest chain of incomplete dependent tasks in days.
4. **Live Split Markdown Editor & Inline Task Sync**:
   - Parses YAML frontmatter (`--- ... ---`), `#tags`, bidirectional `[[WikiLinks]]` (with forward-reference resolution and incoming backlinks), and inline task directives (`- [ ] Task @start(YYYY-MM-DD) @due(YYYY-MM-DD) @priority(high) @milestone`).
   - Checking off `- [x]` in Markdown automatically updates the linked timeline/Kanban task to `done` (`progress = 100`).
5. **Real-Time WebSocket Collaboration Hub (`WS /ws/workspace`)**:
   - Broadcasts live workspace mutations (`project.created`, `sidebar.reordered`, `task.updated`, `kanban.moved`, `note.synced`) and handles client heartbeats (`ping`/`pong`) and cursor presence.

6. **Phase 3 Customizability, Study Sanctuary & Media Suite**:
   - **Study Mode & Pomodoro Clock (`GET/POST /api/study/sessions`, `GET /api/study/stats`)**: Project & subtask targeting, configurable intervals (Focus, Short Break, Long Break), Web Audio API harmonic chime bell & soft ambient rain synthesis, auto-journal bullet logging (`- [x] 🍅 Focus...`), and habit streak synchronization.
   - **Custom Stickers & Calendar/Note Pinning (`GET/POST /api/stickers`, `GET/POST /api/stickers/placements`)**: Curated stamp collection + custom transparent PNG/SVG upload, placement on calendar dates (Month/Week views) and notes with dynamic rotation, scale, and removal.
   - **Google Docs–Style Journal Images (`POST /api/uploads/images`)**: Three layout modes (Inline paragraph flow, Wrap text left/right, and Above-text free draggable floating card with resize handles and zoom lightbox).
   - **Visual Themes & Paper Textures**: 5 bespoke paper styles (`Warm Cream`, `Dot Grid`, `Lined Notebook`, `Sepia Parchment`, `Dark Slate`) and typography pairings (`Editorial Serif`, `Cozy Handwritten`, `Clean Monospace`).

---

## 2. System Architecture

```mermaid
flowchart LR
    subgraph Vue3["Vue 3 Frontend (AppWorkspace.vue)"]
        Sidebar["Left Sidebar\n(Projects, Rollups, Reorder)"]
        Views["Multi-View Canvas\n• Timeline Swimlanes + Critical Path\n• Kanban Board\n• Knowledge Graph SVG"]
        Editor["Split Markdown Editor\n(YAML, #tags, [[WikiLinks]], @directives)"]
        CmdPalette["Command Palette (Ctrl+K)"]
    end

    subgraph FastAPI["FastAPI v2.0 Backend"]
        REST["REST Endpoints\n(/sidebar, /timeline, /kanban, /graph, /notes, /tasks, /search)"]
        WS["WebSocket Hub\n(/ws/workspace)"]
        Services["Core Services\n• markdown_parser.py\n• dependency_scheduler.py\n• ws_manager.py"]
    end

    subgraph DB["Persistence Layer"]
        PG[("PostgreSQL 16 (Primary)\nmigrations/001_postgres_schema.sql\n+ SQLite Dev/Test Fallback")]
    end

    Sidebar <--> REST
    Views <--> REST
    Editor <--> REST
    CmdPalette <--> REST
    Vue3 <--> WS
    REST --> Services
    Services --> PG
```

---

## 3. PostgreSQL 16 Setup & Migrations

- **Configuration**: [`backend/config.py`](backend/config.py) and [`.env.example`](.env.example) configure `DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/chrononote`.
- **Docker Compose**: Run `docker compose up -d` using [`docker-compose.yml`](docker-compose.yml) to spin up PostgreSQL 16 and automatically apply [`migrations/001_postgres_schema.sql`](migrations/001_postgres_schema.sql).
- **Live DDL Inspection**: `GET /api/schema/postgres` compiles all SQLAlchemy 2.0 models directly against `postgresql.dialect()`.

---

## 4. Running the Operable Test Suites (68 Automated Tests)

### Backend Pytest Suite (39/39 Passing)
```powershell
python -m pytest
```

### Frontend Node Test Suite (29/29 Passing)
```powershell
node --test frontend/tests/frontend.test.mjs
```
