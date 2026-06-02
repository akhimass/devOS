import { cn } from "@/lib/utils"

/** Official Y Combinator wordmark: orange Y square + orange Combinator text. */
export function YCombinatorWordmark({ className }: { className?: string }) {
  return (
    <img
      src="/backed-by/ycombinator.png"
      alt="Y Combinator"
      className={cn("inline-block shrink-0 w-auto", className)}
    />
  )
}
