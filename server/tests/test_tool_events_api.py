from __future__ import annotations

from fastapi.testclient import TestClient

import tool_events_api as api


def test_tool_events_api_requires_bearer_token(monkeypatch, tmp_path):
    monkeypatch.setenv("TOOL_EVENTS_DB_PATH", str(tmp_path / "events.sqlite3"))
    monkeypatch.setenv("TOOL_EVENTS_API_TOKEN", "secret-token")

    client = TestClient(api.app)

    response = client.get("/tool-events")

    assert response.status_code == 401


def test_tool_events_api_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("TOOL_EVENTS_DB_PATH", str(tmp_path / "events.sqlite3"))
    monkeypatch.setenv("TOOL_EVENTS_API_TOKEN", "secret-token")

    client = TestClient(api.app)
    headers = {"Authorization": "Bearer secret-token"}
    payload = {
        "tool_name": "check_sol",
        "phase": "start",
        "session_id": "session-123",
        "arguments": {"state": "CA"},
        "result": None,
        "note": None,
    }

    post_response = client.post("/tool-events", headers=headers, json=payload)
    assert post_response.status_code == 200
    created = post_response.json()
    assert created["id"] == 1
    assert created["tool_name"] == "check_sol"
    assert created["phase"] == "start"

    get_response = client.get("/tool-events", headers=headers, params={"limit": 10})
    assert get_response.status_code == 200
    events = get_response.json()
    assert len(events) == 1
    assert events[0]["session_id"] == "session-123"
    assert events[0]["arguments"] == {"state": "CA"}
