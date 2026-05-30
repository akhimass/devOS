# Required environment variables:
# AWS_ACCESS_KEY_ID         — AWS credentials
# AWS_SECRET_ACCESS_KEY     — AWS credentials
# AWS_DEFAULT_REGION        — e.g. "us-east-1"
# INTAKE_S3_BUCKET          — S3 bucket name for intake storage
# BEDROCK_KNOWLEDGE_BASE_ID — Bedrock Knowledge Base ID for SoL RAG queries
# BEDROCK_MODEL_ARN         — Model ARN for Bedrock generation (optional, has default)

from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone
from typing import Any

try:
    from pipecat.services.llm_service import FunctionCallParams
except Exception:  # pragma: no cover - fallback for environments without pipecat installed

    class FunctionCallParams:  # type: ignore[no-redef]
        """Minimal fallback matching the attributes used by the tool handlers."""

        def __init__(self, arguments: dict | None = None, result_callback=None):
            self.arguments = arguments or {}
            self.result_callback = result_callback or self._noop_result_callback

        async def _noop_result_callback(self, *_args, **_kwargs):
            return None

try:
    boto3: Any = importlib.import_module("boto3")
except Exception:  # pragma: no cover - fallback for environments without boto3 installed
    boto3 = None


def _make_s3_client() -> Any | None:
    """Create an S3 client using environment-based AWS credentials.

    Returns:
        A boto3 S3 client when boto3 is available, otherwise None.

    Raises:
        None.
    """

    if boto3 is None:
        return None
    return boto3.client("s3")


def log_intake_to_s3(
    bucket_name: str,
    intake_data: dict,
    transcript: str,
    session_id: str,
    decision: str,
) -> dict:
    """Write the intake JSON and transcript text to S3.

    Args:
        bucket_name: S3 bucket name.
        intake_data: Structured intake JSON object.
        transcript: Full call transcript as plain text.
        session_id: Unique identifier for the call session.
        decision: Final decision string, such as "qualified" or "declined".

    Returns:
        A dictionary with success status, S3 keys, and an error message when
        upload fails.

    Raises:
        None. All failures are caught and returned in the result dictionary.
    """

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    intake_key = f"intake/{today}/{session_id}/intake.json"
    transcript_key = f"intake/{today}/{session_id}/transcript.txt"

    try:
        client = _make_s3_client()
        if client is None:
            raise RuntimeError("boto3 is not installed in this environment")

        client.put_object(
            Bucket=bucket_name,
            Key=intake_key,
            Body=json.dumps(intake_data, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
            Metadata={"decision": decision, "session_id": session_id},
        )
        client.put_object(
            Bucket=bucket_name,
            Key=transcript_key,
            Body=transcript.encode("utf-8"),
            ContentType="text/plain",
            Metadata={"session_id": session_id},
        )
        return {
            "success": True,
            "intake_key": intake_key,
            "transcript_key": transcript_key,
            "error": None,
        }
    except Exception as e:
        return {"success": False, "intake_key": None, "transcript_key": None, "error": str(e)}


def log_queue_to_s3(
    bucket_name: str,
    queue_data: dict,
    session_id: str,
) -> dict:
    """Write post-call queue JSON to S3.

    Args:
        bucket_name: S3 bucket name.
        queue_data: Output of PostCallQueue.flush_to_dict().
        session_id: Unique identifier for the call session.

    Returns:
        A dictionary with success status, the queue key, and an error message
        when upload fails.

    Raises:
        None. All failures are caught and returned in the result dictionary.
    """

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    queue_key = f"intake/{today}/{session_id}/queue.json"

    try:
        client = _make_s3_client()
        if client is None:
            raise RuntimeError("boto3 is not installed in this environment")

        client.put_object(
            Bucket=bucket_name,
            Key=queue_key,
            Body=json.dumps(queue_data, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
            Metadata={"session_id": session_id},
        )
        return {"success": True, "queue_key": queue_key, "error": None}
    except Exception as e:
        return {"success": False, "queue_key": None, "error": str(e)}


def log_session(
    bucket_name: str,
    session_id: str,
    intake_data: dict,
    transcript: str,
    queue_data: dict,
) -> dict:
    """Write all session artifacts to S3 in one call.

    Args:
        bucket_name: S3 bucket name.
        session_id: Unique identifier for the call session.
        intake_data: Structured intake JSON object.
        transcript: Full call transcript.
        queue_data: Serialized queue payload.

    Returns:
        A dictionary containing the intake result, queue result, and an all_success
        boolean.

    Raises:
        None.
    """

    decision = str(intake_data.get("decision", "unknown"))
    intake_result = log_intake_to_s3(
        bucket_name=bucket_name,
        intake_data=intake_data,
        transcript=transcript,
        session_id=session_id,
        decision=decision,
    )
    queue_result = log_queue_to_s3(
        bucket_name=bucket_name,
        queue_data=queue_data,
        session_id=session_id,
    )
    return {
        "intake": intake_result,
        "queue": queue_result,
        "all_success": bool(intake_result.get("success")) and bool(queue_result.get("success")),
    }


async def log_session_handler(params: FunctionCallParams) -> None:
    """Pipecat handler that wraps log_session.

    Args:
        params: Pipecat FunctionCallParams containing function arguments and a
            result callback.

    Returns:
        None. The structured result is emitted with params.result_callback().

    Raises:
        None. Any exception should be handled by the surrounding runtime.
    """

    result = log_session(**params.arguments)
    await params.result_callback(result)
