# FirstCall

## 1. What Is This?
[60% of law firms are essentially unreachable](https://www.clio.com/resources/legal-trends/2024-report/) by phone in a [$61.3 billion industry](https://www.clio.com/blog/personal-injury-law-statistics/) where the average personal injury settlement sits at [$52,900](https://www.clio.com/blog/personal-injury-law-statistics/) and a single missed call is a five-figure case walking to the next firm on the list. FirstCall answers every inbound call immediately and turns the conversation into a structured, qualified case file. No receptionist, no voicemail, no callback lag:

1. Collects the accident details, date, state, and fault account
2. Asks about injuries and medical treatment, detecting severity signals like ER visits, surgery, and spine involvement
3. Silently checks the statute of limitations for the caller's state mid-call
4. Classifies the case as minor, moderate, severe, or catastrophic
5. Screens for prior representation and routes to the right attorney tier
6. Captures contact info and builds a prioritized follow-up task queue

By the time the call ends, the firm has a complete intake record, a qualification decision, and a ranked action list, captured at the moment the client was ready to talk. Built on an all-NVIDIA voice pipeline (Parakeet STT, Nemotron-3-Super LLM, Magpie TTS), orchestrated by Pipecat and deployed on Pipecat Cloud, with every call automatically scored against intake quality metrics via Cekura's evaluation loop. When the agent misses a required question, Cekura flags it and the prompt patches itself.

## 2. Demo
[Video](https://drive.google.com/file/d/1pRKLgKda2NIlZOYrchRQGOnWfBh1sJxI/view?usp=sharing)

## 3. How We Used Cekura, Nemotron, and Pipecat

### Cekura (Evaluation & Self-Improvement)
1. **Goal:** Ensure Aria consistently covers the three questions that determine intake quality on every call: whether she asked what happened, asked about medical attention, and asked about prior legal representation.
2. **Approach:** Every real Twilio call posts its full transcript to Cekura Observability automatically on hangup. Three custom LLM-judge metrics score each call against the intake script. A post-call eval loop (`server/tools/eval_loop.py`) polls the scores, logs pass/fail to `runtime/eval_loop_history.jsonl`, and on any failure injects targeted REMINDER blocks directly into `prompts/master_prompt.md` without any manual copy-paste. We also ran Cekura's simulated WebRTC callers (scenario 273084) as a regression layer, though the live Twilio → Observability path was our authoritative signal during the event.
3. **Results:** On the first instrumented live call (CAffade...), Cekura scored "Agent Asked What Happened" as pass but flagged "Medical Attention" and "Legal Representation" as fail. Aria empathized but didn't follow through on the required questions. The eval loop automatically patched the prompt, and the base prompt was hardened so distressed callers still receive both medical and legal questions via mandatory Stage 2-4 ordering.

### NVIDIA (Open Weights Models)
1. **Role as Conversational Brain:** Nemotron drives every caller turn, deciding what Aria says next and when to invoke one of four structured tools (`check_sol`, `classify_treatment`, `route_case`, `end_call`) via function calling. Responses are capped at 200 tokens with temperature 0.4 to keep replies short and consistent for phone intake.
2. **All-NVIDIA Speech Pipeline:** The full pipeline is Parakeet STT (nemotron-asr-streaming NIM) → Nemotron-3-Super LLM → Magpie TTS (magpie-tts-multilingual NIM), all sharing one `NVIDIA_API_KEY` over gRPC. This end-to-end NVIDIA stack is the primary deployment path, with Gradium STT/TTS as fallbacks.
3. **Multilingual Support:** When `AGENT_LANGUAGE=multi`, Nemotron auto-detects the caller's language from their first words and conducts the entire conversation in that language. It coordinates with the multilingual Parakeet and Magpie NIMs, which support English, Spanish, French, German, and several other languages.
4. **Custom TTFB Wrapper:** We wrote a thin `VLLMOpenAILLMService` subclass (`nemotron_llm.py`) that defers the time-to-first-byte clock stop to the first non-thinking answer token. Without this, stock Pipecat reported ~270ms TTFB on a reasoning model that actually took ~2.2s to produce its first spoken word.

### Pipecat (Voice)
1. **Pipeline Assembly:** The core pipeline is `transport.input()` → STT → `user_aggregator` → LLM → TTS → `transport.output()` → `assistant_aggregator`. Pipecat's `Pipeline` and `PipelineWorker` manage frame routing, metrics collection, and interruption handling across all components, with Silero VAD handling turn detection and barge-in.
2. **Telephony & Transport:** Production calls come in via Twilio WebSocket (`FastAPIWebsocketTransport`); local dev runs via SmallWebRTC at `localhost:7860`. Twilio delivers 8 kHz µ-law audio, so we built an internal resampling stage to upsample to 16 kHz PCM before VAD/STT, since Parakeet requires 16 kHz and silently returns empty transcripts without it. Krisp VIVA noise filtering runs on cloud calls before VAD.
3. **Deployment on Pipecat Cloud:** The bot is containerized via a Dockerfile based on `dailyco/pipecat-base` and deployed as `flower-bot` on Pipecat Cloud, with `min_agents=1` to keep a warm instance ready. All secrets (`NVIDIA_API_KEY`, `NEMOTRON_LLM_URL`, `CEKURA_API_KEY`, etc.) are injected via Pipecat Cloud's secret sets, and the Cekura observability upload plus eval loop trigger automatically on every call hangup.

## 4. What We Built During the Hackathon

We started with the NVIDIA stack. Getting the all-NVIDIA audio pipeline working (Parakeet STT → Nemotron-3-Super → Magpie TTS) took most of the morning. Parakeet silently returned empty transcripts until we traced it to a sample rate mismatch: Twilio sends 8 kHz, Parakeet needs 16 kHz, and nothing in the docs flags this. We wrote a resampling stage inside the Pipecat pipeline to bridge it. We also discovered that Parakeet emits cumulative transcripts since connection open rather than per-turn deltas, so we wrote a token-count deduplication layer to give Pipecat clean per-turn text. Once the audio path was solid, we added the custom `VLLMOpenAILLMService` wrapper to fix TTFB reporting for Nemotron's thinking mode. Stock Pipecat was clocking ~270ms when the real time-to-first-spoken-word was ~2.2s, an 8x underreport that would have made Cekura's latency scores meaningless.

With the NVIDIA pipeline stable, we built the Pipecat function-tool layer: four tools the LLM calls mid-conversation (`check_sol`, `classify_treatment`, `route_case`, `end_call`), backed by an AWS Bedrock RAG for statute-of-limitations lookups and a Supabase + S3 post-call write pipeline. The system prompt grew to ~645 lines covering a 6-stage intake flow, emotional state detection, distressed-caller handling, multilingual routing, and a completeness tracker that bridges back for any missing field before close.

Cekura went in last and changed how we iterated. We wired Cekura Observability into the post-call hangup handler so every real Twilio call was automatically scored against three metrics: did Aria ask what happened, ask about medical attention, and ask about prior representation. The first scored live call showed Aria passing on "what happened" but failing the other two. She empathized with a distressed caller but didn't follow through on the required questions. Rather than patching the prompt manually, we built `eval_loop.py`: it polls Cekura scores after every call, and on any failure injects targeted REMINDER blocks into `master_prompt.md` automatically. The loop then optionally syncs the updated prompt to the Cekura agent description for the next deploy.

## 5. Tool Feedback

### Nemotron Feedback

**What worked well:** Nemotron-3-Super-120B handled nuanced PI intake conversations (emotional callers, ambiguous facts, statute-of-limitations jurisdictional edge cases) better than expected for a completely untuned model. The reasoning capability in thinking mode was the decisive factor. Non-reasoning models we tested tended to over-qualify callers rather than catch the subtle cases that make the difference between a qualified lead and wasted attorney time. Magpie TTS was low-latency and natural-sounding. The vLLM endpoint was stable all day with no timeouts or errors.

**What could be improved:** The 8 kHz → 16 kHz gap is the single biggest integration tax in this stack. Twilio delivers 8 kHz µ-law; Parakeet expects 16 kHz linear PCM. There is no automatic resampling, no format negotiation, and no explicit error. Parakeet silently returns empty transcripts. We spent a significant portion of the morning chasing ghost bugs before tracing it to sample rate. We had to write a resampling stage inside the Pipecat pipeline ourselves. This should be handled transparently at the NIM layer, or at minimum produce an actionable error like "received 8 kHz, expected 16 kHz." Silent empty transcripts on audio format mismatch is a silent killer for any telephony integration.

### Cekura Feedback

**What worked well:** Once correctly wired, the Twilio → Observability → metric scores pipeline was fast and reliable. Scoring real calls automatically and feeding failures directly into prompt patches without manual review is the strongest part of the platform. The MCP + Claude Code integration (`/cekura-report`) was a real productivity win. Driving test runs from the terminal without switching to a browser kept the iteration loop tight.

**Bugs found:** The Observability API requires transcript roles to be exactly "Testing Agent" / "Main Agent." A wrong value returns an opaque error with no indication of which field failed. The ingestion docs also contain a sample payload with an invalid field value that returns a 400 with no explanation.

### Pipecat Feedback

**What worked well:** The pipeline abstraction (`Pipeline`, `PipelineWorker`, `LLMContext`, `LLMContextAggregatorPair`) made it straightforward to compose STT → LLM → TTS with function calling, VAD, and interruption handling as modular, swappable pieces. Deploying to Pipecat Cloud via `pcc-deploy.toml` with `min_agents=1` was simple and fast.

**What could be improved:**
- Krisp VIVA wasn't enough on its own for telephony. Krisp is doing real work (without it, background noise was tripping VAD constantly) but on a live phone line it couldn't fully isolate the caller's voice from line noise and room echo. We had to layer Krisp with raised VAD thresholds (`VAD_CONFIDENCE=0.7`, `VAD_MIN_VOLUME=0.55`) and increased `VAD_START_SECS` to suppress false triggers. Even then, the combination felt like a workaround rather than a clean solution. Tighter Krisp integration tuned specifically for telephony audio profiles (not just conferencing) would help significantly.
- Detected language from STT doesn't flow downstream to TTS. For multilingual pipelines, Magpie needs a language pin (`MAGPIE_LANGUAGE`) rather than being able to follow what Parakeet detected. Auto-propagating the STT's detected language to TTS would make multilingual support genuinely seamless.

## Live demo — Hartley & Associates

**Console:** [https://firstcalllaw.vercel.app](https://firstcalllaw.vercel.app)

| | |
|---|---|
| **Firm** | Hartley & Associates (Personal Injury · California & Nevada) |
| **Sign in** | `hartley@firstcall.app` |
| **Password** | `hartley123` |
| **Intake line** | +1 (385) 363-4730 |

After sign-in, use **Overview**, **Calls**, **Live** (tool telemetry), and **Cekura** (eval scores) in the sidebar.

For local setup (Tool Events API, Pipecat secrets, Supabase), see [SETUP.md](./SETUP.md).
