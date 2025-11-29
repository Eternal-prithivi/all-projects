#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
GREEN_UL='\033[4;32m'
RED_UL='\033[4;31m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
> "$BACKEND_LOG"
> "$FRONTEND_LOG"

tail_with_prefix() {
    local log_file=$1
    local prefix=$2
    local color=$3
    tail -f "$log_file" 2>/dev/null | while IFS= read -r line; do
        echo -e "${color}[${prefix}]${NC} $line"
    done &
}

cleanup() {
    echo -e "\n${RED}🛑 Shutting down frontend and backend...${NC}"
    pkill -P $$
    echo -e "${YELLOW}Stopping Backend API...${NC}"
    kill $BACKEND_PID 2>/dev/null
    echo -e "${YELLOW}Stopping Frontend...${NC}"
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN_UL}✅ Frontend and Backend stopped${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Cloud Resource Platform - Start Frontend & Backend      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}🚀 Starting frontend and backend...${NC}"

# Start Backend API
cd "$PROJECT_ROOT/backend"
echo -e "${GREEN}[1/2] Starting Backend API (port 8000)...${NC}"
uvicorn app.main:app --reload > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
sleep 2
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN_UL}✅ Backend API started (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED_UL}❌ Backend API failed to start. Check logs: $BACKEND_LOG${NC}"
    exit 1
fi

# Start Frontend
cd "$PROJECT_ROOT/frontend"
echo -e "${GREEN}[2/2] Starting Frontend (port 5173)...${NC}"
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
sleep 3
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN_UL}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED_UL}❌ Frontend failed to start. Check logs: $FRONTEND_LOG${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Frontend & Backend Started Successfully! 🎉             ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Backend URL:  ${NC}http://localhost:8000"
echo -e "${CYAN}Frontend URL: ${NC}http://localhost:5173"
echo -e "${CYAN}Log Files:    ${NC}$BACKEND_LOG, $FRONTEND_LOG"
echo -e "${CYAN}Process IDs:  ${NC}$BACKEND_PID (backend), $FRONTEND_PID (frontend)"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📊 Live Logs (Ctrl+C to stop both):${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""
tail_with_prefix "$BACKEND_LOG" "BACKEND" "$BLUE"
tail_with_prefix "$FRONTEND_LOG" "FRONTEND" "$CYAN"
wait
