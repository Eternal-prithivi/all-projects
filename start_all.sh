#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
GREEN_UL='\033[4;32m'
RED_UL='\033[4;31m'

# Get absolute path to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_DIR="$PROJECT_ROOT/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
UVICORN_BIN="$VENV_DIR/bin/uvicorn"
CELERY_BIN="$VENV_DIR/bin/celery"

# Log file paths
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
BACKEND_LOG="$LOG_DIR/backend.log"
CELERY_WORKER_LOG="$LOG_DIR/celery_worker.log"
CELERY_BEAT_LOG="$LOG_DIR/celery_beat.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# Clear old logs
> "$BACKEND_LOG"
> "$CELERY_WORKER_LOG"
> "$CELERY_BEAT_LOG"
> "$FRONTEND_LOG"

# Function to tail logs with prefix
tail_with_prefix() {
    local log_file=$1
    local prefix=$2
    local color=$3
    tail -f "$log_file" 2>/dev/null | while IFS= read -r line; do
        # Highlight HTTP 2xx in green underline, 4xx/5xx in red
        # Format: "METHOD /path HTTP/1.1" 200 OK or similar
        if [[ "$line" =~ HTTP/1.1 ]] && [[ "$line" =~ [[:space:]]2[0-9][0-9][[:space:]] ]]; then
            # Good response (2xx): green underline
            echo -e "${color}[${prefix}]${NC} ${GREEN_UL}$line${NC}"
        elif [[ "$line" =~ HTTP/1.1 ]] && [[ "$line" =~ [[:space:]][45][0-9][0-9][[:space:]] ]]; then
            # Bad response (4xx/5xx): red
            echo -e "${color}[${prefix}]${NC} ${RED}$line${NC}"
        else
            echo -e "${color}[${prefix}]${NC} $line"
        fi
    done &
}

stop_pid() {
    local pid="${1:-}"
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null || true
    fi
}

ensure_executable() {
    local executable_path="$1"
    local install_hint="$2"
    if [ ! -x "$executable_path" ]; then
        echo -e "${RED}❌ Missing executable: $executable_path${NC}"
        echo -e "${YELLOW}$install_hint${NC}"
        exit 1
    fi
}

get_celery_broker_url() {
    cd "$BACKEND_DIR" && "$PYTHON_BIN" - <<'PY'
from app.utils.config import settings
print(settings.CELERY_BROKER_URL)
PY
}

# Cleanup function
cleanup() {
    local status=$?
    trap - SIGINT SIGTERM EXIT
    echo -e "\n${RED}🛑 Shutting down all services...${NC}"
    
    # Kill all child processes
    pkill -P $$ 2>/dev/null || true
    
    # Stop specific services
    echo -e "${YELLOW}Stopping Backend API...${NC}"
    stop_pid "$BACKEND_PID"
    
    echo -e "${YELLOW}Stopping Celery Worker...${NC}"
    stop_pid "$WORKER_PID"
    
    echo -e "${YELLOW}Stopping Celery Beat...${NC}"
    stop_pid "$BEAT_PID"
    
    echo -e "${YELLOW}Stopping Frontend...${NC}"
    stop_pid "$FRONTEND_PID"
    
    # Stop Redis if it was started by this script
    # echo -e "${YELLOW}Stopping Redis...${NC}"
    # brew services stop redis
    
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit "$status"
}

# Trap Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM EXIT

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Cloud Resource Optimization Platform - Start All        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

ensure_executable "$PYTHON_BIN" "Create the virtual environment first, then install backend requirements."
ensure_executable "$UVICORN_BIN" "Run: $PYTHON_BIN -m pip install -r $BACKEND_DIR/requirements.txt"
ensure_executable "$CELERY_BIN" "Run: $PYTHON_BIN -m pip install -r $BACKEND_DIR/requirements.txt"
if ! command -v npm > /dev/null 2>&1; then
    echo -e "${RED}❌ npm not found. Install Node.js before starting the frontend.${NC}"
    exit 1
fi

if ! BROKER_URL="$(get_celery_broker_url)"; then
    echo -e "${RED}❌ Could not read Celery broker settings from backend configuration.${NC}"
    exit 1
