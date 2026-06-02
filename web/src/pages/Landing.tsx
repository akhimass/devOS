import { Link } from "react-router-dom"
import { ArrowRight, FileText } from "lucide-react"
import MarketingLayout from "@/components/MarketingLayout"
import { BackedBy } from "@/components/BackedBy"
import { LogoMark } from "@/components/Logo"
import { Button } from "@/components/ui/button"
import { FEATURES, STATS } from "@/lib/marketing"

const MOCK_ROWS = [
  {
    caller: "Caller · (570) 332-2862",
    type: "Auto accident",
    disposition: "Qualified",
    score: "92",
    caseValue: "$186K",
    summary: "intake-570332.pdf",
    ok: true,
  },
  {
    caller: "Maria Delgado",
    type: "Auto accident",
    disposition: "Qualified",
    score: "96",
    caseValue: "$240K",
    summary: "intake-delgado.pdf",
    ok: true,
  },
  {
    caller: "James Okafor",
    type: "Slip & fall",
    disposition: "Qualified",
    score: "91",
    caseValue: "$92K",
    summary: "intake-okafor.pdf",
    ok: true,
  },
  {
    caller: "Priya Nair",
    type: "Auto accident",
    disposition: "Declined",
    score: "88",
    caseValue: "—",
    summary: "—",
    ok: false,
  },
  {
    caller: "Carlos Mendoza",
    type: "Auto · ES",
    disposition: "Qualified",
    score: "94",
    caseValue: "$310K",
    summary: "intake-mendoza.pdf",
    ok: true,
  },
] as const

const TABLE_COLS =
  "grid-cols-[minmax(7rem,1.15fr)_minmax(5rem,0.85fr)_minmax(5.5rem,0.9fr)_2.5rem_minmax(3.5rem,0.65fr)_minmax(5.5rem,0.85fr)]"

export default function Landing() {
  return (
    <MarketingLayout>
      <section className="mx-auto max-w-7xl px-6 pb-6 pt-8 md:pt-10">
        <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] lg:gap-10 xl:grid-cols-[minmax(0,24rem)_minmax(0,1fr)]">
          <div className="text-center lg:text-left">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-border bg-muted/50 px-3 py-1 text-sm text-muted-foreground">
              <span className="size-2 rounded-full bg-emerald-500" />
              Now answering in 25+ languages · 24/7
            </div>
            <h1 className="text-4xl font-semibold tracking-tight md:text-5xl lg:text-6xl">FirstCall</h1>
            <p className="mt-4 text-lg text-muted-foreground md:text-xl">
              Every firm gets its own AI receptionist. Aria answers your dedicated line 24/7, screens
              callers, qualifies leads economically and lawfully, and books the consult — so your firm
              only talks to cases worth taking.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
              <Button asChild size="lg">
                <Link to="/signup">Start free trial</Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link to="/how-it-works">See how it works</Link>
              </Button>
            </div>
          </div>

          <div className="w-full min-w-0 lg:max-w-none">
            <div className="overflow-hidden rounded-xl border border-border bg-card shadow-lg">
              <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-4 py-3">
                <span className="size-3 rounded-full bg-[#ff5f57]" />
                <span className="size-3 rounded-full bg-[#febc2e]" />
                <span className="size-3 rounded-full bg-[#28c840]" />
              </div>
              <div className="grid md:grid-cols-[140px_minmax(0,1fr)]">
                <aside className="hidden border-r border-border bg-muted/30 p-3 md:block">
                  <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
                    <LogoMark className="size-6 rounded-sm" />
                    <span className="lowercase">firstcall</span>
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
                <div className="min-w-0 p-3 sm:p-4">
                  <div className="mb-3 grid gap-2 sm:grid-cols-3">
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
                  <div className="overflow-x-auto rounded-lg border border-border">
                    <div className="min-w-[36rem]">
                      <div
                        className={`grid ${TABLE_COLS} gap-2 border-b border-border bg-muted/40 px-3 py-2 text-[9px] font-semibold uppercase tracking-wide text-muted-foreground sm:text-[10px]`}
                      >
                        <span>Caller</span>
                        <span>Case type</span>
                        <span>Disposition</span>
                        <span>Score</span>
                        <span>Case value</span>
                        <span>Summary</span>
                      </div>
                      {MOCK_ROWS.map((row) => (
                        <div
                          key={row.caller}
                          className={`grid ${TABLE_COLS} gap-2 border-b border-border px-3 py-2 text-xs last:border-b-0 sm:text-sm`}
                        >
                          <span className="truncate">{row.caller}</span>
                          <span className="truncate text-muted-foreground">{row.type}</span>
                          <span>
                            <span
                              className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium sm:text-xs ${
                                row.ok ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                              }`}
                            >
                              {row.disposition}
                            </span>
                          </span>
                          <span>{row.score}</span>
                          <span className="font-medium tabular-nums">{row.caseValue}</span>
                          <span>
                            {row.summary === "—" ? (
                              <span className="text-muted-foreground">—</span>
                            ) : (
                              <span className="inline-flex max-w-full items-center gap-1 truncate text-primary">
                                <FileText className="size-3 shrink-0" />
                                <span className="truncate underline decoration-primary/40 underline-offset-2">
                                  {row.summary}
                                </span>
                              </span>
                            )}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-border bg-muted/20">
        <div className="mx-auto grid max-w-6xl gap-6 px-6 py-8 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map(({ value, label }) => (
            <div key={label}>
              <div className="text-3xl font-bold tracking-tight md:text-4xl">{value}</div>
              <p className="mt-2 text-sm text-muted-foreground">{label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-b border-border px-6 py-6">
        <BackedBy className="mx-auto max-w-6xl" />
      </section>

      <section className="mx-auto max-w-6xl px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-widest text-primary">Features</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
              Built for plaintiff intake.
            </h2>
          </div>
          <Button asChild variant="ghost" className="hidden sm:inline-flex">
            <Link to="/features">
              All features
              <ArrowRight className="ml-1 size-4" />
            </Link>
          </Button>
        </div>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.slice(0, 3).map(({ icon: Icon, title, body }) => (
            <div key={title} className="rounded-xl border border-border bg-card p-6">
              <div className="mb-4 inline-flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Icon className="size-5" strokeWidth={2} />
              </div>
              <h3 className="text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 text-center sm:hidden">
          <Button asChild variant="outline">
            <Link to="/features">All features</Link>
          </Button>
        </div>
      </section>

      <section className="border-y border-border bg-muted/20 px-6 py-10">
        <blockquote className="mx-auto max-w-3xl text-center">
          <p className="text-xl font-medium leading-relaxed md:text-2xl">
            &ldquo;FirstCall booked four signed cases in its first weekend — calls we would have lost to
            voicemail. It paid for itself before Monday.&rdquo;
          </p>
          <footer className="mt-6 text-sm text-muted-foreground">
            <strong className="text-foreground">James Hartley</strong> · Managing Partner, Hartley
            &amp; Associates
          </footer>
        </blockquote>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-12">
        <div className="rounded-2xl border border-border bg-card px-6 py-10 text-center shadow-sm md:px-12">
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            Stop losing cases to voicemail.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            Starter from $299/mo · Growth $799/mo · 14-day free trial on every plan.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button asChild size="lg">
              <Link to="/signup?plan=growth">Start free trial</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link to="/pricing">View pricing</Link>
            </Button>
          </div>
        </div>
      </section>
    </MarketingLayout>
  )
}
