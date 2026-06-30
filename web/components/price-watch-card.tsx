"use client"

import { useState } from "react"
import Link from "next/link"
import {
  AlertTriangle,
  Clock,
  ExternalLink,
  Loader2,
  RefreshCw,
  Target,
  TrendingDown,
  TrendingUp,
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
import type { PriceWatch } from "@/lib/types"
import { formatPriceWithCurrency, formatScrapeInterval, timeAgo, truncateUrl } from "@/lib/format"
import { cn } from "@/lib/utils"

interface PriceWatchCardProps {
  watch: PriceWatch
  onDelete: (id: number) => Promise<void> | void
  isDeleting?: boolean
}

interface PriceTrend {
  percent: number
  down: boolean
}

/** Veränderung des aktuellen Preises gegenüber dem Startpreis. */
function computeTrend(watch: PriceWatch): PriceTrend | null {
  const { last_price, initial_price } = watch
  if (last_price == null || initial_price == null || initial_price === 0) return null
  if (last_price === initial_price) return null
  const percent = ((last_price - initial_price) / initial_price) * 100
  return { percent: Math.abs(percent), down: last_price < initial_price }
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

export function PriceWatchCard({ watch, onDelete, isDeleting }: PriceWatchCardProps) {
  const [open, setOpen] = useState(false)
  const trend = computeTrend(watch)
  const hasPrice = watch.last_price != null
  const thresholdReached =
    watch.notify_threshold != null && hasPrice && watch.last_price! <= watch.notify_threshold

  return (
    <Card className="group relative h-full min-h-[208px] overflow-hidden border-border/80 bg-card/95 py-0 shadow-sm transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-md">
      <Link
        href={`/price-alerts/${watch.id}`}
        className="absolute inset-0 z-10 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        aria-label={`Details für ${watch.name}`}
        prefetch={false}
      />

      <CardContent className="pointer-events-none relative z-20 flex h-full flex-col p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <SearchStatusBadge isActive={watch.is_active} className="mb-3" />
            <h3
              className="line-clamp-2 text-pretty text-base font-semibold leading-snug text-foreground"
              title={watch.name}
            >
              {watch.name}
            </h3>
            <p
              className="mt-1.5 flex min-w-0 items-center gap-1.5 truncate text-xs text-muted-foreground"
              title={watch.url}
            >
              <ExternalLink className="size-3 shrink-0 opacity-55" aria-hidden />
              <span className="truncate">{truncateUrl(watch.url, 42)}</span>
            </p>
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
                aria-label="Preis-Alarm löschen"
              >
                {isDeleting ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Trash2 className="size-4" aria-hidden />
                )}
              </Button>
              <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                <AlertDialogHeader>
                  <AlertDialogTitle>Preis-Alarm löschen?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Der Preis-Alarm &ldquo;{watch.name}&rdquo; und sein gesamter Preisverlauf werden
                    unwiderruflich gelöscht.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="cursor-pointer">Abbrechen</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(e) => {
                      e.preventDefault()
                      onDelete(watch.id)
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

        {/* Aktueller Preis + Trend */}
        <div className="mt-4 flex items-end justify-between gap-2">
          <div className="min-w-0">
            {watch.last_error && !hasPrice ? (
              <span className="flex items-center gap-1.5 text-sm font-medium text-amber-600">
                <AlertTriangle className="size-4 shrink-0" aria-hidden /> Preis nicht gefunden
              </span>
            ) : hasPrice ? (
              <span className="block text-2xl font-bold tabular-nums tracking-tight text-foreground">
                {formatPriceWithCurrency(watch.last_price, watch.currency)}
              </span>
            ) : (
              <span className="text-sm text-muted-foreground">Wird geprüft…</span>
            )}
            <span className="mt-0.5 block truncate text-xs text-muted-foreground">
              {watch.selected_label || "Beobachteter Preis"}
            </span>
          </div>
          {trend && (
            <span
              className={cn(
                "inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold tabular-nums",
                trend.down
                  ? "bg-emerald-500/15 text-emerald-600"
                  : "bg-red-500/15 text-red-600",
              )}
              title="Veränderung seit Beobachtungsbeginn"
            >
              {trend.down ? (
                <TrendingDown className="size-3.5" aria-hidden />
              ) : (
                <TrendingUp className="size-3.5" aria-hidden />
              )}
              {trend.down ? "−" : "+"}
              {trend.percent.toFixed(trend.percent < 10 ? 1 : 0)}%
            </span>
          )}
        </div>

        <div className="mt-auto grid grid-cols-1 gap-2 border-t border-border/70 pt-4 min-[380px]:grid-cols-2">
          <MetaItem
            icon={RefreshCw}
            label="Intervall"
            value={formatScrapeInterval(watch.scrape_interval_minutes)}
          />
          <MetaItem icon={Clock} label="Zuletzt geprüft" value={timeAgo(watch.last_checked_at)} />
          {watch.notify_threshold != null && (
            <div className="min-[380px]:col-span-2">
              <span
                className={cn(
                  "flex min-w-0 items-center gap-2 rounded-lg px-2.5 py-2",
                  thresholdReached ? "bg-emerald-500/10" : "bg-muted/45",
                )}
              >
                <Target
                  className={cn(
                    "size-3.5 shrink-0",
                    thresholdReached ? "text-emerald-600" : "text-muted-foreground/75",
                  )}
                  aria-hidden
                />
                <span className="min-w-0">
                  <span className="block text-[0.68rem] font-medium uppercase tracking-[0.1em] text-muted-foreground/70">
                    Zielpreis {thresholdReached ? "· erreicht" : ""}
                  </span>
                  <span
                    className={cn(
                      "block truncate text-xs font-medium",
                      thresholdReached ? "text-emerald-700" : "text-foreground",
                    )}
                  >
                    {formatPriceWithCurrency(watch.notify_threshold, watch.currency)}
                  </span>
                </span>
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
