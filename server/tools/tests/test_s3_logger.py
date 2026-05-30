from __future__ import annotations

import asyncio

import tools.s3_logger as s3


class FakeS3Client:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.calls = []

    def put_object(self, **kwargs):
        self.calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("boom")
        return {"ETag": '"ok"'}


def test_log_session_writes_intake_transcript_and_queue(monkeypatch):
    client = FakeS3Client()
    monkeypatch.setattr(s3, "_make_s3_client", lambda: client)

    result = s3.log_session(
        bucket_name="bucket-name",
        session_id="session-123",
        intake_data={"decision": "qualified", "caller_name": "Alex"},
        transcript="hello world",
        queue_data={"tasks": [{"task_type": "save_transcript"}]},
    )

    assert result["all_success"] is True
    assert result["intake"]["success"] is True
    assert result["queue"]["success"] is True
    assert result["intake"]["intake_key"].endswith("/session-123/intake.json")
    assert result["intake"]["transcript_key"].endswith("/session-123/transcript.txt")
    assert result["queue"]["queue_key"].endswith("/session-123/queue.json")
    assert len(client.calls) == 3
    assert client.calls[0]["Metadata"]["decision"] == "qualified"
    assert client.calls[1]["ContentType"] == "text/plain"


def test_log_session_returns_error_instead_of_raising(monkeypatch):
    client = FakeS3Client(should_fail=True)
    monkeypatch.setattr(s3, "_make_s3_client", lambda: client)

    result = s3.log_session(
        bucket_name="bucket-name",
        session_id="session-456",
        intake_data={"decision": "declined"},
        transcript="hello world",
        queue_data={"tasks": []},
    )

    assert result["all_success"] is False
    assert result["intake"]["success"] is False
    assert result["intake"]["error"] is not None
    assert result["queue"]["success"] is False
    assert result["queue"]["error"] is not None


def test_log_session_handler_returns_callback_payload():
    captured = {}

    async def callback(result):
        captured.update(result)

    async def fake_log_session(**kwargs):
        return {"ok": True, "kwargs": kwargs}

    original = s3.log_session
    try:
        s3.log_session = lambda **kwargs: {"status": "logged", "received": kwargs}
        params = s3.FunctionCallParams(
            arguments={"bucket_name": "b", "session_id": "s", "intake_data": {}, "transcript": "t", "queue_data": {}},
            result_callback=callback,
        )
        asyncio.run(s3.log_session_handler(params))
    finally:
        s3.log_session = original

    assert captured["status"] == "logged"
    assert captured["received"]["session_id"] == "s"
