import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Wordmark } from "@/components/Logo"
import {
  AGENT_NAME,
  PRODUCT_DESCRIPTION,
  PRODUCT_NAME,
  PRODUCT_TAGLINE,
} from "@/lib/mock"

export default function Landing() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-border px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Wordmark />
          <Button asChild variant="outline">
            <Link to="/signin">Sign in</Link>
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-20">
        <p className="text-sm font-medium text-muted-foreground">{PRODUCT_TAGLINE}</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">
          {PRODUCT_NAME}
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
          {PRODUCT_DESCRIPTION} {AGENT_NAME} handles intake calls around the clock while
          your firm reviews outcomes, transcripts, and live activity in one dashboard.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link to="/signin">Firm sign in</Link>
          </Button>
        </div>
        <p className="mt-16 text-xs text-muted-foreground">Build {__APP_BUILD__}</p>
      </main>
    </div>
  )
}
