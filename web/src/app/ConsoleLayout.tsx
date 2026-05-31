import { NavLink, Outlet, useNavigate } from "react-router-dom"
import {
  LayoutDashboard,
  PhoneCall,
  Radio,
  LogOut,
  Circle,
} from "lucide-react"
import { Wordmark } from "@/components/Logo"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/auth/AuthProvider"
import { FIRM_TAGLINE } from "@/lib/mock"
import { cn } from "@/lib/utils"

const NAV = [
  { to: "/app/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/app/calls", label: "Calls", icon: PhoneCall },
  { to: "/app/live", label: "Live", icon: Radio },
]

export default function ConsoleLayout() {
  const { firmName, email, signOut } = useAuth()
  const navigate = useNavigate()

  async function handleSignOut() {
    await signOut()
    navigate("/", { replace: true })
  }

  const initials = (firmName ?? "FC")
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase()

  return (
    <div className="flex min-h-screen bg-muted/30">
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col border-r border-sidebar-border bg-sidebar md:flex">
        <div className="flex h-16 items-center border-b border-sidebar-border px-5">
          <Wordmark />
        </div>

        <div className="border-b border-sidebar-border px-3 py-3">
          <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
            <span className="flex size-8 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground">
              {initials}
            </span>
            <div className="min-w-0">
              <div className="truncate text-sm font-medium">
                {firmName ?? "Your firm"}
              </div>
              <div className="text-xs text-muted-foreground">
                {FIRM_TAGLINE}
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                )
              }
            >
              <item.icon className="size-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-sidebar-border p-3">
          <div className="mb-2 flex items-center gap-2 px-2 text-xs text-muted-foreground">
            <Circle className="size-2 fill-success text-success" />
            Agent online · 24/7
          </div>
          <div className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5">
            <span className="truncate text-xs text-muted-foreground">
              {email}
            </span>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleSignOut}
              title="Sign out"
            >
              <LogOut className="size-4" />
            </Button>
          </div>
        </div>
      </aside>

      <div className="flex-1 md:pl-60">
        <Outlet />
      </div>
    </div>
  )
}
