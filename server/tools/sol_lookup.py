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
import os
import re
from datetime import date
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=True)

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

RelativedeltaType: Any
try:
    _relativedelta_module = importlib.import_module("dateutil.relativedelta")
    RelativedeltaType = _relativedelta_module.relativedelta
except Exception:  # pragma: no cover - fallback for environments without python-dateutil

    class _FallbackRelativedelta:
        """Minimal relativedelta fallback for environments missing python-dateutil.

        This fallback supports the subset of date arithmetic used by this tool:
        year, month, and day offsets. It keeps the module importable in lean test
        environments while the real dependency is still declared in requirements.
        """

        def __init__(self, years: int = 0, months: int = 0, days: int = 0):
            self.years = years
            self.months = months
            self.days = days

        def _apply(self, base_date: date, sign: int) -> date:
            """Apply the offset to a date, preserving month-end behavior."""

            from calendar import monthrange
            from datetime import timedelta

            year = base_date.year + sign * self.years
            month = base_date.month + sign * self.months
            while month > 12:
                year += 1
                month -= 12
            while month < 1:
                year -= 1
                month += 12

            day = min(base_date.day, monthrange(year, month)[1])
            adjusted = base_date.replace(year=year, month=month, day=day)
            if self.days:
                adjusted = adjusted + timedelta(days=sign * self.days)
            return adjusted

        def __radd__(self, other):
            """Support date + relativedelta."""

            return self._apply(other, 1)

        def __rsub__(self, other):
            """Support date - relativedelta."""

            return self._apply(other, -1)

    RelativedeltaType = _FallbackRelativedelta


SOL_TABLE: dict[str, dict[str, float | int]] = {
    "CA": {"sol_years": 2.0, "govt_notice_days": 180},
    "TX": {"sol_years": 2.0, "govt_notice_days": 180},
    "FL": {"sol_years": 4.0, "govt_notice_days": 180},
    "NY": {"sol_years": 3.0, "govt_notice_days": 90},
    "IL": {"sol_years": 2.0, "govt_notice_days": 180},
    "PA": {"sol_years": 2.0, "govt_notice_days": 180},
    "OH": {"sol_years": 2.0, "govt_notice_days": 180},
    "GA": {"sol_years": 2.0, "govt_notice_days": 180},
    "NC": {"sol_years": 3.0, "govt_notice_days": 180},
    "MI": {"sol_years": 3.0, "govt_notice_days": 180},
}
DEFAULT_SOL = {"sol_years": 2.0, "govt_notice_days": 180}
_NUMBER_WORDS: dict[str, float] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
    "half": 0.5,
}


def _add_years(base_date: date, years: float) -> date:
    """Add a year-based interval to a date using month-aware arithmetic.

    Args:
        base_date: The starting date.
        years: Number of years to add. The tool rounds this to the nearest month.

    Returns:
        The adjusted date.

    Raises:
        ValueError: If the input years cannot be converted into a valid month offset.
    """

    months = int(round(years * 12))
    return base_date + RelativedeltaType(months=months)


def _word_to_number(token: str) -> float | None:
    """Convert a small number word or phrase fragment into a numeric value.

    Args:
        token: Text token such as "two" or "ninety".

    Returns:
        The numeric value if recognized, otherwise None.

    Raises:
        None.
    """

    return _NUMBER_WORDS.get(token.lower())


def _extract_number(text: str, unit_pattern: str) -> float | int | None:
    """Extract a nearby numeric or word-based value from natural-language text.

    Args:
        text: Natural-language text returned by Bedrock.
        unit_pattern: Regex snippet describing the target unit (e.g. years|days).

    Returns:
        The first matching numeric value, or None if nothing parseable is found.

    Raises:
        None.
    """

    numeric_match = re.search(rf"\b(\d+(?:\.\d+)?)\s*(?:{unit_pattern})\b", text, flags=re.I)
    if numeric_match:
        raw_value = numeric_match.group(1)
        return float(raw_value) if "." in raw_value else int(raw_value)

    word_match = re.search(
        rf"\b({'|'.join(sorted(_NUMBER_WORDS))})\s*(?:{unit_pattern})\b",
        text,
        flags=re.I,
    )
    if word_match:
        return _word_to_number(word_match.group(1))

    return None


