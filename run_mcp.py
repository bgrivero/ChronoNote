"""ChronoNote MCP Server Launcher
Starts the ChronoNote MCP server over standard I/O (stdio) for Claude Desktop, Claude Code, or any MCP client.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root directory is on Python path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.mcp_server import main

if __name__ == "__main__":
    main()
