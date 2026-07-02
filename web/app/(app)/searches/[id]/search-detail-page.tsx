"use client"

import { useCallback, useEffect, useState, type ReactNode } from "react"
import { usePathname, useRouter } from "next/navigation"
import {
  AlertTriangle,
  ArrowLeft,
  Clock,
  Euro,
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
import { cn } from "@/lib/utils"
import { usePageHead } from "../../page-head-context"

function DetailField({
  icon: Icon,
  label,
  children,
  className,
}: {
  icon: LucideIcon
  label: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn("rounded-xl border border-border/70 bg-muted/30 p-4", className)}>
      <div className="mb-2 flex items-center gap-2">
        <Icon className="size-3.5 text-muted-foreground" aria-hidden />
        <span className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
          {label}
        </span>
      </div>
      <div className="min-w-0 text-sm font-medium leading-relaxed text-foreground">{children}</div>
    </div>
  )
}

function SourcePill({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background px-2.5 py-1 text-xs font-medium text-foreground">
      <Icon className="size-3.5 text-primary" aria-hidden />
      {label}
    </span>
  )
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
  const anyAd = order.kleinanzeigen ?? order.ebay
  const usedRange =
    anyAd && (anyAd.min_price != null || anyAd.max_price != null)
      ? `${anyAd.min_price != null ? formatPrice(anyAd.min_price) : "0 €"} – ${
          anyAd.max_price != null ? formatPrice(anyAd.max_price) : "beliebig"
        }`
      : "beliebig"
  const lastError = order.mydealz?.last_error

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
              <Button variant="destructive" size="sm" disabled={isDeleting} className="cursor-pointer">
                {isDeleting ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Trash2 className="size-3.5" />
                )}
                Löschen
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

      {lastError && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-500" aria-hidden />
          <span>Bei der letzten MyDealz-Prüfung gab es ein Problem: {lastError}</span>
        </div>
      )}

      {/* Übersicht */}
      <Card className="border-border/80 bg-card/95 py-0 shadow-sm">
        <CardContent className="grid grid-cols-1 gap-3 p-4 sm:p-5 md:grid-cols-2 lg:grid-cols-4">
          <DetailField icon={Search} label="Suchbegriff" className="md:col-span-2">
            <div className="flex flex-wrap items-center gap-2">
              <span>{order.query ? `„${order.query}“` : "Alt-Suche über URL"}</span>
              <span className="flex flex-wrap gap-1.5">
                {order.kleinanzeigen && <SourcePill icon={Store} label="Kleinanzeigen" />}
                {order.ebay && <SourcePill icon={ShoppingBag} label="eBay" />}
                {order.mydealz && <SourcePill icon={Flame} label="MyDealz" />}
              </span>
            </div>
          </DetailField>
          <DetailField icon={Euro} label="Gebraucht-Preis">
            {anyAd ? usedRange : "—"}
          </DetailField>
          <DetailField icon={Flame} label="MyDealz-Alarm">
            {order.mydealz
              ? [
                  formatDealAlarmThreshold(order.mydealz),
                  order.mydealz.max_price != null
                    ? `bis ${formatPrice(order.mydealz.max_price)}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(" · ")
              : "—"}
          </DetailField>
          <DetailField icon={RefreshCw} label="Intervall" className="md:col-span-2">
            {interval != null ? formatScrapeInterval(interval) : "—"}
          </DetailField>
          <DetailField icon={Clock} label="Zuletzt geprüft" className="md:col-span-2">
            {timeAgo(order.last_checked_at)}
          </DetailField>
        </CardContent>
      </Card>

      {/* Ergebnisse aller Quellen, chronologisch gemischt */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Ergebnisse ({order.ad_count + order.deal_count})
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
