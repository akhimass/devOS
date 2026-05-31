import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Wordmark } from "@/components/Logo"
import { FIRM_NAME, FIRM_TAGLINE } from "@/lib/mock"

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
        <p className="text-sm font-medium text-muted-foreground">{FIRM_TAGLINE}</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight">{FIRM_NAME}</h1>
        <p className="mt-4 max-w-xl text-lg text-muted-foreground">
          Personal injury clients reach us 24/7 at +1 (385) 363-4730. Team members
          can sign in to review calls, outcomes, and live activity.
        </p>
        <div className="mt-8">
          <Button asChild size="lg">
            <Link to="/signin">Sign in</Link>
          </Button>
        </div>
        <p className="mt-16 text-xs text-muted-foreground">Build {__APP_BUILD__}</p>
      </main>
    </div>
  )
}
