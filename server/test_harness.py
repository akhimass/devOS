"""Local terminal test harness for the PI intake agent tools.

This is a text-only simulator that loads the same system prompt used by the
voice pipeline, registers the same four tool schemas, and lets a human step
through the intake flow from the terminal.
"""

from __future__ import annotations

import inspect
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.syntax import Syntax

SERVER_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SERVER_DIR / "tools"
PROMPT_PATH = SERVER_DIR / "prompts" / "master_prompt.md"
DEFAULT_SESSION_ID = "test-session"

sys.path.insert(0, str(SERVER_DIR))

from tools.case_router import route_case
from tools.post_call_queue import build_standard_queue
from tools.sol_lookup import check_sol
from tools.treatment_classifier import classify_treatment

console = Console()

DEFAULTS: dict[str, dict[str, Any]] = {
    "check_sol": {"plaintiff_age": 30, "defendant_type": "private"},
    "classify_treatment": {
        "injuries_described": "",
        "er_visit": False,
        "hospitalized": False,
        "hospitalization_days": 0,
        "surgery_required": False,
        "loss_of_consciousness": False,
        "persistent_headaches": False,
        "spine_or_nerve_mentioned": False,
        "physical_therapy": False,
        "still_in_treatment": False,
        "returned_to_work": True,
        "psychological_symptoms": False,
    },
    "route_case": {
        "case_type": "other",
        "severity_tier": "moderate",
        "state": "",
        "sol_viable": True,
        "has_prior_representation": False,
        "defendant_type": "private",
        "estimated_case_value": "medium",
    },
    "end_call": {"session_id": DEFAULT_SESSION_ID, "decision": "declined", "urgency": "low"},
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_sol",
            "description": (
                "Check the filing window (statute of limitations) for the caller's "
                "state. Call silently the moment both state and accident_date are known."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "Two-letter US state code, e.g. 'CA'.",
                    },
                    "accident_date": {
                        "type": "string",
                        "description": "ISO date YYYY-MM-DD.",
                    },
                    "plaintiff_age": {
                        "type": "integer",
                        "description": "Approximate caller age. Default 30 if unknown.",
                    },
                    "defendant_type": {
                        "type": "string",
                        "enum": ["private", "government"],
                        "description": "'government' if a city/municipality/govt vehicle is involved.",
                    },
                },
                "required": ["state", "accident_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "classify_treatment",
            "description": (
                "Classify injury/treatment severity and red flags. Call after Stage 3 "
                "once er_visit, hospitalized, and still_in_treatment are known."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "injuries_described": {"type": "string"},
                    "er_visit": {"type": "boolean"},
                    "hospitalized": {"type": "boolean"},
                    "hospitalization_days": {"type": "integer"},
                    "surgery_required": {"type": "boolean"},
                    "loss_of_consciousness": {"type": "boolean"},
                    "persistent_headaches": {"type": "boolean"},
                    "spine_or_nerve_mentioned": {"type": "boolean"},
                    "physical_therapy": {"type": "boolean"},
                    "still_in_treatment": {"type": "boolean"},
                    "returned_to_work": {"type": "boolean"},
                    "psychological_symptoms": {"type": "boolean"},
                },
                "required": ["er_visit", "hospitalized", "still_in_treatment"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "route_case",
            "description": (
                "Final qualification gate. Call after check_sol, classify_treatment, "
                "case type, and prior-representation status are all known."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "case_type": {
                        "type": "string",
                        "enum": [
                            "mva",
                            "slip_fall",
                            "dog_bite",
                            "trucking",
                            "medmal",
                            "product_liability",
                            "workers_comp",
                            "wrongful_death",
                            "other",
                        ],
                    },
                    "severity_tier": {
                        "type": "string",
                        "enum": ["minor", "moderate", "severe", "catastrophic"],
                    },
                    "state": {"type": "string"},
                    "sol_viable": {"type": "boolean"},
                    "has_prior_representation": {"type": "boolean"},
                    "defendant_type": {
                        "type": "string",
                        "enum": ["private", "government"],
                    },
                    "estimated_case_value": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
                "required": ["case_type", "severity_tier", "sol_viable"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "end_call",
            "description": (
                "Signal that intake is complete. Call immediately after delivering "
                "the closing script."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "decision": {"type": "string", "enum": ["qualified", "declined"]},
                    "urgency": {"type": "string", "enum": ["immediate", "standard", "low"]},
                },
                "required": [],
            },
        },
    },
]


def _load_system_prompt() -> str:
    """Load the full master prompt and append today's date line.

    Returns:
        The system prompt string used for the chat completion session.

    Raises:
        SystemExit: If the prompt file is missing.
    """

    if not PROMPT_PATH.exists():
        console.print(f"[red]Error:[/red] master_prompt.md not found at {PROMPT_PATH}")
        raise SystemExit(1)

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    prompt += (
        f"\n\nToday is {date.today().strftime('%A, %B %d, %Y')}. "
        "Use this to resolve relative dates the caller mentions."
    )
    return prompt


