"use client"

import { useState } from "react"
import Link from "next/link"
import {
  AlertTriangle,
  Check,
  Globe,
  Loader2,
  Target,
  TrendingDown,
  TrendingUp,
  Trash2,
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
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
import { formatPriceWithCurrency, formatScrapeInterval, timeAgo } from "@/lib/format"
import { cn } from "@/lib/utils"

interface PriceWatchCardProps {
  watch: PriceWatch
  onDelete: (id: number) => Promise<void> | void
  onToggleActive: (watch: PriceWatch, active: boolean) => Promise<void> | void
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

/** Fortschritt vom Startpreis Richtung Zielpreis (0–1), wenn sinnvoll berechenbar. */
function computeTargetProgress(watch: PriceWatch): number | null {
  const { last_price, initial_price, notify_threshold } = watch
  if (last_price == null || initial_price == null || notify_threshold == null) return null
  if (initial_price <= notify_threshold) return null // Ziel lag schon beim Start darunter
  const progress = (initial_price - last_price) / (initial_price - notify_threshold)
  return Math.min(1, Math.max(0, progress))
}

function hostOf(url: string): string | null {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return null
  }
}

export function PriceWatchCard({ watch, onDelete, onToggleActive, isDeleting }: PriceWatchCardProps) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [faviconFailed, setFaviconFailed] = useState(false)
  const trend = computeTrend(watch)
  const hasPrice = watch.last_price != null
  const thresholdReached =
    watch.notify_threshold != null && hasPrice && watch.last_price! <= watch.notify_threshold
  const targetProgress = computeTargetProgress(watch)
  const host = hostOf(watch.url)

  return (
    <Card
      className={cn(
        "group relative h-full overflow-hidden py-0 shadow-sm",
        "transition-[border-color,box-shadow,transform] duration-200",
        "hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-md",
      )}
    >
      <Link
        href={`/price-alerts/${watch.id}`}
        className="absolute inset-0 z-10 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        aria-label={`Details für ${watch.name}`}
        prefetch={false}
      />

      <CardContent className="pointer-events-none relative z-20 flex h-full flex-col gap-3 p-4 sm:p-5">
        {/* Kopfzeile: Shop links, Löschen rechts */}
        <div className="flex items-center justify-between gap-2">
          <span
            className={cn(
              "flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground",
              !watch.is_active && "opacity-50",
            )}
            title={watch.url}
          >
            {host && !faviconFailed ? (
              // eslint-disable-next-line @next/next/no-img-element -- externes Favicon, kein Next-Loader
              <img
                src={`https://www.google.com/s2/favicons?domain=${host}&sz=64`}
                alt=""
                loading="lazy"
                onError={() => setFaviconFailed(true)}
                className="size-4 shrink-0 rounded-sm"
              />
            ) : (
              <Globe className="size-3.5 shrink-0 opacity-55" aria-hidden />
            )}
            <span className="truncate">{host ?? watch.url}</span>
          </span>

          <div className="pointer-events-auto shrink-0">
            <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  setConfirmOpen(true)
                }}
                disabled={isDeleting}
                className="size-8 cursor-pointer rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
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
                      setConfirmOpen(false)
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

        {/* Titel */}
        <h3
          className={cn(
            "line-clamp-2 text-pretty text-base font-semibold leading-snug text-foreground",
            !watch.is_active && "opacity-50",
          )}
          title={watch.name}
        >
          {watch.name}
        </h3>

        {/* Aktueller Preis + Trend seit Beobachtungsbeginn */}
        <div className={cn("flex items-end justify-between gap-2", !watch.is_active && "opacity-50")}>
          <div className="min-w-0">
            {hasPrice ? (
              <span className="block text-2xl font-bold tabular-nums tracking-tight text-foreground">
                {formatPriceWithCurrency(watch.last_price, watch.currency)}
              </span>
            ) : watch.last_error ? (
              <span className="flex items-center gap-1.5 text-sm font-medium text-amber-600">
                <AlertTriangle className="size-4 shrink-0" aria-hidden /> Preis nicht gefunden
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
                trend.down ? "bg-emerald-500/15 text-emerald-600" : "bg-red-500/15 text-red-600",
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

        {/* Zielpreis: Fortschritt vom Startpreis Richtung Ziel */}
        {watch.notify_threshold != null && (
          <div className={cn("flex flex-col gap-1.5", !watch.is_active && "opacity-50")}>
            <div className="flex items-center justify-between gap-2 text-xs">
              <span
                className={cn(
                  "inline-flex items-center gap-1 font-medium",
                  thresholdReached ? "text-emerald-600" : "text-muted-foreground",
                )}
              >
                {thresholdReached ? (
                  <Check className="size-3.5" aria-hidden />
                ) : (
                  <Target className="size-3.5" aria-hidden />
                )}
                Zielpreis {formatPriceWithCurrency(watch.notify_threshold, watch.currency)}
              </span>
              {thresholdReached && (
                <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-semibold text-emerald-600">
                  erreicht
                </span>
              )}
            </div>
            {targetProgress != null && !thresholdReached && (
              <div
                className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
                role="progressbar"
                aria-valuenow={Math.round(targetProgress * 100)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Fortschritt zum Zielpreis"
                title={`${Math.round(targetProgress * 100)} % des Wegs zum Zielpreis`}
              >
                <div
                  className="h-full rounded-full bg-emerald-500/70 transition-[width] duration-500"
                  style={{ width: `${Math.max(4, Math.round(targetProgress * 100))}%` }}
                />
              </div>
            )}
          </div>
        )}

        {/* Fußzeile: Prüf-Rhythmus links, Aktiv-Schalter rechts */}
        <div className="mt-auto flex items-center justify-between gap-3 border-t border-border/70 pt-3">
          <p
            className={cn(
              "flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-muted-foreground",
              !watch.is_active && "opacity-60",
            )}
          >
            {watch.is_active ? (
              <>
                <span>{formatScrapeInterval(watch.scrape_interval_minutes)}</span>
                <span aria-hidden>·</span>
                <span title="Zuletzt geprüft">{timeAgo(watch.last_checked_at)}</span>
              </>
            ) : (
              <span>pausiert</span>
            )}
            {watch.last_error && hasPrice && (
              <span className="inline-flex" title={`Letzte Prüfung fehlgeschlagen: ${watch.last_error}`}>
                <AlertTriangle
                  className="size-3.5 shrink-0 text-amber-500"
                  aria-label="Letzte Prüfung fehlgeschlagen"
                />
              </span>
            )}
          </p>
          <span
            className="pointer-events-auto inline-flex shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            <Switch
              checked={watch.is_active}
              onCheckedChange={(checked) => onToggleActive(watch, checked)}
              className="cursor-pointer"
              aria-label={watch.is_active ? "Preis-Alarm pausieren" : "Preis-Alarm aktivieren"}
            />
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
