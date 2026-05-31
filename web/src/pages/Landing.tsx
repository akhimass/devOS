import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Wordmark } from "@/components/Logo"
import { AGENT_NAME } from "@/lib/mock"

export default function Landing() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-border px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Wordmark />
          <Button asChild>
            <Link to="/signin">Sign in</Link>
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-20">
        <h1 className="text-4xl font-semibold tracking-tight">FirstCall</h1>
        <p className="mt-4 max-w-xl text-lg text-muted-foreground">
          {AGENT_NAME} answers +1 (385) 363-4730, screens callers, and logs every tool call.
          Sign in to view live calls and technical telemetry.
        </p>
        <div className="mt-8 flex gap-3">
          <Button asChild size="lg">
            <Link to="/signin">Open dashboard</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link to="/app/live">Live view</Link>
          </Button>
        </div>
      </main>
    </div>
  )
}
