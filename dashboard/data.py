"""Intake metrics + call records. Live calls come from Supabase (RLS-scoped to the
signed-in staff); demo data is the fallback when Supabase is unconfigured/empty."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from auth import get_client, is_configured


FIRM_NAME = "Morrison & Associates"
FIRM_TAGLINE = "Personal Injury · California & Nevada"
AVG_CASE_VALUE = 5_000

AGENT_NAME = "FirstCall"
AGENT_VERSION = "v3"
AGENT_PROVIDER = "Pipecat Cloud · NVIDIA Nemotron 3 Super"


@dataclass(frozen=True)
class TodaySnapshot:
    total_calls: int
    qualified: int
    declined: int
    after_hours_calls: int
    after_hours_qualified: int
    business_hours_calls: int


@dataclass(frozen=True)
class WeeklySnapshot:
    qualified_leads: int
    consultations_booked: int
    retainers_signed: int
    total_calls: int


@dataclass(frozen=True)
class FunnelStage:
    label: str
    count: int


def get_today() -> TodaySnapshot:
    return TodaySnapshot(
        total_calls=23,
        qualified=14,
        declined=9,
        after_hours_calls=11,
        after_hours_qualified=8,
        business_hours_calls=12,
    )


def get_week() -> WeeklySnapshot:
    return WeeklySnapshot(
        total_calls=118,
        qualified_leads=87,
        consultations_booked=52,
        retainers_signed=31,
    )


def get_funnel() -> list[FunnelStage]:
    week = get_week()
    return [
        FunnelStage("Calls received", week.total_calls),
        FunnelStage("Qualified leads", week.qualified_leads),
        FunnelStage("Consultations booked", week.consultations_booked),
        FunnelStage("Retainers signed", week.retainers_signed),
    ]


def get_decline_reasons() -> dict[str, int]:
    return {
        "No physical injury / emotional distress only": 18,
        "Statute of limitations expired": 14,
        "Already represented by counsel": 12,
        "Outside practice area": 9,
        "Insufficient accident details": 8,
        "Caller declined to proceed": 6,
    }


def get_call_heatmap() -> tuple[list[str], list[str], list[list[int]]]:
    """Hour blocks (rows) × weekday columns. Realistic PI intake pattern."""
    hours = [
        "12–3 AM",
        "3–6 AM",
        "6–9 AM",
        "9 AM–12 PM",
        "12–3 PM",
        "3–6 PM",
        "6–9 PM",
        "9 PM–12 AM",
    ]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    # Evening/weekend heavy — after-hours answering value prop
    values = [
        [1, 0, 2, 1, 1, 3, 4],   # 12-3 AM
        [0, 0, 1, 0, 1, 2, 3],   # 3-6 AM
        [2, 3, 4, 3, 3, 5, 4],   # 6-9 AM
        [8, 9, 11, 10, 9, 4, 3], # 9-12
        [6, 7, 8, 9, 8, 5, 4],   # 12-3
        [5, 6, 7, 8, 7, 6, 5],   # 3-6
        [9, 10, 12, 11, 10, 14, 12],  # 6-9 PM peak
        [7, 8, 9, 8, 9, 16, 15],      # 9-12 PM peak
    ]
    return hours, days, values


def estimated_pipeline(qualified_leads: int, conversion_to_retainer: float = 0.36) -> int:
    """Qualified leads × expected retainer rate × average case value."""
    return int(qualified_leads * conversion_to_retainer * AVG_CASE_VALUE)


def format_currency(amount: int) -> str:
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount:,}"
    return f"${amount}"


# ── Call-level records (Observability › Calls) ───────────────────────────────
@dataclass(frozen=True)
class CallRecord:
    call_id: str
    started_at: str  # human-readable timestamp
    caller: str
    phone: str
    case_type: str
    disposition: str  # "Qualified" | "Declined" | "Transferred"
    score: int  # 0-100 evaluator score
    duration: str  # mm:ss
    channel: str  # "After-hours" | "Business hours"
    language: str  # "English" | "Spanish"
    summary: str


def _mock_calls() -> list[CallRecord]:
    """Demo intake calls (fallback when Supabase is unconfigured/empty)."""
    return [
        CallRecord(
            "2025-11-04-a1f3", "Nov 4, 2025 · 11:42 PM", "Maria Delgado", "+1 (415) 555-0142",
            "Auto accident", "Qualified", 96, "06:12", "After-hours", "English",
            "Rear-ended at a red light, in active treatment, no prior counsel.",
        ),
        CallRecord(
            "recording_2025-11-04-9c", "Nov 4, 2025 · 9:08 PM", "James Okafor", "+1 (702) 555-0188",
            "Slip & fall", "Qualified", 91, "07:48", "After-hours", "English",
            "Fell at a grocery store, ongoing physical therapy.",
        ),
        CallRecord(
            "recording_2025-11-04-2b", "Nov 4, 2025 · 8:21 PM", "Priya Nair", "+1 (408) 555-0173",
            "Auto accident", "Declined", 88, "03:31", "After-hours", "English",
            "Statute of limitations expired (TX, 3 yrs). Polite soft decline.",
        ),
        CallRecord(
            "e6b3773bd0e4", "Nov 4, 2025 · 6:55 PM", "Carlos Mendoza", "+1 (619) 555-0119",
            "Auto accident", "Qualified", 94, "05:27", "After-hours", "Spanish",
            "Bilingual handoff worked; injury + treatment confirmed.",
        ),
        CallRecord(
            "d7bfa7d8801c", "Nov 4, 2025 · 4:33 PM", "Sandra Whitfield", "+1 (415) 555-0150",
            "Already represented", "Declined", 90, "02:14", "Business hours", "English",
            "Caller already has an attorney. Declined per policy.",
        ),
        CallRecord(
            "b61e83ca7942", "Nov 4, 2025 · 3:02 PM", "Tom Bradshaw", "+1 (916) 555-0166",
            "Fender-bender", "Declined", 82, "02:58", "Business hours", "English",
            "Minor collision, no injury, no treatment. Low-value decline.",
        ),
        CallRecord(
            "f0c92a14de77", "Nov 4, 2025 · 1:19 PM", "Aisha Rahman", "+1 (510) 555-0124",
            "Dog bite", "Qualified", 93, "06:41", "Business hours", "English",
            "Dog bite requiring stitches; gathered all required fields.",
        ),
        CallRecord(
            "9a7e22b6c0f1", "Nov 4, 2025 · 11:47 AM", "Robert Kim", "+1 (650) 555-0137",
            "Motorcycle", "Qualified", 89, "08:03", "Business hours", "English",
            "Motorcycle accident; comparative-fault questioning completed.",
        ),
        CallRecord(
            "3d5f81aa90b2", "Nov 3, 2025 · 10:12 PM", "Evelyn Foster", "+1 (775) 555-0198",
            "Slip & fall", "Transferred", 87, "04:50", "After-hours", "English",
            "Distressed elderly caller; empathized then warm-transferred.",
        ),
        CallRecord(
            "7c1b46e2f8a9", "Nov 3, 2025 · 7:38 PM", "Marcus Lee", "+1 (213) 555-0181",
            "Auto accident", "Qualified", 95, "05:09", "After-hours", "English",
            "T-bone collision, ER visit, no prior representation.",
        ),
        CallRecord(
            "5e8a90c1b3d4", "Nov 3, 2025 · 5:55 PM", "Nina Petrova", "+1 (408) 555-0155",
            "Outside practice area", "Declined", 84, "01:47", "Business hours", "English",
            "Workers'-comp matter, outside PI scope. Referred out.",
        ),
        CallRecord(
            "8f2c73d5e6a0", "Nov 3, 2025 · 2:26 PM", "Derek Coleman", "+1 (909) 555-0162",
            "Auto accident", "Qualified", 92, "06:33", "Business hours", "English",
            "Hit by distracted driver, in treatment, strong liability.",
        ),
    ]


def _row_to_record(row: dict[str, Any]) -> CallRecord:
    """Map a Supabase `calls` row to the dashboard's CallRecord dataclass."""
    decision = (row.get("decision") or "").strip()
    case_type = (row.get("case_type") or "").replace("_", " ").strip()
    parts: list[str] = []
    if row.get("severity_tier"):
        parts.append(f"{row['severity_tier']} severity")
    if row.get("state"):
        parts.append(row["state"])
    if row.get("attorney_tier"):
        parts.append((row["attorney_tier"] or "").replace("_", " "))
    summary = ", ".join(p for p in parts if p) or (row.get("transcript") or "")[:90]
    ended = (str(row.get("ended_at") or ""))[:19].replace("T", " ")
    return CallRecord(
        call_id=row.get("session_id") or str(row.get("id") or "—"),
        started_at=ended or "—",
        caller=row.get("caller_name") or "Unknown caller",
        phone=row.get("caller_phone") or "—",
        case_type=case_type.title() if case_type else "—",
        disposition=decision.capitalize() if decision else "—",
        score=0,
        duration="—",
        channel="—",
        language="—",
        summary=summary,
    )


