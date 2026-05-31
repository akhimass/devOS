import { useEffect, useMemo, useState } from "react"
import { Search } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  DecisionBadge,
  UrgencyBadge,
  SolBadge,
} from "@/components/CallBadges"
import {
  computeKpis,
  durationLabel,
  fetchCalls,
  isAfterHours,
  whenLabel,
} from "@/lib/calls"
import type { Call } from "@/lib/types"
import { cn } from "@/lib/utils"

type FilterKey = "all" | "qualified" | "declined" | "afterhours"

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "qualified", label: "Qualified" },
  { key: "declined", label: "Declined" },
  { key: "afterhours", label: "After-hours" },
]

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-border bg-card px-5 py-4">
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-semibold tracking-tight">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div>}
    </div>
  )
}

export default function Calls() {
  const [calls, setCalls] = useState<Call[]>([])
  const [live, setLive] = useState(false)
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState("")
  const [filter, setFilter] = useState<FilterKey>("all")

  useEffect(() => {
    fetchCalls().then(({ calls, live }) => {
      setCalls(calls)
      setLive(live)
      setLoading(false)
    })
  }, [])

  const kpis = useMemo(() => computeKpis(calls), [calls])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return calls.filter((c) => {
      if (filter === "qualified" && c.decision !== "qualified") return false
      if (filter === "declined" && c.decision !== "declined") return false
      if (filter === "afterhours" && !isAfterHours(c)) return false
      if (!q) return true
      return (
        (c.caller_name ?? "").toLowerCase().includes(q) ||
        (c.case_type ?? "").toLowerCase().includes(q) ||
        (c.caller_phone ?? "").toLowerCase().includes(q) ||
        (c.state ?? "").toLowerCase().includes(q)
      )
    })
  }, [calls, query, filter])

  return (
    <div>
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-xl">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Calls</h1>
          <p className="text-xs text-muted-foreground">
            Hartley & Associates · Aria
          </p>
        </div>
        <Badge variant={live ? "success" : "outline"}>
          {live ? "Live data" : "Demo data"}
        </Badge>
      </header>

      <div className="space-y-6 p-6">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Kpi label="Total calls" value={String(kpis.total)} />
          <Kpi
            label="Qualified"
            value={String(kpis.qualified)}
            hint={`${kpis.qualifiedRate}% of calls`}
          />
          <Kpi label="Declined" value={String(kpis.declined)} />
          <Kpi label="After-hours" value={String(kpis.afterHours)} />
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="inline-flex rounded-md border border-border bg-card p-0.5">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={cn(
                  "rounded-[6px] px-3 py-1.5 text-sm font-medium transition-colors",
                  filter === f.key
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="relative w-full sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search caller, case, phone, state…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left text-xs font-medium text-muted-foreground">
                  <th className="px-4 py-3">Caller</th>
                  <th className="px-4 py-3">Case type</th>
                  <th className="px-4 py-3">State</th>
                  <th className="px-4 py-3">Urgency</th>
                  <th className="px-4 py-3">Decision</th>
                  <th className="px-4 py-3">SOL</th>
                  <th className="px-4 py-3">When</th>
                  <th className="px-4 py-3 text-right">Duration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-muted-foreground">
                      Loading calls…
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-muted-foreground">
                      No calls match your filters.
                    </td>
                  </tr>
                ) : (
                  filtered.map((c) => (
                    <tr key={c.id} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <div className="font-medium">{c.caller_name ?? "Unknown"}</div>
                        <div className="text-xs text-muted-foreground">
                          {c.caller_phone ?? "—"}
                        </div>
                      </td>
                      <td className="px-4 py-3">{c.case_type ?? "—"}</td>
                      <td className="px-4 py-3 text-muted-foreground">{c.state ?? "—"}</td>
                      <td className="px-4 py-3">
                        <UrgencyBadge urgency={c.urgency} />
                      </td>
                      <td className="px-4 py-3">
                        <DecisionBadge decision={c.decision} />
                      </td>
                      <td className="px-4 py-3">
                        <SolBadge viable={c.sol_viable} days={c.sol_days_remaining} />
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {whenLabel(c)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-muted-foreground">
                        {durationLabel(c)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="border-t border-border px-4 py-2.5 text-xs text-muted-foreground">
            Showing {filtered.length} of {calls.length} calls
          </div>
        </div>
      </div>
    </div>
  )
}
