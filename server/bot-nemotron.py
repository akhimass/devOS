#
# Copyright (c) 2024–2026, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Field & Flower — flower shop voice ordering bot (hackathon starter).

A customer calls in and the bot helps them pick a bouquet and arrange delivery.
All backend calls (catalog, customer lookup, order placement) are mocked so the
starter runs with no external dependencies beyond the AI services.

Pipeline: Nemotron Speech Streaming STT → Nemotron-3-Super-120B LLM → Gradium TTS, with direct
function tools registered on the LLM context.

Run the bot using::

    uv run bot-nemotron.py
"""

import asyncio
import os
import random
import time
from datetime import date
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import EndTaskFrame, FunctionCallResultProperties, LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.runner.types import (
    RunnerArguments,
    SmallWebRTCRunnerArguments,
    WebSocketRunnerArguments,
)
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.gradium.stt import GradiumSTTService
from pipecat.services.gradium.tts import GradiumTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
from pipecat.turns.user_stop import SpeechTimeoutUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import (
    FilterIncompleteUserTurnStrategies,
    UserTurnStrategies,
)
from pipecat.workers.runner import WorkerRunner

from mock_backend import BOUQUETS, KNOWN_CUSTOMERS
from nemotron_llm import VLLMOpenAILLMService
from nvidia_stt import NVidiaWebSocketSTTService
from tools.case_router import route_case
from tools.intake_assembly import (
    build_transcript,
    finalize_session,
    new_intake_state,
    update_intake_state,
)
from tools.sol_lookup import check_sol
from tools.treatment_classifier import classify_treatment

load_dotenv(override=True)

# Directory of this file, so prompt loading works regardless of CWD (local vs the
# Pipecat Cloud container, where this file is copied in as /app/bot.py).
_HERE = Path(__file__).resolve().parent


def load_system_prompt() -> str:
    """Load the intake system prompt from prompts/master_prompt.md.

    The deployed agent's persona lives in this file (Aria, Hartley & Associates
    legal intake). If it is missing — e.g. the prompts/ dir was not copied into
    the image — we log loudly and fall back to a minimal instruction so the bot
    still speaks instead of failing silently.
    """
    prompt_path = _HERE / "prompts" / "master_prompt.md"
    try:
        text = prompt_path.read_text(encoding="utf-8")
        logger.info(
            "[PROMPT] loaded master_prompt.md from {} ({} chars, {} lines)",
            prompt_path,
            len(text),
            text.count("\n") + 1,
        )
        return text
    except FileNotFoundError:
        logger.error(
            "[PROMPT] master_prompt.md NOT FOUND at {} — falling back to minimal "
            "instruction. (Is prompts/ copied into the Docker image?)",
            prompt_path,
        )
        return (
            "You are Aria, a warm, professional legal intake specialist at Hartley & "
            "Associates. Greet the caller, then ask what happened and gather details "
            "about the accident, injuries, treatment, fault, and prior representation. "
            "Keep replies to 1–3 short spoken sentences. No markdown or lists."
        )


async def check_nemotron_health() -> None:
    """Ping the configured Nemotron LLM endpoint once at startup and log the result.

    This is the single most useful diagnostic for the "bot never speaks" failure:
    the greeting is LLM-generated, so if this endpoint is unreachable from where
    the bot is deployed (Pipecat Cloud), the bot produces no audio at all. The
    .env / cloud secret set must point at a PUBLICLY reachable URL — a private
    192.168.x.x address resolves from a laptop but never from the cloud.
    """
    base_url = os.getenv("NEMOTRON_LLM_URL", "http://192.168.7.228:8000/v1").rstrip("/")
    models_url = f"{base_url}/models"
    api_key = os.getenv("NEMOTRON_LLM_API_KEY", "EMPTY")
    headers = {"Authorization": f"Bearer {api_key}"}
    logger.info("[HEALTH] pinging Nemotron LLM at {} …", models_url)
    t0 = time.perf_counter()
    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(models_url, headers=headers) as resp:
                elapsed = (time.perf_counter() - t0) * 1000
                body = await resp.text()
                if resp.status == 200:
                    logger.info(
                        "[HEALTH] ✓ Nemotron reachable ({:.0f}ms, HTTP {}): {}",
                        elapsed,
                        resp.status,
                        body[:300],
                    )
                else:
                    logger.error(
                        "[HEALTH] ✖ Nemotron returned HTTP {} after {:.0f}ms: {}",
                        resp.status,
                        elapsed,
                        body[:300],
                    )
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        logger.error(
            "[HEALTH] ✖ Nemotron UNREACHABLE after {:.0f}ms from this deployment: {!r}. "
            "If this is Pipecat Cloud, check NEMOTRON_LLM_URL in the secret set is a "
            "public address (not 192.168.x.x).",
            elapsed,
            e,
        )


async def get_call_info(call_sid: str) -> dict:
    """Fetch call information from Twilio REST API using aiohttp.

    Args:
        call_sid: The Twilio call SID

    Returns:
        Dictionary containing call information including from_number, to_number, status, etc.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        logger.warning("Missing Twilio credentials, cannot fetch call info")
        return {}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"

    try:
        # Use HTTP Basic Auth with aiohttp
        auth = aiohttp.BasicAuth(account_sid, auth_token)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Twilio API error ({response.status}): {error_text}")
                    return {}

                data = await response.json()

                call_info = {
                    "from_number": data.get("from"),
                    "to_number": data.get("to"),
                }

                return call_info

    except Exception as e:
        logger.error(f"Error fetching call info from Twilio: {e}")
        return {}


