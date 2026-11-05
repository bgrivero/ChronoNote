#!/usr/bin/env bash
#
# start.sh - Launch ChronoNote backend and frontend concurrently
#

set -e

# Change directory to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "   ChronoNote Development Environment   "
echo "========================================="

# 1. Detect Python executable
PYTHON_BIN=""
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_BIN="python"
elif [ -f ".venv/bin/activate" ]; then
    echo "[*] Activating virtual environment (.venv)..."
    source .venv/bin/activate
    PYTHON_BIN="python"
elif [ -f ".venv/Scripts/activate" ]; then
    echo "[*] Activating virtual environment (.venv)..."
    source .venv/Scripts/activate
    PYTHON_BIN="python"
elif [ -f "venv/bin/activate" ]; then
    echo "[*] Activating virtual environment (venv)..."
    source venv/bin/activate
    PYTHON_BIN="python"
elif [ -f "venv/Scripts/activate" ]; then
    echo "[*] Activating virtual environment (venv)..."
    source venv/Scripts/activate
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "[!] Error: Neither 'python3' nor 'python' was found in PATH." >&2
    exit 1
fi

echo "[✓] Using Python: $($PYTHON_BIN --version 2>&1)"

# 2. Detect npm binary
NPM_BIN=""
if command -v npm >/dev/null 2>&1; then
    NPM_BIN="npm"
elif command -v npm.cmd >/dev/null 2>&1; then
    NPM_BIN="npm.cmd"
else
    echo "[!] Error: npm was not found in PATH." >&2
    exit 1
fi

echo "[✓] Using npm: $($NPM_BIN --version 2>&1)"

# 3. Check frontend dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo "[*] frontend/node_modules missing. Running 'npm install'..."
    (cd frontend && "$NPM_BIN" install)
fi

# Track background process IDs
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    # Disable trap to avoid recursion on exit
    trap - INT TERM EXIT
    echo ""
    echo "[*] Shutting down ChronoNote services..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "    Stopping backend (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "    Stopping frontend (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    echo "[✓] All processes stopped."
}

trap cleanup INT TERM EXIT

# 4. Start Backend (FastAPI via Uvicorn)
echo "[*] Starting Backend (FastAPI on http://127.0.0.1:8000)..."
"$PYTHON_BIN" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# 5. Start Frontend (Vite)
echo "[*] Starting Frontend (Vite on http://localhost:5173)..."
(cd frontend && "$NPM_BIN" run dev) &
FRONTEND_PID=$!

echo ""
echo "========================================="
echo "   ChronoNote Services Running:"
echo "   - Frontend:  http://localhost:5173"
echo "   - Backend:   http://127.0.0.1:8000"
echo "   - API Docs:  http://127.0.0.1:8000/docs"
echo "========================================="
echo "Press Ctrl+C to stop all services."
echo ""

# Wait for both processes
wait