def get_calls() -> list[CallRecord]:
    """Recent intake calls. Live from Supabase when signed in; demo data otherwise."""
    if is_configured() and st.session_state.get("authed"):
        client = get_client()
        if client is not None:
            try:
                resp = (
                    client.table("calls")
                    .select("*")
                    .order("ended_at", desc=True)
                    .limit(200)
                    .execute()
                )
                rows = resp.data or []
                if rows:
                    return [_row_to_record(r) for r in rows]
            except Exception:
                pass
    return _mock_calls()


def get_caller_history(phone: str) -> list[CallRecord]:
    """All prior calls from a phone number — the returning-caller view."""
    if not (phone and is_configured() and st.session_state.get("authed")):
        return []
    client = get_client()
    if client is None:
        return []
    try:
        resp = (
            client.table("calls")
            .select("*")
            .eq("caller_phone", phone)
            .order("ended_at", desc=True)
            .execute()
        )
        return [_row_to_record(r) for r in (resp.data or [])]
    except Exception:
        return []


def call_kpis(calls: list[CallRecord]) -> dict[str, int]:
    total = len(calls)
    qualified = sum(1 for c in calls if c.disposition == "Qualified")
    declined = sum(1 for c in calls if c.disposition == "Declined")
    after_hours = sum(1 for c in calls if c.channel == "After-hours")
    avg_score = round(sum(c.score for c in calls) / total) if total else 0
    return {
        "total": total,
        "qualified": qualified,
        "declined": declined,
        "after_hours": after_hours,
        "avg_score": avg_score,
    }
