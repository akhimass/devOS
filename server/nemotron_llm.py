#
# Copyright (c) 2024–2026, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""vLLM OpenAI-compatible LLM service that times TTFB to the first NON-THINKING token.

Stock pipecat (``BaseOpenAILLMService._process_context``) stops the TTFB clock on
the first streamed chunk that carries any ``choices`` (base_llm.py:467) — i.e. the
first role / reasoning delta. For a reasoning model served with thinking enabled
(Nemotron-3-Super over vLLM), the answer (``content``) tokens do not begin until
the model finishes thinking, so the stock metric badly understates TTFB (in
aiewf-eval, ~270 ms reported vs. ~2.2 s to the first real answer token).

This subclass defers the TTFB stop until a delta actually carries user-visible
output (text ``content`` or a ``tool_call``), WITHOUT duplicating the large
``_process_context`` method:

  * ``get_chat_completions`` wraps the chunk stream and "arms" a flag on the first
    content/tool delta (resetting it per invocation);
  * ``stop_ttfb_metrics`` is gated on that flag.

Pipecat already calls ``stop_ttfb_metrics()`` on every chunk with ``choices``, so
once armed the existing call records TTFB at the correct moment; before that it is
a no-op. ``reasoning_content``-only, role-only, and empty deltas never arm it. When
thinking is disabled the first delta is already ``content``, so this is a no-op
correction (TTFB == stock).

Mirrors aiewf-eval's ``multi_turn_eval.services.vllm_openai.VLLMOpenAILLMService``,
adapted to this pipecat's ``get_chat_completions(self, context)`` signature.
"""

import time

from loguru import logger
from pipecat.services.openai.llm import OpenAILLMService


def _preview(text: str, limit: int = 500) -> str:
    """Truncate text for log output so we never dump a 600-line prompt."""
    if text is None:
        return "<none>"
    text = str(text).replace("\n", " ")
    return text if len(text) <= limit else f"{text[:limit]}… [+{len(text) - limit} chars]"


class VLLMOpenAILLMService(OpenAILLMService):
    """OpenAI-compatible vLLM service whose TTFB metric is the first answer token."""

    def __init__(self, *args, **kwargs):
        """Initialize the service; see OpenAILLMService for accepted args."""
        super().__init__(*args, **kwargs)
        self._ttft_armed = False

    async def get_chat_completions(self, context):
        """Wrap the chunk stream to arm TTFB on the first content/tool delta.

        ``_process_context`` calls this once per turn, right after
        ``start_ttfb_metrics()`` and before iterating — so reset the per-turn
        arming flag here.
        """
        self._ttft_armed = False

        # ---- DIAGNOSTIC: what we are about to send to the LLM --------------
        try:
            messages = context.get_messages()
        except Exception as e:  # pragma: no cover - defensive logging only
            messages = None
            logger.warning(f"[LLM] could not read context messages: {e}")

        system_msg = ""
        last_user_msg = ""
        if messages:
            for m in messages:
                role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
                content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
                if role == "system" and not system_msg:
                    system_msg = content or ""
                if role == "user":
                    last_user_msg = content or last_user_msg

        logger.info(
            "[LLM] ▶ REQUEST model={} url={} msgs={} system_prompt='{}' last_user='{}'",
            self.get_full_model_name(),
            str(getattr(self._client, "base_url", "?")),
            len(messages) if messages else 0,
            _preview(system_msg),
            _preview(last_user_msg, 300),
        )

        t0 = time.perf_counter()

        try:
            stream = await super().get_chat_completions(context)
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.error("[LLM] ✖ ERROR opening stream after {:.0f}ms: {!r}", elapsed, e)
            raise

        async def _armed_stream():
            first_token_ms = None
            content_acc = []
            tool_calls_seen = False
            try:
                async for chunk in stream:
                    choices = getattr(chunk, "choices", None)
                    delta = getattr(choices[0], "delta", None) if choices else None
                    if delta is not None:
                        piece = getattr(delta, "content", None)
                        if piece:
                            content_acc.append(piece)
                        if getattr(delta, "tool_calls", None):
                            tool_calls_seen = True
                        if not self._ttft_armed and (piece or getattr(delta, "tool_calls", None)):
                            # First non-thought token = first text content or tool call.
                            self._ttft_armed = True
                            first_token_ms = (time.perf_counter() - t0) * 1000
                            logger.info("[LLM] ⋯ first token at {:.0f}ms", first_token_ms)
                    yield chunk
            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000
                logger.error("[LLM] ✖ ERROR mid-stream after {:.0f}ms: {!r}", elapsed, e)
                raise
            finally:
                elapsed = (time.perf_counter() - t0) * 1000
                logger.info(
                    "[LLM] ◀ RESPONSE total={:.0f}ms ttft={} tool_calls={} text='{}'",
                    elapsed,
                    f"{first_token_ms:.0f}ms" if first_token_ms is not None else "NONE(no token!)",
                    tool_calls_seen,
                    _preview("".join(content_acc)),
                )
                # pipecat's _closing() only closes this wrapper generator; close the
                # underlying OpenAI stream too (HTTP resource + uvloop asyncgen safety).
                if hasattr(stream, "close"):
                    await stream.close()
                elif hasattr(stream, "aclose"):
                    await stream.aclose()

        return _armed_stream()

    async def stop_ttfb_metrics(self, *, end_time: float | None = None):
        """Defer the per-chunk TTFB stop until a non-thought token has streamed."""
        if self._ttft_armed:
            await super().stop_ttfb_metrics(end_time=end_time)