fi
if [[ "$BROKER_URL" == redis://* || "$BROKER_URL" == rediss://* ]]; then
    echo -e "${BLUE}🔍 Redis broker detected. Checking Redis status...${NC}"
    if ! redis-cli ping > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Redis not running. Starting Redis...${NC}"
        brew services start redis
        sleep 2
        if redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis started successfully${NC}"
        else
            echo -e "${RED}❌ Failed to start Redis. Please check your installation.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ Redis is already running${NC}"
    fi
else
    echo -e "${GREEN}✅ External Celery broker configured; skipping Redis check${NC}"
fi

echo ""
echo -e "${BLUE}🚀 Starting all services...${NC}"
echo ""

# Start Backend API
echo -e "${GREEN}[1/4] Starting Backend API (port 8000)...${NC}"
cd "$BACKEND_DIR"
"$UVICORN_BIN" app.main:app --reload > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
sleep 2

# Check if backend started successfully
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✅ Backend API started (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}❌ Backend API failed to start. Check logs: $BACKEND_LOG${NC}"
    exit 1
fi

# Start Celery Worker
echo -e "${GREEN}[2/4] Starting Celery Worker...${NC}"
"$CELERY_BIN" -A app.celery_worker worker --loglevel=info > "$CELERY_WORKER_LOG" 2>&1 &
WORKER_PID=$!
sleep 2

# Check if celery worker started successfully
if ps -p $WORKER_PID > /dev/null; then
    echo -e "${GREEN}✅ Celery Worker started (PID: $WORKER_PID)${NC}"
else
    echo -e "${RED}❌ Celery Worker failed to start. Check logs: $CELERY_WORKER_LOG${NC}"
    exit 1
fi

# Start Celery Beat
echo -e "${GREEN}[3/4] Starting Celery Beat (Scheduler)...${NC}"
"$CELERY_BIN" -A app.celery_worker beat --loglevel=info > "$CELERY_BEAT_LOG" 2>&1 &
BEAT_PID=$!
sleep 2

# Check if celery beat started successfully
if ps -p $BEAT_PID > /dev/null; then
    echo -e "${GREEN}✅ Celery Beat started (PID: $BEAT_PID)${NC}"
else
    echo -e "${RED}❌ Celery Beat failed to start. Check logs: $CELERY_BEAT_LOG${NC}"
    exit 1
fi

# Start Frontend
echo -e "${GREEN}[4/4] Starting Frontend (port 5173)...${NC}"
cd "$FRONTEND_DIR"
npm run dev -- --port 5173 --strictPort > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
sleep 3

# Check if frontend started successfully
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}❌ Frontend failed to start. Check logs: $FRONTEND_LOG${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   All Services Started Successfully! 🎉                   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${MAGENTA}📍 Service URLs:${NC}"
echo -e "   ${BLUE}Backend API:${NC}     http://localhost:8000"
echo -e "   ${BLUE}API Docs:${NC}        http://localhost:8000/docs"
echo -e "   ${BLUE}Frontend:${NC}        http://localhost:5173"
echo ""
echo -e "${MAGENTA}📝 Log Files:${NC}"
echo -e "   ${YELLOW}Backend:${NC}         $BACKEND_LOG"
echo -e "   ${YELLOW}Celery Worker:${NC}   $CELERY_WORKER_LOG"
echo -e "   ${YELLOW}Celery Beat:${NC}     $CELERY_BEAT_LOG"
echo -e "   ${YELLOW}Frontend:${NC}        $FRONTEND_LOG"
echo ""
echo -e "${MAGENTA}🔧 Process IDs:${NC}"
echo -e "   ${YELLOW}Backend:${NC}         $BACKEND_PID"
echo -e "   ${YELLOW}Celery Worker:${NC}   $WORKER_PID"
echo -e "   ${YELLOW}Celery Beat:${NC}     $BEAT_PID"
echo -e "   ${YELLOW}Frontend:${NC}        $FRONTEND_PID"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📊 Live Logs (Ctrl+C to stop all services):${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Start tailing logs with colored prefixes
tail_with_prefix "$BACKEND_LOG" "BACKEND" "$BLUE"
tail_with_prefix "$CELERY_WORKER_LOG" "CELERY-WORKER" "$YELLOW"
tail_with_prefix "$CELERY_BEAT_LOG" "CELERY-BEAT" "$MAGENTA"
tail_with_prefix "$FRONTEND_LOG" "FRONTEND" "$CYAN"

# Wait for all background processes
wait
