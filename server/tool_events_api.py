from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

load_dotenv(override=True)

APP_TITLE = "Tool Events API"
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "runtime" / "tool_events.sqlite3"


class ToolEventIn(BaseModel):
    timestamp: str | None = None
    tool_name: str
    phase: str
    session_id: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any | None = None
    note: str | None = None


class ToolEventOut(ToolEventIn):
    id: int


def db_path() -> Path:
    override = os.getenv("TOOL_EVENTS_DB_PATH", "").strip()
    return Path(override).expanduser() if override else DEFAULT_DB_PATH


def api_token() -> str | None:
    return os.getenv("TOOL_EVENTS_API_TOKEN", "").strip() or None


def _ensure_db() -> None:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                phase TEXT NOT NULL,
                session_id TEXT,
                arguments_json TEXT NOT NULL,
                result_json TEXT,
                note TEXT
            )
            """
        )
        conn.commit()


@contextmanager
def _connect():
    _ensure_db()
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _authenticate(authorization: str | None = Header(default=None)) -> None:
    token = api_token()
    if not token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    if authorization.removeprefix("Bearer ").strip() != token:
        raise HTTPException(status_code=401, detail="invalid bearer token")


def _row_to_event(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "timestamp": row["timestamp"],
        "tool_name": row["tool_name"],
        "phase": row["phase"],
        "session_id": row["session_id"],
        "arguments": json.loads(row["arguments_json"] or "{}"),
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "note": row["note"],
    }


app = FastAPI(title=APP_TITLE)


@app.get("/health")
def health() -> dict[str, Any]:
    _ensure_db()
    return {"ok": True, "db_path": str(db_path())}


@app.post("/tool-events", response_model=ToolEventOut)
def create_tool_event(event: ToolEventIn, _auth: None = Depends(_authenticate)) -> dict[str, Any]:
    payload = event.model_dump()
    timestamp = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tool_events (
                timestamp, tool_name, phase, session_id, arguments_json, result_json, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                payload["tool_name"],
                payload["phase"],
                payload.get("session_id"),
                json.dumps(payload.get("arguments") or {}, ensure_ascii=False, default=str),
                json.dumps(payload.get("result"), ensure_ascii=False, default=str)
                if payload.get("result") is not None
                else None,
                payload.get("note"),
            ),
        )
        event_id = cursor.lastrowid
    if event_id is None:
        raise RuntimeError("failed to insert tool event")
    return {
        "id": int(event_id),
        "timestamp": timestamp,
        **{k: payload[k] for k in ("tool_name", "phase", "session_id", "arguments", "result", "note")},
    }


@app.get("/tool-events", response_model=list[ToolEventOut])
def list_tool_events(
    limit: int = Query(50, ge=1, le=200),
    session_id: str | None = None,
    after_id: int | None = Query(default=None, ge=0),
    _auth: None = Depends(_authenticate),
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    if after_id is not None:
        clauses.append("id > ?")
        params.append(after_id)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT id, timestamp, tool_name, phase, session_id, arguments_json, result_json, note
        FROM tool_events
        {where}
        ORDER BY id DESC
        LIMIT ?
    """
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()

    events = [_row_to_event(row) for row in reversed(rows)]
    return events


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("TOOL_EVENTS_API_PORT", "8001")))
