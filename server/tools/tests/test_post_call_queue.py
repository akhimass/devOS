from __future__ import annotations

import asyncio

import tools.post_call_queue as pcq


def test_build_standard_queue_orders_tasks_by_priority():
    queue = pcq.build_standard_queue(
        caller_name="Alex Rivera",
        caller_phone="555-111-2222",
        caller_email="alex@example.com",
        decision="qualified",
        attorney_tier="mid_associate",
        case_type="mva",
        severity_tier="moderate",
        urgency="immediate",
        appointment_slot="2026-06-01T14:00:00Z",
        sol_deadline="2026-01-01",
        red_flags=["possible_TBI"],
        emotional_state="distressed",
    )

    payload = queue.flush_to_dict()
    task_types = [task["task_type"] for task in payload["tasks"]]

    assert payload["task_count"] == 8
    assert task_types == [
        "save_transcript",
        "send_appointment_confirmation",
        "push_case_summary_to_attorney",
        "flag_for_senior_partner_immediate_review",
        "flag_tbi_risk",
        "request_defendant_insurance_info",
        "send_intake_form_link",
        "send_comfort_followup_sms",
    ]
    assert payload["tasks"][0]["priority"] == "high"
    assert payload["tasks"][-1]["priority"] == "medium"


def test_build_standard_queue_adds_decline_followup_for_declined_calls():
    queue = pcq.build_standard_queue(
        caller_name="Jordan Lee",
        caller_phone="555-999-0000",
        caller_email=None,
        decision="declined",
        attorney_tier=None,
        case_type="other",
        severity_tier="minor",
        urgency="low",
        appointment_slot=None,
        sol_deadline=None,
        red_flags=[],
        emotional_state="calm",
    )

    payload = queue.flush_to_dict()
    assert payload["task_count"] == 2
    assert [task["task_type"] for task in payload["tasks"]] == [
        "save_transcript",
        "send_decline_followup_sms",
    ]


def test_flush_queue_handler_returns_task_count():
    captured = {}

    async def callback(result):
        captured.update(result)

    params = pcq.FunctionCallParams(arguments={"task_count": 7}, result_callback=callback)
    asyncio.run(pcq.flush_queue_handler(params))

    assert captured == {"status": "queue_flushed", "task_count": 7}
