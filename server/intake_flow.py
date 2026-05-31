"""Pipecat Flows intake graph (opt-in via BOT_MODE=flows).

Formalizes the master_prompt stages into a node graph so the knowledge tools fire
as DETERMINISTIC node transitions instead of relying on the LLM to remember to call
them mid-conversation (the under-firing we saw with the monolithic prompt). Reuses
the pure tool functions in tools/ and the shared intake_state, so finalize_session,
the live tool-event stream, and the dashboard all work unchanged.

Graph:  accident ──check_sol──▶ medical ──classify_treatment──▶ fault_rep
        ──route_case──▶ close ──end_call──▶ (hang up)
A non-viable statute-of-limitations result short-circuits straight to a decline close.
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from pipecat.frames.frames import EndTaskFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat_flows import FlowManager, FlowsFunctionSchema, NodeConfig

from tools.case_router import route_case
from tools.intake_assembly import append_tool_event, update_intake_state
from tools.sol_lookup import check_sol
from tools.supabase_logger import record_live_event_async
from tools.treatment_classifier import classify_treatment

PERSONA = (
    "You are Aria, the intake specialist at Hartley & Associates, a personal-injury "
    "law firm. Speak like a warm, steady human on the phone — 1 to 3 short spoken "
    "sentences per turn, no markdown or lists, mirror the caller's words. Never give "
    "legal advice or guarantee outcomes. Ask one thing at a time. Say numbers and "
    "dates naturally."
)

# Case types route_case accepts; we let the model classify in the fault/rep node.
_CASE_TYPES = [
    "mva", "slip_fall", "dog_bite", "trucking", "medmal",
    "product_liability", "workers_comp", "wrongful_death", "other",
]


def build_intake_flow(*, llm, context_aggregator, worker, intake_state: dict[str, Any]) -> FlowManager:
    """Construct the FlowManager + node graph. Call `await fm.initialize(accident_node())`."""

    def _record(tool_name: str, args: dict, result: dict) -> None:
        """Mirror a tool call into intake_state + the live/JSONL event streams, so the
        dashboard and finalize_session see flow-mode calls exactly like prompt-mode."""
        try:
            update_intake_state(intake_state, tool_name, args or {}, result or {})
            event = append_tool_event(
                tool_name=tool_name,
                phase="end",
                session_id=intake_state.get("session_id"),
                arguments=args,
                result=result,
            )
            record_live_event_async(event)
        except Exception as e:  # never let bookkeeping break the call
            logger.warning("[FLOW] event bookkeeping failed for {}: {!r}", tool_name, e)

    # ---- tool handlers: run the pure fn, record it, return (result, next_node) -----

    async def on_check_sol(args: dict, _fm: FlowManager):
        result = check_sol(
            state=args.get("state", ""),
            accident_date=args.get("accident_date", ""),
            plaintiff_age=int(args.get("plaintiff_age") or 30),
            defendant_type=args.get("defendant_type") or "private",
        )
        _record("check_sol", args, result)
        if result.get("viable") is False:
            return result, close_node(decision="declined", reason="sol_expired")
        return result, medical_node()

    async def on_classify_treatment(args: dict, _fm: FlowManager):
        defaults = {
            "injuries_described": "", "er_visit": False, "hospitalized": False,
            "hospitalization_days": 0, "surgery_required": False,
            "loss_of_consciousness": False, "persistent_headaches": False,
            "spine_or_nerve_mentioned": False, "physical_therapy": False,
            "still_in_treatment": False, "returned_to_work": True,
            "psychological_symptoms": False,
        }
        merged = {**defaults, **(args or {})}
        result = classify_treatment(**{k: merged[k] for k in defaults})
        _record("classify_treatment", args, result)
        return result, fault_rep_node()

    async def on_route_case(args: dict, _fm: FlowManager):
        severity = intake_state.get("severity_tier") or "moderate"
        est = {"catastrophic": "high", "severe": "high", "moderate": "medium"}.get(severity, "low")
        result = route_case(
            case_type=args.get("case_type") or "other",
            severity_tier=severity,
            state=intake_state.get("state") or "",
            sol_viable=bool(intake_state.get("sol_viable", True)),
            has_prior_representation=bool(args.get("has_prior_representation", False)),
            defendant_type=args.get("defendant_type") or intake_state.get("defendant_type") or "private",
            estimated_case_value=args.get("estimated_case_value") or est,
        )
        _record("route_case", args, result)
        return result, close_node(decision=result.get("decision", "declined"),
                                  reason=result.get("decline_reason"))

    async def on_end_call(args: dict, _fm: FlowManager):
        update_intake_state(intake_state, "end_call", args or {}, {})
        logger.info("[FLOW] end_call — decision={} urgency={}", args.get("decision"), args.get("urgency"))
        await llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
        return {"status": "ok"}, None

    # ---- function schemas ----------------------------------------------------------

    check_sol_fn = FlowsFunctionSchema(
        name="check_sol",
        description="Record the accident and check the filing window. Call once you know the state and roughly when it happened.",
        properties={
            "state": {"type": "string", "description": "Two-letter US state code."},
            "accident_date": {"type": "string", "description": "ISO date YYYY-MM-DD (best estimate)."},
            "plaintiff_age": {"type": "integer"},
            "defendant_type": {"type": "string", "enum": ["private", "government"]},
        },
        required=["state", "accident_date"],
        handler=on_check_sol,
    )
    classify_fn = FlowsFunctionSchema(
        name="classify_treatment",
        description="Classify the injuries/treatment. Call once you know whether they went to the ER, were hospitalized, and are still in treatment.",
        properties={
            "injuries_described": {"type": "string"},
            "er_visit": {"type": "boolean"}, "hospitalized": {"type": "boolean"},
            "hospitalization_days": {"type": "integer"}, "surgery_required": {"type": "boolean"},
            "loss_of_consciousness": {"type": "boolean"}, "persistent_headaches": {"type": "boolean"},
            "spine_or_nerve_mentioned": {"type": "boolean"}, "physical_therapy": {"type": "boolean"},
            "still_in_treatment": {"type": "boolean"}, "returned_to_work": {"type": "boolean"},
            "psychological_symptoms": {"type": "boolean"},
        },
        required=["er_visit", "hospitalized", "still_in_treatment"],
        handler=on_classify_treatment,
    )
    route_fn = FlowsFunctionSchema(
        name="route_case",
        description="Make the qualification decision. Call once you know the case type, fault, and whether they already have a lawyer.",
        properties={
            "case_type": {"type": "string", "enum": _CASE_TYPES},
            "has_prior_representation": {"type": "boolean"},
            "defendant_type": {"type": "string", "enum": ["private", "government"]},
            "estimated_case_value": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        required=["case_type", "has_prior_representation"],
        handler=on_route_case,
    )
    end_fn = FlowsFunctionSchema(
        name="end_call",
        description="End the call after the closing line. Pass the final summary fields.",
        properties={
            "decision": {"type": "string", "enum": ["qualified", "declined"]},
            "urgency": {"type": "string", "enum": ["immediate", "standard", "low"]},
            "emotional_state": {"type": "string", "enum": ["calm", "distressed", "urgent", "guarded"]},
            "caller_name": {"type": "string"},
            "caller_email": {"type": "string"},
            "appointment_slot": {"type": "string"},
        },
        required=[],
        handler=on_end_call,
    )

    # ---- nodes ----------------------------------------------------------------------

    def accident_node() -> NodeConfig:
        return {
            "name": "accident",
            "role_messages": [{"role": "system", "content": PERSONA}],
            "task_messages": [{
                "role": "system",
                "content": (
                    "Open the call: \"Hello, thanks for calling Hartley & Associates. I'm Aria, "
                    "the intake specialist, and this call is free and confidential. What happened?\" "
                    "Then find out what happened, which US state it happened in, and roughly when. "
                    "The state and date are essential. As soon as you have both, call check_sol."
                ),
            }],
            "functions": [check_sol_fn],
            "respond_immediately": True,
        }

    def medical_node() -> NodeConfig:
        return {
            "name": "medical",
            "task_messages": [{
                "role": "system",
                "content": (
                    "Acknowledge what they shared. Now ask about their injuries, then about medical "
                    "care — did they go to the ER, were they hospitalized, are they still being treated. "
                    "One question at a time. Once you know ER, hospitalization, and ongoing treatment, "
                    "call classify_treatment."
                ),
            }],
            "functions": [classify_fn],
        }

    def fault_rep_node() -> NodeConfig:
        return {
            "name": "fault_rep",
            "task_messages": [{
                "role": "system",
                "content": (
                    "Ask whether they've already spoken with or hired another lawyer for this, and "
                    "briefly who they think was at fault. Infer the case type from the conversation. "
                    "Then call route_case."
                ),
            }],
            "functions": [route_fn],
        }

    def close_node(*, decision: str, reason: str | None = None) -> NodeConfig:
        if decision == "qualified":
            content = (
                "Tell them this is something the team can help with and that one of our attorneys "
                "will reach out (today if urgent, otherwise within a business day or two). Confirm "
                "the best phone number. Then deliver one clean closing line and call end_call with "
                "decision='qualified'."
            )
        elif reason == "sol_expired":
            content = (
                "Gently explain that, based on what they've shared, the window for taking legal action "
                "in their state appears to have passed, and you're sorry. Encourage them to still speak "
                "with an attorney directly. Then call end_call with decision='declined'."
            )
        else:
            content = (
                "Kindly explain this isn't the right fit and encourage a second opinion from another "
                "attorney. Keep it warm and brief, then call end_call with decision='declined'."
            )
        return {
            "name": f"close_{decision}",
            "task_messages": [{"role": "system", "content": content}],
            "functions": [end_fn],
        }

    fm = FlowManager(llm=llm, context_aggregator=context_aggregator, worker=worker)
    # expose the entry node so the caller can `await fm.initialize(fm.entry_node)`
    fm.entry_node = accident_node()  # type: ignore[attr-defined]
    return fm
