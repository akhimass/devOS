"""Automatic post-call eval loop: score call in Cekura, patch prompt on failures."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)

CEKURA_API_BASE = "https://api.cekura.ai"
EVAL_LOOP_MARKER_START = "<!-- EVAL_LOOP_AUTO_START -->"
EVAL_LOOP_MARKER_END = "<!-- EVAL_LOOP_AUTO_END -->"

# Scenario 273084 metrics on the Cekura dashboard
DEFAULT_TRACKED_METRICS: dict[str, int] = {
    "Agent Asked What Happened": 147963,
    "Agent Asked About Medical Attention": 147964,
    "Agent Asked About Legal Representation": 147965,
}

METRIC_PATCHES: dict[str, str] = {
    "Agent Asked What Happened": (
        "REMINDER: Open with the standard greeting and ask what happened in the first agent turn."
    ),
    "Agent Asked About Medical Attention": (
        "REMINDER: Within three turns after the caller describes the incident, ask exactly: "
        '"Have you seen a doctor or received any medical care for this since the accident?" '
        "Do not skip this for distressed callers — use distressed_medical_bridge if needed."
    ),
    "Agent Asked About Legal Representation": (
        'REMINDER: Before fault or contact collection, ask exactly: '
        '"Before I go further — do you currently have an attorney representing you for this incident?"'
    ),
}


def _api_headers() -> dict[str, str] | None:
    api_key = os.getenv("CEKURA_API_KEY", "").strip()
    if not api_key:
        return None
    return {"X-CEKURA-API-KEY": api_key, "Content-Type": "application/json"}


def _tracked_metric_ids() -> dict[str, int]:
    raw = os.getenv("CEKURA_TRACKED_METRIC_IDS", "").strip()
    if not raw:
        return dict(DEFAULT_TRACKED_METRICS)
    out: dict[str, int] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        name, mid = part.rsplit(":", 1)
        out[name.strip()] = int(mid.strip())
    return out or dict(DEFAULT_TRACKED_METRICS)


def _prompt_path() -> Path:
    override = os.getenv("MASTER_PROMPT_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[1] / "prompts" / "master_prompt.md"


def _history_path() -> Path:
    override = os.getenv("EVAL_LOOP_HISTORY_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[2] / "runtime" / "eval_loop_history.jsonl"


def metric_passed(metric: dict[str, Any]) -> bool:
    """Return True when Cekura scored the metric as passing."""

    norm = metric.get("score_normalized")
    if norm is not None:
        try:
            return float(norm) >= 1.0
        except (TypeError, ValueError):
            pass
    score = metric.get("score")
    if score is not None:
        try:
            return float(score) >= 1.0
        except (TypeError, ValueError):
            pass
    return False


def parse_tracked_metrics(call_detail: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract tracked metric results from a call-log detail payload."""

    tracked = _tracked_metric_ids()
    id_to_name = {v: k for k, v in tracked.items()}
    found: dict[str, dict[str, Any]] = {}

    evaluation = call_detail.get("evaluation") or {}
    metrics = evaluation.get("metrics") if isinstance(evaluation, dict) else []
    if not isinstance(metrics, list):
        metrics = call_detail.get("metrics") or []

    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        mid = metric.get("id")
        name = metric.get("name") or id_to_name.get(mid)
        if name in tracked:
            found[name] = metric
    return found


def poll_call_log(call_log_id: int, *, max_wait_s: float = 120, interval_s: float = 5) -> dict[str, Any]:
    """Poll observability call log until evaluation finishes or timeout."""

    headers = _api_headers()
    if not headers:
        return {"status": "skipped", "reason": "no CEKURA_API_KEY"}

    url = f"{CEKURA_API_BASE}/observability/v1/call-logs-external/{call_log_id}/"
    deadline = time.time() + max_wait_s
    last: dict[str, Any] = {}

    while time.time() < deadline:
        response = requests.get(url, headers=headers, timeout=30)
        if not response.ok:
            return {"status": "error", "http_status": response.status_code, "body": response.text[:500]}
        last = response.json()
        status = (last.get("status") or "").lower()
        if status in ("success", "failure", "completed", "reviewed"):
            return last
        if status not in ("evaluating", "pending", ""):
            return last
        time.sleep(interval_s)

    return last


def trigger_metric_evaluation(call_log_id: int, metric_ids: list[int], project_id: int) -> None:
    """Kick off async metric evaluation if the observe upload did not."""

    headers = _api_headers()
    if not headers:
        return
    payload = {"call_logs": [call_log_id], "metrics": metric_ids, "project_id": project_id}
    requests.post(
        f"{CEKURA_API_BASE}/observability/v1/call-logs/evaluate_metrics/",
        headers=headers,
        json=payload,
        timeout=30,
    )


