#!/bin/bash
# Start Celery worker + beat (Redis started only if broker URL is redis://).

set -e
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/dev-common.sh"

WORKER_PID=""
BEAT_PID=""

zenith_init_logs
CELERY_WORKER_LOG="${LOG_DIR}/celery_worker.log"
CELERY_BEAT_LOG="${LOG_DIR}/celery_beat.log"
: > "$CELERY_WORKER_LOG"
: > "$CELERY_BEAT_LOG"

cleanup() {
  local status=$?
  set +e
  trap - SIGINT SIGTERM EXIT
  echo -e "\n${RED}🛑 Shutting down Celery services...${NC}"
  zenith_kill_script_children
  zenith_stop_pid "$WORKER_PID"
  zenith_stop_pid "$BEAT_PID"
  echo -e "${GREEN_UL}✅ Celery services stopped (broker left running)${NC}"
  exit "$status"
}
trap cleanup SIGINT SIGTERM EXIT

echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║   Zenith — Start Celery Worker + Beat                       ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

zenith_ensure_python_tooling
zenith_ensure_celery

BROKER_URL="$(zenith_get_celery_broker_url)" || {
  echo -e "${RED_UL}❌ Could not read Celery broker from backend config.${NC}"
  exit 1
}
zenith_ensure_redis_if_broker_needs_it "$BROKER_URL"

echo ""
echo -e "${MAGENTA}🚀 Starting Celery...${NC}"

echo -e "${GREEN}[1/2] Starting Celery Worker...${NC}"
(cd "$BACKEND_DIR" && "$CELERY_BIN" -A app.celery_worker worker --loglevel=info) >"$CELERY_WORKER_LOG" 2>&1 &
WORKER_PID=$!
zenith_wait_for_service "$WORKER_PID" "$CELERY_WORKER_LOG" "Celery Worker" || exit 1
echo -e "${GREEN_UL}✅ Celery Worker started (PID: ${WORKER_PID})${NC}"

echo -e "${GREEN}[2/2] Starting Celery Beat...${NC}"
(cd "$BACKEND_DIR" && "$CELERY_BIN" -A app.celery_worker beat --loglevel=info) >"$CELERY_BEAT_LOG" 2>&1 &
BEAT_PID=$!
zenith_wait_for_service "$BEAT_PID" "$CELERY_BEAT_LOG" "Celery Beat" || exit 1
echo -e "${GREEN_UL}✅ Celery Beat started (PID: ${BEAT_PID})${NC}"

echo ""
echo -e "${GREEN}📊 Live Logs (Ctrl+C to stop):${NC}"
echo ""

zenith_tail_with_prefix "$CELERY_WORKER_LOG" "CELERY-WORKER" "$YELLOW" 1
zenith_tail_with_prefix "$CELERY_BEAT_LOG" "CELERY-BEAT" "$MAGENTA" 1

wait
