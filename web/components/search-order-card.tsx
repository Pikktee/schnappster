"use client"

import { useState } from "react"
import Link from "next/link"
import {
  Clock,
  Flame,
  Loader2,
  Package,
  RefreshCw,
  Search,
  ShoppingBag,
  Store,
  Trash2,
  type LucideIcon,
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { SearchStatusBadge } from "@/components/search-status-badge"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import type { SearchOrder } from "@/lib/types"
import { formatScrapeInterval, timeAgo } from "@/lib/format"
import { cn } from "@/lib/utils"

interface SearchOrderCardProps {
  order: SearchOrder
  onDelete: (id: number) => Promise<void> | void
  isDeleting?: boolean
}

function SourceBadge({
  icon: Icon,
  label,
  active,
}: {
  icon: LucideIcon
  label: string
  active: boolean
}) {
  if (!active) return null
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-border/70 bg-muted/50 px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
      <Icon className="size-3" aria-hidden />
      {label}
    </span>
  )
}

function MetaItem({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <span className="flex min-w-0 items-center gap-2 rounded-lg bg-muted/45 px-2.5 py-2">
      <Icon className="size-3.5 shrink-0 text-muted-foreground/75" aria-hidden />
      <span className="min-w-0">
        <span className="block text-[0.68rem] font-medium uppercase tracking-[0.1em] text-muted-foreground/70">
          {label}
        </span>
        <span className="block truncate text-xs font-medium text-foreground">{value}</span>
      </span>
    </span>
  )
}

export function SearchOrderCard({ order, onDelete, isDeleting }: SearchOrderCardProps) {
  const [open, setOpen] = useState(false)
  const interval =
    order.kleinanzeigen?.scrape_interval_minutes ??
    order.ebay?.scrape_interval_minutes ??
    order.mydealz?.scrape_interval_minutes ??
    null
  const totalFinds = order.ad_count + order.deal_count

  return (
    <Card className="group relative h-full min-h-[196px] overflow-hidden border-border/80 bg-card/95 py-0 shadow-sm transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-md">
      <Link
        href={`/searches/${order.id}`}
        className="absolute inset-0 z-10 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        aria-label={`Details für ${order.name}`}
        prefetch={false}
      />

      <CardContent className="pointer-events-none relative z-20 flex h-full flex-col p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <SearchStatusBadge isActive={order.is_active} className="mb-3" />
            <h3
              className="line-clamp-2 text-pretty text-base font-semibold leading-snug text-foreground"
              title={order.name}
            >
              {order.name}
            </h3>
            {order.query ? (
              <p
                className="mt-1.5 flex min-w-0 items-center gap-1.5 truncate text-xs text-muted-foreground"
                title={order.query}
              >
                <Search className="size-3 shrink-0 opacity-55" aria-hidden />
                <span className="truncate">{`„${order.query}“`}</span>
              </p>
            ) : (
              <p className="mt-1.5 text-xs text-muted-foreground">Alt-Suche über URL</p>
            )}
            <div className={cn("mt-2 flex flex-wrap gap-1.5")}>
              <SourceBadge icon={Store} label="Kleinanzeigen" active={!!order.kleinanzeigen} />
              <SourceBadge icon={ShoppingBag} label="eBay" active={!!order.ebay} />
              <SourceBadge icon={Flame} label="MyDealz" active={!!order.mydealz} />
            </div>
          </div>

          <div className="pointer-events-auto shrink-0">
            <AlertDialog open={open} onOpenChange={setOpen}>
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  setOpen(true)
                }}
                disabled={isDeleting}
                className="size-8 cursor-pointer rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive sm:size-9"
                aria-label="Suchauftrag löschen"
              >
                {isDeleting ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Trash2 className="size-4" aria-hidden />
                )}
              </Button>
              <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                <AlertDialogHeader>
                  <AlertDialogTitle>Suchauftrag löschen?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Der Suchauftrag &ldquo;{order.name}&rdquo; und alle darüber gefundenen
                    Angebote und Deals werden unwiderruflich gelöscht.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="cursor-pointer">Abbrechen</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(e) => {
                      e.preventDefault()
                      onDelete(order.id)
                      setOpen(false)
                    }}
                    className="cursor-pointer bg-destructive text-white hover:bg-destructive/90"
                  >
                    Löschen
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>

        <div className="mt-auto grid grid-cols-1 gap-2 border-t border-border/70 pt-4 min-[380px]:grid-cols-2">
          <MetaItem
            icon={Package}
            label="Funde"
            value={totalFinds === 1 ? "1 Fund" : `${totalFinds} Funde`}
          />
          <MetaItem
            icon={RefreshCw}
            label="Intervall"
            value={interval != null ? formatScrapeInterval(interval) : "—"}
          />
          <div className="min-[380px]:col-span-2">
            <MetaItem icon={Clock} label="Zuletzt geprüft" value={timeAgo(order.last_checked_at)} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
