from __future__ import annotations

from pathlib import Path

import tools.intake_assembly as ia


def test_tool_event_log_path_uses_env_override(monkeypatch, tmp_path):
    event_path = tmp_path / "tool-events.jsonl"
    monkeypatch.setenv("INTAKE_TOOL_EVENTS_PATH", str(event_path))

    assert ia.tool_event_log_path() == event_path


def test_append_and_read_tool_events_round_trip(monkeypatch, tmp_path):
    event_path = tmp_path / "tool-events.jsonl"
    monkeypatch.setenv("INTAKE_TOOL_EVENTS_PATH", str(event_path))

    appended = ia.append_tool_event(
        tool_name="check_sol",
        phase="start",
        session_id="session-123",
        arguments={"state": "CA", "accident_date": "2026-05-30"},
    )

    assert appended["tool_name"] == "check_sol"
    assert appended["phase"] == "start"
    assert event_path.exists()

    events = ia.read_tool_events()
    assert len(events) == 1
    assert events[0]["session_id"] == "session-123"
    assert events[0]["arguments"] == {"state": "CA", "accident_date": "2026-05-30"}


def test_read_tool_events_skips_malformed_lines(monkeypatch, tmp_path):
    event_path = tmp_path / "tool-events.jsonl"
    monkeypatch.setenv("INTAKE_TOOL_EVENTS_PATH", str(event_path))
    event_path.write_text(
        '{"tool_name": "check_sol", "phase": "end", "session_id": "session-123"}\n'
        "not-json\n"
        '{"tool_name": "route_case", "phase": "end", "session_id": "session-123"}\n',
        encoding="utf-8",
    )

    events = ia.read_tool_events()

    assert [event["tool_name"] for event in events] == ["check_sol", "route_case"]
