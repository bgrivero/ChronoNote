# ChronoNote Model Context Protocol (MCP) Configuration & Claude Integration Guide

ChronoNote is configured with full **Model Context Protocol (MCP)** integration so Claude (via **Claude Desktop**, **Claude Code CLI**, or **Cursor / VS Code**) can directly inspect, create, and manage projects, tasks, and notes in your local ChronoNote workspace.

---

## 1. What Has Been Configured

Everything is set up and configured locally on your machine:

1. **MCP Server Core (`backend/mcp_server.py`)**:
   - Implements native MCP tools using the official `mcp` 2.x standard (`MCPServer`).
   - Connects directly to ChronoNote's SQLite or PostgreSQL database via SQLAlchemy ORM.
   - Automatically maps created projects to your primary user (`brycerivero@gmail.com`).
   - Emits real-time WebSocket notifications (`project.created`, `task.updated`, `note.synced`) so any open ChronoNote browser window updates instantly.

2. **Launcher Script (`run_mcp.py`)**:
   - Root-level entry point that sets up Python paths and launches the MCP server over standard input/output (`stdio`).

3. **Claude Desktop Configuration (`%APPDATA%\Claude\claude_desktop_config.json`)**:
   - Configured with the absolute path to Python 3.15 and `run_mcp.py` so Claude Desktop automatically launches the ChronoNote MCP tools whenever Claude Desktop opens.

4. **Claude Code & Editor Configuration (`.mcp.json` & `~/.claude.json`)**:
   - Configured for Claude Code CLI and Cursor/VS Code in the project root.

5. **Automated Test Suite (`tests/test_mcp_server.py`)**:
   - 4 automated tests verifying tool registration, project creation, bulk task insertion, note creation with Markdown frontmatter/wikilinks/tasks, and project updates.

---

## 2. Available MCP Tools for Claude

Claude has access to the following 7 tools:

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `create_project` | Creates a new project in ChronoNote. | `name`, `description`, `color`, `icon`, `status`, `is_pinned`, `start_date`, `target_date` |
| `create_project_with_tasks` | Creates a project **and** its initial timeline/Kanban tasks and Markdown note in a single call. | `name`, `tasks: [{title, status, priority, due_date, is_milestone}]`, `initial_note` |
| `list_projects` | Lists all projects with rollup statistics (task count, progress %, overdue count). | `status_filter` (`active`, `planned`, etc.) |
| `get_project` | Fetches full project details including all tasks, dates, and linked notes. | `project_id` or `slug` |
| `create_task` | Adds an individual task or milestone to an existing project. | `project_id`, `title`, `description`, `status`, `priority`, `start_date`, `due_date`, `is_milestone` |
| `update_project` | Updates title, status, pin state, or dates of an existing project. | `project_id`, `name`, `status`, `color`, `icon`, `is_pinned`, `target_date` |
| `create_project_note` | Creates a Markdown note attached to a project (auto-parses `#tags`, `[[WikiLinks]]`, and `@directives`). | `project_id`, `title`, `content` |

---

## 3. Example Prompts You Can Give Claude Locally

Open **Claude Desktop** (or run `claude` in your terminal in this folder) and prompt naturally:

### Example 1: Creating a Full Project with Tasks
> *"Claude, create a new active project in ChronoNote called 'Q1 Growth Marketing' with a purple color and target icon. Add three tasks: 'Launch Landing Page' (urgent, milestone, due 2026-11-15), 'Set up Newsletter Automation' (high priority, due 2026-11-20), and 'Run Ad Campaign' (medium priority, due 2026-11-30). Also create a brief project note with our key performance indicators."*

### Example 2: Inspecting Current Projects
> *"What projects do I currently have in ChronoNote, and what are their completion percentages?"*

### Example 3: Adding Tasks to an Existing Project
> *"Add a high-priority milestone task 'Security Audit' to project 'ChronoNote Core Engine' due next Friday."*

### Example 4: Quick Project Creation
> *"Create a planned project called 'Home Server Setup' with a green color and server icon."*

---

---

## 5. Deployed to Render (Always-On Remote MCP)

### Does it work on Render?
**Yes!** The MCP server is mounted directly into the FastAPI application at `/mcp/sse`. With your Render service deployed:
- Render hosts your FastAPI application 24/7.
- The MCP server is continuously live at:
  ```
  https://chrononote-personal.onrender.com/mcp/sse
  ```

### Configured Claude Settings
Both your `%APPDATA%\Claude\claude_desktop_config.json` and `.mcp.json` are now pre-configured with your exact Render URL:

```json
{
  "mcpServers": {
    "chrononote": {
      "url": "https://chrononote-personal.onrender.com/mcp/sse"
    },
    "chrononote-local": {
      "command": "C:\\Python315\\python.exe",
      "args": [
        "C:\\Users\\river\\Documents\\Bryce\\WORKING\\PERSONAL PROJECTS\\NOTE TAKING\\run_mcp.py"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\river\\Documents\\Bryce\\WORKING\\PERSONAL PROJECTS\\NOTE TAKING"
      }
    }
  }
}
```

### Do you ever have to manually start it up?
**No! You never have to manually run or start anything:**
- **Locally**: When using local stdio, Claude Desktop spawns `run_mcp.py` in the background automatically every time Claude opens. You do not need to open a terminal or start the web server.
- **On Render**: Render runs 24/7 in the cloud. Claude simply connects to your Render HTTPS URL on demand.
