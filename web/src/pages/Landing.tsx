import { Link } from "react-router-dom"
import {
  BarChart3,
  Check,
  FileText,
  FlaskConical,
  Globe,
  Phone,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Wordmark } from "@/components/Logo"
import { AGENT_NAME } from "@/lib/mock"

const FEATURES = [
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
    title: "Bilingual intake",
    body: "Seamless English and Spanish handling with a warm handoff to your bilingual staff when needed.",
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

const MOCK_ROWS = [
  { caller: "Caller · (570) 332-2862", type: "Auto accident", disposition: "Qualified", score: "92", ok: true },
  { caller: "Maria Delgado", type: "Auto accident", disposition: "Qualified", score: "96", ok: true },
  { caller: "James Okafor", type: "Slip & fall", disposition: "Qualified", score: "91", ok: true },
  { caller: "Priya Nair", type: "Auto accident", disposition: "Declined", score: "88", ok: false },
  { caller: "Carlos Mendoza", type: "Auto · ES", disposition: "Qualified", score: "94", ok: true },
] as const

const STATS = [
  { value: "24/7", label: "Always answering, never on hold" },
  { value: "3.2×", label: "More qualified leads captured" },
  { value: "<1s", label: "Average response latency" },
  { value: "$4,200", label: "Saved monthly vs. answering services" },
] as const

export default function Landing() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <Wordmark />
          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <a href="#features" className="hover:text-foreground">
              Features
            </a>
            <a href="#how" className="hover:text-foreground">
              How it works
            </a>
            <a href="#pricing" className="hover:text-foreground">
              Pricing
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" className="hidden sm:inline-flex">
              <Link to="/signin">Sign in</Link>
            </Button>
            <Button asChild>
              <Link to="/signin">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      <main>
        <section className="mx-auto max-w-6xl px-6 pb-16 pt-16 md:pt-24">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-muted/50 px-3 py-1 text-sm text-muted-foreground">
              <span className="size-2 rounded-full bg-emerald-500" />
              Now answering in English &amp; Spanish · 24/7
            </div>
            <h1 className="text-4xl font-semibold tracking-tight md:text-5xl lg:text-6xl">
              FirstCall
            </h1>
            <p className="mt-5 text-lg text-muted-foreground md:text-xl">
              {AGENT_NAME} answers +1 (385) 363-4730, screens callers, and logs every tool call.
              Qualifies the lead, checks the statute of limitations, and books the consult — so your
              firm only talks to cases worth taking.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Button asChild size="lg">
                <Link to="/signin">Open dashboard</Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link to="/app/live">Live view</Link>
              </Button>
            </div>
            <p className="mt-6 text-sm text-muted-foreground">
              No credit card required · Live in under 10 minutes · Trusted by 200+ PI firms
            </p>
          </div>

          <div className="mx-auto mt-14 max-w-4xl">
            <div className="overflow-hidden rounded-xl border border-border bg-card shadow-lg">
              <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-4 py-3">
                <span className="size-3 rounded-full bg-[#ff5f57]" />
                <span className="size-3 rounded-full bg-[#febc2e]" />
                <span className="size-3 rounded-full bg-[#28c840]" />
              </div>
              <div className="grid md:grid-cols-[200px_1fr]">
                <aside className="hidden border-r border-border bg-muted/30 p-4 md:block">
                  <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
                    <span className="inline-flex size-6 items-center justify-center rounded-md bg-primary text-xs text-primary-foreground">
                      FC
                    </span>
                    FirstCall
                  </div>
                  {["Home", "Metrics", "Results", "Calls", "Overview"].map((item) => (
                    <div
                      key={item}
                      className={`mb-1 rounded-md px-2 py-1.5 text-sm ${
                        item === "Calls"
                          ? "bg-accent font-medium text-accent-foreground"
                          : "text-muted-foreground"
                      }`}
                    >
                      {item}
                    </div>
                  ))}
                </aside>
                <div className="p-5">
                  <div className="mb-4 grid gap-3 sm:grid-cols-3">
                    {[
                      { label: "Calls today", value: "23" },
                      { label: "Qualified", value: "14", accent: true },
                      { label: "After-hours", value: "11" },
                    ].map(({ label, value, accent }) => (
                      <div key={label} className="rounded-lg border border-border p-3">
                        <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                          {label}
                        </div>
                        <div
                          className={`mt-1 text-2xl font-bold tracking-tight ${
                            accent ? "text-primary" : ""
                          }`}
                        >
                          {value}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="overflow-hidden rounded-lg border border-border">
                    <div className="grid grid-cols-[1.3fr_1fr_1fr_0.7fr] gap-2 border-b border-border bg-muted/40 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                      <span>Caller</span>
                      <span>Case type</span>
                      <span>Disposition</span>
                      <span>Score</span>
                    </div>
                    {MOCK_ROWS.map((row) => (
                      <div
                        key={row.caller}
                        className="grid grid-cols-[1.3fr_1fr_1fr_0.7fr] gap-2 border-b border-border px-3 py-2.5 text-sm last:border-b-0"
                      >
                        <span className="truncate">{row.caller}</span>
                        <span className="text-muted-foreground">{row.type}</span>
                        <span>
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                              row.ok
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-red-100 text-red-800"
                            }`}
                          >
                            {row.disposition}
                          </span>
                        </span>
                        <span>{row.score}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-border bg-muted/20">
          <div className="mx-auto grid max-w-6xl gap-8 px-6 py-14 sm:grid-cols-2 lg:grid-cols-4">
            {STATS.map(({ value, label }) => (
              <div key={label}>
                <div className="text-3xl font-bold tracking-tight md:text-4xl">{value}</div>
                <p className="mt-2 text-sm text-muted-foreground">{label}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-20" id="features">
          <p className="text-sm font-semibold uppercase tracking-widest text-primary">Built for plaintiff firms</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
            Everything your intake team does — automatically.
          </h2>
          <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
            FirstCall isn&apos;t a generic chatbot. It&apos;s trained on personal-injury intake and
            graded on every call.
          </p>
          <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <div
                key={title}
                className="rounded-xl border border-border bg-card p-6 transition-shadow hover:shadow-md"
              >
                <div className="mb-4 inline-flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Icon className="size-5" strokeWidth={2} />
                </div>
                <h3 className="text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 pb-20" id="how">
          <p className="text-sm font-semibold uppercase tracking-widest text-primary">Live in minutes</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
            Three steps to never missing a call.
          </h2>
          <div className="mt-12 grid gap-8 md:grid-cols-3">
            {[
              {
                step: "1",
                title: "Forward your number",
                body: "Point your after-hours or overflow line to FirstCall. No new hardware, no IT project.",
              },
              {
                step: "2",
                title: "AI answers & qualifies",
                body: "FirstCall greets the caller, gathers the facts, screens the matter, and books the consult.",
              },
              {
                step: "3",
                title: "Qualified leads, delivered",
                body: "You wake up to scored, summarized, ready-to-sign cases — and a full audit trail.",
              },
            ].map(({ step, title, body }) => (
              <div key={step}>
                <div className="mb-4 flex size-10 items-center justify-center rounded-lg border border-border bg-muted text-sm font-bold">
                  {step}
                </div>
                <h3 className="text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-y border-border bg-muted/20 px-6 py-16">
          <blockquote className="mx-auto max-w-3xl text-center">
            <p className="text-xl font-medium leading-relaxed md:text-2xl">
              &ldquo;FirstCall booked four signed cases in its first weekend — calls we would have lost
              to voicemail. It paid for itself before Monday.&rdquo;
            </p>
            <footer className="mt-6 text-sm text-muted-foreground">
              <strong className="text-foreground">Dana Morrison</strong> · Managing Partner, Morrison
              &amp; Associates
            </footer>
          </blockquote>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-20" id="pricing">
          <div className="rounded-2xl border border-border bg-card px-6 py-14 text-center shadow-sm md:px-12">
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
              Stop losing cases to voicemail.
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
              Spin up your firm&apos;s AI intake line today. Free for 14 days — live before your next
              missed call.
            </p>
            <Button asChild size="lg" className="mt-8">
              <Link to="/signin">Create your workspace →</Link>
            </Button>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-8">
          <Wordmark />
          <p className="text-sm text-muted-foreground">
            © 2026 FirstCall AI · Built on Pipecat &amp; NVIDIA Nemotron
          </p>
          <div className="flex gap-5 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground">
              Features
            </a>
            <a href="#pricing" className="hover:text-foreground">
              Pricing
            </a>
            <Link to="/signin" className="hover:text-foreground">
              Sign in
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
