import { cn } from "@/lib/utils"

interface SearchStatusBadgeProps {
  isActive: boolean
  className?: string
}

export function SearchStatusBadge({ isActive, className }: SearchStatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        isActive
          ? "border-primary/25 bg-primary/10 text-accent-foreground"
          : "border-border bg-muted/70 text-muted-foreground",
        className
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full",
          isActive ? "bg-primary" : "bg-muted-foreground/50"
        )}
        aria-hidden
      />
      {isActive ? "Läuft" : "Pausiert"}
    </span>
  )
}
