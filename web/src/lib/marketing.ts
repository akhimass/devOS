import {
  BarChart3,
  Check,
  FileText,
  FlaskConical,
  Globe,
  Phone,
  Shield,
  Zap,
} from "lucide-react"

export const FEATURES = [
  {
    icon: Phone,
    title: "After-hours capture",
    body: "Evenings, nights, and weekends — the calls that used to hit voicemail now become signed cases.",
  },
  {
    icon: Check,
    title: "Instant qualification",
    body: "Confirms injury, treatment, fault, and representation, then scores the lead before it reaches your team.",
  },
  {
    icon: Globe,
    title: "25+ language intake",
    body: "Natural conversation in 25+ languages — with a warm handoff to your team when needed.",
  },
  {
    icon: FlaskConical,
    title: "Statute-of-limitations checks",
    body: "Flags time-barred matters automatically so you stop wasting consults on cases you can't take.",
  },
  {
    icon: BarChart3,
    title: "Quality, measured",
    body: "Every conversation is evaluated and trended — see exactly how your intake improves over time.",
  },
  {
    icon: FileText,
    title: "Drops into your CRM",
    body: "Qualified leads, transcripts, and summaries flow straight to your inbox, Litify, or Clio.",
  },
] as const

export const FEATURE_HIGHLIGHTS = [
  {
    icon: Zap,
    title: "Answers in under one second",
    body: "No hold music, no queue. Callers talk to Aria immediately — the way a great intake coordinator would.",
  },
  {
    icon: Shield,
    title: "Built for legal compliance",
    body: "No legal advice, clear disclaimers, full transcripts, and audit trails for every interaction.",
  },
] as const

export const HOW_IT_WORKS_STEPS = [
  {
    step: "1",
    title: "Forward your number",
    body: "Point your after-hours or overflow line to FirstCall. No new hardware, no IT project.",
    detail:
      "During signup we provision a dedicated Twilio line wired to your AI agent. Forward your existing firm number after hours, or route overflow when your front desk is busy.",
  },
  {
    step: "2",
    title: "AI answers & qualifies",
    body: "FirstCall greets the caller, gathers the facts, screens the matter, and books the consult.",
    detail:
      "Aria runs your PI intake script: injury details, treatment, fault, prior representation, and SOL viability. Tool calls are logged live so you can see qualification happen in real time.",
  },
  {
    step: "3",
    title: "Qualified leads, delivered",
    body: "You wake up to scored, summarized, ready-to-sign cases — and a full audit trail.",
    detail:
      "Qualified matters land in your dashboard with disposition, score, and transcript. Your team reviews only cases worth taking — not every wrong-number and spam call.",
  },
] as const

export const ON_CALL_FLOW = [
  "Caller dials your firm line (or forwarded after-hours number)",
  "Aria answers instantly with your firm greeting",
  "Intake script gathers facts and runs SOL / conflict checks",
  "Lead scored and disposition set (qualified, declined, transfer)",
  "Summary + transcript delivered to dashboard and CRM",
] as const

export type PricingPlanId = "starter" | "growth" | "firm"

export interface PricingPlan {
  id: PricingPlanId
  name: string
  price: number | null
  priceLabel: string
  annualPrice?: number
  description: string
  bestFor: string
  featured?: boolean
  cta: string
  includes: string[]
}

export const PRICING_PLANS: PricingPlan[] = [
  {
    id: "starter",
    name: "Starter",
    price: 299,
    priceLabel: "$299",
    annualPrice: 249,
    description: "After-hours intake for solo and small PI practices.",
    bestFor: "1–2 attorneys · under 100 calls/mo",
    cta: "Start free trial",
    includes: [
      "1 dedicated intake line",
      "100 intake calls / month included",
      "After-hours & weekend coverage",
      "English + Spanish",
      "PI playbook (auto, slip & fall, WC)",
      "Email summaries & full transcripts",
      "Firm dashboard",
      "$2.50 per call over limit",
    ],
  },
  {
    id: "growth",
    name: "Growth",
    price: 799,
    priceLabel: "$799",
    annualPrice: 666,
    description: "Full-time AI intake for growing plaintiff firms.",
    bestFor: "3–15 attorneys · 100–400 calls/mo",
    featured: true,
    cta: "Start free trial",
    includes: [
      "2 intake lines (after-hours + overflow)",
      "400 intake calls / month included",
      "24/7 coverage",
      "25+ languages",
      "SOL screening & lead scoring",
      "Live call monitoring & tool telemetry",
      "CRM webhooks (Litify, Clio, Filevine)",
      "Cekura quality scoring on every call",
      "$1.75 per call over limit",
    ],
  },
  {
    id: "firm",
    name: "Firm",
    price: null,
    priceLabel: "Custom",
    description: "Multi-office firms with high volume and custom workflows.",
    bestFor: "15+ attorneys · 400+ calls/mo",
    cta: "Contact sales",
    includes: [
      "Unlimited lines & office routing",
      "Volume-based minute pricing",
      "Custom intake playbooks per practice area",
      "Dedicated success manager",
      "SSO, BAA, and compliance review",
      "API access & custom integrations",
      "SLA-backed uptime",
      "Onboarding & prompt tuning included",
    ],
  },
]

export const PRICING_COMPARISON = [
  { feature: "Dedicated Twilio intake line", starter: true, growth: true, firm: true },
  { feature: "After-hours coverage", starter: true, growth: true, firm: true },
  { feature: "24/7 coverage", starter: false, growth: true, firm: true },
  { feature: "25+ languages", starter: false, growth: true, firm: true },
  { feature: "SOL & conflict screening", starter: true, growth: true, firm: true },
  { feature: "Live tool-call feed", starter: false, growth: true, firm: true },
  { feature: "CRM integrations", starter: "Email only", growth: true, firm: true },
  { feature: "Cekura call quality scoring", starter: false, growth: true, firm: true },
  { feature: "Custom playbooks", starter: false, growth: false, firm: true },
] as const

export const PRICING_FAQ = [
  {
    q: "What counts as an intake call?",
    a: "Any inbound call answered by FirstCall — including after-hours, overflow, and weekend traffic. Declined and spam calls still count toward your plan; you only pay overage on answered calls.",
  },
  {
    q: "How does FirstCall compare to an answering service?",
    a: "Traditional answering services run $3–8 per call and only take messages. FirstCall qualifies the matter, checks SOL, scores the lead, and books consults — typically replacing $4,000+/mo in answering fees for mid-size firms.",
  },
  {
    q: "Is there a contract?",
    a: "Month-to-month on all plans. Annual billing saves two months (Starter $249/mo, Growth $666/mo). Cancel anytime.",
  },
  {
    q: "What's included in the 14-day trial?",
    a: "Full Growth-tier features: dedicated line, dashboard, transcripts, and live monitoring. No credit card required to start.",
  },
  {
    q: "Can I keep my existing phone number?",
    a: "Yes. Forward your current firm line to FirstCall after hours, or we provision a new number you can advertise for intake.",
  },
] as const

export const STATS = [
  { value: "24/7", label: "Always answering" },
  { value: "<1s", label: "Average response latency" },
  { value: "25+", label: "Languages supported" },
  { value: "6-stage", label: "Intake flow per call" },
] as const

export function planSignupHref(planId: PricingPlanId): string {
  return planId === "firm" ? "/signup?plan=firm" : `/signup?plan=${planId}`
}
