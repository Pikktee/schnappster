"use client"

import { useCallback, useEffect, useState, type ReactNode } from "react"
import { usePathname, useRouter } from "next/navigation"
import {
  AlertTriangle,
  ArrowLeft,
  Clock,
  Flame,
  Loader2,
  RefreshCw,
  Search,
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
import { SearchStatusBadge } from "@/components/search-status-badge"
import { DealCard } from "@/components/deal-card"
import { EmptyState } from "@/components/empty-state"
import {
  checkDealWatchNow,
  deleteDealWatch,
  fetchDealWatch,
  fetchDealWatchDeals,
  updateDealWatch,
} from "@/lib/api"
import type { Deal, DealWatch } from "@/lib/types"
import { formatDealAlarmThreshold, formatScrapeInterval, timeAgo } from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { ContentReveal } from "@/components/content-reveal"
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

export function DealAlarmDetailPage() {
  const router = useRouter()
  const pathname = usePathname()
  const { setTitle, setTitleSuffix } = usePageHead()
  const [id, setId] = useState<number>(NaN)

  const [watch, setWatch] = useState<DealWatch | null>(null)
  const [deals, setDeals] = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
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
        const [w, d] = await Promise.all([fetchDealWatch(id), fetchDealWatchDeals(id)])
        setWatch(w)
        setDeals(d)
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
      const updated = await updateDealWatch(id, { is_active: !watch.is_active })
      setWatch(updated)
      toast.success(updated.is_active ? "Deal-Alarm aktiviert" : "Deal-Alarm pausiert")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Aktualisierung fehlgeschlagen.")
    } finally {
      setIsToggling(false)
    }
  }

  async function handleCheckNow() {
    setIsChecking(true)
    try {
      const updated = await checkDealWatchNow(id)
      setWatch(updated)
      setDeals(await fetchDealWatchDeals(id))
      toast.success(
        updated.last_error ? "Geprüft — MyDealz war nicht erreichbar." : "Geprüft — Deals aktualisiert.",
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
      await deleteDealWatch(id)
      toast.success("Deal-Alarm gelöscht")
      router.push("/deal-alarms")
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

  if (error || !watch) {
    return (
      <ContentReveal className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-muted-foreground">{error || "Deal-Alarm nicht gefunden."}</p>
        <Button variant="outline" onClick={() => router.push("/deal-alarms")} className="cursor-pointer">
          Zurück zur Übersicht
        </Button>
      </ContentReveal>
    )
  }

  const thresholdLabel = formatDealAlarmThreshold(watch)

  return (
    <ContentReveal className="flex flex-col gap-6">
      {/* Kopfzeile */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => router.push("/deal-alarms")}
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
                <AlertDialogTitle>Deal-Alarm löschen?</AlertDialogTitle>
                <AlertDialogDescription>
                  Der Deal-Alarm &ldquo;{watch.name}&rdquo; und alle dafür gefundenen Deals werden
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
          <span>Bei der letzten Prüfung gab es ein Problem: {watch.last_error}</span>
        </div>
      )}

      {/* Übersicht */}
      <Card className="border-border/80 bg-card/95 py-0 shadow-sm">
        <CardContent className="grid grid-cols-1 gap-3 p-4 sm:p-5 md:grid-cols-2 lg:grid-cols-4">
          <DetailField icon={Search} label="Suchbegriff" className="md:col-span-2">
            {`„${watch.query}" · MyDealz`}
          </DetailField>
          <DetailField icon={Flame} label="Alarm ab">
            {thresholdLabel}
          </DetailField>
          <DetailField icon={RefreshCw} label="Intervall">
            {formatScrapeInterval(watch.scrape_interval_minutes)}
          </DetailField>
          <DetailField icon={Clock} label="Zuletzt geprüft" className="md:col-span-2 lg:col-span-4">
            {timeAgo(watch.last_checked_at)}
          </DetailField>
        </CardContent>
      </Card>

      {/* Gefundene Deals */}
      {deals.length === 0 ? (
        <EmptyState
          message={
            watch.last_checked_at
              ? "Noch keine passenden Deals gefunden. Neue Deals erscheinen hier automatisch."
              : "Die erste Prüfung läuft — gefundene Deals erscheinen gleich hier."
          }
          icon={<Flame className="size-12 text-muted-foreground/50" />}
        />
      ) : (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Gefundene Deals ({deals.length})
          </h2>
          <ul className="m-0 grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
            {deals.map((deal) => (
              <li key={deal.external_id} className="min-w-0">
                <DealCard deal={deal} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </ContentReveal>
  )
}
