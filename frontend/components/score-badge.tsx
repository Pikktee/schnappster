import { cn } from "@/lib/utils"
import { formatScore, getScoreColor } from "@/lib/format"

interface ScoreBadgeProps {
  score: number | null
  size?: "sm" | "md" | "lg"
}

export function ScoreBadge({ score, size = "md" }: ScoreBadgeProps) {
  if (score === null || score === undefined) return null

  const sizeClasses = {
    sm: "size-7 text-xs",
    md: "size-9 text-sm",
    lg: "size-14 text-xl",
  }

  return (
    <div
      className={cn(
        "inline-flex items-center justify-center rounded-full font-bold shrink-0",
        getScoreColor(score),
        sizeClasses[size],
      )}
    >
      {formatScore(score)}
    </div>
  )
}
