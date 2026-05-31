import { supabase, isSupabaseConfigured } from "@/lib/supabase"

/**
 * Provision a Twilio number for the signed-in firm (calls /api/provision-number,
 * which buys the number, wires its Voice webhook to the agent, and stores it on
 * the firm's profile). Returns the new E.164 number.
 */
export async function provisionNumber(areaCode?: string): Promise<{ phone_number: string }> {
  if (!isSupabaseConfigured || !supabase) throw new Error("Sign-in required to provision a number")
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (!token) throw new Error("Not signed in")

  const res = await fetch("/api/provision-number", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ areaCode }),
  })
  const json = (await res.json()) as { phone_number?: string; error?: string }
  if (!res.ok || !json.phone_number) throw new Error(json.error || "Provisioning failed")
  return { phone_number: json.phone_number }
}

/** Save the firm's business hours + timezone to its profile (RLS: own row only). */
export async function saveFirmConfig(opts: {
  businessHours?: unknown
  timezone?: string
}): Promise<void> {
  if (!isSupabaseConfigured || !supabase) return
  const { data } = await supabase.auth.getSession()
  const uid = data.session?.user?.id
  if (!uid) throw new Error("Not signed in")
  const patch: Record<string, unknown> = {}
  if (opts.businessHours !== undefined) patch.business_hours = opts.businessHours
  if (opts.timezone !== undefined) patch.timezone = opts.timezone
  const { error } = await supabase.from("profiles").update(patch).eq("id", uid)
  if (error) throw new Error(error.message)
}
