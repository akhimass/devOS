import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Loader2 } from "lucide-react"
import AuthLayout from "@/pages/AuthLayout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/auth/AuthProvider"

export default function SignIn() {
  const { authed, email, firmName, signIn, signOut } = useAuth()
  const navigate = useNavigate()
  const [login, setLogin] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const { error } = await signIn(login.trim(), password)
    setLoading(false)
    if (error) {
      setError(error)
      return
    }
    navigate("/app/overview", { replace: true })
  }

  if (authed) {
    return (
      <AuthLayout
        title="Already signed in"
        subtitle={
          firmName
            ? `You're signed in as ${email} at ${firmName}.`
            : `You're signed in as ${email}.`
        }
      >
        <div className="space-y-3">
          <Button asChild className="w-full">
            <Link to="/app/overview">Continue to dashboard</Link>
          </Button>
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => void signOut()}
          >
            Sign out and use a different account
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Sign in" subtitle="Sign in with your firm workspace email.">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="login">Email</Label>
          <Input
            id="login"
            type="email"
            autoComplete="username"
            placeholder="you@firm.com"
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
            required
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading && <Loader2 className="animate-spin" />}
          Sign in
        </Button>
        <p className="text-center text-sm text-muted-foreground">
          New firm?{" "}
          <Link to="/signup" className="font-medium text-primary hover:underline">
            Create your workspace
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
