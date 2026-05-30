"""Post-call intake assembly: accumulate structured intake state during a call,
then build the follow-up queue and log everything to S3 when the call ends.

The voice pipeline (bot-nemotron.py) does not have a single structured intake
payload — the LLM holds the facts in conversation and surfaces them through tool
calls (check_sol, classify_treatment, route_case, end_call). This module captures
those tool args/results into an `intake_state` dict as they happen, then on call
end assembles the PostCallQueue and ships intake JSON + transcript + queue to S3.

The state schema and the tool→state merge logic mirror server/test_harness.py
(the teammate's terminal simulator) so the live bot and the harness behave
identically. Kept as a separate module rather than imported from test_harness so
the bot has no dependency on rich/openai or the harness's import-time side effects.
"""

from __future__ import annotations

import json
import os
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from loguru import logger
except ImportError:  # pragma: no cover - allows test/import environments without loguru
    import logging

    logger = logging.getLogger(__name__)

from tools.post_call_queue import build_standard_queue
from tools.s3_logger import log_session

# Text injected to trigger the LLM's opening line — filtered out of the transcript.
_GREETING_TRIGGER_MARKER = "The caller has just connected"


def tool_event_log_path() -> Path:
    """Return the shared JSONL path for live tool-call events."""

    override = os.getenv("INTAKE_TOOL_EVENTS_PATH")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[2] / "runtime" / "tool_events.jsonl"