async def run_bot(
    transport: BaseTransport,
    from_number: str | None = None,
    session_id: str | None = None,
    audio_in_sample_rate: int = 16000,
    audio_out_sample_rate: int = 24000,
):
    """Main bot logic.

    Args:
        transport: The transport to use.
        from_number: Caller's phone number (Twilio path only) for known-customer lookup.
        session_id: Unique session identifier (Twilio call SID, or generated).
        audio_in_sample_rate: Input audio sample rate in Hz. Defaults to 16000 (WebRTC).
        audio_out_sample_rate: Output audio sample rate in Hz. Defaults to 24000 (WebRTC).
    """
    logger.info("Starting bot")

    # Startup health check: confirm the LLM endpoint is reachable from wherever
    # this bot is actually running (laptop vs Pipecat Cloud). The greeting is
    # LLM-generated, so an unreachable endpoint here == total silence on the call.
    await check_nemotron_health()

    # Per-call structured intake state. The LLM surfaces facts through the four
    # tool calls; the handlers below merge each call's args/results into here, and
    # on call end we build the follow-up queue and log intake + transcript + queue
    # to S3 (see tools/intake_assembly.py). Closed over by the tools and handlers.
    intake_state = new_intake_state(caller_phone=from_number, session_id=session_id)
    logger.info("[POSTCALL] session_id={} caller_phone={}", intake_state["session_id"], from_number)
    _finalized = {"done": False}

    # Per-call order state (legacy flower tools, unused by the legal-intake flow).
    order: dict = {"items": [], "delivery": None}

    async def _finalize_postcall(reason: str) -> None:
        """Build the follow-up queue and log intake/transcript/queue to S3, once.

        Triggered by end_call (normal close) or on_client_disconnected (caller
        hung up / dropped). Guarded so it runs exactly once per call. The actual
        work is blocking (boto3), so it runs in a worker thread.
        """
        if _finalized["done"]:
            return
        _finalized["done"] = True
        logger.info("[POSTCALL] finalizing (trigger={})", reason)
        try:
            messages = context.get_messages()
        except Exception:
            messages = None
        transcript = build_transcript(messages)
        try:
            await asyncio.to_thread(finalize_session, intake_state, transcript)
        except Exception as e:
            logger.error("[POSTCALL] finalize failed: {!r}", e)

    # --- Tools the LLM can call ---------------------------------------------

    async def list_bouquets(
        params: FunctionCallParams,
        occasion: str | None = None,
        specials_only: bool = False,
    ) -> None:
        """List bouquets available today. Optionally filter by occasion or by
        what's currently on special.

        Use this when the caller asks what's available, mentions a specific
        occasion ("it's for my mom's birthday", "for Valentine's Day", "for a
        funeral"), or asks about specials/deals. Sold-out bouquets are
        automatically excluded from results.

        Args:
            occasion: Lowercase occasion to filter by. Common values:
                "birthday", "anniversary", "valentine's day", "mother's day",
                "sympathy", "wedding", "graduation", "thank you", "get well",
                "new baby", "housewarming", "christmas", "easter", "just
                because". Pass the canonical short form ("birthday", not "mom's
                birthday"). Omit to return the full catalog.
            specials_only: If True, only return bouquets currently on special.
        """
        results = []
        for name, info in BOUQUETS.items():
            if not info["in_stock"]:
                continue
            if specials_only and not info.get("on_special", False):
                continue
            if occasion is not None:
                occ = occasion.strip().lower()
                tags = [o.lower() for o in info.get("occasions", [])]
                if not any(occ in tag or tag in occ for tag in tags):
                    continue
            results.append({"name": name, **info})

        if not results and (occasion is not None or specials_only):
            await params.result_callback(
                {
                    "bouquets": [],
                    "note": (
                        "No bouquets match those filters. Tell the caller you don't have "
                        "anything specifically for that, and offer to browse the full "
                        "catalog or try a different angle."
                    ),
                }
            )
            return

        await params.result_callback({"bouquets": results})

    async def check_availability(params: FunctionCallParams, bouquet_name: str) -> None:
        """Check whether a specific bouquet is in stock today.

        Args:
            bouquet_name: The name of the bouquet to check, lowercase.
        """
        item = BOUQUETS.get(bouquet_name.lower())
        if not item:
            await params.result_callback(
                {"available": False, "reason": f"We don't carry a bouquet called '{bouquet_name}'."}
            )
            return
        if not item["in_stock"]:
            await params.result_callback(
                {"available": False, "reason": f"{bouquet_name} is sold out today."}
            )
            return
        await params.result_callback({"available": True, "price": item["price"]})

    async def add_to_order(
        params: FunctionCallParams, bouquet_name: str, quantity: int = 1
    ) -> None:
        """Add a bouquet to the customer's order. Only call this after the
        customer has confirmed they want this bouquet.

        Args:
            bouquet_name: The name of the bouquet to add, lowercase.
            quantity: How many of this bouquet to add. Defaults to 1.
        """
        item = BOUQUETS.get(bouquet_name.lower())
        if not item:
            await params.result_callback(
                {"ok": False, "reason": f"We don't carry a bouquet called '{bouquet_name}'."}
            )
            return
        if not item["in_stock"]:
            await params.result_callback(
                {"ok": False, "reason": f"{bouquet_name} is sold out today."}
            )
            return
        order["items"].append(
            {"bouquet": bouquet_name.lower(), "quantity": quantity, "price": item["price"]}
        )
        await params.result_callback({"ok": True, "items": order["items"]})

    async def get_order_summary(params: FunctionCallParams) -> None:
        """Read back the current order: items, quantities, and running total."""
        total = sum(line["price"] * line["quantity"] for line in order["items"])
        await params.result_callback(
            {"items": order["items"], "total": round(total, 2), "delivery": order["delivery"]}
        )

    async def set_delivery_details(
        params: FunctionCallParams,
        recipient_name: str,
        address: str,
        delivery_date: str,
    ) -> None:
        """Capture delivery details for the order.

        Args:
            recipient_name: Name of the person receiving the flowers.
            address: Delivery street address.
            delivery_date: Requested delivery date, in the customer's own words
                (e.g. "Friday", "May 20th"). No parsing required.
        """
        order["delivery"] = {
            "recipient_name": recipient_name,
            "address": address,
            "delivery_date": delivery_date,
        }
        await params.result_callback({"ok": True, "delivery": order["delivery"]})

    async def place_order(params: FunctionCallParams) -> None:
        """Finalize the order. Only call this after the customer has confirmed
        the items AND delivery details."""
        if not order["items"]:
            await params.result_callback({"ok": False, "reason": "No items in the order yet."})
            return
        if not order["delivery"]:
            await params.result_callback({"ok": False, "reason": "Missing delivery details."})
            return
        total = sum(line["price"] * line["quantity"] for line in order["items"])
        confirmation = f"FLW-{random.randint(100000, 999999)}"
        logger.info(f"Order placed: {confirmation} total=${total:.2f} order={order}")
        await params.result_callback(
            {
                "ok": True,
                "confirmation_number": confirmation,
                "total": round(total, 2),
                "eta": "within 2 business days",
            }
        )

    async def end_call(params: FunctionCallParams) -> None:
        """Signal that intake is complete. Call this immediately after delivering
        the closing script. The pipeline flushes queued speech and hangs up."""
        args = params.arguments or {}
        logger.info(
            "end_call invoked (decision={}, urgency={}, session_id={})",
            args.get("decision"),
            args.get("urgency"),
            args.get("session_id"),
        )
        # Capture the LLM's closing summary into intake state, then run the
        # post-call queue + S3 logging before we tear the pipeline down.
        update_intake_state(intake_state, "end_call", args, {})
        await _finalize_postcall("end_call")
        await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
        # run_llm=False prevents the LLM from generating a follow-up response
        # after this function returns — the goodbye should already be in flight.
        await params.result_callback(
            {"ok": True}, properties=FunctionCallResultProperties(run_llm=False)
        )

    # --- Legal-intake knowledge sub-agent tools -----------------------------
    # These wrap the pure functions in tools/. Each handler merges the model's
    # arguments over safe defaults (per master_prompt.md) and filters to the
    # function's real parameters, so an omitted/extra arg from the LLM never
    # raises and kills the turn — it degrades to a sensible default instead.

    def _safe_call(fn, defaults: dict, args: dict) -> dict:
        merged = {**defaults, **(args or {})}
        allowed = fn.__code__.co_varnames[: fn.__code__.co_argcount]
        kwargs = {k: v for k, v in merged.items() if k in allowed}
        try:
            return fn(**kwargs)
        except Exception as e:  # never let a malformed tool call break the call
            logger.error("[TOOL] {} failed args={}: {!r}", fn.__name__, kwargs, e)
            return {"error": str(e), "note": "Tool call failed; continue intake gracefully."}

    async def check_sol_tool(params: FunctionCallParams) -> None:
        """Check the filing window (statute of limitations) for the caller's state."""
        logger.info("[TOOL] check_sol args={}", params.arguments)
        result = _safe_call(
            check_sol,
            {"plaintiff_age": 30, "defendant_type": "private"},
            params.arguments,
        )
        logger.info("[TOOL] check_sol -> {}", result)
        update_intake_state(intake_state, "check_sol", params.arguments or {}, result)
        await params.result_callback(result)

    async def classify_treatment_tool(params: FunctionCallParams) -> None:
        """Classify injury/treatment severity and surface red flags."""
        logger.info("[TOOL] classify_treatment args={}", params.arguments)
        result = _safe_call(
            classify_treatment,
            {
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
            params.arguments,
        )
        logger.info("[TOOL] classify_treatment -> {}", result)
        update_intake_state(intake_state, "classify_treatment", params.arguments or {}, result)
        await params.result_callback(result)

    async def route_case_tool(params: FunctionCallParams) -> None:
        """Final qualification gate: decide accept/decline and attorney tier."""
        logger.info("[TOOL] route_case args={}", params.arguments)
        result = _safe_call(
            route_case,
            {
                "case_type": "other",
                "severity_tier": "moderate",
                "state": "",
                "sol_viable": True,
                "has_prior_representation": False,
                "defendant_type": "private",
                "estimated_case_value": "medium",
            },
            params.arguments,
        )
        logger.info("[TOOL] route_case -> {}", result)
        update_intake_state(intake_state, "route_case", params.arguments or {}, result)
        await params.result_callback(result)

    # Tool schemas advertised to the LLM. Arg names/types mirror master_prompt.md
    # PHASE 2 exactly. `required` is kept minimal so the model is never forced to
    # invent a value; the handlers default the rest.
    check_sol_schema = FunctionSchema(
        name="check_sol",
        description=(
            "Check the filing window (statute of limitations) for the caller's state. "
            "Call silently the moment both state and accident_date are known."
        ),
        properties={
            "state": {"type": "string", "description": "Two-letter US state code, e.g. 'CA'."},
            "accident_date": {"type": "string", "description": "ISO date YYYY-MM-DD."},
            "plaintiff_age": {"type": "integer", "description": "Approx caller age; default 30."},
            "defendant_type": {
                "type": "string",
                "enum": ["private", "government"],
                "description": "'government' if a city/state/municipality/govt vehicle is involved.",
            },
        },
        required=["state", "accident_date"],
    )
    classify_treatment_schema = FunctionSchema(
        name="classify_treatment",
        description=(
            "Classify injury/treatment severity and red flags. Call silently after "
            "Stage 3 once er_visit, hospitalized, and still_in_treatment are known."
        ),
        properties={
            "injuries_described": {"type": "string", "description": "Concise injury summary."},
            "er_visit": {"type": "boolean"},
            "hospitalized": {"type": "boolean"},
            "hospitalization_days": {"type": "integer", "description": "0 if not hospitalized."},
            "surgery_required": {"type": "boolean"},
            "loss_of_consciousness": {"type": "boolean"},
            "persistent_headaches": {"type": "boolean"},
            "spine_or_nerve_mentioned": {"type": "boolean"},
            "physical_therapy": {"type": "boolean"},
            "still_in_treatment": {"type": "boolean"},
            "returned_to_work": {"type": "boolean"},
            "psychological_symptoms": {"type": "boolean"},
        },
        required=["er_visit", "hospitalized", "still_in_treatment"],
    )
    route_case_schema = FunctionSchema(
        name="route_case",
        description=(
            "Final qualification gate. Call after check_sol, classify_treatment, "
            "case type, and prior-representation status are all known."
        ),
        properties={
            "case_type": {
                "type": "string",
                "enum": [
                    "mva", "slip_fall", "dog_bite", "trucking", "medmal",
                    "product_liability", "workers_comp", "wrongful_death", "other",
                ],
            },
            "severity_tier": {
                "type": "string",
                "enum": ["minor", "moderate", "severe", "catastrophic"],
            },
            "state": {"type": "string", "description": "Two-letter state code."},
            "sol_viable": {"type": "boolean", "description": "viable result from check_sol."},
            "has_prior_representation": {"type": "boolean"},
            "defendant_type": {"type": "string", "enum": ["private", "government"]},
            "estimated_case_value": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        required=["case_type", "severity_tier", "sol_viable"],
    )
    end_call_schema = FunctionSchema(
        name="end_call",
        description=(
            "Signal that intake is complete. Call immediately after delivering the "
            "closing script, even if the caller has not hung up. Pass the final "
            "summary fields so the post-call follow-up queue is built correctly."
        ),
        properties={
            "session_id": {"type": "string", "description": "Session identifier."},
            "decision": {"type": "string", "enum": ["qualified", "declined"]},
            "urgency": {
                "type": "string",
                "enum": ["immediate", "standard", "low"],
                "description": "From route_case; 'low' if route_case was not called.",
            },
            "emotional_state": {
                "type": "string",
                "enum": ["calm", "distressed", "urgent", "guarded"],
                "description": "Caller's emotional state. 'distressed' queues a comfort follow-up.",
            },
            "caller_name": {"type": "string", "description": "Caller's name, if collected."},
            "caller_email": {"type": "string", "description": "Caller's email, if collected."},
            "appointment_slot": {
                "type": "string",
                "description": "Time preference the caller gave for a consultation, if any.",
            },
        },
        required=[],
    )

    tools = ToolsSchema(
        standard_tools=[
            check_sol_schema,
            classify_treatment_schema,
            route_case_schema,
            end_call_schema,
        ]
    )

    # --- Language configuration ----------------------------------------------
    # AGENT_LANGUAGE: BCP-47 code (e.g. "en-US", "es-US", "fr-FR", "de-DE",
    #   "it-IT", "hi-IN", "ja-JP") to run the whole pipeline in one language, OR
    #   "multi" to let the caller speak ANY supported language (STT auto-detects;
    #   the LLM mirrors it). Supported by all three NVIDIA models:
    #   Parakeet-multilingual STT, Nemotron LLM, Magpie multilingual TTS.
    agent_language = os.getenv("AGENT_LANGUAGE", "en-US")
    multilingual = agent_language.lower() == "multi"
    logger.info("[LANG] agent_language={} multilingual={}", agent_language, multilingual)

    # --- System instruction --------------------------------------------------
    # The persona + intake flow + tool/decision logic lives in
    # prompts/master_prompt.md (Aria, Hartley & Associates legal intake). We load
    # it here and inject it as the LLM's system instruction. A short dated footer
    # is appended so the model can resolve relative dates the caller mentions.
    system_instruction = (
        f"{load_system_prompt()}\n\n"
        f"Today is {date.today().strftime('%A, %B %d, %Y')}. Use this to resolve "
        'relative dates the caller mentions (e.g. "last Tuesday", "about three months ago").'
    )
    if multilingual:
        system_instruction += (
            "\n\n# Language\n"
            "The caller may speak ANY language. From their first words, detect the "
            "language they are using and conduct the ENTIRE conversation in that same "
            "language — every question, every script, and the closing. Mirror the "
            "caller's language naturally and never switch languages unless they do."
        )
    elif not agent_language.lower().startswith("en"):
        system_instruction += (
            f"\n\n# Language\nConduct the ENTIRE conversation in {agent_language} — "
            "every question, script, and the closing. The caller is speaking this "
            "language; do not reply in English."
        )
    logger.info("[PROMPT] system_instruction preview: {}", system_instruction[:400].replace("\n", " "))

    # Speech-to-Text service
    #
    # STT_PROVIDER selects the transcription backend:
    #   - "gradium" (default): Gradium streaming STT. Stable ~50ms latency.
    #   - "nvidia": NVIDIA Nemotron Speech Streaming over WebSocket (16-bit PCM,
    #     16 kHz, mono). This is the hackathon's shared ASR endpoint; it can spike
    #     to 5-25s under load, so we default away from it for reliable demos.
    # Flip back with STT_PROVIDER=nvidia once the shared endpoint calms down.
    # STT_PROVIDER selects the transcription backend:
    #   - "nvidia" (default): NVIDIA Parakeet via the Riva/NIM gRPC endpoint, same
    #     reliable NVIDIA cloud + nvapi key as Magpie. This is the all-NVIDIA path.
    #   - "nvidia_ws": the shared hackathon Parakeet WebSocket box (NVIDIA_ASR_URL).
    #     Free but it spikes 5-25s under load and can drop transcripts — that was
    #     the "greets but never replies to me" bug. Kept only as an escape hatch.
    #   - "gradium": Gradium streaming STT (stable ~50ms) — non-NVIDIA fallback.
    stt_provider = os.getenv("STT_PROVIDER", "nvidia").lower()
    if stt_provider == "gradium":
        logger.info("STT provider: Gradium")
        stt = GradiumSTTService(
            api_key=os.environ["GRADIUM_API_KEY"],
            settings=GradiumSTTService.Settings(
                language=Language.EN,
            ),
        )
    elif stt_provider in ("nvidia_ws", "parakeet_ws"):
        logger.info("STT provider: NVIDIA Parakeet (shared WebSocket box)")
        stt = NVidiaWebSocketSTTService(
            url=os.getenv("NVIDIA_ASR_URL", "ws://192.168.7.228:8081"),
            strip_interim_prefix=True,
            preroll_seconds=0.2,
        )
    else:
        from pipecat.services.nvidia.stt import NvidiaSTTService

        stt_server = os.getenv("NVIDIA_STT_SERVER", "grpc.nvcf.nvidia.com:443")
        stt_api_key = os.getenv("NVIDIA_API_KEY") or os.environ["NEMOTRON_LLM_API_KEY"]
        stt_use_ssl = os.getenv("NVIDIA_STT_USE_SSL", "true").lower() == "true"
        # The default nemotron-asr-streaming NIM is English-only. For "multi" or
        # any non-English language we use parakeet-1.1b-rnnt-multilingual, which
        # auto-detects with language_code="multi" or transcribes a specific code
        # (verified: en/es/fr). English stays on the dedicated nemotron NIM.
        english_only = (not multilingual) and agent_language.lower().startswith("en")
        if english_only:
            logger.info("STT provider: NVIDIA Parakeet NIM (en-US, server={})", stt_server)
            stt = NvidiaSTTService(
                api_key=stt_api_key,
                server=stt_server,
                use_ssl=stt_use_ssl,
                sample_rate=16000,  # Parakeet expects 16 kHz; pipecat upsamples Twilio's 8 kHz
                model_function_map={
                    "function_id": os.getenv(
                        "PARAKEET_FUNCTION_ID", "bb0837de-8c7b-481f-9ec8-ef5663e9c1fa"
                    ),
                    "model_name": os.getenv("PARAKEET_MODEL", "nemotron-asr-streaming"),
                },
            )
        else:
            # "multi" auto-detects any language; otherwise force the specific code.
            lang_code = "multi" if multilingual else agent_language

            class _MultilingualParakeetSTT(NvidiaSTTService):
                def _create_recognition_config(self):
                    cfg = super()._create_recognition_config()
                    cfg.config.language_code = lang_code
                    return cfg

            logger.info(
                "STT provider: NVIDIA Parakeet-multilingual NIM (language_code={})", lang_code
            )
            stt = _MultilingualParakeetSTT(
                api_key=stt_api_key,
                server=stt_server,
                use_ssl=stt_use_ssl,
                sample_rate=16000,
                model_function_map={
                    "function_id": os.getenv(
                        "PARAKEET_ML_FUNCTION_ID", "71203149-d3b7-4460-8231-1be2543a1fca"
                    ),
                    "model_name": os.getenv(
                        "PARAKEET_ML_MODEL", "parakeet-1.1b-rnnt-multilingual"
                    ),
                },
            )

    # LLM service — Nemotron-3-Super-120B served by vLLM (OpenAI-compatible chat
    # completions at /v1). vLLM exposes the Chat Completions API, not the Responses
    # API, so we use OpenAILLMService (not OpenAIResponsesLLMService). The live
    # endpoint serves the model as "nemotron-3-super" (per its /v1/models).
    #
    # Reasoning ("thinking") toggle — Nemotron is controlled per-request via
    # chat_template_kwargs.enable_thinking, forwarded through the OpenAI client's
    # extra_body (the request-body convention confirmed against this endpoint in
    # ../aiewf-eval traces). Default OFF for low-latency voice. To ENABLE, set
    # NEMOTRON_ENABLE_THINKING=true; to DISABLE, leave unset/false.
    #
    # CAUTION for voice: reasoning is only kept out of the spoken `content` if the
    # vLLM server runs a reasoning parser (e.g. --reasoning-parser nemotron_v3, which
    # routes it to a separate `reasoning_content` field). This live endpoint did NOT
    # surface reasoning_content in testing, so if thinking is enabled and the server
    # lacks a parser, chain-of-thought would appear inline in `content` and get
    # spoken. Keep thinking OFF for voice unless the parser is confirmed active.
    # VLLMOpenAILLMService is a thin OpenAILLMService subclass that reports TTFB to
    # the first NON-THINKING token (so the metric reflects time-to-first-spoken-word
    # when reasoning is enabled, not time-to-first-reasoning-token). No-op when
    # thinking is off. See server/nemotron_llm.py.
    enable_thinking = os.getenv("NEMOTRON_ENABLE_THINKING", "false").lower() == "true"
    # Response shaping (env-toggleable for A/B):
    #   LLM_MAX_TOKENS  — cap reply length so TTS playback stays short (default 200).
    #   LLM_TEMPERATURE — low for consistent legal-intake slot-filling (default 0.4).
    llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "200"))
    llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.4"))
    logger.info(
        "[LLM] config max_tokens={} temperature={} thinking={}",
        llm_max_tokens,
        llm_temperature,
        enable_thinking,
    )
    llm = VLLMOpenAILLMService(
        api_key=os.getenv("NEMOTRON_LLM_API_KEY", "EMPTY"),  # vLLM ignores unless --api-key set
        base_url=os.getenv("NEMOTRON_LLM_URL", "http://192.168.7.228:8000/v1"),
        settings=VLLMOpenAILLMService.Settings(
            model=os.getenv("NEMOTRON_LLM_MODEL", "nvidia/nemotron-3-super"),
            system_instruction=system_instruction,
            max_tokens=llm_max_tokens,
            temperature=llm_temperature,
            extra={"extra_body": {"chat_template_kwargs": {"enable_thinking": enable_thinking}}},
        ),
    )

    # Text-to-Speech service
    #
    # TTS_PROVIDER selects the speech-output backend:
    #   - "nvidia" (default): NVIDIA Magpie (magpie-tts-multilingual) over the
    #     Riva/NIM gRPC endpoint, authenticated with the nvapi key. This is the
    #     all-NVIDIA pipeline (Parakeet STT → Nemotron LLM → Magpie TTS).
    #   - "gradium": Gradium streaming TTS (fallback if the NIM endpoint misbehaves).
    # Voice/model/endpoint are env-overridable so we can point at a self-hosted
    # Magpie NIM on AWS (NVIDIA_TTS_SERVER=host:port, NVIDIA_TTS_USE_SSL=false)
    # instead of NVIDIA's cloud, keeping every layer on AWS if desired.
    tts_provider = os.getenv("TTS_PROVIDER", "nvidia").lower()
    if tts_provider == "gradium":
        logger.info("TTS provider: Gradium")
        tts = GradiumTTSService(
            api_key=os.environ["GRADIUM_API_KEY"],
            settings=GradiumTTSService.Settings(
                voice=os.getenv("GRADIUM_VOICE_ID", "Eu9iL_CYe8N-Gkx_"),
            ),
        )
    else:
        from pipecat.services.nvidia.tts import NvidiaTTSService

        # Magpie multilingual: one voice covers en/es/fr/de/zh/vi/it/hi/ja; the
        # spoken language is chosen by the request's language_code. A specific
        # AGENT_LANGUAGE drives it directly. In "multi" mode Magpie can't be
        # auto-switched per turn (pipecat doesn't surface STT's detected
        # language), so it synthesizes in MAGPIE_LANGUAGE (default en-US) — set
        # that to the caller's language for a single-language demo.
        magpie_lang = os.getenv("MAGPIE_LANGUAGE", "en-US") if multilingual else agent_language
        # The .EN-US.Aria voice is warm for English; for other languages use the
        # base multilingual voice so the language_code drives pronunciation.
        default_voice = (
            "Magpie-Multilingual.EN-US.Aria"
            if magpie_lang.lower().startswith("en")
            else "Magpie-Multilingual"
        )
        magpie_voice = os.getenv("MAGPIE_VOICE", default_voice)
        magpie_server = os.getenv("NVIDIA_TTS_SERVER", "grpc.nvcf.nvidia.com:443")
        logger.info(
            "TTS provider: NVIDIA Magpie (voice={}, lang={}, server={})",
            magpie_voice,
            magpie_lang,
            magpie_server,
        )
        tts = NvidiaTTSService(
            api_key=os.getenv("NVIDIA_API_KEY") or os.environ["NEMOTRON_LLM_API_KEY"],
            server=magpie_server,
            use_ssl=os.getenv("NVIDIA_TTS_USE_SSL", "true").lower() == "true",
            model_function_map={
                "function_id": os.getenv(
                    "MAGPIE_FUNCTION_ID", "877104f7-e885-42b9-8de8-f6e4c6303969"
                ),
                "model_name": os.getenv("MAGPIE_MODEL", "magpie-tts-multilingual"),
            },
            settings=NvidiaTTSService.Settings(voice=magpie_voice, language=Language(magpie_lang)),
        )

    # ToolsSchema (above) describes the tools to the LLM; register_function wires
    # each name to the handler the LLM will invoke. Both are required.
    llm.register_function("check_sol", check_sol_tool)
    llm.register_function("classify_treatment", classify_treatment_tool)
    llm.register_function("route_case", route_case_tool)
    llm.register_function("end_call", end_call)

    # Turn detection / endpointing (env-toggleable for A/B):
    #   VAD_STOP_SECS  — silence after speech before the turn is considered over.
    #     Silero's default is 0.8s; 0.5 shaves ~300ms off perceived latency per turn.
    #   VAD_CONFIDENCE — speech-probability threshold. Raised to 0.7 (default 0.5) to
    #     suppress false interrupt triggers from Krisp/Twilio line noise now that
    #     interruptions are re-enabled (see ALLOW_INTERRUPTIONS below).
    # Noise robustness (env-tunable): a loud demo room was tripping VAD on
    # background chatter, firing spurious "user started speaking" -> interruption
    # that cut the bot off mid-sentence. Defaults below gate that out:
    #   VAD_CONFIDENCE — speech-probability threshold (0.8: ignore low-prob noise).
    #   VAD_MIN_VOLUME — audio must be at least this loud to count as speech
    #     (0.8: ignores far-field room chatter; the caller's own voice is louder).
    #   VAD_START_SECS — require sustained speech before triggering (0.2: ignore
    #     short noise blips like a cough/door/clap).
    #   VAD_STOP_SECS  — silence after speech before the turn ends.
    vad_params = VADParams(
        confidence=float(os.getenv("VAD_CONFIDENCE", "0.8")),
        start_secs=float(os.getenv("VAD_START_SECS", "0.2")),
        stop_secs=float(os.getenv("VAD_STOP_SECS", "0.6")),
        min_volume=float(os.getenv("VAD_MIN_VOLUME", "0.8")),
    )
    logger.info(
        "[VAD] confidence={} min_volume={} start_secs={} stop_secs={}",
        vad_params.confidence,
        vad_params.min_volume,
        vad_params.start_secs,
        vad_params.stop_secs,
    )

    # Turn-taking finalizer (env-toggleable for A/B):
    #   TURN_MODE=vad (default) — finalize the user turn on VAD silence + a
    #     received transcript (SpeechTimeoutUserTurnStopStrategy). Robust on
    #     noisy phone lines: the bot replies as soon as the caller pauses.
    #   TURN_MODE=llm — gate turn completion on the LLM emitting a ✓ marker
    #     (FilterIncompleteUserTurnStrategies). Smarter endpointing when the
    #     line is quiet, but it STALLS on the phone: background noise yields
    #     fragmented transcripts, the LLM keeps returning ○/◐ ("incomplete"),
    #     and the bot never commits to a reply. That was the "no response when
    #     we talk" bug, so we default away from it.
    turn_mode = os.getenv("TURN_MODE", "vad").lower()
    if turn_mode == "llm":
        logger.info("[TURN] mode=llm (FilterIncompleteUserTurnStrategies)")
        turn_strategies = FilterIncompleteUserTurnStrategies()
    else:
        logger.info("[TURN] mode=vad (SpeechTimeoutUserTurnStopStrategy)")
        turn_strategies = UserTurnStrategies(
            stop=[
                SpeechTimeoutUserTurnStopStrategy(
                    user_speech_timeout=float(os.getenv("USER_SPEECH_TIMEOUT", "0.6"))
                )
            ]
        )

    context = LLMContext(tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(
                sample_rate=audio_in_sample_rate, params=vad_params
            ),
            user_turn_strategies=turn_strategies,
        ),
    )

    # Pipeline - assembled from reusable components
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    # Interruptions re-enabled by default so the caller can barge in (natural
    # conversation). Previously off to dodge Krisp/Twilio noise false-triggers;
    # the raised VAD confidence above is the better fix. Toggle with
    # ALLOW_INTERRUPTIONS=false to A/B.
    allow_interruptions = os.getenv("ALLOW_INTERRUPTIONS", "true").lower() == "true"
    logger.info("[PIPELINE] allow_interruptions={}", allow_interruptions)
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=audio_in_sample_rate,
            audio_out_sample_rate=audio_out_sample_rate,
            allow_interruptions=allow_interruptions,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        # Brief pause to let Krisp VIVA warm up and Twilio connection noise settle
        # before the greeting LLM runs, preventing spurious VAD interruptions.
        await asyncio.sleep(1.0)
        context.add_message(
            {
                "role": "user",
                "content": (
                    "The caller has just connected. Open the call now using your exact "
                    "opening script from your instructions (the Hartley & Associates "
                    "greeting). Speak first — do not wait for the caller."
                ),
            }
        )
        logger.info("[GREETING] client connected — queuing LLMRunFrame to generate opening")
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        # Safety net: if the caller hung up before the agent called end_call,
        # still build the queue and log the session (guarded; no double-run).
        await _finalize_postcall("disconnect")
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=False)

    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Main bot entry point."""

    from_number: str | None = None
    session_id: str | None = None
    transport_overrides: dict = {}

    # Krisp is available when deployed to Pipecat Cloud
    if os.environ.get("ENV") != "local":
        from pipecat.audio.filters.krisp_viva_filter import KrispVivaFilter

        krisp_filter = KrispVivaFilter()
    else:
        krisp_filter = None

    match runner_args:
        case SmallWebRTCRunnerArguments():
            webrtc_connection: SmallWebRTCConnection = runner_args.webrtc_connection

            transport = SmallWebRTCTransport(
                webrtc_connection=webrtc_connection,
                params=TransportParams(
                    audio_in_enabled=True,
                    audio_in_filter=krisp_filter,
                    audio_out_enabled=True,
                ),
            )
        case WebSocketRunnerArguments():
            # Twilio media streams are 8 kHz μ-law on the wire. We keep OUTPUT at
            # 8 kHz (the serializer re-encodes to μ-law for Twilio), but run INPUT
            # at 16 kHz: the TwilioFrameSerializer upsamples the incoming 8 kHz
            # μ-law to 16 kHz PCM (ulaw_to_pcm -> pipeline rate), so VAD and the
            # Parakeet NIM STT receive TRUE 16 kHz audio. Parakeet is configured
            # for 16 kHz; feeding it 8 kHz frames mislabeled as 16 kHz produced
            # empty transcripts ("greets but never replies"). 16 kHz in fixes that.
            transport_overrides["audio_in_sample_rate"] = 16000
            transport_overrides["audio_out_sample_rate"] = 8000

            # Parse Twilio websocket and fetch call information
            _, call_data = await parse_telephony_websocket(runner_args.websocket)
            # Use the Twilio call SID as the session id (S3 keys, queue payloads).
            session_id = call_data["call_id"]

            # Fetch call information from Twilio REST API so we can personalize
            # the bot for known customers (see KNOWN_CUSTOMERS).
            call_info = await get_call_info(call_data["call_id"])
            if call_info:
                from_number = call_info.get("from_number")
                logger.info(f"Call from: {from_number} to: {call_info.get('to_number')}")

            serializer = TwilioFrameSerializer(
                stream_sid=call_data["stream_id"],
                call_sid=call_data["call_id"],
                account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
                auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            )

            transport = FastAPIWebsocketTransport(
                websocket=runner_args.websocket,
                params=FastAPIWebsocketParams(
                    audio_in_enabled=True,
                    audio_in_filter=krisp_filter,
                    audio_out_enabled=True,
                    add_wav_header=False,
                    serializer=serializer,
                ),
            )
        case _:
            logger.error(f"Unsupported runner arguments type: {type(runner_args)}")
            return

    await run_bot(
        transport, from_number=from_number, session_id=session_id, **transport_overrides
    )


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
