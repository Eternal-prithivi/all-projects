#!/bin/bash
# Start FastAPI backend + Vite frontend only.

set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/dev-common.sh"

BACKEND_PID=""
FRONTEND_PID=""

zenith_init_logs
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
: > "$BACKEND_LOG"
: > "$FRONTEND_LOG"

cleanup() {
  local status=$?
  set +e
  trap - SIGINT SIGTERM EXIT
  echo -e "\n${RED}🛑 Shutting down frontend and backend...${NC}"
  zenith_kill_script_children
  zenith_stop_pid "$BACKEND_PID"
  zenith_stop_pid "$FRONTEND_PID"
  zenith_stop_port "$FRONTEND_PORT"
  zenith_stop_port "$BACKEND_PORT"
  echo -e "${GREEN_UL}✅ Frontend and Backend stopped${NC}"
  exit "$status"
}
trap cleanup SIGINT SIGTERM EXIT

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Zenith — Start Frontend & Backend                       ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

zenith_ensure_python_tooling
zenith_ensure_npm

echo -e "${GREEN}[1/2] Starting Backend API (port ${BACKEND_PORT})...${NC}"
(cd "$BACKEND_DIR" && "$UVICORN_BIN" app.main:app --reload --port "$BACKEND_PORT") >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
zenith_wait_for_service "$BACKEND_PID" "$BACKEND_LOG" "Backend API" || exit 1
echo -e "${GREEN_UL}✅ Backend API started (PID: ${BACKEND_PID})${NC}"

echo -e "${GREEN}[2/2] Starting Frontend (port ${FRONTEND_PORT})...${NC}"
(cd "$FRONTEND_DIR" && npm run dev -- --port "$FRONTEND_PORT" --strictPort) >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
sleep 3
if ! zenith_process_running "$FRONTEND_PID" && ! zenith_port_in_use "$FRONTEND_PORT"; then
  echo -e "${RED_UL}❌ Frontend failed to start. Check logs: ${FRONTEND_LOG}${NC}"
  exit 1
fi
echo -e "${GREEN_UL}✅ Frontend started (port ${FRONTEND_PORT})${NC}"

echo ""
echo -e "${CYAN}Backend:  http://localhost:${BACKEND_PORT}${NC}"
echo -e "${CYAN}Frontend: http://localhost:${FRONTEND_PORT}${NC}"
echo -e "${GREEN}📊 Live Logs (Ctrl+C to stop):${NC}"
echo ""

zenith_tail_with_prefix "$BACKEND_LOG" "BACKEND" "$BLUE" 1
zenith_tail_with_prefix "$FRONTEND_LOG" "FRONTEND" "$CYAN" 0

wait
