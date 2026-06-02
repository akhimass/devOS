import { cn } from "@/lib/utils"
import { YCombinatorWordmark } from "@/components/YCombinatorWordmark"

const LABEL_CLASS =
  "text-[10px] font-semibold uppercase leading-snug tracking-[0.18em] text-muted-foreground sm:text-xs sm:tracking-[0.22em]"

const PARTNERS = [
  { name: "Cekura", src: "/backed-by/cekura.svg", className: "h-5 sm:h-6" },
  { name: "Daily", src: "/backed-by/daily.svg", className: "h-4 sm:h-5" },
  { name: "NVIDIA", src: "/backed-by/nvidia.svg", className: "h-5 sm:h-6" },
  { name: "AWS", src: "/backed-by/aws.svg", className: "h-6 sm:h-7" },
  { name: "Twilio", src: "/backed-by/twilio.svg", className: "h-5 sm:h-6" },
] as const

export function BackedBy({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-5 sm:flex-row sm:justify-center sm:gap-8",
        className,
      )}
    >
      <p className="flex max-w-[18rem] shrink-0 flex-wrap items-center justify-center gap-x-1.5 gap-y-1.5 text-center sm:max-w-none sm:justify-start sm:text-left">
        <span className={LABEL_CLASS}>Built at</span>
        <span className="inline-flex items-center gap-1">
          <YCombinatorWordmark className="h-[18px] sm:h-5" />
          <span className={LABEL_CLASS}>Voice Agents Hackathon with</span>
        </span>
      </p>
      <ul className="flex flex-wrap items-center justify-center gap-x-8 gap-y-4 sm:gap-x-10">
        {PARTNERS.map(({ name, src, className: logoClass }) => (
          <li key={name}>
            <img
              src={src}
              alt={name}
              className={cn(
                "w-auto opacity-55 grayscale transition-opacity hover:opacity-80",
                logoClass,
              )}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}
