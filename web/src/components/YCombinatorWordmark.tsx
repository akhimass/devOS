import { cn } from "@/lib/utils"

const YC_ORANGE = "#FF6600"

/** Y Combinator wordmark: orange Y square + orange Combinator text. */
export function YCombinatorWordmark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 104 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("inline-block shrink-0", className)}
      role="img"
      aria-label="Y Combinator"
    >
      <rect width="24" height="24" fill={YC_ORANGE} />
      <text
        x="12"
        y="17"
        fill="#fff"
        fontFamily="Helvetica, Arial, ui-sans-serif, sans-serif"
        fontSize="14"
        fontWeight="700"
        textAnchor="middle"
      >
        Y
      </text>
      <text
        x="30"
        y="17.5"
        fill={YC_ORANGE}
        fontFamily="Helvetica, Arial, ui-sans-serif, sans-serif"
        fontSize="15.5"
        fontWeight="600"
        letterSpacing="-0.01em"
      >
        Combinator
      </text>
    </svg>
  )
}