def build_patch_block(failures: dict[str, dict[str, Any]]) -> str:
    """Build auto-patch text from failed metrics."""

    lines = [
        f"# Eval loop update — {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    for name, metric in failures.items():
        patch = METRIC_PATCHES.get(name, f"Improve behavior for metric: {name}")
        explanation = metric.get("explanation")
        if isinstance(explanation, list):
            explanation = " ".join(str(x) for x in explanation)
        lines.append(f"## Failed: {name}")
        if explanation:
            lines.append(f"Cekura feedback: {explanation}")
        lines.append(patch)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def apply_prompt_patches(patch_block: str) -> Path:
    """Replace content between EVAL_LOOP markers in master_prompt.md."""

    path = _prompt_path()
    text = path.read_text(encoding="utf-8")
    if EVAL_LOOP_MARKER_START not in text or EVAL_LOOP_MARKER_END not in text:
        raise ValueError(f"Eval loop markers missing in {path}")

    replacement = (
        f"{EVAL_LOOP_MARKER_START}\n"
        f"{patch_block.rstrip()}\n"
        f"{EVAL_LOOP_MARKER_END}"
    )
    pattern = re.compile(
        re.escape(EVAL_LOOP_MARKER_START) + r".*?" + re.escape(EVAL_LOOP_MARKER_END),
        flags=re.DOTALL,
    )
    updated = pattern.sub(replacement, text, count=1)
    path.write_text(updated, encoding="utf-8")
        logger.info(f"[EVAL_LOOP] updated prompt patches in {path}")
    return path


def append_history(entry: dict[str, Any]) -> None:
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def sync_agent_description(prompt_text: str) -> dict[str, Any] | None:
    """Mirror prompt into Cekura agent description (truncated)."""

    if os.getenv("CEKURA_EVAL_LOOP_SYNC_AGENT", "true").lower() != "true":
        return None

    headers = _api_headers()
    agent_id = os.getenv("CEKURA_AGENT_ID", "").strip()
    if not headers or not agent_id:
        return None

    description = prompt_text[:12000]
    response = requests.patch(
        f"{CEKURA_API_BASE}/test_framework/v1/aiagents/{agent_id}/",
        headers=headers,
        json={"description": description},
        timeout=30,
    )
    if response.ok:
        logger.info(f"[EVAL_LOOP] synced agent {agent_id} description ({len(description)} chars)")
        return {"status": "ok"}
    logger.error(f"[EVAL_LOOP] agent sync failed: {response.text[:300]}")
    return {"status": "error", "body": response.text[:300]}


def run_post_call_eval_loop(
    *,
    observe_result: dict[str, Any] | None,
    call_id: str,
) -> dict[str, Any]:
    """Run eval loop after observability upload.

    1. Poll Cekura until metrics are scored.
    2. Record pass/fail for tracked metrics.
    3. Patch master_prompt.md on failures.
    4. Optionally sync description to Cekura agent.
    """

    if os.getenv("CEKURA_EVAL_LOOP_ENABLED", "true").lower() != "true":
        return {"status": "disabled"}

    headers = _api_headers()
    if not headers:
        return {"status": "skipped", "reason": "no CEKURA_API_KEY"}

    call_log_id = observe_result.get("id") if isinstance(observe_result, dict) else None
    if not call_log_id:
        return {"status": "skipped", "reason": "no call log id from observe"}

    project_id = int(os.getenv("CEKURA_PROJECT_ID", "5853"))
    metric_ids = list(_tracked_metric_ids().values())
    trigger_metric_evaluation(int(call_log_id), metric_ids, project_id)

    detail = poll_call_log(int(call_log_id))
    metrics = parse_tracked_metrics(detail)
    if not metrics:
        return {"status": "pending", "call_log_id": call_log_id, "detail_status": detail.get("status")}

    passed = {name: metric_passed(m) for name, m in metrics.items()}
    failures = {name: m for name, m in metrics.items() if not passed[name]}

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "call_id": call_id,
        "call_log_id": call_log_id,
        "passed": passed,
        "failures": {
            name: {
                "explanation": m.get("explanation"),
                "score_normalized": m.get("score_normalized"),
            }
            for name, m in failures.items()
        },
    }
    append_history(entry)

    result: dict[str, Any] = {
        "status": "ok",
        "call_log_id": call_log_id,
        "passed": passed,
        "all_passed": len(failures) == 0,
    }

    if failures:
        patch_block = build_patch_block(failures)
        apply_prompt_patches(patch_block)
        result["patched"] = list(failures.keys())
        prompt_text = _prompt_path().read_text(encoding="utf-8")
        result["agent_sync"] = sync_agent_description(prompt_text)
        logger.warning(
            f"[EVAL_LOOP] call {call_id} failed metrics: {list(failures.keys())} — prompt patched"
        )
    else:
        apply_prompt_patches(
            f"# Eval loop — all tracked metrics passed ({datetime.now(timezone.utc).date()})\n"
        )
        result["patched"] = []
        logger.info(f"[EVAL_LOOP] call {call_id} passed all tracked metrics")

    return result
