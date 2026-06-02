import { Navigate, Route, Routes } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { useAuth } from "@/auth/AuthProvider"
import Landing from "@/pages/Landing"
import Features from "@/pages/Features"
import HowItWorks from "@/pages/HowItWorks"
import Pricing from "@/pages/Pricing"
import SignIn from "@/pages/SignIn"
import SignUp from "@/pages/SignUp"
import ConsoleLayout from "@/app/ConsoleLayout"
import Overview from "@/app/Overview"
import Calls from "@/app/Calls"
import Live from "@/app/Live"
import Cekura from "@/app/Cekura"
import type { ReactNode } from "react"

function AuthBoot({ children }: { children: ReactNode }) {
  const { ready } = useAuth()
  if (!ready) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background text-muted-foreground">
        <Loader2 className="size-8 animate-spin" />
        <p className="text-sm">Loading FirstCall…</p>
      </div>
    )
  }
  return <>{children}</>
}

function Protected({ children }: { children: ReactNode }) {
  const { authed } = useAuth()
  if (!authed) return <Navigate to="/signin" replace />
  return <>{children}</>
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { authed } = useAuth()
  if (authed) return <Navigate to="/app/overview" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <AuthBoot>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/features" element={<Features />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/signin" element={<SignIn />} />
        <Route
          path="/signup"
          element={
            <PublicOnly>
              <SignUp />
            </PublicOnly>
          }
        />
        <Route
          path="/app"
          element={
            <Protected>
              <ConsoleLayout />
            </Protected>
          }
        >
          <Route index element={<Navigate to="/app/overview" replace />} />
          <Route path="overview" element={<Overview />} />
          <Route path="calls" element={<Calls />} />
          <Route path="live" element={<Live />} />
          <Route path="cekura" element={<Cekura />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthBoot>
  )
}
