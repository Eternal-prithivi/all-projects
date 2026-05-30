"""NDJSON debug logs for Cursor debug mode (session 8e7315). No secrets."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

LOG_PATH = os.environ.get(
    "DEBUG_AGENT_LOG_PATH",
    "/Users/a.prithiviraj/Documents/Projects/.cursor/debug-8e7315.log",
)
SESSION_ID = "8e7315"


def agent_log(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any] | None = None,
    run_id: str = "pre-fix",
) -> None:
    payload = {
        "sessionId": SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except OSError:
        pass
    logger.info("AGENT_DEBUG %s", json.dumps(payload))
