from __future__ import annotations

from datetime import datetime, timezone

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


class PostCallQueue:
    """In-memory queue for post-call tasks.

    The queue preserves insertion order within the same priority level and can be
    serialized into a JSON-ready dictionary for S3 storage.
    """

    def __init__(self):
        """Initialize an empty task queue."""

        self.tasks: list[dict] = []

    def add_task(self, task_type: str, priority: str, payload: dict) -> None:
        """Add a task to the queue.

        Args:
            task_type: Queue task identifier.
            priority: One of "high", "medium", or "low".
            payload: Task-specific data payload.

        Returns:
            None.

        Raises:
            ValueError: If priority is not one of the accepted values.
        """

        normalized_priority = priority.strip().lower()
        if normalized_priority not in {"high", "medium", "low"}:
            raise ValueError(f"Invalid priority: {priority!r}")

        self.tasks.append(
            {
                "task_type": task_type,
                "priority": normalized_priority,
                "payload": payload,
                "added_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )

    def get_queue(self) -> list[dict]:
        """Return tasks sorted by priority while preserving stable insertion order.

        Returns:
            A sorted list of queued task dictionaries.

        Raises:
            None.
        """

        order = {"high": 0, "medium": 1, "low": 2}
        return sorted(self.tasks, key=lambda task: order[task["priority"]])

    def flush_to_dict(self) -> dict:
        """Serialize the queue to a JSON-friendly dictionary.

        Returns:
            A dictionary containing the sorted tasks, the total task count, and a
            UTC generation timestamp.

        Raises:
            None.
        """

        return {
            "tasks": self.get_queue(),
            "task_count": len(self.tasks),
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }


def build_standard_queue(
    caller_name: str,
    caller_phone: str,
    caller_email: str | None,
    decision: str,
    attorney_tier: str | None,
    case_type: str,
    severity_tier: str,
    urgency: str,
    appointment_slot: str | None,
    sol_deadline: str | None,
    red_flags: list[str],
    emotional_state: str,
) -> PostCallQueue:
    """Build the standard follow-up queue for a call.

    Args:
        caller_name: Caller name.
        caller_phone: Caller phone number.
        caller_email: Caller email address if available.
        decision: "qualified" or "declined".
        attorney_tier: Assigned attorney tier, if any.
        case_type: Case category.
        severity_tier: Injury severity tier.
        urgency: "immediate", "standard", or "low".
        appointment_slot: ISO datetime string for a booked appointment, if any.
        sol_deadline: Statute-of-limitations deadline string, if any.
        red_flags: Red-flag markers from treatment classification.
        emotional_state: "calm", "distressed", or "urgent".

    Returns:
        A populated PostCallQueue with the standard follow-up tasks.

    Raises:
        ValueError: If a task priority is invalid.
    """

    queue = PostCallQueue()
    normalized_decision = decision.strip().lower()
    normalized_case_type = case_type.strip().lower()
    normalized_severity = severity_tier.strip().lower()
    normalized_urgency = urgency.strip().lower()
    normalized_emotional_state = emotional_state.strip().lower()

    queue.add_task(
        "save_transcript",
        "high",
        {
            "caller_phone": caller_phone,
            "case_type": normalized_case_type,
            "decision": normalized_decision,
        },
    )

    if normalized_decision == "qualified":
        queue.add_task(
            "send_appointment_confirmation",
            "high",
            {
                "caller_name": caller_name,
                "caller_phone": caller_phone,
                "caller_email": caller_email,
                "appointment_slot": appointment_slot,
                "attorney_tier": attorney_tier,
            },
        )
        queue.add_task(
            "push_case_summary_to_attorney",
            "high",
            {
                "attorney_tier": attorney_tier,
                "case_type": normalized_case_type,
                "severity_tier": normalized_severity,
                "sol_deadline": sol_deadline,
                "red_flags": red_flags,
                "caller_phone": caller_phone,
            },
        )

    if normalized_urgency == "immediate":
        queue.add_task(
            "flag_for_senior_partner_immediate_review",
            "high",
            {
                "case_type": normalized_case_type,
                "severity_tier": normalized_severity,
                "red_flags": red_flags,
                "caller_phone": caller_phone,
            },
        )

    if "possible_TBI" in red_flags:
        queue.add_task(
            "flag_tbi_risk",
            "high",
            {
                "caller_phone": caller_phone,
                "red_flags": red_flags,
            },
        )

    if normalized_decision == "qualified":
        queue.add_task(
            "request_defendant_insurance_info",
            "medium",
            {
                "case_type": normalized_case_type,
                "caller_phone": caller_phone,
            },
        )
        queue.add_task(
            "send_intake_form_link",
            "medium",
            {
                "caller_name": caller_name,
                "caller_phone": caller_phone,
                "caller_email": caller_email,
            },
        )

    if normalized_emotional_state == "distressed":
        queue.add_task(
            "send_comfort_followup_sms",
            "medium",
            {
                "caller_name": caller_name,
                "caller_phone": caller_phone,
            },
        )

    if normalized_decision == "declined":
        queue.add_task(
            "send_decline_followup_sms",
            "low",
            {
                "caller_name": caller_name,
                "caller_phone": caller_phone,
                "decision": normalized_decision,
                "case_type": normalized_case_type,
                "severity_tier": normalized_severity,
            },
        )

    return queue


async def flush_queue_handler(params: FunctionCallParams) -> None:
    """Pipecat handler that acknowledges a queue flush.

    Args:
        params: Pipecat FunctionCallParams containing the queue payload and result
            callback.

    Returns:
        None. The handler returns a minimal acknowledgement through the callback.

    Raises:
        None.
    """

    await params.result_callback(
        {
            "status": "queue_flushed",
            "task_count": params.arguments.get("task_count", 0),
        }
    )
