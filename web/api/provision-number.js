/**
 * Provision a Twilio phone number for the signed-in firm and wire it to the agent.
 *
 * POST /api/provision-number  { areaCode?: string, country?: string }
 *   Authorization: Bearer <supabase access token>   (the signed-in staff user)
 *
 * Flow: verify the caller's Supabase session -> search an available voice-capable
 * number -> purchase it with VoiceUrl = this deployment's /api/twiml -> store it on
 * the caller's profiles.twilio_phone (service role). The agent then answers calls to
 * that number and tags them to this firm automatically (bot uses Twilio `to`).
 *
 * Server env (NOT VITE_): TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, SUPABASE_URL,
 * SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY. Optional PIPECAT_SERVICE_HOST.
 */
export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*")
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS")
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization")
  if (req.method === "OPTIONS") return res.status(200).end()
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" })

  const sid = process.env.TWILIO_ACCOUNT_SID
  const token = process.env.TWILIO_AUTH_TOKEN
  const supaUrl = process.env.SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  const anonKey = process.env.SUPABASE_ANON_KEY || process.env.VITE_SUPABASE_ANON_KEY
  if (!sid || !token) return res.status(503).json({ error: "Twilio not configured on Vercel" })
  if (!supaUrl || !serviceKey || !anonKey)
    return res.status(503).json({ error: "Supabase server keys not configured on Vercel" })

  // 1) Verify the caller and get their user id (don't trust a client-supplied id).
  const accessToken = (req.headers.authorization || "").replace(/^Bearer\s+/i, "").trim()
  if (!accessToken) return res.status(401).json({ error: "Missing Authorization bearer token" })
  let userId
  try {
    const ures = await fetch(`${supaUrl}/auth/v1/user`, {
      headers: { apikey: anonKey, Authorization: `Bearer ${accessToken}` },
    })
    if (!ures.ok) return res.status(401).json({ error: "Invalid session" })
    userId = (await ures.json()).id
  } catch {
    return res.status(401).json({ error: "Could not verify session" })
  }

  const { areaCode, country = "US" } = (req.body && typeof req.body === "object" ? req.body : {}) || {}
  const twBase = `https://api.twilio.com/2010-04-01/Accounts/${sid}`
  const twAuth = "Basic " + Buffer.from(`${sid}:${token}`).toString("base64")
  const voiceUrl = `https://${req.headers.host}/api/twiml`

  try {
    // 2) Find an available voice-capable local number.
    const search = new URLSearchParams({ VoiceEnabled: "true", SmsEnabled: "true", PageSize: "1" })
    if (areaCode) search.set("AreaCode", String(areaCode))
    const avail = await fetch(
      `${twBase}/AvailablePhoneNumbers/${country}/Local.json?${search}`,
      { headers: { Authorization: twAuth } }
    ).then((r) => r.json())
    const candidate = avail?.available_phone_numbers?.[0]?.phone_number
    if (!candidate) return res.status(404).json({ error: "No available numbers for that area code" })

    // 3) Purchase it and point its Voice webhook at our TwiML.
    const buyBody = new URLSearchParams({
      PhoneNumber: candidate,
      VoiceUrl: voiceUrl,
      VoiceMethod: "POST",
    })
    const bought = await fetch(`${twBase}/IncomingPhoneNumbers.json`, {
      method: "POST",
      headers: { Authorization: twAuth, "Content-Type": "application/x-www-form-urlencoded" },
      body: buyBody,
    }).then((r) => r.json())
    if (!bought?.phone_number) {
      return res.status(502).json({ error: "Twilio purchase failed", detail: bought })
    }

    // 4) Attach the number to the firm's profile (service role bypasses RLS).
    const patch = await fetch(`${supaUrl}/rest/v1/profiles?id=eq.${userId}`, {
      method: "PATCH",
      headers: {
        apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`,
        "Content-Type": "application/json",
        Prefer: "return=representation",
      },
      body: JSON.stringify({ twilio_phone: bought.phone_number }),
    })
    if (!patch.ok) {
      return res.status(500).json({ error: "Saved number but failed to update profile", phone_number: bought.phone_number })
    }

    return res.status(200).json({ phone_number: bought.phone_number, voice_url: voiceUrl })
  } catch (e) {
    return res.status(500).json({ error: "Provisioning failed", detail: String(e) })
  }
}
