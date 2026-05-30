from __future__ import annotations

from pathlib import Path

import tools.intake_assembly as ia


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


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


def test_append_tool_event_posts_to_remote_api(monkeypatch):
    monkeypatch.setenv("TOOL_EVENTS_API_URL", "https://events.example")
    monkeypatch.setenv("TOOL_EVENTS_API_TOKEN", "secret-token")
    recorded = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        payload = dict(json or {})
        recorded.update({"url": url, "headers": headers or {}, "json": payload, "timeout": timeout})
        payload = {**payload, "id": 42}
        return _FakeResponse(payload)

    monkeypatch.setattr(ia.requests, "post", fake_post)

    event = ia.append_tool_event(
        tool_name="check_sol",
        phase="start",
        session_id="session-123",
        arguments={"state": "CA"},
    )

    assert event["id"] == 42
    assert recorded["url"] == "https://events.example/tool-events"
    assert recorded["headers"]["Authorization"] == "Bearer secret-token"
    assert recorded["json"]["tool_name"] == "check_sol"


def test_read_tool_events_fetches_remote_api(monkeypatch):
    monkeypatch.setenv("TOOL_EVENTS_API_URL", "https://events.example")
    monkeypatch.setenv("TOOL_EVENTS_API_TOKEN", "secret-token")

    def fake_get(url, headers=None, params=None, timeout=None):
        assert url == "https://events.example/tool-events"
        assert headers["Authorization"] == "Bearer secret-token"
        assert params["limit"] == 5
        return _FakeResponse(
            [
                {"id": 1, "tool_name": "check_sol", "phase": "start", "session_id": "s1", "arguments": {}, "result": None, "note": None},
                {"id": 2, "tool_name": "check_sol", "phase": "end", "session_id": "s1", "arguments": {}, "result": {"ok": True}, "note": None},
            ]
        )

    monkeypatch.setattr(ia.requests, "get", fake_get)

    events = ia.read_tool_events(limit=5)

    assert [event["id"] for event in events] == [1, 2]
