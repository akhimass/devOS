/** Proxy tool-events to the FastAPI server using Vercel env (no browser CORS/token). */
export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*")
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS")
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization")

  if (req.method === "OPTIONS") {
    return res.status(200).end()
  }
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" })
  }

  const base = process.env.TOOL_EVENTS_API_URL?.trim()
  if (!base) {
    return res.status(503).json({ error: "TOOL_EVENTS_API_URL is not configured on Vercel" })
  }

  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(req.query ?? {})) {
    if (value != null) params.set(key, String(value))
  }

  const url = `${base.replace(/\/$/, "")}/tool-events?${params}`
  const headers = {}
  const token = process.env.TOOL_EVENTS_API_TOKEN?.trim()
  if (token) headers.Authorization = `Bearer ${token}`

  try {
    const upstream = await fetch(url, { headers })
    const body = await upstream.text()
    res.status(upstream.status)
    res.setHeader("Content-Type", "application/json")
    return res.send(body)
  } catch (err) {
    return res.status(502).json({
      error: "Failed to reach tool-events API",
      detail: err instanceof Error ? err.message : String(err),
    })
  }
}
