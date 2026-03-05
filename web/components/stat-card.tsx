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
    <Card className="flex flex-row items-center justify-between px-6 py-5 gap-4">
      <div className="flex flex-col gap-1 min-w-0">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className="text-2xl font-bold text-foreground tracking-tight">{value}</span>
      </div>
      <div className={cn("flex items-center justify-center size-10 rounded-full shrink-0", iconBgColor)}>
        <Icon className={cn("size-5", iconTextColor)} />
      </div>
    </Card>
  )
}
