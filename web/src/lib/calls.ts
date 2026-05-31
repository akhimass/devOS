import { supabase, isSupabaseConfigured } from "@/lib/supabase"
import { MOCK_CALLS } from "@/lib/mock"
import type { Call, CallKpis } from "@/lib/types"

const SELECT_COLS =
  "id, session_id, caller_name, caller_phone, firm_phone, caller_email, case_type, state, decision, urgency, severity_tier, red_flags, sol_viable, sol_days_remaining, emotional_state, attorney_tier, appointment_slot, has_prior_representation, transcript, call_ended_reason, started_at, ended_at"

const DEMO_CALLER_PHONE = "5703322862"

function phoneDigits(phone: string | null | undefined): string {
  return (phone ?? "").replace(/\D/g, "")
}

function ensureDemoCall(calls: Call[]): Call[] {
  const demo = MOCK_CALLS.find((c) => phoneDigits(c.caller_phone).includes(DEMO_CALLER_PHONE))
  if (!demo) return calls
  if (calls.some((c) => phoneDigits(c.caller_phone).includes(DEMO_CALLER_PHONE))) return calls
  return [demo, ...calls]
}

export async function fetchCalls(): Promise<{ calls: Call[]; live: boolean }> {
  if (!isSupabaseConfigured || !supabase) {
    return { calls: MOCK_CALLS, live: false }
  }
  const { data, error } = await supabase
    .from("calls")
    .select(SELECT_COLS)
    .order("ended_at", { ascending: false })
    .limit(200)

  if (error || !data || data.length === 0) {
    return { calls: MOCK_CALLS, live: false }
  }
  return { calls: ensureDemoCall(data as unknown as Call[]), live: true }
}

export function computeKpis(calls: Call[]): CallKpis {
  const total = calls.length
  const qualified = calls.filter((c) => c.decision === "qualified").length
  const declined = calls.filter((c) => c.decision === "declined").length
  const afterHours = calls.filter((c) => isAfterHours(c)).length
  return {
    total,
    qualified,
    declined,
    afterHours,
    qualifiedRate: total ? Math.round((qualified / total) * 100) : 0,
  }
}

export function isAfterHours(call: Call): boolean {
  const ts = call.started_at ?? call.ended_at
  const h = new Date(ts).getHours()
  return h < 9 || h >= 17
}

export function durationLabel(call: Call): string {
  if (!call.started_at) return "—"
  const ms = new Date(call.ended_at).getTime() - new Date(call.started_at).getTime()
  if (ms <= 0) return "—"
  const total = Math.round(ms / 1000)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, "0")}`
}

export function whenLabel(call: Call): string {
  const ts = call.started_at ?? call.ended_at
  return new Date(ts).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}
