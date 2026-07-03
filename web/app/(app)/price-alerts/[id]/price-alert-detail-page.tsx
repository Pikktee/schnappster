"use client"

import { useCallback, useEffect, useState, type ReactNode } from "react"
import { usePathname, useRouter } from "next/navigation"
import {
  AlertTriangle,
  ArrowLeft,
  Clock,
  ExternalLink as ExternalLinkIcon,
  Loader2,
  Pencil,
  RefreshCw,
  Tag,
  Target,
  Trash2,
  TrendingDown,
  TrendingUp,
  type LucideIcon,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
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
import { SearchStatusBadge } from "@/components/search-status-badge"
import { ExternalLink } from "@/components/external-link"
import { PriceHistoryChart } from "@/components/price-history-chart"
import {
  checkPriceWatchNow,
  deletePriceWatch,
  fetchPriceHistory,
  fetchPriceWatch,
  updatePriceWatch,
} from "@/lib/api"
import type { PricePoint, PriceWatch } from "@/lib/types"
import { formatPriceWithCurrency, formatScrapeInterval, timeAgo, truncateUrl } from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { ContentReveal } from "@/components/content-reveal"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { cn } from "@/lib/utils"
import { usePageHead } from "../../page-head-context"

const INTERVAL_PRESETS = [
  { label: "30 Min", value: 30 },
  { label: "1 Std", value: 60 },
  { label: "6 Std", value: 360 },
  { label: "12 Std", value: 720 },
  { label: "Täglich", value: 1440 },
]

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

export function PriceAlertDetailPage() {
  const router = useRouter()
  const pathname = usePathname()
  const { setTitle, setTitleSuffix } = usePageHead()
  const [id, setId] = useState<number>(NaN)

  const [watch, setWatch] = useState<PriceWatch | null>(null)
  const [history, setHistory] = useState<PricePoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [isChecking, setIsChecking] = useState(false)

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
        const [w, h] = await Promise.all([fetchPriceWatch(id), fetchPriceHistory(id)])
        setWatch(w)
        setHistory(h)
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Daten konnten nicht geladen werden."
        if (!opts?.silent) {
          setError(msg)
          setWatch(null)
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
    if (watch) {
      setTitle(watch.name)
      setTitleSuffix(<SearchStatusBadge isActive={watch.is_active} />)
    }
    return () => setTitleSuffix(null)
  }, [watch, setTitle, setTitleSuffix])

  async function handleToggleActive() {
    if (!watch) return
    setIsToggling(true)
    try {
      const updated = await updatePriceWatch(id, { is_active: !watch.is_active })
      setWatch(updated)
      toast.success(updated.is_active ? "Preis-Alarm aktiviert" : "Preis-Alarm pausiert")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Aktualisierung fehlgeschlagen.")
    } finally {
      setIsToggling(false)
    }
  }

  async function handleCheckNow() {
    setIsChecking(true)
    try {
      const updated = await checkPriceWatchNow(id)
      setWatch(updated)
      setHistory(await fetchPriceHistory(id))
      toast.success(
        updated.last_error
          ? "Geprüft — aber kein Preis gefunden."
          : `Geprüft — aktueller Preis: ${formatPriceWithCurrency(updated.last_price, updated.currency)}`,
      )
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Prüfung fehlgeschlagen.")
    } finally {
      setIsChecking(false)
    }
  }

  async function handleDelete() {
    setIsDeleting(true)
    try {
      await deletePriceWatch(id)
      toast.success("Preis-Alarm gelöscht")
      router.push("/price-alerts")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Löschen fehlgeschlagen.")
      setIsDeleting(false)
    }
  }

  async function handleEditSubmit(data: Partial<PriceWatch>) {
    const updated = await updatePriceWatch(id, data)
    setWatch(updated)
    setIsEditOpen(false)
    toast.success("Preis-Alarm aktualisiert")
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

  if (error || !watch) {
    return (
      <ContentReveal className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-muted-foreground">{error || "Preis-Alarm nicht gefunden."}</p>
        <Button
          variant="outline"
          onClick={() => router.push("/price-alerts")}
          className="cursor-pointer"
        >
          Zurück zur Übersicht
        </Button>
      </ContentReveal>
    )
  }

  const trend = priceTrend(watch)
  const prices = history.map((p) => p.price)
  const low = prices.length ? Math.min(...prices) : watch.last_price
  const high = prices.length ? Math.max(...prices) : watch.last_price

  return (
    <ContentReveal className="flex flex-col gap-6">
      {/* Kopfzeile */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => router.push("/price-alerts")}
          className="cursor-pointer"
          aria-label="Zurück"
        >
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex flex-1 flex-wrap items-center justify-end gap-3">
          <div className="mr-1 flex items-center gap-2">
            <Switch
              id="active-toggle"
              checked={watch.is_active}
              onCheckedChange={handleToggleActive}
              disabled={isToggling}
              className="data-[state=checked]:border-primary data-[state=checked]:bg-primary"
            />
            <Label htmlFor="active-toggle" className="cursor-pointer text-sm">
              {watch.is_active ? "Läuft" : "Pausiert"}
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
                <AlertDialogTitle>Preis-Alarm löschen?</AlertDialogTitle>
                <AlertDialogDescription>
                  Der Preis-Alarm &ldquo;{watch.name}&rdquo; und sein gesamter Preisverlauf werden
                  unwiderruflich gelöscht.
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

      {watch.last_error && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-500" aria-hidden />
          <span>
            Bei der letzten Prüfung konnte kein Preis gefunden werden ({watch.last_error}). Die Seite
            hat sich evtl. geändert — lege den Alarm bei Bedarf neu an.
          </span>
        </div>
      )}

      {/* Preis-Hero + Details */}
      <Card className="border-border/80 bg-card/95 py-0 shadow-sm">
        <CardContent className="p-4 sm:p-5">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/70 pb-5">
            <div>
              <span className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
                {watch.selected_label || "Beobachteter Preis"}
              </span>
              <div className="mt-1 flex items-center gap-3">
                <span className="text-3xl font-bold tabular-nums tracking-tight text-foreground">
                  {watch.last_price != null
                    ? formatPriceWithCurrency(watch.last_price, watch.currency)
                    : "—"}
                </span>
                {trend && (
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold tabular-nums",
                      trend.down ? "bg-emerald-500/15 text-emerald-600" : "bg-red-500/15 text-red-600",
                    )}
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
            </div>
            {watch.initial_price != null && (
              <span className="text-sm text-muted-foreground">
                Startpreis:{" "}
                <span className="font-medium tabular-nums text-foreground">
                  {formatPriceWithCurrency(watch.initial_price, watch.currency)}
                </span>
              </span>
            )}
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            <DetailField icon={ExternalLinkIcon} label="URL" className="md:col-span-2 lg:col-span-3">
              <ExternalLink href={watch.url} className="break-all text-sm">
                {truncateUrl(watch.url, 96)}
              </ExternalLink>
            </DetailField>
            <DetailField icon={RefreshCw} label="Intervall">
              {formatScrapeInterval(watch.scrape_interval_minutes)}
            </DetailField>
            <DetailField icon={Target} label="Zielpreis">
              {watch.notify_threshold != null
                ? formatPriceWithCurrency(watch.notify_threshold, watch.currency)
                : "Bei jeder Senkung"}
            </DetailField>
            <DetailField icon={Clock} label="Zuletzt geprüft">
              {timeAgo(watch.last_checked_at)}
            </DetailField>
          </div>
        </CardContent>
      </Card>

      {/* Preisverlauf */}
      <Card className="border-border/80 bg-card/95 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Tag className="size-4 text-muted-foreground" aria-hidden />
            Preisverlauf
          </CardTitle>
          {low != null && high != null && (
            <div className="flex gap-4 text-xs text-muted-foreground">
              <span>
                Tief{" "}
                <span className="font-semibold tabular-nums text-emerald-600">
                  {formatPriceWithCurrency(low, watch.currency)}
                </span>
              </span>
              <span>
                Hoch{" "}
                <span className="font-semibold tabular-nums text-foreground">
                  {formatPriceWithCurrency(high, watch.currency)}
                </span>
              </span>
            </div>
          )}
        </CardHeader>
        <CardContent>
          <PriceHistoryChart
            points={history}
            currency={watch.currency}
            threshold={watch.notify_threshold}
          />
        </CardContent>
      </Card>

      <Sheet open={isEditOpen} onOpenChange={setIsEditOpen}>
        <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
          <SheetHeader className="shrink-0 space-y-1 border-b px-6 py-4 text-left">
            <SheetTitle>Preis-Alarm bearbeiten</SheetTitle>
            <SheetDescription>Name, Prüf-Intervall und Zielpreis anpassen.</SheetDescription>
          </SheetHeader>
          <PriceWatchEditForm watch={watch} onSubmit={handleEditSubmit} />
        </SheetContent>
      </Sheet>
    </ContentReveal>
  )
}

