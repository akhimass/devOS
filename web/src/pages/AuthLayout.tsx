import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import { Check } from "lucide-react"
import { Wordmark } from "@/components/Logo"
import { PRODUCT_NAME, PRODUCT_TAGLINE } from "@/lib/mock"
import { useAuth } from "@/auth/AuthProvider"
import { isSupabaseConfigured } from "@/lib/supabase"

const POINTS = [
  "Live tool-call telemetry (check_sol, route_case, end_call)",
  "Twilio intake line +1 (385) 363-4730 wired to Supabase",
  "Qualified / declined disposition with full transcripts",
]

export default function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: ReactNode
}) {
  const { demoMode } = useAuth()

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="grid min-h-screen lg:grid-cols-2">
        <div className="flex flex-col px-6 py-8 sm:px-12 lg:px-16">
          <Link to="/" className="w-fit">
            <Wordmark />
          </Link>
          <div className="flex flex-1 items-center justify-center py-8 lg:py-10">
            <div className="w-full max-w-sm rounded-xl border border-border bg-white p-6 shadow-sm sm:p-8">
              <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
              <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
              <div className="mt-8">{children}</div>
              {demoMode && (
                <p className="mt-6 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                  {isSupabaseConfigured
                    ? "Demo session — sample calls and tool events. Use your firm account above for live Supabase data."
                    : "Demo mode — set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY for live data."}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="relative overflow-hidden bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700 px-8 py-12 text-white lg:flex lg:flex-col lg:justify-center lg:px-16">
          <div
            className="pointer-events-none absolute inset-0 opacity-40"
            style={{
              background:
                "radial-gradient(circle at 20% 20%, rgba(255,255,255,0.25), transparent 45%), radial-gradient(circle at 80% 80%, rgba(255,255,255,0.15), transparent 40%)",
            }}
          />
          <div className="relative max-w-md">
            <div className="text-sm font-medium text-white/70">
              {PRODUCT_NAME} · {PRODUCT_TAGLINE}
            </div>
            <h2 className="mt-4 text-3xl font-semibold leading-tight tracking-tight">
              Sign in to your firm dashboard.
            </h2>
            <p className="mt-3 text-sm text-white/85">
              Review live intake calls, qualification outcomes, and tool telemetry in one place.
            </p>
            <ul className="mt-8 space-y-4">
              {POINTS.map((p) => (
                <li key={p} className="flex items-start gap-3 text-sm text-white/90">
                  <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-white/15">
                    <Check className="size-3" />
                  </span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
