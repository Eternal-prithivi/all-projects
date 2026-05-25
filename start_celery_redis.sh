#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
GREEN_UL='\033[4;32m'
RED_UL='\033[4;31m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$PROJECT_ROOT/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
CELERY_BIN="$VENV_DIR/bin/celery"
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
CELERY_WORKER_LOG="$LOG_DIR/celery_worker.log"
CELERY_BEAT_LOG="$LOG_DIR/celery_beat.log"
> "$CELERY_WORKER_LOG"
> "$CELERY_BEAT_LOG"

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

get_celery_broker_url() {
    cd "$BACKEND_DIR" && "$PYTHON_BIN" - <<'PY'
from app.utils.config import settings
print(settings.CELERY_BROKER_URL)
PY
}

cleanup() {
    local status=$?
    trap - SIGINT SIGTERM EXIT
    echo -e "\n${RED}🛑 Shutting down Celery services...${NC}"
    pkill -P $$ 2>/dev/null || true
    echo -e "${YELLOW}Stopping Celery Worker...${NC}"
    stop_pid "$WORKER_PID"
    echo -e "${YELLOW}Stopping Celery Beat...${NC}"
    stop_pid "$BEAT_PID"
    echo -e "${YELLOW}Leaving broker service running.${NC}"
    # Uncomment if you want to stop Redis started by this script
    # brew services stop redis
    echo -e "${GREEN_UL}✅ Celery services stopped${NC}"
    exit "$status"
}
trap cleanup SIGINT SIGTERM EXIT

echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║   Cloud Resource Platform - Start Celery Services         ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ ! -x "$PYTHON_BIN" ]; then
    echo -e "${RED_UL}❌ Missing executable: $PYTHON_BIN${NC}"
    echo -e "${YELLOW}Create the virtual environment first, then install backend requirements.${NC}"
    exit 1
fi
if [ ! -x "$CELERY_BIN" ]; then
    echo -e "${RED_UL}❌ Missing executable: $CELERY_BIN${NC}"
    echo -e "${YELLOW}Run: $PYTHON_BIN -m pip install -r $BACKEND_DIR/requirements.txt${NC}"
    exit 1
fi

if ! BROKER_URL="$(get_celery_broker_url)"; then
    echo -e "${RED_UL}❌ Could not read Celery broker settings from backend configuration.${NC}"
    exit 1
fi
if [[ "$BROKER_URL" == redis://* || "$BROKER_URL" == rediss://* ]]; then
    echo -e "${MAGENTA}🔍 Redis broker detected. Checking Redis status...${NC}"
    if ! redis-cli ping > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Redis not running. Starting Redis...${NC}"
        brew services start redis
        sleep 2
        if redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN_UL}✅ Redis started successfully${NC}"
        else
            echo -e "${RED_UL}❌ Failed to start Redis. Please check your installation.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN_UL}✅ Redis is already running${NC}"
    fi
else
    echo -e "${GREEN_UL}✅ External Celery broker configured; skipping Redis check${NC}"
fi

echo ""
echo -e "${MAGENTA}🚀 Starting Celery Worker and Beat...${NC}"
cd "$BACKEND_DIR"
echo -e "${GREEN}[1/2] Starting Celery Worker...${NC}"
"$CELERY_BIN" -A app.celery_worker worker --loglevel=info > "$CELERY_WORKER_LOG" 2>&1 &
WORKER_PID=$!
sleep 2
if ps -p $WORKER_PID > /dev/null; then
    echo -e "${GREEN_UL}✅ Celery Worker started (PID: $WORKER_PID)${NC}"
else
    echo -e "${RED_UL}❌ Celery Worker failed to start. Check logs: $CELERY_WORKER_LOG${NC}"
    exit 1
fi

echo -e "${GREEN}[2/2] Starting Celery Beat (Scheduler)...${NC}"
"$CELERY_BIN" -A app.celery_worker beat --loglevel=info > "$CELERY_BEAT_LOG" 2>&1 &
BEAT_PID=$!
sleep 2
if ps -p $BEAT_PID > /dev/null; then
    echo -e "${GREEN_UL}✅ Celery Beat started (PID: $BEAT_PID)${NC}"
else
    echo -e "${RED_UL}❌ Celery Beat failed to start. Check logs: $CELERY_BEAT_LOG${NC}"
    exit 1
fi

echo ""
echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║   Celery Services Started Successfully! 🎉                ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${MAGENTA}Log Files:    ${NC}$CELERY_WORKER_LOG, $CELERY_BEAT_LOG"
echo -e "${MAGENTA}Process IDs:  ${NC}$WORKER_PID (worker), $BEAT_PID (beat)"
echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📊 Live Logs (Ctrl+C to stop both):${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}"
echo ""
tail_with_prefix "$CELERY_WORKER_LOG" "CELERY-WORKER" "$YELLOW"
tail_with_prefix "$CELERY_BEAT_LOG" "CELERY-BEAT" "$MAGENTA"
wait
