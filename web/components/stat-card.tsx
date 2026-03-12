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
    <Card className="group relative flex flex-row items-center justify-between px-6 py-5 gap-4 overflow-hidden">
      <div className="flex flex-col gap-1 min-w-0 relative z-10">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{label}</span>
        <span className="text-2xl font-semibold text-foreground tracking-tight">{value}</span>
      </div>
      <div className={cn("flex items-center justify-center size-12 rounded-xl shrink-0 ring-1 ring-black/5", iconBgColor)}>
        <Icon className={cn("size-6", iconTextColor)} />
      </div>
    </Card>
  )
}
