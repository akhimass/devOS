"""Persist a finished call to Supabase via the atomic `record_call` RPC.

Mirrors tools/s3_logger.py's contract: synchronous (called from finalize_session
inside asyncio.to_thread), degrades gracefully when unconfigured, and NEVER raises
— a Supabase outage must not break call teardown.

Auth uses the SERVICE_ROLE key (bypasses RLS) and must only ever live in the
Pipecat Cloud secret set / gitignored .env — never in the dashboard or git.
"""

from __future__ import annotations

import os
from typing import Any

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover - allows import in envs without supabase installed
    Client = None  # type: ignore[assignment, misc]
    create_client = None  # type: ignore[assignment]

_client: Any | None = None


def _get_client() -> Any | None:
    """Return a cached Supabase client, or None if unconfigured/unavailable."""
    global _client
    if _client is not None:
        return _client
    if create_client is None:
        logger.warning("[SUPABASE] supabase package not installed — DB write skipped.")
        return None
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    _client = create_client(url, key)
    return _client


def _s3_keys(s3_result: Any | None) -> dict[str, Any]:
    """Extract the S3 object keys from a log_session() result, if present."""
    if not isinstance(s3_result, dict):
        return {}
    intake = s3_result.get("intake") or {}
    queue = s3_result.get("queue") or {}
    return {
        "intake_key": intake.get("intake_key"),
        "transcript_key": intake.get("transcript_key"),
        "queue_key": queue.get("queue_key"),
    }


def record_call_to_supabase(
    intake_state: dict[str, Any],
    transcript: str,
    events: list[dict[str, Any]],
    queue_dict: dict[str, Any],
    call_ended_reason: str = "completed",
    s3_keys: Any | None = None,
) -> dict[str, Any]:
    """Upsert the call (+ caller + events + queue tasks) via the record_call RPC.

    Returns a small status dict; never raises.
    """
    client = _get_client()
    if client is None:
        logger.warning(
            "[SUPABASE] SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY not set — DB write skipped."
        )
        return {"skipped": True}

    args = {
        "p_session_id": intake_state.get("session_id") or "unknown-session",
        "p_caller_phone": intake_state.get("caller_phone"),
        "p_intake": intake_state,
        "p_transcript": transcript or "",
        "p_events": events or [],
        "p_tasks": (queue_dict or {}).get("tasks", []),
        "p_call_ended_reason": call_ended_reason,
        "p_s3": _s3_keys(s3_keys),
    }
    try:
        resp = client.rpc("record_call", args).execute()
        call_id = getattr(resp, "data", None)
        logger.info("[SUPABASE] ✓ record_call ok session={} call_id={}", args["p_session_id"], call_id)
        return {"ok": True, "call_id": call_id}
    except Exception as e:
        logger.error("[SUPABASE] ✖ record_call failed session={}: {!r}", args["p_session_id"], e)
        return {"ok": False, "error": str(e)}
