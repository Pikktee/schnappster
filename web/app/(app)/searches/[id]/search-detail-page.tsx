"use client"

import { useCallback, useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import {
  AlertTriangle,
  ArrowLeft,
  Flame,
  Loader2,
  Pencil,
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
import { Label } from "@/components/ui/label"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { SearchStatusBadge } from "@/components/search-status-badge"
import { SearchOrderForm } from "@/components/search-order-form"
import { ResultStream } from "@/components/result-stream"
import { ContentReveal } from "@/components/content-reveal"
import {
  checkSearchOrderNow,
  deleteSearchOrder,
  fetchSearchOrder,
  updateSearchOrder,
} from "@/lib/api"
import type { SearchOrder, SearchOrderCreate } from "@/lib/types"
import { formatDealAlarmThreshold, formatPrice, formatScrapeInterval, timeAgo } from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { usePageHead } from "../../page-head-context"

/** Eine Zeile der Quellen-Übersicht: Icon, Name, Konfiguration, Fundzahl, optionaler Fehler. */
function SourceRow({
  icon: Icon,
  label,
  config,
  count,
  countLabel,
  error,
}: {
  icon: LucideIcon
  label: string
  config: string
  count: number
  countLabel: [string, string]
  error?: string | null
}) {
  return (
    <li className="flex items-center gap-3 px-4 py-3 sm:px-5">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="size-4" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="truncate text-xs text-muted-foreground" title={config}>
          {config}
        </p>
        {error && (
          <p className="mt-0.5 flex items-start gap-1 text-xs text-amber-600" title={error}>
            <AlertTriangle className="mt-px size-3 shrink-0" aria-hidden />
            <span className="line-clamp-2">Letzte Prüfung fehlgeschlagen: {error}</span>
          </p>
        )}
      </div>
      <p className="shrink-0 text-right">
        <span className="block text-sm font-semibold tabular-nums text-foreground">{count}</span>
        <span className="block text-[11px] text-muted-foreground">
          {count === 1 ? countLabel[0] : countLabel[1]}
        </span>
      </p>
    </li>
  )
}

/** Baut die Konfigurations-Kurzbeschreibung einer Gebraucht-Quelle ("50 € – 400 € · PLZ …"). */
function usedConfigLine(
  child: { min_price: number | null; max_price: number | null },
  location: string,
): string {
  const hasRange = child.min_price != null || child.max_price != null
  const range = hasRange
    ? `${child.min_price != null ? formatPrice(child.min_price) : "0 €"} – ${
        child.max_price != null ? formatPrice(child.max_price) : "beliebig"
      }`
    : "Preis beliebig"
  return `${range} · ${location}`
}

export function SearchDetailPage() {
  const router = useRouter()
  const pathname = usePathname()
  const { setTitle, setTitleSuffix } = usePageHead()
  const [id, setId] = useState<number>(NaN)

  const [order, setOrder] = useState<SearchOrder | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [isChecking, setIsChecking] = useState(false)
  const [streamEpoch, setStreamEpoch] = useState(0)

  useEffect(() => {
    const match = window.location.pathname.match(/\/(\d+)\/?$/)
    if (match) setId(Number(match[1]))
  }, [pathname])

  const load = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (Number.isNaN(id)) return
      if (!opts?.silent) {
        setLoading(true)
        setError(null)
      }
      try {
        setOrder(await fetchSearchOrder(id))
      } catch (e) {
        if (!opts?.silent) {
          setError(e instanceof Error ? e.message : "Suchauftrag konnte nicht geladen werden.")
          setOrder(null)
        }
      } finally {
        setLoading(false)
      }
    },
    [id],
  )

  useEffect(() => {
    load()
  }, [load])

  useRefetchOnFocus(() => load({ silent: true }))

  useEffect(() => {
    if (order) {
      setTitle(order.name)
      setTitleSuffix(<SearchStatusBadge isActive={order.is_active} />)
    }
    return () => setTitleSuffix(null)
  }, [order, setTitle, setTitleSuffix])

  async function handleToggleActive() {
    if (!order) return
    setIsToggling(true)
    try {
      const updated = await updateSearchOrder(id, { is_active: !order.is_active })
      setOrder(updated)
      toast.success(updated.is_active ? "Suchauftrag aktiviert" : "Suchauftrag pausiert")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Aktualisierung fehlgeschlagen.")
    } finally {
      setIsToggling(false)
    }
  }

  async function handleCheckNow() {
    setIsChecking(true)
    try {
      setOrder(await checkSearchOrderNow(id))
      toast.success("Prüfung angestoßen — neue Ergebnisse erscheinen gleich im Stream.")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Prüfung fehlgeschlagen.")
    } finally {
      setIsChecking(false)
    }
  }

  async function handleUpdate(data: SearchOrderCreate) {
    setIsSaving(true)
    try {
      const updated = await updateSearchOrder(id, data)
      setOrder(updated)
      setIsEditOpen(false)
      setStreamEpoch((n) => n + 1) // Quellen können sich geändert haben → Stream neu laden
      toast.success("Suchauftrag aktualisiert")
    } finally {
      setIsSaving(false)
    }
  }

  async function handleDelete() {
    setIsDeleting(true)
    try {
      await deleteSearchOrder(id)
      toast.success("Suchauftrag gelöscht")
      router.push("/searches")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Löschen fehlgeschlagen.")
      setIsDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-36" />
        <Skeleton className="h-72" />
      </div>
    )
  }

  if (error || !order) {
    return (
      <ContentReveal className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-muted-foreground">{error || "Suchauftrag nicht gefunden."}</p>
        <Button variant="outline" onClick={() => router.push("/searches")} className="cursor-pointer">
          Zurück zur Übersicht
        </Button>
      </ContentReveal>
    )
  }

  const interval =
    order.kleinanzeigen?.scrape_interval_minutes ??
    order.ebay?.scrape_interval_minutes ??
    order.mydealz?.scrape_interval_minutes ??
    null
  const lastError = order.mydealz?.last_error
  const kaLocation = order.kleinanzeigen?.postal_code
    ? `PLZ ${order.kleinanzeigen.postal_code}${
        order.kleinanzeigen.radius_km ? ` (${order.kleinanzeigen.radius_km} km)` : ""
      }`
    : "deutschlandweit"
  const mydealzConfig = order.mydealz
    ? [
        order.mydealz.max_price != null ? `bis ${formatPrice(order.mydealz.max_price)}` : null,
        formatDealAlarmThreshold(order.mydealz),
      ]
        .filter(Boolean)
        .join(" · ")
    : ""
  // Der Suchbegriff steht meist schon als Titel im Seitenkopf — nur zeigen, wenn er abweicht.
  const showQueryLine = !order.query || order.query.trim() !== order.name.trim()

  return (
    <ContentReveal className="flex flex-col gap-6">
      {/* Kopfzeile */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => router.push("/searches")}
          className="cursor-pointer"
          aria-label="Zurück"
        >
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex flex-1 flex-wrap items-center justify-end gap-3">
          <div className="mr-1 flex items-center gap-2">
            <Switch
              id="active-toggle"
              checked={order.is_active}
              onCheckedChange={handleToggleActive}
              disabled={isToggling}
              className="data-[state=checked]:border-primary data-[state=checked]:bg-primary"
            />
            <Label htmlFor="active-toggle" className="cursor-pointer text-sm">
              {order.is_active ? "Läuft" : "Pausiert"}
            </Label>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCheckNow}
            disabled={isChecking}
            className="cursor-pointer"
          >
            {isChecking ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <RefreshCw className="size-3.5" />
            )}
            Jetzt prüfen
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsEditOpen(true)}
            className="cursor-pointer"
          >
            <Pencil className="size-3.5" />
            Bearbeiten
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                disabled={isDeleting}
                className="cursor-pointer text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                aria-label="Suchauftrag löschen"
                title="Suchauftrag löschen"
              >
                {isDeleting ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4" />
                )}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Suchauftrag löschen?</AlertDialogTitle>
                <AlertDialogDescription>
                  Der Suchauftrag &ldquo;{order.name}&rdquo; und alle darüber gefundenen Angebote
                  und Deals werden unwiderruflich gelöscht.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel className="cursor-pointer">Abbrechen</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  className="cursor-pointer bg-destructive text-white hover:bg-destructive/90"
                >
                  Löschen
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Übersicht: eine Zeile pro Quelle + Prüf-Rhythmus in der Fußzeile */}
      <Card className="border-border/80 bg-card/95 py-0 shadow-sm">
        <CardContent className="p-0">
          {showQueryLine && (
            <p className="flex items-center gap-2 border-b border-border/70 px-4 py-3 text-sm text-muted-foreground sm:px-5">
              <Search className="size-3.5 shrink-0 opacity-60" aria-hidden />
              {order.query ? (
                <span className="truncate" title={order.query}>
                  Sucht nach {`„${order.query}“`}
                </span>
              ) : (
                <span>Alt-Suche über Kleinanzeigen-URL</span>
              )}
            </p>
          )}
          <ul className="m-0 flex list-none flex-col divide-y divide-border/70 p-0">
            {order.kleinanzeigen && (
              <SourceRow
                icon={Store}
                label="Kleinanzeigen"
                config={usedConfigLine(order.kleinanzeigen, kaLocation)}
                count={order.kleinanzeigen.ad_count ?? 0}
                countLabel={["Fund", "Funde"]}
              />
            )}
            {order.ebay && (
              <SourceRow
                icon={ShoppingBag}
                label="eBay"
                config={usedConfigLine(order.ebay, "bundesweit")}
                count={order.ebay.ad_count ?? 0}
                countLabel={["Fund", "Funde"]}
              />
            )}
            {order.mydealz && (
              <SourceRow
                icon={Flame}
                label="MyDealz"
                config={mydealzConfig}
                count={order.deal_count}
                countLabel={["Deal", "Deals"]}
                error={lastError}
              />
            )}
          </ul>
          <p className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 border-t border-border/70 px-4 py-3 text-xs text-muted-foreground sm:px-5">
            <RefreshCw className="size-3 opacity-60" aria-hidden />
            <span>{interval != null ? `Geprüft ${formatScrapeInterval(interval)}` : "—"}</span>
            <span aria-hidden>·</span>
            <span>zuletzt {timeAgo(order.last_checked_at)}</span>
          </p>
        </CardContent>
      </Card>

      {/* Ergebnisse aller Quellen, chronologisch gemischt */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Ergebnisse
        </h2>
        <ResultStream key={streamEpoch} searchOrderId={id} />
      </div>

      {/* Bearbeiten */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent
          className="max-h-[calc(100dvh-2rem)] overflow-y-auto overscroll-y-contain sm:max-w-xl"
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>Suchauftrag bearbeiten</DialogTitle>
          </DialogHeader>
          <SearchOrderForm
            initial={order}
            onSubmit={handleUpdate}
            onCancel={() => setIsEditOpen(false)}
            isLoading={isSaving}
          />
        </DialogContent>
      </Dialog>
    </ContentReveal>
  )
}
