import { type ReactNode } from "react"
import { PackageOpen } from "lucide-react"
import { Button } from "@/components/ui/button"

interface EmptyStateProps {
  message: string
  actionLabel?: string
  onAction?: () => void
  icon?: ReactNode
}

export function EmptyState({ message, actionLabel, onAction, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
      {icon ?? <PackageOpen className="size-12 text-muted-foreground/50" />}
      <p className="text-muted-foreground text-sm max-w-sm">{message}</p>
      {actionLabel && onAction && (
        <Button onClick={onAction} className="cursor-pointer">
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
