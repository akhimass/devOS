export type Decision = "qualified" | "declined"
export type Urgency = "immediate" | "standard" | "low"

/** Mirrors the denormalized summary columns on public.calls. */
export interface Call {
  id: string
  session_id: string
  caller_name: string | null
  caller_phone: string | null
  caller_email: string | null
  case_type: string | null
  state: string | null
  decision: Decision | null
  urgency: Urgency | null
  severity_tier: string | null
  red_flags: string[]
  sol_viable: boolean | null
  sol_days_remaining: number | null
  emotional_state: string | null
  attorney_tier: string | null
  appointment_slot: string | null
  has_prior_representation: boolean | null
  transcript: string
  call_ended_reason: string | null
  started_at: string | null
  ended_at: string
}

export interface CallKpis {
  total: number
  qualified: number
  declined: number
  afterHours: number
  qualifiedRate: number
}

export interface Profile {
  id: string
  display_name: string | null
  role: "admin" | "attorney" | "intake_staff" | "viewer"
  firm_name: string | null
  twilio_phone: string | null
}

/** Structured tool-call event (API or Supabase model_events). */
export interface ToolEvent {
  id: string | number
  timestamp: string
  tool_name: string
  phase: string
  session_id: string | null
  arguments: Record<string, unknown>
  result: unknown
  note: string | null
  source: "api" | "supabase"
}