interface PriceTrendResult {
  percent: number
  down: boolean
}

function priceTrend(watch: PriceWatch): PriceTrendResult | null {
  const { last_price, initial_price } = watch
  if (last_price == null || initial_price == null || initial_price === 0) return null
  if (last_price === initial_price) return null
  const percent = ((last_price - initial_price) / initial_price) * 100
  return { percent: Math.abs(percent), down: last_price < initial_price }
}

function PriceWatchEditForm({
  watch,
  onSubmit,
}: {
  watch: PriceWatch
  onSubmit: (data: Partial<PriceWatch>) => Promise<void>
}) {
  const [name, setName] = useState(watch.name)
  const [interval, setInterval] = useState(watch.scrape_interval_minutes)
  const [threshold, setThreshold] = useState(
    watch.notify_threshold != null ? String(watch.notify_threshold) : "",
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await onSubmit({
        name: name.trim() || watch.name,
        scrape_interval_minutes: interval,
        notify_threshold: threshold ? Number(threshold) : null,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen.")
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto overscroll-contain px-6 py-6">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="edit-name" className="font-normal">
            Name
          </Label>
          <Input id="edit-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label className="font-normal">Prüf-Intervall</Label>
          <div className="grid grid-cols-5 gap-1.5">
            {INTERVAL_PRESETS.map((preset) => (
              <Button
                key={preset.value}
                type="button"
                variant={interval === preset.value ? "default" : "outline"}
                size="sm"
                onClick={() => setInterval(preset.value)}
                className="h-9 cursor-pointer px-2 text-xs"
              >
                {preset.label}
              </Button>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="edit-threshold" className="font-normal">
            Benachrichtigen unter (optional)
          </Label>
          <Input
            id="edit-threshold"
            type="number"
            inputMode="decimal"
            min={0}
            step="0.01"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            placeholder="Leer = bei jeder Senkung"
          />
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>
      <div className="flex shrink-0 justify-end border-t px-6 py-4">
        <Button type="submit" disabled={saving} className="cursor-pointer">
          {saving ? "Speichern…" : "Speichern"}
        </Button>
      </div>
    </form>
  )
}
