import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  iconBgColor: string
  iconTextColor: string
}

export function StatCard({ label, value, icon: Icon, iconBgColor, iconTextColor }: StatCardProps) {
  return (
    <Card className="group relative flex min-h-32 flex-row items-start justify-between gap-3 overflow-hidden px-5 py-5 sm:items-center sm:px-6">
      <div className="flex flex-col gap-1 min-w-0 relative z-10">
        <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">{label}</span>
        <span className="text-xl font-semibold leading-tight text-foreground tracking-tight sm:text-2xl break-words">
          {value}
        </span>
      </div>
      <div className={cn("flex size-11 shrink-0 items-center justify-center rounded-xl ring-1 ring-black/5 sm:size-12", iconBgColor)}>
        <Icon className={cn("size-6", iconTextColor)} />
      </div>
    </Card>
  )
}
