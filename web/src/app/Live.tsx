import { useCallback, useEffect, useMemo, useState } from "react"
import { Loader2, RefreshCw, Radio } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DecisionBadge, UrgencyBadge } from "@/components/CallBadges"
import { fetchCalls, durationLabel, whenLabel } from "@/lib/calls"
import { fetchToolEvents, toolEventsSourceLabel } from "@/lib/tool-events"
import { AGENT_NAME, FIRM_NAME } from "@/lib/mock"
import type { Call, ToolEvent } from "@/lib/types"
import { cn } from "@/lib/utils"

const POLL_MS = 8000

function phaseBadge(phase: string) {
  if (phase === "start")
    return (
      <Badge variant="warning" className="uppercase">
        Calling
      </Badge>
    )
  if (phase === "end")
    return (
      <Badge variant="success" className="uppercase">
        Done
      </Badge>
    )
  return <Badge variant="outline">{phase}</Badge>
}

function JsonBlock({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return (
      <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
        Tool still running…
      </p>
    )
  }
  return (
    <pre className="max-h-48 overflow-auto rounded-md border border-border bg-muted/30 p-3 font-mono text-[11px] leading-relaxed">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

function ToolEventCard({ event }: { event: ToolEvent }) {
  const accent =
    event.phase === "start"
      ? "border-l-warning"
      : event.phase === "end"
        ? "border-l-[var(--success)]"
        : "border-l-info"

  return (
    <div
      className={cn(
        "rounded-xl border border-border border-l-4 bg-card p-4 shadow-sm",
        accent
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="font-semibold">{event.tool_name}</div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {phaseBadge(event.phase)}
          <span>{new Date(event.timestamp).toLocaleString()}</span>
        </div>
      </div>
      <p className="mt-1 font-mono text-xs text-muted-foreground">
        Session: {event.session_id ?? "n/a"}
      </p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-medium text-muted-foreground">Arguments</p>
          <JsonBlock value={event.arguments} />
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-muted-foreground">Result</p>
          <JsonBlock value={event.result} />
        </div>
      </div>
      {event.note && (
        <p className="mt-2 text-xs text-muted-foreground">Note: {event.note}</p>
      )}
    </div>
  )
}

export default function Live() {
  const [calls, setCalls] = useState<Call[]>([])
  const [events, setEvents] = useState<ToolEvent[]>([])
  const [selected, setSelected] = useState<Call | null>(null)
  const [callsLive, setCallsLive] = useState(false)
  const [eventsLive, setEventsLive] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true)
    const [callsRes, eventsRes] = await Promise.all([
      fetchCalls(),
      fetchToolEvents({ limit: 24 }),
    ])
    setCalls(callsRes.calls)
    setCallsLive(callsRes.live)
    setEvents(eventsRes.events)
    setEventsLive(eventsRes.live)
    setSelected((prev) => prev ?? callsRes.calls[0] ?? null)
    setLoading(false)
    setRefreshing(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!autoRefresh) return
    const id = window.setInterval(() => load(true), POLL_MS)
    return () => window.clearInterval(id)
  }, [autoRefresh, load])

  const sessionEvents = useMemo(() => {
    if (!selected?.session_id) return events
    return events.filter((e) => e.session_id === selected.session_id)
  }, [events, selected?.session_id])

  const source = toolEventsSourceLabel()

  return (
    <div>
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-xl">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Live dashboard</h1>
          <p className="text-xs text-muted-foreground">
            {FIRM_NAME} · {AGENT_NAME} · +1 (385) 363-4730
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={callsLive && eventsLive ? "success" : "outline"}>
            {callsLive ? "Live" : "Demo"}
          </Badge>
          <Button
            variant={autoRefresh ? "secondary" : "outline"}
            size="sm"
            onClick={() => setAutoRefresh((v) => !v)}
          >
            <Radio className={cn("size-3.5", autoRefresh && "text-success")} />
            Auto {autoRefresh ? "on" : "off"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => load()} disabled={refreshing}>
            {refreshing ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <RefreshCw className="size-3.5" />
            )}
            Refresh
          </Button>
        </div>
      </header>

      <div className="space-y-6 p-6">
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          {/* Live tool feed — Streamlit parity */}
          <section className="space-y-4">
            <div>
              <h2 className="text-sm font-semibold">Live tool activity</h2>
              <p className="text-xs text-muted-foreground">
                Source: {source}. Polls every {POLL_MS / 1000}s when auto-refresh is on.
              </p>
            </div>
            {loading ? (
              <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>
            ) : events.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border bg-card px-6 py-10 text-center text-sm text-muted-foreground">
                Waiting for the agent to call a tool…
              </div>
            ) : (
              <div className="space-y-3">
                {[...events].reverse().map((event) => (
                  <ToolEventCard key={`${event.source}-${event.id}`} event={event} />
                ))}
              </div>
            )}
          </section>

          {/* Calls + transcript */}
          <section className="space-y-4">
            <div>
              <h2 className="text-sm font-semibold">Recent calls</h2>
              <p className="text-xs text-muted-foreground">
                Live calls from Supabase (Twilio line +13853634730).
              </p>
            </div>
            <div className="overflow-hidden rounded-xl border border-border bg-card">
              <div className="max-h-64 divide-y divide-border overflow-y-auto">
                {calls.map((call) => (
                  <button
                    key={call.id}
                    type="button"
                    onClick={() => setSelected(call)}
                    className={cn(
                      "flex w-full items-start justify-between gap-3 px-4 py-3 text-left text-sm transition-colors hover:bg-muted/40",
                      selected?.id === call.id && "bg-secondary/60"
                    )}
                  >
                    <div className="min-w-0">
                      <div className="truncate font-medium">
                        {call.caller_name ?? "Unknown caller"}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {call.case_type ?? "—"} · {whenLabel(call)} · {durationLabel(call)}
                      </div>
                      <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                        {call.session_id}
                      </div>
                    </div>
                    <DecisionBadge decision={call.decision} />
                  </button>
                ))}
              </div>
            </div>

            {selected && (
              <div className="rounded-xl border border-border bg-card p-5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-semibold">{selected.caller_name ?? "Call detail"}</h3>
                  <div className="flex gap-2">
                    <UrgencyBadge urgency={selected.urgency} />
                    <DecisionBadge decision={selected.decision} />
                  </div>
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <div>
                    <dt className="text-muted-foreground">Phone</dt>
                    <dd>{selected.caller_phone ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">State</dt>
                    <dd>{selected.state ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Ended</dt>
                    <dd>{selected.call_ended_reason ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">When</dt>
                    <dd>{whenLabel(selected)}</dd>
                  </div>
                </dl>

                <h4 className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Tool trace ({sessionEvents.length})
                </h4>
                <div className="mt-2 space-y-2">
                  {sessionEvents.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No tool events for this session yet.</p>
                  ) : (
                    sessionEvents.map((e) => (
                      <div
                        key={`${e.id}-${e.tool_name}`}
                        className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-xs"
                      >
                        <span className="font-medium">{e.tool_name}</span>
                        {phaseBadge(e.phase)}
                      </div>
                    ))
                  )}
                </div>

                <h4 className="mt-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Transcript
                </h4>
                <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-md border border-border bg-muted/30 p-3 font-mono text-[11px] leading-relaxed">
                  {selected.transcript?.trim() || "No transcript stored for this call."}
                </pre>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
