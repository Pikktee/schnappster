"use client"

import Link from "next/link"
import { ArrowRight, TrendingDown, TrendingUp } from "lucide-react"
import { Card } from "@/components/ui/card"
import type { FeedPriceEvent } from "@/lib/types"
import { formatPriceWithCurrency, timeAgo } from "@/lib/format"
import { cn } from "@/lib/utils"

/** Kompakte Stream-Karte für eine Preisänderung eines Preis-Alarms. */
export function PriceEventCard({ event }: { event: FeedPriceEvent }) {
  const prev = event.previous_price
  const dropped = prev != null && event.price < prev
  const rose = prev != null && event.price > prev
  const percent =
    prev != null && prev > 0 ? Math.round(((event.price - prev) / prev) * 100) : null

  return (
    <Card className="group relative flex h-full flex-col gap-3 p-4 transition-shadow hover:shadow-md">
      <Link
        href={`/price-alerts/${event.watch_id}`}
        className="absolute inset-0 z-10 rounded-xl"
        aria-label={`Preis-Alarm ${event.watch_name} öffnen`}
        prefetch={false}
      />

      <div className="flex items-center justify-between gap-2">
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold",
            dropped
              ? "bg-emerald-500/15 text-emerald-600"
              : rose
                ? "bg-red-500/15 text-red-600"
                : "bg-muted text-muted-foreground",
          )}
        >
          {dropped ? (
            <TrendingDown className="size-3.5" aria-hidden />
          ) : (
            <TrendingUp className="size-3.5" aria-hidden />
          )}
          {dropped ? "Preis gefallen" : rose ? "Preis gestiegen" : "Preis erfasst"}
          {percent != null && percent !== 0 && (
            <span className="tabular-nums">
              {percent > 0 ? "+" : ""}
              {percent}%
            </span>
          )}
        </span>
        <span className="text-[11px] text-muted-foreground">{timeAgo(event.recorded_at)}</span>
      </div>

      <h3
        className="line-clamp-2 text-sm font-medium leading-snug text-foreground"
        title={event.watch_name}
      >
        {event.watch_name}
      </h3>

      {/* Alt → Neu direkt unter dem Titel; Leerraum fällt ans Karten-Ende */}
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm">
        {prev != null && (
          <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="line-through">{formatPriceWithCurrency(prev, event.currency)}</span>
            <ArrowRight className="size-3 opacity-50" aria-hidden />
          </span>
        )}
        <span
          className={cn(
            "text-base font-bold tabular-nums",
            dropped ? "text-emerald-600" : "text-foreground",
          )}
        >
          {formatPriceWithCurrency(event.price, event.currency)}
        </span>
      </div>

      <span className="mt-auto text-[11px] uppercase tracking-wide text-muted-foreground/70">
        Preis-Alarm
      </span>
    </Card>
  )
}
