import { cn } from "@/lib/utils"
import { formatScore, getScoreColor } from "@/lib/format"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface ScoreBadgeProps {
  score: number | null
  size?: "sm" | "md" | "lg"
}

function getScoreLabel(score: number): string {
  if (score >= 8) return "Top-Angebot"
  if (score >= 6) return "Guter Deal"
  return "Normaler Preis"
}

export function ScoreBadge({ score, size = "md" }: ScoreBadgeProps) {
  if (score === null || score === undefined) return null

  const sizeClasses = {
    sm: "size-8 text-sm",
    md: "size-9 text-sm",
    lg: "size-14 text-xl",
  }

  const badge = (
    <div
      className={cn(
        "inline-flex items-center justify-center rounded-full font-bold shrink-0",
        getScoreColor(score),
        sizeClasses[size],
      )}
      aria-label={`Score ${formatScore(score)} — ${getScoreLabel(score)}`}
    >
      <span>{formatScore(score)}</span>
    </div>
  )

  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          <p className="font-medium">{getScoreLabel(score)}</p>
          <p>Score: {formatScore(score)} / 10</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