def _parse_bedrock_sol_response(text: str, state: str, defendant_type: str) -> dict[str, Any] | None:
    """Parse Bedrock's natural-language response into structured SoL data.

    Args:
        text: Raw text returned by Bedrock retrieve_and_generate.
        state: Two-letter state code used for the lookup.
        defendant_type: "private" or "government".

    Returns:
        A dict containing sol_years and govt_notice_days when parsing succeeds, or
        None if the response cannot be parsed confidently enough to use.

    Raises:
        None.
    """

    if not text.strip():
        return None

    sol_years = _extract_number(text, r"year(?:s)?|yr(?:s)?")
    if sol_years is None:
        return None

    govt_notice_days = _extract_number(text, r"day(?:s)?")
    if defendant_type.strip().lower() == "government" and govt_notice_days is None:
        return None

    if govt_notice_days is None:
        govt_notice_days = DEFAULT_SOL["govt_notice_days"]

    return {
        "state": state.upper(),
        "sol_years": float(sol_years),
        "govt_notice_days": int(govt_notice_days),
    }


def _query_bedrock_sol(state: str, accident_date: str, defendant_type: str) -> dict[str, Any] | None:
    """Query the Bedrock Knowledge Base for SoL information.

    Args:
        state: Two-letter state code.
        accident_date: Accident date in ISO format.
        defendant_type: "private" or "government".

    Returns:
        Parsed SoL data when Bedrock is available and the response is parseable, or
        None when Bedrock is unavailable, misconfigured, or returns unparseable text.

    Raises:
        None. All client and API failures are swallowed so the caller can fall back
        to the static SoL table.
    """

    kb_id = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
    if not kb_id:
        return None

    try:
        boto3 = importlib.import_module("boto3")
    except Exception:
        return None

    model_arn = os.getenv(
        "BEDROCK_MODEL_ARN",
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    )
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    query = (
        f"What is the statute of limitations for personal injury cases in {state}? "
        f"Include the standard filing deadline in years, any government notice of claim "
        f"deadline in days if the defendant is a government entity, and any tolling "
        f"exceptions for minors or the discovery rule. Return only factual legal data. "
        f"Accident date context: {accident_date}. Defendant type: {defendant_type}."
    )

    try:
        client = boto3.client("bedrock-agent-runtime", region_name=region)
        response = client.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": kb_id,
                    "modelArn": model_arn,
                },
            },
        )
        output_text = response.get("output", {}).get("text", "")
        return _parse_bedrock_sol_response(output_text, state, defendant_type)
    except Exception:
        return None


def _deadline_note(sol_deadline: date, days_remaining: int) -> str:
    """Build a human-readable deadline note for the agent.

    Args:
        sol_deadline: Final filing deadline.
        days_remaining: Number of days remaining until the deadline.

    Returns:
        A concise note suitable for conversational output.

    Raises:
        None.
    """

    if days_remaining < 0:
        return (
            f"SoL expired as of {sol_deadline.isoformat()}. "
            f"Filing window closed {abs(days_remaining)} days ago."
        )
    if days_remaining <= 30:
        return f"SoL viable but close. Only {days_remaining} days remaining. Flag as urgent."
    return f"SoL viable. {days_remaining} days remaining until {sol_deadline.isoformat()}."


