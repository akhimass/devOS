# Setup

This repo has two main pieces you may want to run during the hackathon:

- the voice agent backend in `server/`
- the Streamlit dashboard in `dashboard/`

There is also an optional live tool-events API so the deployed agent and your local dashboard can see the same real-time tool activity.

## Prerequisites

- Python 3.11+
- `uv`
- API keys required by the voice agent you choose to run
- Optional: `ngrok` if you want to expose the live tool-events API

## 1) Backend setup

From the repo root:

```bash
cd server
cp .env.example .env
```

Fill in the values you need in `server/.env`.

At minimum, you will usually need the voice/LLM keys for the bot you are running. If you want live tool visibility, also set the tool-events variables described below.

Install backend dependencies:

```bash
uv sync
```

Run the bot:

```bash
uv run bot-nemotron.py
```

If you want to use the simpler test harness or the GPT version instead, follow the existing server README instructions for those entrypoints.

## 2) Dashboard setup

The Streamlit dashboard lives in `dashboard/hackathon.py`.

Install dashboard dependencies:

```bash
cd ../dashboard
pip install -r requirements.txt
```

Run the dashboard from the repo root or from `dashboard/`:

```bash
streamlit run dashboard/hackathon.py
```

## 3) Live tool-events setup

This project supports a shared live tool-events source so:

- the deployed agent can emit tool activity
- your local dashboard can read the same live events

There are two modes:

### A. Local fallback mode

If you do nothing, the code falls back to a local JSONL file.

This is fine for same-machine dev, but it will not work if the agent is deployed somewhere else.

### B. Shared remote mode, recommended

Run the FastAPI + SQLite tool-events service locally, then expose it with ngrok.

#### Step 1: set a token

Pick any secret token and set it in the environment for both the API and the agent/dashboard.

Example:

```bash
export TOOL_EVENTS_API_TOKEN='your-secret-token'
```

#### Step 2: start the API

From `server/`:

```bash
export TOOL_EVENTS_API_TOKEN='your-secret-token'
uv run uvicorn tool_events_api:app --host 0.0.0.0 --port 8001
```

The API stores events in SQLite. By default the database lives at:

```text
server/runtime/tool_events.sqlite3
```

You can override that with `TOOL_EVENTS_DB_PATH` if needed.

#### Step 3: expose it with ngrok

In another terminal:

```bash
ngrok http 8001
```

Copy the HTTPS ngrok URL, for example:

```text
https://xxxx.ngrok-free.app
```

#### Step 4: point the agent and dashboard at the same API

Set these environment variables in both places that need live tool events:

```bash
TOOL_EVENTS_API_URL=https://xxxx.ngrok-free.app
TOOL_EVENTS_API_TOKEN=your-secret-token
```

The backend will POST events to `POST /tool-events`.
The dashboard will poll `GET /tool-events`.

## 4) Example env vars

Add the following to `server/.env` or export them in your shell:

```bash
# Optional live tool feed
INTAKE_TOOL_EVENTS_PATH=
TOOL_EVENTS_API_URL=https://xxxx.ngrok-free.app
TOOL_EVENTS_API_TOKEN=your-secret-token
```

If `TOOL_EVENTS_API_URL` is not set, the code uses the local file fallback.

## 5) Verify the API

Once the API is running, check health:

```bash
curl http://localhost:8001/health
```

If you are using auth, include the bearer token:

```bash
curl -H "Authorization: Bearer your-secret-token" http://localhost:8001/tool-events
```

## 6) Suggested local workflow

1. Start the tool-events API.
2. Start ngrok.
3. Configure the same API URL + token in the deployed agent environment.
4. Start the dashboard locally.
5. Place a test call / trigger a tool call.
6. Confirm the dashboard shows the live tool events.

## Notes

- The dashboard does not need to auto-refresh constantly; it reads the current source and updates when you refresh the page or rerun the app.
- The local JSONL fallback is useful for quick single-machine testing, but a shared remote API is the correct setup when the agent runs elsewhere.
- Keep the bearer token private. Do not commit it to git.
