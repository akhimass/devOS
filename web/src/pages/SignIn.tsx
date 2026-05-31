import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Loader2 } from "lucide-react"
import AuthLayout from "@/pages/AuthLayout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/auth/AuthProvider"

export default function SignIn() {
  const { signIn, signInDemo, authed } = useAuth()
  const navigate = useNavigate()
  const [login, setLogin] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [goLive, setGoLive] = useState(false)

  useEffect(() => {
    if (goLive && authed) {
      navigate("/app/live", { replace: true })
    }
  }, [goLive, authed, navigate])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const { error: signInError } = await signIn(login.trim(), password)
    setLoading(false)
    if (signInError) {
      setError(signInError)
      return
    }
    setGoLive(true)
  }

  function onDemo() {
    setError(null)
    signInDemo(login.trim() || undefined)
    setGoLive(true)
  }

  return (
    <AuthLayout
      title="FirstCall"
      subtitle="Sign in to review live intake calls and tool telemetry."
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="login">Username or email</Label>
          <Input
            id="login"
            type="text"
            autoComplete="username"
            placeholder="hartley@firstcall.app"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading || goLive}>
          {loading && <Loader2 className="animate-spin" />}
          Sign in
        </Button>
      </form>
      <div className="mt-4 space-y-3">
        <Button
          type="button"
          variant="outline"
          className="w-full"
          disabled={goLive}
          onClick={onDemo}
        >
          Open demo dashboard
        </Button>
        <p className="text-center text-xs text-muted-foreground">
          <Link to="/app/live" className="underline-offset-4 hover:underline">
            Skip sign-in · view live dashboard
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
