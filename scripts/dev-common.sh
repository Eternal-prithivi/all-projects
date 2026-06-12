# shellcheck shell=bash
# Shared helpers for Zenith dev startup scripts (source, do not execute directly).

# Strict mode (cleanup handlers use set +e where needed)
set -uo pipefail

_DEV_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${_DEV_COMMON_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
LOG_DIR="${PROJECT_ROOT}/logs"

# Canonical venv per ai-docs — fallback to legacy project-root venv with warning
if [[ -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
  VENV_DIR="${BACKEND_DIR}/.venv"
elif [[ -x "${PROJECT_ROOT}/venv/bin/python" ]]; then
  VENV_DIR="${PROJECT_ROOT}/venv"
  _ZENITH_VENV_FALLBACK=1
else
  VENV_DIR="${BACKEND_DIR}/.venv"
fi

PYTHON_BIN="${VENV_DIR}/bin/python"
UVICORN_BIN="${VENV_DIR}/bin/uvicorn"
CELERY_BIN="${VENV_DIR}/bin/celery"

# Watch app/ only — avoids .venv pip installs triggering endless reload loops.
UVICORN_DEV_ARGS=(--reload --reload-dir app)

FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'
GREEN_UL='\033[4;32m'
RED_UL='\033[4;31m'

zenith_warn_venv_fallback() {
  if [[ -n "${_ZENITH_VENV_FALLBACK:-}" ]]; then
    echo -e "${YELLOW}⚠️  Using legacy ${PROJECT_ROOT}/venv — prefer: python3 -m venv ${BACKEND_DIR}/.venv${NC}"
  fi
}

zenith_init_logs() {
  mkdir -p "$LOG_DIR"
}

zenith_process_running() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && ps -p "$pid" > /dev/null 2>&1
}

zenith_port_in_use() {
  local port="$1"
  if command -v lsof > /dev/null 2>&1; then
    lsof -ti "tcp:${port}" -sTCP:LISTEN > /dev/null 2>&1
  else
    return 1
  fi
}

zenith_stop_pid() {
  local pid="${1:-}"
  if [[ -n "$pid" ]]; then
    kill "$pid" 2>/dev/null || true
  fi
}

zenith_stop_port() {
  local port="$1"
  if ! command -v lsof > /dev/null 2>&1; then
    return 0
  fi
  local pids
  pids="$(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
  fi
}

zenith_ensure_executable() {
  local executable_path="$1"
  local install_hint="$2"
  if [[ ! -x "$executable_path" ]]; then
    echo -e "${RED}❌ Missing executable: ${executable_path}${NC}"
    echo -e "${YELLOW}${install_hint}${NC}"
    echo -e "${YELLOW}Expected venv: ${BACKEND_DIR}/.venv${NC}"
    echo -e "${YELLOW}  python3 -m venv ${BACKEND_DIR}/.venv && ${PYTHON_BIN} -m pip install -r ${BACKEND_DIR}/requirements.txt${NC}"
    exit 1
  fi
}

zenith_ensure_python_tooling() {
  zenith_warn_venv_fallback
  zenith_ensure_executable "$PYTHON_BIN" "Create backend/.venv and install requirements."
  zenith_ensure_executable "$UVICORN_BIN" "Run: ${PYTHON_BIN} -m pip install -r ${BACKEND_DIR}/requirements.txt"
}

zenith_ensure_celery() {
  zenith_ensure_executable "$CELERY_BIN" "Run: ${PYTHON_BIN} -m pip install -r ${BACKEND_DIR}/requirements.txt"
}

zenith_ensure_npm() {
  if ! command -v npm > /dev/null 2>&1; then
    echo -e "${RED}❌ npm not found. Install Node.js before starting the frontend.${NC}"
    exit 1
  fi
}

zenith_get_celery_broker_url() {
  (cd "$BACKEND_DIR" && "$PYTHON_BIN" - <<'PY'
from app.utils.config import settings
print(settings.CELERY_BROKER_URL)
PY
  )
}

zenith_ensure_redis_if_broker_needs_it() {
  local broker_url="$1"
  if [[ "$broker_url" == redis://* || "$broker_url" == rediss://* ]]; then
    echo -e "${BLUE}🔍 Redis broker detected. Checking Redis...${NC}"
    if ! command -v redis-cli > /dev/null 2>&1; then
      echo -e "${RED}❌ redis-cli not found but broker is Redis.${NC}"
      exit 1
    fi
    if ! redis-cli ping > /dev/null 2>&1; then
      echo -e "${YELLOW}⚠️  Redis not running.${NC}"
      if [[ "$(uname -s)" == "Darwin" ]] && command -v brew > /dev/null 2>&1; then
        echo -e "${YELLOW}Starting Redis via brew services...${NC}"
        brew services start redis
        sleep 2
      else
        echo -e "${RED}❌ Start Redis manually (brew services start redis on macOS).${NC}"
        exit 1
      fi
      if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis is running${NC}"
      else
        echo -e "${RED}❌ Failed to reach Redis.${NC}"
        exit 1
      fi
    else
      echo -e "${GREEN}✅ Redis is already running${NC}"
    fi
  else
    echo -e "${GREEN}✅ External Celery broker configured; skipping Redis${NC}"
  fi
}

zenith_wait_for_service() {
  local pid="$1"
  local log_file="$2"
  local label="$3"
  local attempts="${4:-10}"
  local i=0
  while (( i < attempts )); do
    if zenith_process_running "$pid"; then
      return 0
    fi
    sleep 1
    ((i++)) || true
  done
  echo -e "${RED}❌ ${label} failed to start. Check logs: ${log_file}${NC}"
  return 1
}

zenith_tail_with_prefix() {
  local log_file="$1"
  local prefix="$2"
  local color="$3"
  local highlight_http="${4:-0}"
  tail -f "$log_file" 2>/dev/null | while IFS= read -r line; do
    if [[ "$highlight_http" == "1" ]] && [[ "$line" =~ HTTP/1.1 ]]; then
      if [[ "$line" =~ [[:space:]]2[0-9][0-9][[:space:]] ]]; then
        echo -e "${color}[${prefix}]${NC} ${GREEN_UL}${line}${NC}"
      elif [[ "$line" =~ [[:space:]][45][0-9][0-9][[:space:]] ]]; then
        echo -e "${color}[${prefix}]${NC} ${RED}${line}${NC}"
      else
        echo -e "${color}[${prefix}]${NC} ${line}"
      fi
    else
      echo -e "${color}[${prefix}]${NC} ${line}"
    fi
  done &
}

zenith_kill_script_children() {
  pkill -P $$ 2>/dev/null || true
}
