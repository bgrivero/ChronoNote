# ChronoNote Model Context Protocol (MCP) — Multi-User Authentication Guide

ChronoNote features secure **Multi-User Account Authentication** over the Model Context Protocol (MCP).

Just like connecting GitHub, Notion, or Linear:
- **No hardcoded user accounts**: The server never assumes who you are.
- **Strict User Isolation**: Claude only has access to projects, tasks, and notes belonging to the currently logged-in account.
- **Authentication Required**: Calling any project or workspace tool without logging in prompts the user to authenticate first.

---

## 1. How to Authenticate in Claude

When you connect Claude or ask Claude to do something, Claude will prompt you to connect your ChronoNote account.

### Option A: Email & Password
If you registered your account with an email and password:
> *"Claude, log in to ChronoNote with email `your@email.com` and password `yourpassword`"*

Claude calls the `login` tool, verifies your credentials against the PBKDF2 hash in the database, and unlocks your workspace.

### Option B: 6-Digit Connection Code (Recommended for Google Sign-In)
If you sign in using Google OAuth:
1. Open your browser and go to your ChronoNote app:
   ```
   https://chrononote-personal.onrender.com/api/auth/mcp-code
   ```
   *(or `http://localhost:8000/api/auth/mcp-code` if running locally)*
2. It displays your 6-digit temporary connection code (valid for 15 minutes), for example: `849201`.
3. In Claude, simply tell it:
   > *"Connect to ChronoNote with code 849201"*

Claude calls the `connect_with_code` tool, validates your code, and permanently links your session!

---

## 2. Session Persistence & Security

- **Stay Logged In**: Once you log in or connect with code in Claude Desktop, your authenticated session is saved locally in `~/.chrononote_mcp_session.json` so you don't need to re-login every time Claude opens.
- **Logout Anytime**: You can tell Claude: *"Log out of ChronoNote"*, which invokes the `logout` tool and locks all workspace tools immediately.
- **Who am I?**: You can ask Claude: *"Which ChronoNote account am I logged into?"*, which calls `whoami` to verify your active user ID and email.

---

## 3. Available MCP Tools

### Authentication Tools
| Tool | Purpose | Arguments |
|------|---------|-----------|
| `login` | Authenticate with ChronoNote account email and password. | `email`, `password` |
| `connect_with_code` | Connect using a 6-digit one-time code from the web app. | `code` |
| `connect_with_token` | Connect using an existing ChronoNote session token. | `token` |
| `whoami` | Check current authenticated account and status. | None |
| `logout` | Log out and lock all tools. | None |

### Workspace Tools (Requires Authentication)
| Tool | Purpose | User Scoping |
|------|---------|--------------|
| `list_projects` | Lists all your projects and stats. | Only returns your projects (`user_id == current_user.id`) |
| `get_project` | Fetches project tasks, notes, deadlines. | Verifies ownership before returning data |
| `create_project` | Creates a new project. | Automatically assigned to your account |
| `create_project_with_tasks` | Creates a project with tasks & note. | Automatically assigned to your account |
| `create_task` | Adds a task/milestone to a project. | Verifies project ownership |
| `update_project` | Updates project metadata/status. | Verifies project ownership |
| `create_project_note` | Creates a linked Markdown note. | Verifies project ownership |

---

## 4. Claude Desktop & Claude Code Configuration

### Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`)
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