def check_sol(
    state: str,
    accident_date: str,
    plaintiff_age: int,
    defendant_type: str,
) -> dict:
    """Check statute-of-limitations viability for a personal injury intake.

    Args:
        state: Two-letter US state code, e.g. "CA".
        accident_date: ISO format accident date in YYYY-MM-DD form.
        plaintiff_age: Plaintiff age at the time of the accident.
        defendant_type: "private" or "government".

    Returns:
        A dictionary containing viability, deadline information, tolling, notice
        timing, the source used for the SoL data, and a human-readable note.

    Raises:
        ValueError: If accident_date is not ISO-formatted or plaintiff_age is negative.
    """

    if plaintiff_age < 0:
        raise ValueError("plaintiff_age must be non-negative")

    accident = date.fromisoformat(accident_date)
    today = date.today()
    state_code = state.strip().upper()
    defendant_kind = defendant_type.strip().lower()

    rag_result = _query_bedrock_sol(state_code, accident_date, defendant_kind)
    if rag_result is not None:
        sol_years = float(rag_result["sol_years"])
        govt_notice_days = int(rag_result["govt_notice_days"])
        rag_source = "bedrock"
        notes_parts = [
            f"Bedrock knowledge base lookup succeeded for {state_code}.",
        ]
    else:
        table_entry = SOL_TABLE.get(state_code, DEFAULT_SOL)
        sol_years = float(table_entry["sol_years"])
        govt_notice_days = int(table_entry["govt_notice_days"])
        rag_source = "fallback_table"
        notes_parts = ["Bedrock lookup was unavailable or unparseable; using the fallback table."]
        if state_code not in SOL_TABLE:
            notes_parts.append(
                f"State {state_code} is not in the fallback table, so the default values were used."
            )

    tolling_applied = False
    tolling_reason: str | None = None
    if plaintiff_age < 18:
        approx_birthday = accident - RelativedeltaType(years=plaintiff_age)
        eighteenth = approx_birthday + RelativedeltaType(years=18)
        deadline = _add_years(eighteenth, sol_years)
        tolling_applied = True
        tolling_reason = "minority"
        notes_parts.append("Minority tolling applied because the plaintiff was under 18 at the time of the accident.")
    else:
        deadline = _add_years(accident, sol_years)

    days_remaining = (deadline - today).days
    expired = days_remaining < 0
    viable = not expired

    govt_notice_deadline: str | None = None
    govt_notice_days_remaining: int | None = None
    if defendant_kind == "government":
        govt_deadline = accident + RelativedeltaType(days=govt_notice_days)
        govt_notice_deadline = govt_deadline.isoformat()
        govt_notice_days_remaining = (govt_deadline - today).days
        if govt_notice_days_remaining < 0:
            notes_parts.append(
                f"Government defendant. Notice of claim deadline was {govt_notice_deadline} ({govt_notice_days_remaining} days remaining). "
                "The government notice window may already be closed, which could be a case-killer regardless of the general SoL."
            )
        else:
            notes_parts.append(
                f"Government defendant. Notice of claim deadline was {govt_notice_deadline} ({govt_notice_days_remaining} days remaining)."
            )

    notes_parts.append(_deadline_note(deadline, days_remaining))

    return {
        "viable": viable,
        "sol_years": sol_years,
        "sol_deadline": deadline.isoformat(),
        "days_remaining": days_remaining,
        "expired": expired,
        "tolling_applied": tolling_applied,
        "tolling_reason": tolling_reason,
        "govt_notice_deadline": govt_notice_deadline,
        "govt_notice_days_remaining": govt_notice_days_remaining,
        "rag_source": rag_source,
        "notes": " ".join(notes_parts),
    }


async def check_sol_handler(params: FunctionCallParams) -> None:
    """Pipecat function-call handler for statute-of-limitations lookups.

    Args:
        params: Pipecat FunctionCallParams containing tool arguments and the result
            callback.

    Returns:
        None. The structured result is emitted via params.result_callback().

    Raises:
        None. Any exception should be handled by the surrounding Pipecat runtime.
    """

    result = check_sol(**params.arguments)
    await params.result_callback(result)
