"use client"

import { useState } from "react"
import Link from "next/link"
import { Bell, Loader2, MapPin, MoreVertical, RefreshCw, Trash2 } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
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
import type { GiftWatch } from "@/lib/types"
import { formatScrapeInterval, timeAgo } from "@/lib/format"
import { cn } from "@/lib/utils"

interface GiftWatchCardProps {
  watch: GiftWatch
  onDelete: (id: number) => Promise<void> | void
  onToggleActive: (watch: GiftWatch, active: boolean) => Promise<void> | void
  onCheckNow: (watch: GiftWatch) => Promise<void> | void
  isDeleting?: boolean
  isChecking?: boolean
}

export function GiftWatchCard({
  watch,
  onDelete,
  onToggleActive,
  onCheckNow,
  isDeleting,
  isChecking,
}: GiftWatchCardProps) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const busy = isDeleting || isChecking

  return (
    <Card
      className={cn(
        "group relative h-full overflow-hidden py-0 shadow-sm",
        "transition-[border-color,box-shadow,transform] duration-200",
        "hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-md",
      )}
    >
      <Link
        href={`/fundgrube/${watch.id}`}
        className="absolute inset-0 z-10 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        aria-label={`Details für ${watch.name}`}
        prefetch={false}
      />

      <CardContent className="pointer-events-none relative z-20 flex h-full flex-col gap-3 p-4 sm:p-5">
        {/* Kopfzeile: Standort links, Menü rechts */}
        <div className="flex items-center justify-between gap-2">
          <span
            className={cn(
              "flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground",
              !watch.is_active && "opacity-50",
            )}
          >
            <MapPin className="size-3.5 shrink-0 opacity-60" aria-hidden />
            <span className="truncate">
              {watch.postal_code} · {watch.radius_km} km
            </span>
          </span>

          <div
            className="pointer-events-auto shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                  }}
                  disabled={busy}
                  className="size-8 cursor-pointer rounded-md text-muted-foreground hover:text-foreground"
                  aria-label="Aktionen"
                >
                  {busy ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <MoreVertical className="size-4" aria-hidden />
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-44">
                <DropdownMenuItem
                  disabled={!watch.is_active || isChecking}
                  onSelect={() => onCheckNow(watch)}
                  className="cursor-pointer"
                >
                  <RefreshCw aria-hidden />
                  Jetzt prüfen
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  variant="destructive"
                  onSelect={() => setConfirmOpen(true)}
                  className="cursor-pointer"
                >
                  <Trash2 aria-hidden />
                  Löschen
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
              <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                <AlertDialogHeader>
                  <AlertDialogTitle>Fundgrube löschen?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Die Fundgrube &ldquo;{watch.name}&rdquo; und alle darüber gefundenen Angebote
                    werden unwiderruflich gelöscht.
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

        {/* Funde-Zahl + Benachrichtigungs-Schwelle */}
        <div className={cn("flex items-end justify-between gap-2", !watch.is_active && "opacity-50")}>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-bold tabular-nums tracking-tight text-foreground">
              {watch.ad_count}
            </span>
            <span className="text-sm text-muted-foreground">
              {watch.ad_count === 1 ? "Fund" : "Funde"}
            </span>
          </div>
          <span
            className="inline-flex shrink-0 items-center gap-1 rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary/90 ring-1 ring-inset ring-primary/15"
            title="Benachrichtigung ab diesem Abhol-Lohn"
          >
            <Bell className="size-3" aria-hidden />
            ab Score {watch.min_score_notify}
          </span>
        </div>

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
                <span title="Zuletzt geprüft">{timeAgo(watch.last_scraped_at)}</span>
              </>
            ) : (
              <span>pausiert</span>
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
              aria-label={watch.is_active ? "Fundgrube pausieren" : "Fundgrube aktivieren"}
            />
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