def _tool_schema_prompt() -> None:
    """Print the run header and environment mode."""

    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    prompt_lines = len(SYSTEM_PROMPT.splitlines())
    sol_mode = (
        "Bedrock RAG active"
        if os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
        else "Fallback table mode (no Bedrock KB configured)"
    )

    console.print("PI Intake Test Harness", style="bold")
    console.print(
        f"Model: {model}  |  Prompt: {prompt_lines} lines  |  Tools: 4 registered"
    )
    console.print(f"SoL mode: {sol_mode}")
    console.print()
    console.print("Type your responses as the caller. Type 'quit' to exit.")
    console.print("──────────────────────────────────────────────────────")


SYSTEM_PROMPT = _load_system_prompt()


def _format_json(data: Any) -> str:
    """Pretty-print a Python object as JSON for terminal output."""

    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _compact_tool_result(name: str, result: dict[str, Any]) -> dict[str, Any]:
    """Keep only the result fields that matter for console output."""

    if "error" in result:
        return {"error": result["error"]}

    if name == "check_sol":
        keys = ["viable", "days_remaining", "sol_deadline", "tolling_applied", "rag_source"]
    elif name == "classify_treatment":
        keys = ["severity_tier", "severity_score", "red_flags", "delayed_onset_risk"]
    elif name == "route_case":
        keys = ["decision", "attorney_tier", "urgency", "decline_reason"]
    elif name == "end_call":
        keys = ["ok", "decision"]
    else:
        keys = list(result.keys())[:5]

    compact: dict[str, Any] = {}
    for key in keys:
        if key in result:
            compact[key] = result[key]
    return compact


def _update_intake_state(
    intake_state: dict[str, Any],
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """Merge new tool-derived information into the session intake state."""

    if tool_name == "check_sol":
        intake_state["state"] = arguments.get("state") or intake_state.get("state")
        intake_state["accident_date"] = arguments.get("accident_date") or intake_state.get(
            "accident_date"
        )
        intake_state["sol_viable"] = result.get("viable", intake_state.get("sol_viable"))
        intake_state["sol_deadline"] = result.get("sol_deadline", intake_state.get("sol_deadline"))
        intake_state["sol_days_remaining"] = result.get(
            "days_remaining", intake_state.get("sol_days_remaining")
        )
    elif tool_name == "classify_treatment":
        intake_state["severity_tier"] = result.get(
            "severity_tier", intake_state.get("severity_tier")
        )
        red_flags = result.get("red_flags")
        if isinstance(red_flags, list):
            intake_state["red_flags"] = red_flags
    elif tool_name == "route_case":
        intake_state["decision"] = result.get("decision", intake_state.get("decision"))
        intake_state["urgency"] = result.get("urgency", intake_state.get("urgency"))
        intake_state["case_type"] = arguments.get("case_type") or intake_state.get("case_type")
        intake_state["attorney_tier"] = result.get("attorney_tier", intake_state.get("attorney_tier"))
        intake_state["has_prior_representation"] = arguments.get(
            "has_prior_representation", intake_state.get("has_prior_representation")
        )
        intake_state["defendant_type"] = arguments.get("defendant_type") or intake_state.get(
            "defendant_type"
        )
    elif tool_name == "end_call":
        intake_state["decision"] = arguments.get("decision", intake_state.get("decision"))
        intake_state["urgency"] = arguments.get("urgency", intake_state.get("urgency"))


def _execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a real tool function with safe defaults for missing optional arguments."""

    defaults = DEFAULTS.get(name, {})
    merged = {**defaults, **arguments}

    if name == "check_sol":
        fn = check_sol
    elif name == "classify_treatment":
        fn = classify_treatment
    elif name == "route_case":
        fn = route_case
    elif name == "end_call":
        return {"ok": True, **merged}
    else:
        return {"error": f"Unknown tool: {name}"}

    try:
        signature = inspect.signature(fn)
        filtered = {
            key: value
            for key, value in merged.items()
            if key in signature.parameters
        }
        return fn(**filtered)
    except Exception as exc:
        return {"error": str(exc)}


def _print_tool_call(name: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
    """Render a tool call block with compact result fields."""

    console.print(f"[yellow]── TOOL CALL: {name} ──[/yellow]")
    console.print("[dim yellow]  args:[/dim yellow]")
    console.print(Syntax(_format_json(arguments), "json", theme="monokai", line_numbers=False))
    console.print("[green]  result:[/green]")
    console.print(Syntax(_format_json(_compact_tool_result(name, result)), "json", theme="monokai", line_numbers=False))


def _openai_client() -> OpenAI:
    """Construct the OpenAI client from environment variables."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] OPENAI_API_KEY is missing. Set it in server/.env.")
        raise SystemExit(1)
    return OpenAI(api_key=api_key)


def _call_model(client: OpenAI, messages: list[dict[str, Any]]) -> Any:
    """Send the current message history to the OpenAI chat completions API."""

    return client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.3,
        max_tokens=300,
    )


