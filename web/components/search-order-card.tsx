"use client"

import { useState } from "react"
import Link from "next/link"
import {
  AlertTriangle,
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
import type { SearchOrder } from "@/lib/types"
import { formatScrapeInterval, timeAgo } from "@/lib/format"
import { cn } from "@/lib/utils"

interface SearchOrderCardProps {
  order: SearchOrder
  onDelete: (id: number) => Promise<void> | void
  onToggleActive: (order: SearchOrder, active: boolean) => Promise<void> | void
  onCheckNow: (order: SearchOrder) => Promise<void> | void
  isDeleting?: boolean
  isChecking?: boolean
}

const SOURCES: { key: "kleinanzeigen" | "ebay" | "mydealz"; icon: LucideIcon; label: string }[] = [
  { key: "kleinanzeigen", icon: Store, label: "Kleinanzeigen" },
  { key: "ebay", icon: ShoppingBag, label: "eBay" },
  { key: "mydealz", icon: Flame, label: "MyDealz" },
]

export function SearchOrderCard({
  order,
  onDelete,
  onToggleActive,
  onCheckNow,
  isDeleting,
  isChecking,
}: SearchOrderCardProps) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const interval =
    order.kleinanzeigen?.scrape_interval_minutes ??
    order.ebay?.scrape_interval_minutes ??
    order.mydealz?.scrape_interval_minutes ??
    null
  const totalFinds = order.ad_count + order.deal_count
  const sourceError = order.mydealz?.last_error ?? null
  // Der Name ist meist der Suchbegriff — die Begriff-Zeile nur zeigen, wenn sie etwas hinzufügt.
  const showQueryLine = !!order.query && order.query.trim() !== order.name.trim()

  return (
    <Card
      className={cn(
        "group relative h-full overflow-hidden py-0 shadow-sm",
        "transition-[border-color,box-shadow,transform] duration-200",
        "hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-md",
      )}
    >
      <Link
        href={`/searches/${order.id}`}
        className="absolute inset-0 z-10 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        aria-label={`Details für ${order.name}`}
        prefetch={false}
      />

      <CardContent className="pointer-events-none relative z-20 flex h-full flex-col gap-3 p-4 sm:p-5">
        {/* Kopfzeile: Quellen links, Aktionen rechts */}
        <div className="flex items-center justify-between gap-2">
          <div
            className={cn("flex flex-wrap gap-1.5", !order.is_active && "opacity-50")}
            aria-label="Quellen"
          >
            {SOURCES.filter((s) => order[s.key]).map((s) => (
              <span
                key={s.key}
                className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary/90 ring-1 ring-inset ring-primary/15"
              >
                <s.icon className="size-3" aria-hidden />
                {s.label}
              </span>
            ))}
          </div>

          <div className="pointer-events-auto flex shrink-0 items-center gap-0.5">
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                onCheckNow(order)
              }}
              disabled={isChecking || !order.is_active}
              className="size-8 cursor-pointer rounded-md text-muted-foreground hover:text-foreground"
              aria-label="Jetzt prüfen"
              title={order.is_active ? "Jetzt prüfen" : "Pausierte Suchaufträge werden nicht geprüft"}
            >
              <RefreshCw className={cn("size-4", isChecking && "animate-spin")} aria-hidden />
            </Button>
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

        {/* Titel + optionaler Suchbegriff */}
        <div className={cn("min-w-0", !order.is_active && "opacity-50")}>
          <h3
            className="line-clamp-2 text-pretty text-base font-semibold leading-snug text-foreground"
            title={order.name}
          >
            {order.name}
          </h3>
          {showQueryLine && (
            <p
              className="mt-1 flex min-w-0 items-center gap-1.5 truncate text-xs text-muted-foreground"
              title={order.query}
            >
              <Search className="size-3 shrink-0 opacity-55" aria-hidden />
              <span className="truncate">{`„${order.query}“`}</span>
            </p>
          )}
          {!order.query && (
            <p className="mt-1 text-xs text-muted-foreground">Alt-Suche über URL</p>
          )}
        </div>

        {sourceError && (
          <p
            className="flex items-start gap-1.5 text-xs leading-snug text-amber-600"
            title={sourceError}
          >
            <AlertTriangle className="mt-px size-3.5 shrink-0" aria-hidden />
            <span className="line-clamp-2">Letzte MyDealz-Prüfung fehlgeschlagen</span>
          </p>
        )}

        {/* Fußzeile: Kennzahlen links, Aktiv-Schalter rechts */}
        <div className="mt-auto flex items-center justify-between gap-3 border-t border-border/70 pt-3">
          <p
            className={cn(
              "flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-muted-foreground",
              !order.is_active && "opacity-60",
            )}
          >
            <span className="inline-flex items-center gap-1 font-medium text-foreground">
              <Package className="size-3.5 text-muted-foreground/75" aria-hidden />
              {totalFinds === 1 ? "1 Fund" : `${totalFinds} Funde`}
            </span>
            {order.is_active ? (
              <>
                <span aria-hidden>·</span>
                <span>{interval != null ? formatScrapeInterval(interval) : "—"}</span>
                <span aria-hidden>·</span>
                <span title="Zuletzt geprüft">{timeAgo(order.last_checked_at)}</span>
              </>
            ) : (
              <>
                <span aria-hidden>·</span>
                <span>pausiert</span>
              </>
            )}
          </p>
          <span
            className="pointer-events-auto inline-flex shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            <Switch
              checked={order.is_active}
              onCheckedChange={(checked) => onToggleActive(order, checked)}
              className="cursor-pointer"
              aria-label={order.is_active ? "Suchauftrag pausieren" : "Suchauftrag aktivieren"}
            />
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
