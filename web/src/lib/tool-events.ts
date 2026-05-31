import { supabase, isSupabaseConfigured } from "@/lib/supabase"
import type { ToolEvent } from "@/lib/types"

const API_URL = import.meta.env.VITE_TOOL_EVENTS_API_URL as string | undefined
const API_TOKEN = import.meta.env.VITE_TOOL_EVENTS_API_TOKEN as string | undefined

export const isToolEventsApiConfigured = Boolean(
  API_URL?.trim() || import.meta.env.PROD
)

export function toolEventsSourceLabel(): string {
  if (import.meta.env.PROD && typeof window !== "undefined") {
    return `${window.location.origin}/api/tool-events`
  }
  if (API_URL?.trim()) return API_URL.replace(/\/$/, "")
  if (isSupabaseConfigured) return "Supabase model_events"
  return "demo"
}

function buildApiRequests(limit: number, sessionId?: string): { url: string; headers: Record<string, string> }[] {
  const params = new URLSearchParams({ limit: String(limit) })
  if (sessionId) params.set("session_id", sessionId)
  const headers: Record<string, string> = {}
  if (API_TOKEN?.trim()) headers.Authorization = `Bearer ${API_TOKEN.trim()}`

  const requests: { url: string; headers: Record<string, string> }[] = [
    { url: `/api/tool-events?${params}`, headers: {} },
  ]
  if (API_URL?.trim()) {
    requests.push({
      url: `${API_URL.replace(/\/$/, "")}/tool-events?${params}`,
      headers,
    })
  }
  return requests
}

async function fetchFromApi(limit = 24, sessionId?: string): Promise<ToolEvent[]> {
  for (const { url, headers } of buildApiRequests(limit, sessionId)) {
    try {
      const res = await fetch(url, { headers })
      if (!res.ok) continue
      const payload = (await res.json()) as unknown
      if (!Array.isArray(payload)) continue
      return payload.map((row) => ({
        id: (row as { id?: number }).id ?? crypto.randomUUID(),
        timestamp: String((row as { timestamp?: string }).timestamp ?? ""),
        tool_name: String((row as { tool_name?: string }).tool_name ?? "unknown"),
        phase: String((row as { phase?: string }).phase ?? ""),
        session_id: ((row as { session_id?: string }).session_id as string | null) ?? null,
        arguments: ((row as { arguments?: Record<string, unknown> }).arguments ?? {}) as Record<
          string,
          unknown
        >,
        result: (row as { result?: unknown }).result ?? null,
        note: ((row as { note?: string | null }).note as string | null) ?? null,
        source: "api" as const,
      }))
    } catch {
      continue
    }
  }
  return []
}

async function fetchFromSupabase(limit = 24, sessionId?: string): Promise<ToolEvent[]> {
  if (!isSupabaseConfigured || !supabase) return []
  let query = supabase
    .from("model_events")
    .select("id, session_id, tool_name, phase, arguments, result, note, event_ts")
    .order("event_ts", { ascending: false })
    .limit(limit)
  if (sessionId) query = query.eq("session_id", sessionId)
  const { data, error } = await query
  if (error || !data) return []
  return data.map((row) => ({
    id: row.id as number,
    timestamp: String(row.event_ts ?? ""),
    tool_name: String(row.tool_name ?? "unknown"),
    phase: String(row.phase ?? ""),
    session_id: (row.session_id as string | null) ?? null,
    arguments: (row.arguments as Record<string, unknown>) ?? {},
    result: row.result ?? null,
    note: (row.note as string | null) ?? null,
    source: "supabase" as const,
  }))
}

const DEMO_EVENTS: ToolEvent[] = [
  {
    id: 1,
    timestamp: new Date().toISOString(),
    tool_name: "check_sol",
    phase: "end",
    session_id: "CA5703322862",
    arguments: { state: "PA", accident_date: "2026-03-15" },
    result: { sol_viable: true, sol_days_remaining: 730 },
    note: null,
    source: "api",
  },
  {
    id: 2,
    timestamp: new Date().toISOString(),
    tool_name: "route_case",
    phase: "end",
    session_id: "CA5703322862",
    arguments: { case_type: "Auto accident" },
    result: { decision: "qualified", attorney_tier: "associate" },
    note: null,
    source: "api",
  },
]

/** Latest tool events — prefers live API, merges Supabase history when both exist. */
export async function fetchToolEvents(opts?: {
  limit?: number
  sessionId?: string
}): Promise<{ events: ToolEvent[]; live: boolean }> {
  const limit = opts?.limit ?? 24
  const sessionId = opts?.sessionId

  const [apiEvents, dbEvents] = await Promise.all([
    fetchFromApi(limit, sessionId),
    fetchFromSupabase(limit, sessionId),
  ])

  if (apiEvents.length > 0) {
    const merged = mergeToolEvents([...apiEvents, ...dbEvents]).slice(0, limit)
    return { events: merged, live: true }
  }
  if (dbEvents.length > 0) {
    return { events: dbEvents, live: true }
  }
  if (!isSupabaseConfigured && !isToolEventsApiConfigured) {
    return { events: DEMO_EVENTS, live: false }
  }
  return { events: [], live: isSupabaseConfigured || isToolEventsApiConfigured }
}

function mergeToolEvents(events: ToolEvent[]): ToolEvent[] {
  const seen = new Map<string, ToolEvent>()
  for (const e of events) {
    const key = `${e.session_id ?? ""}:${e.tool_name}:${e.phase}:${e.timestamp}`
    const existing = seen.get(key)
    if (!existing || e.source === "api") seen.set(key, e)
  }
  return [...seen.values()].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  )
}