def _print_session_summary(tool_log: list[dict[str, Any]], intake_state: dict[str, Any]) -> None:
    """Print the final session summary and the derived post-call queue."""

    queue = build_standard_queue(
        caller_name=intake_state.get("caller_name") or "Unknown Caller",
        caller_phone=intake_state.get("caller_phone") or "000-000-0000",
        caller_email=intake_state.get("caller_email"),
        decision=intake_state.get("decision") or "declined",
        attorney_tier=intake_state.get("attorney_tier"),
        case_type=intake_state.get("case_type") or "other",
        severity_tier=intake_state.get("severity_tier") or "moderate",
        urgency=intake_state.get("urgency") or "low",
        appointment_slot=intake_state.get("appointment_slot"),
        sol_deadline=intake_state.get("sol_deadline"),
        red_flags=intake_state.get("red_flags") or [],
        emotional_state=intake_state.get("emotional_state") or "calm",
    )
    queue_data = queue.flush_to_dict()

    decision = (intake_state.get("decision") or "unknown").upper()
    attorney_tier = intake_state.get("attorney_tier") or "None"
    urgency = intake_state.get("urgency") or "low"
    sol_viable = intake_state.get("sol_viable")
    sol_days = intake_state.get("sol_days_remaining")
    severity = intake_state.get("severity_tier") or "unknown"
    red_flags = ", ".join(intake_state.get("red_flags") or []) or "None"

    console.print()
    console.print("═" * 36, style="bold blue")
    console.print("  SESSION COMPLETE", style="bold blue")
    console.print("═" * 36, style="bold blue")
    console.print(f"  Decision:       {decision}")
    console.print(f"  Attorney tier:  {attorney_tier}")
    console.print(f"  Urgency:        {urgency}")
    if sol_viable is None:
        console.print("  SoL viable:     unknown")
    else:
        if sol_days is not None:
            console.print(f"  SoL viable:     {sol_viable} ({sol_days} days remaining)")
        else:
            console.print(f"  SoL viable:     {sol_viable}")
    console.print(f"  Severity:       {severity}")
    console.print(f"  Red flags:      {red_flags}")
    console.print()
    console.print("  Tool calls made:", style="bold blue")
    if not tool_log:
        console.print("  (none)")
    else:
        for idx, item in enumerate(tool_log, 1):
            result = item["result"]
            compact = _compact_tool_result(item["name"], result)
            console.print(f"  [{idx}] {item['name']}")
            console.print(f"      args:   {_format_json(item['arguments'])}")
            console.print(f"      result: {_format_json(compact)}")
    console.print()
    console.print("  POST-CALL QUEUE (would execute):", style="bold blue")
    for idx, task in enumerate(queue_data["tasks"], 1):
        console.print(f"  [{idx}] {task['task_type']:<32} [{str(task['priority']).upper()}]")
    console.print("═" * 36, style="bold blue")


def _initial_messages(system_prompt: str) -> list[dict[str, Any]]:
    """Create the initial chat history with the startup user injection."""

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "A customer just called. Greet them, 'Hello, thanks for calling Hartley & Associates. "
                "I'm Aria, the intake specialist, and this call is free and confidential. What happened?'"
            ),
        },
    ]


def main() -> None:
    """Run the terminal intake simulator."""

    load_dotenv(SERVER_DIR / ".env", override=True)
    system_prompt = SYSTEM_PROMPT
    _tool_schema_prompt()

    client = _openai_client()
    messages = _initial_messages(system_prompt)
    intake_state: dict[str, Any] = {
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
    tool_log: list[dict[str, Any]] = []

    try:
        while True:
            response = _call_model(client, messages)
            choice = response.choices[0]
            message = choice.message
            tool_calls = message.tool_calls or []

            if tool_calls:
                assistant_message = {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                messages.append(assistant_message)

                terminate_after_tools = False
                for tc in tool_calls:
                    name = tc.function.name
                    raw_args = tc.function.arguments or "{}"
                    try:
                        arguments = json.loads(raw_args)
                    except Exception as exc:
                        arguments = {}
                        result = {"error": f"Could not parse tool arguments: {exc}"}
                    else:
                        result = _execute_tool(name, arguments)

                    _print_tool_call(name, arguments, result)
                    _update_intake_state(intake_state, name, arguments, result)
                    tool_log.append({"name": name, "arguments": arguments, "result": result})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, ensure_ascii=False, default=str),
                        }
                    )
                    if name == "end_call":
                        terminate_after_tools = True

                if terminate_after_tools:
                    _print_session_summary(tool_log, intake_state)
                    break

                continue

            content = (message.content or "").strip()
            if content:
                console.print(f"[bold white]Aria:[/bold white] {content}")
            messages.append({"role": "assistant", "content": message.content or ""})

            console.print("[dim cyan]You:[/dim cyan] ", end="")
            user_text = input()
            if user_text.strip().lower() in {"quit", "exit"}:
                break

            messages.append({"role": "user", "content": user_text})

    except KeyboardInterrupt:
        console.print("\nSession ended.")
        return

    console.print("Session ended.")


if __name__ == "__main__":
    main()
