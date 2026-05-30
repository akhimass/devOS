from __future__ import annotations

import builtins
from datetime import date as real_date
from pathlib import Path
from types import SimpleNamespace

import pytest

import test_harness as harness


class FixedDate:
    @classmethod
    def today(cls):
        return real_date(2026, 5, 30)


def test_load_system_prompt_appends_today_line(monkeypatch, tmp_path):
    prompt_path = tmp_path / "master_prompt.md"
    prompt_path.write_text("BASE PROMPT\n")
    monkeypatch.setattr(harness, "PROMPT_PATH", prompt_path)
    monkeypatch.setattr(harness, "date", FixedDate)

    loaded = harness._load_system_prompt()

    assert loaded.startswith("BASE PROMPT\n")
    assert loaded.endswith(
        "Today is Saturday, May 30, 2026. Use this to resolve relative dates the caller mentions."
    )


@pytest.mark.parametrize("sol_mode", [None, "kb-123"])
def test_tool_schema_prompt_reports_mode_and_prompt_length(monkeypatch, capsys, sol_mode):
    monkeypatch.setattr(harness, "SYSTEM_PROMPT", "line1\nline2\nline3")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    if sol_mode is None:
        monkeypatch.delenv("BEDROCK_KNOWLEDGE_BASE_ID", raising=False)
    else:
        monkeypatch.setenv("BEDROCK_KNOWLEDGE_BASE_ID", sol_mode)

    harness._tool_schema_prompt()
    output = capsys.readouterr().out

    assert "PI Intake Test Harness" in output
    assert "Model: gpt-4o-mini" in output
    assert "Prompt: 3 lines" in output
    if sol_mode is None:
        assert "Fallback table mode (no Bedrock KB configured)" in output
    else:
        assert "Bedrock RAG active" in output


def test_execute_tool_applies_defaults_and_filters_arguments(monkeypatch):
    seen = {}

    def fake_check_sol(state, accident_date, plaintiff_age, defendant_type):
        seen["args"] = {
            "state": state,
            "accident_date": accident_date,
            "plaintiff_age": plaintiff_age,
            "defendant_type": defendant_type,
        }
        return {"viable": True, "days_remaining": 7, "sol_deadline": "2026-06-06", "tolling_applied": False, "rag_source": "fallback_table"}

    monkeypatch.setattr(harness, "check_sol", fake_check_sol)

    result = harness._execute_tool("check_sol", {"state": "CA", "accident_date": "2026-05-30"})

    assert seen["args"] == {
        "state": "CA",
        "accident_date": "2026-05-30",
        "plaintiff_age": 30,
        "defendant_type": "private",
    }
    assert result["viable"] is True
    assert result["days_remaining"] == 7


def test_update_intake_state_tracks_tool_outputs():
    state = {
        "caller_name": None,
        "caller_phone": None,
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

    harness._update_intake_state(
        state,
        "check_sol",
        {"state": "CA", "accident_date": "2026-05-30"},
        {"viable": True, "days_remaining": 7, "sol_deadline": "2026-06-06"},
    )
    harness._update_intake_state(
        state,
        "classify_treatment",
        {},
        {"severity_tier": "moderate", "red_flags": ["spinal_injury"]},
    )
    harness._update_intake_state(
        state,
        "route_case",
        {"case_type": "mva", "has_prior_representation": False, "defendant_type": "private"},
        {"decision": "qualified", "urgency": "standard", "attorney_tier": "mid_associate"},
    )
    harness._update_intake_state(
        state,
        "end_call",
        {"decision": "declined", "urgency": "low"},
        {"ok": True},
    )

    assert state["state"] == "CA"
    assert state["accident_date"] == "2026-05-30"
    assert state["sol_viable"] is True
    assert state["sol_deadline"] == "2026-06-06"
    assert state["sol_days_remaining"] == 7
    assert state["severity_tier"] == "moderate"
    assert state["red_flags"] == ["spinal_injury"]
    assert state["case_type"] == "mva"
    assert state["decision"] == "declined"
    assert state["urgency"] == "low"
    assert state["attorney_tier"] == "mid_associate"
    assert state["defendant_type"] == "private"
    assert state["has_prior_representation"] is False


def test_print_session_summary_builds_queue_from_intake_state(monkeypatch, capsys):
    queue_kwargs = {}

    class FakeQueue:
        def flush_to_dict(self):
            return {
                "tasks": [
                    {"task_type": "save_transcript", "priority": "high"},
                    {"task_type": "send_appointment_confirmation", "priority": "high"},
                ],
                "task_count": 2,
                "generated_at": "2026-05-30T00:00:00Z",
            }

    def fake_build_standard_queue(**kwargs):
        queue_kwargs.update(kwargs)
        return FakeQueue()

    monkeypatch.setattr(harness, "build_standard_queue", fake_build_standard_queue)

    harness._print_session_summary(
        tool_log=[
            {"name": "check_sol", "arguments": {"state": "CA"}, "result": {"viable": True, "days_remaining": 7, "sol_deadline": "2026-06-06", "tolling_applied": False, "rag_source": "fallback_table"}},
            {"name": "route_case", "arguments": {"case_type": "mva"}, "result": {"decision": "qualified", "attorney_tier": "mid_associate", "urgency": "standard", "decline_reason": None}},
        ],
        intake_state={
            "caller_name": "Alex Rivera",
            "caller_phone": "555-111-2222",
            "caller_email": "alex@example.com",
            "case_type": "mva",
            "state": "CA",
            "accident_date": "2026-05-30",
            "severity_tier": "moderate",
            "red_flags": ["spinal_injury"],
            "sol_viable": True,
            "sol_deadline": "2026-06-06",
            "sol_days_remaining": 7,
            "urgency": "standard",
            "decision": "qualified",
            "emotional_state": "distressed",
            "appointment_slot": "tomorrow 3pm",
            "attorney_tier": "mid_associate",
            "defendant_type": "private",
            "has_prior_representation": False,
        },
    )

    out = capsys.readouterr().out
    assert "SESSION COMPLETE" in out
    assert "Decision:       QUALIFIED" in out
    assert "POST-CALL QUEUE (would execute):" in out
    assert queue_kwargs["caller_name"] == "Alex Rivera"
    assert queue_kwargs["decision"] == "qualified"
    assert queue_kwargs["emotional_state"] == "distressed"
    assert queue_kwargs["red_flags"] == ["spinal_injury"]


def test_main_happy_path_prints_opening_line_and_exits_on_quit(monkeypatch, capsys):
    class FakeOpenAIClient:
        pass

    calls = []

    def fake_call_model(client, messages):
        calls.append(messages)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Hello, I’m Aria. What happened?", tool_calls=None)
                )
            ]
        )

    monkeypatch.setattr(harness, "SYSTEM_PROMPT", "system prompt")
    monkeypatch.setattr(harness, "_tool_schema_prompt", lambda: None)
    monkeypatch.setattr(harness, "_openai_client", lambda: FakeOpenAIClient())
    monkeypatch.setattr(harness, "_call_model", fake_call_model)
    monkeypatch.setattr(builtins, "input", lambda: "quit")

    harness.main()

    out = capsys.readouterr().out
    assert "Aria:" in out
    assert "Hello, I’m Aria. What happened?" in out
    assert "Session ended." in out
    assert len(calls) == 1
    assert calls[0][0]["role"] == "system"
    assert "A customer just called." in calls[0][1]["content"]
