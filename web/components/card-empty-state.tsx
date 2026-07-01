import Link from "next/link"
import type { LucideIcon } from "lucide-react"

interface CardEmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  actionLabel: string
  actionHref: string
}

/** Einheitlicher Leerzustand für die Dashboard-Karten (gleiche Struktur für alle Bereiche). */
export function CardEmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  actionHref,
}: CardEmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 py-12 text-center">
      <Icon className="mb-1 size-10 text-muted-foreground/40" aria-hidden />
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="max-w-xs text-xs text-muted-foreground">{description}</p>
      <Link
        href={actionHref}
        className="mt-1 text-sm font-medium text-primary underline-offset-4 hover:underline"
      >
        {actionLabel}
      </Link>
    </div>
  )
}
