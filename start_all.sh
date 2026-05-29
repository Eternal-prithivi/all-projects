#!/bin/bash
# Start backend, Celery worker + beat, and frontend (dev stack).

set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/dev-common.sh"

BACKEND_PID=""
WORKER_PID=""
BEAT_PID=""
FRONTEND_PID=""

zenith_init_logs
BACKEND_LOG="${LOG_DIR}/backend.log"
CELERY_WORKER_LOG="${LOG_DIR}/celery_worker.log"
CELERY_BEAT_LOG="${LOG_DIR}/celery_beat.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
: > "$BACKEND_LOG"
: > "$CELERY_WORKER_LOG"
: > "$CELERY_BEAT_LOG"
: > "$FRONTEND_LOG"

cleanup() {
  local status=$?
  set +e
  trap - SIGINT SIGTERM EXIT
  echo -e "\n${RED}🛑 Shutting down all services...${NC}"
  zenith_kill_script_children
  echo -e "${YELLOW}Stopping Backend API...${NC}"
  zenith_stop_pid "$BACKEND_PID"
  echo -e "${YELLOW}Stopping Celery Worker...${NC}"
  zenith_stop_pid "$WORKER_PID"
  echo -e "${YELLOW}Stopping Celery Beat...${NC}"
  zenith_stop_pid "$BEAT_PID"
  echo -e "${YELLOW}Stopping Frontend...${NC}"
  zenith_stop_pid "$FRONTEND_PID"
  zenith_stop_port "$FRONTEND_PORT"
  echo -e "${GREEN}✅ All services stopped${NC}"
  exit "$status"
}
trap cleanup SIGINT SIGTERM EXIT

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Cloud Resource Optimization Platform - Start All        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "${YELLOW}Tip: Heavy stack — on 18GB RAM prefer ./start_frontend_backend.sh + ./start_celery_redis.sh separately.${NC}"
echo ""

zenith_ensure_python_tooling
zenith_ensure_celery
zenith_ensure_npm

BROKER_URL="$(zenith_get_celery_broker_url)" || {
  echo -e "${RED}❌ Could not read Celery broker from backend config.${NC}"
  exit 1
}
zenith_ensure_redis_if_broker_needs_it "$BROKER_URL"

echo ""
echo -e "${BLUE}🚀 Starting all services...${NC}"
echo ""

echo -e "${GREEN}[1/4] Starting Backend API (port ${BACKEND_PORT})...${NC}"
(cd "$BACKEND_DIR" && "$UVICORN_BIN" app.main:app --reload --port "$BACKEND_PORT") >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
zenith_wait_for_service "$BACKEND_PID" "$BACKEND_LOG" "Backend API" || exit 1
echo -e "${GREEN}✅ Backend API started (PID: ${BACKEND_PID})${NC}"

echo -e "${GREEN}[2/4] Starting Celery Worker...${NC}"
(cd "$BACKEND_DIR" && "$CELERY_BIN" -A app.celery_worker worker --loglevel=info) >"$CELERY_WORKER_LOG" 2>&1 &
WORKER_PID=$!
zenith_wait_for_service "$WORKER_PID" "$CELERY_WORKER_LOG" "Celery Worker" || exit 1
echo -e "${GREEN}✅ Celery Worker started (PID: ${WORKER_PID})${NC}"

echo -e "${GREEN}[3/4] Starting Celery Beat...${NC}"
(cd "$BACKEND_DIR" && "$CELERY_BIN" -A app.celery_worker beat --loglevel=info) >"$CELERY_BEAT_LOG" 2>&1 &
BEAT_PID=$!
zenith_wait_for_service "$BEAT_PID" "$CELERY_BEAT_LOG" "Celery Beat" || exit 1
echo -e "${GREEN}✅ Celery Beat started (PID: ${BEAT_PID})${NC}"

echo -e "${GREEN}[4/4] Starting Frontend (port ${FRONTEND_PORT})...${NC}"
(cd "$FRONTEND_DIR" && npm run dev -- --port "$FRONTEND_PORT" --strictPort) >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
sleep 3
if ! zenith_process_running "$FRONTEND_PID" && ! zenith_port_in_use "$FRONTEND_PORT"; then
  echo -e "${RED}❌ Frontend failed to start. Check logs: ${FRONTEND_LOG}${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Frontend started (PID: ${FRONTEND_PID}, port ${FRONTEND_PORT})${NC}"

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   All Services Started Successfully! 🎉                   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${MAGENTA}📍 URLs:${NC} API http://localhost:${BACKEND_PORT} · Docs /docs · UI http://localhost:${FRONTEND_PORT}"
echo -e "${MAGENTA}📝 Logs:${NC} ${LOG_DIR}/"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📊 Live Logs (Ctrl+C to stop all):${NC}"
echo ""

zenith_tail_with_prefix "$BACKEND_LOG" "BACKEND" "$BLUE" 1
zenith_tail_with_prefix "$CELERY_WORKER_LOG" "CELERY-WORKER" "$YELLOW" 1
zenith_tail_with_prefix "$CELERY_BEAT_LOG" "CELERY-BEAT" "$MAGENTA" 1
zenith_tail_with_prefix "$FRONTEND_LOG" "FRONTEND" "$CYAN" 0

wait
