/**
 * Twilio Voice webhook for every provisioned firm number. Returns TwiML that
 * bridges the call into the Pipecat Cloud agent over a media stream. The same
 * TwiML works for ALL firms — the bot tags each call by the called number
 * (Twilio `to`), so per-firm attribution is automatic.
 *
 * Set this URL as the VoiceUrl when provisioning numbers (see provision-number.js).
 */
export default function handler(req, res) {
  const host = process.env.PIPECAT_SERVICE_HOST || "flower-bot.saibha123"
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://api.pipecat.daily.co/ws/twilio">
      <Parameter name="_pipecatCloudServiceHost" value="${host}" />
    </Stream>
  </Connect>
</Response>`
  res.setHeader("Content-Type", "text/xml")
  return res.status(200).send(xml)
}
