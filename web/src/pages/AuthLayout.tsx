import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import { Check } from "lucide-react"
import { Wordmark } from "@/components/Logo"
import { FIRM_NAME, FIRM_TAGLINE } from "@/lib/mock"
import { useAuth } from "@/auth/AuthProvider"

const POINTS = [
  "Review qualified and declined calls in one place",
  "After-hours coverage on +1 (385) 363-4730",
  "Secure access for Hartley & Associates team members",
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
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col px-6 py-8 sm:px-12 lg:px-16">
        <Link to="/" className="w-fit">
          <Wordmark />
        </Link>
        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-sm">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
            <div className="mt-8">{children}</div>
            {demoMode && (
              <p className="mt-6 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                Demo mode — set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY for live data.
              </p>
            )}
          </div>
        </div>
      </div>
      <div className="relative hidden overflow-hidden bg-primary text-primary-foreground lg:block">
        <div className="relative flex h-full flex-col justify-center px-16">
          <div className="max-w-md">
            <div className="text-sm font-medium text-primary-foreground/60">
              {FIRM_NAME} · {FIRM_TAGLINE}
            </div>
            <h2 className="mt-4 text-3xl font-semibold leading-tight tracking-tight">
              Member sign-in for your firm dashboard.
            </h2>
            <ul className="mt-8 space-y-4">
              {POINTS.map((p) => (
                <li key={p} className="flex items-start gap-3 text-sm text-primary-foreground/90">
                  <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-primary-foreground/15">
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