def append_tool_event(
    *,
    tool_name: str,
    phase: str,
    session_id: str | None,
    arguments: Any | None = None,
    result: Any | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Append a single structured tool event to the shared JSONL stream."""

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
        "phase": phase,
        "session_id": session_id,
        "arguments": dict(arguments or {}),
        "result": result,
        "note": note,
    }
    path = tool_event_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
    return event


def read_tool_events(limit: int = 50) -> list[dict[str, Any]]:
    """Read the most recent tool events from the shared JSONL log."""

    path = tool_event_log_path()
    if limit <= 0 or not path.exists():
        return []

    events: deque[dict[str, Any]] = deque(maxlen=limit)
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"[TOOL-EVENT] skipping malformed line in {path}")
    return list(events)


def new_intake_state(
    caller_phone: str | None = None, session_id: str | None = None
) -> dict[str, Any]:
    """Create a fresh per-call intake state.

    Args:
        caller_phone: Caller's phone number (from caller ID) if known.
        session_id: Unique session identifier; a random hex id is generated if None.

    Returns:
        An intake-state dict with every tracked field initialized.
    """
    return {
        "session_id": session_id or uuid.uuid4().hex,
        "caller_name": None,
        "caller_phone": caller_phone,
        "caller_email": None,
        "case_type": None,
        "state": None,
        "accident_date": None,
        "severity_tier": None,
        "red_flags": [],
        "sol_viable": None,
        "sol_deadline": None,
        "sol_days_remaining": None,
        "urgency": None,
        "decision": None,
        "emotional_state": "calm",
        "appointment_slot": None,
        "attorney_tier": None,
        "defendant_type": None,
        "has_prior_representation": None,
    }


def update_intake_state(
    intake_state: dict[str, Any],
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """Merge new tool-derived information into the session intake state.

    Mirrors test_harness._update_intake_state for check_sol/classify_treatment/
    route_case, and additionally captures the closing summary fields the LLM may
    pass to end_call (decision, urgency, emotional_state, caller_name,
    caller_email, appointment_slot).
    """
    arguments = arguments or {}
    result = result or {}

    if tool_name == "check_sol":
        intake_state["state"] = arguments.get("state") or intake_state.get("state")
        intake_state["accident_date"] = arguments.get("accident_date") or intake_state.get(
            "accident_date"
        )
        intake_state["sol_viable"] = result.get("viable", intake_state.get("sol_viable"))
        intake_state["sol_deadline"] = result.get("sol_deadline", intake_state.get("sol_deadline"))
        intake_state["sol_days_remaining"] = result.get(
            "days_remaining", intake_state.get("sol_days_remaining")
        )
    elif tool_name == "classify_treatment":
        intake_state["severity_tier"] = result.get(
            "severity_tier", intake_state.get("severity_tier")
        )
        red_flags = result.get("red_flags")
        if isinstance(red_flags, list):
            intake_state["red_flags"] = red_flags
    elif tool_name == "route_case":
        intake_state["decision"] = result.get("decision", intake_state.get("decision"))
        intake_state["urgency"] = result.get("urgency", intake_state.get("urgency"))
        intake_state["case_type"] = arguments.get("case_type") or intake_state.get("case_type")
        intake_state["attorney_tier"] = result.get(
            "attorney_tier", intake_state.get("attorney_tier")
        )
        intake_state["has_prior_representation"] = arguments.get(
            "has_prior_representation", intake_state.get("has_prior_representation")
        )
        intake_state["defendant_type"] = arguments.get("defendant_type") or intake_state.get(
            "defendant_type"
        )
    elif tool_name == "end_call":
        for key in (
            "decision",
            "urgency",
            "emotional_state",
            "caller_name",
            "caller_email",
            "appointment_slot",
        ):
            value = arguments.get(key)
            if value is not None:
                intake_state[key] = value


def build_queue_dict(intake_state: dict[str, Any]) -> dict[str, Any]:
    """Build the post-call follow-up queue from intake state and serialize it.

    Field mapping mirrors test_harness._print_session_summary.
    """
    queue = build_standard_queue(
        caller_name=intake_state.get("caller_name") or "Unknown Caller",
        caller_phone=intake_state.get("caller_phone") or "000-000-0000",
        caller_email=intake_state.get("caller_email"),
        decision=intake_state.get("decision") or "declined",
        attorney_tier=intake_state.get("attorney_tier"),
        case_type=intake_state.get("case_type") or "other",
        severity_tier=intake_state.get("severity_tier") or "moderate",
        urgency=intake_state.get("urgency") or "low",
        appointment_slot=intake_state.get("appointment_slot"),
        sol_deadline=intake_state.get("sol_deadline"),
        red_flags=intake_state.get("red_flags") or [],
        emotional_state=intake_state.get("emotional_state") or "calm",
    )
    return queue.flush_to_dict()


def build_transcript(messages: list[dict[str, Any]] | None) -> str:
    """Render the conversation messages into a plain-text transcript.

    Includes only spoken user/assistant turns; skips the system prompt, tool
    messages, and the injected greeting-trigger turn.
    """
    if not messages:
        return ""
    lines: list[str] = []
    for m in messages:
        role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        text = content.strip()
        if not text or _GREETING_TRIGGER_MARKER in text:
            continue
        lines.append(f"{'Caller' if role == 'user' else 'Aria'}: {text}")
    return "\n".join(lines)


def finalize_session(intake_state: dict[str, Any], transcript: str) -> dict[str, Any]:
    """Build the follow-up queue and persist intake + transcript + queue to S3.

    Synchronous (boto3 is blocking) — call via a thread executor from async code.
    Degrades gracefully: if INTAKE_S3_BUCKET is unset or boto3/credentials are
    missing, the queue is still built and logged; only the upload is skipped.

    Returns:
        {"queue": <queue_dict>, "s3": <log_session result or None>}.
    """
    session_id = intake_state.get("session_id") or "unknown-session"
    queue_data = build_queue_dict(intake_state)

    logger.info(
        "[POSTCALL] session={} decision={} urgency={} severity={} red_flags={} tasks={}",
        session_id,
        intake_state.get("decision"),
        intake_state.get("urgency"),
        intake_state.get("severity_tier"),
        intake_state.get("red_flags"),
        queue_data["task_count"],
    )
    for task in queue_data["tasks"]:
        logger.info("[POSTCALL]   queued: {} [{}]", task["task_type"], task["priority"])

    bucket = os.getenv("INTAKE_S3_BUCKET")
    if not bucket:
        logger.warning(
            "[POSTCALL] INTAKE_S3_BUCKET not set — queue built and logged, S3 upload skipped."
        )
        return {"queue": queue_data, "s3": None}

    s3_result = log_session(
        bucket_name=bucket,
        session_id=session_id,
        intake_data=dict(intake_state),
        transcript=transcript,
        queue_data=queue_data,
    )
    if s3_result.get("all_success"):
        logger.info("[POSTCALL] ✓ S3 upload ok: {}", s3_result)
    else:
        logger.error("[POSTCALL] ✖ S3 upload failed: {}", s3_result)
    return {"queue": queue_data, "s3": s3_result}
