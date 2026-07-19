"use client"

import { useCallback, useEffect, useState, type ReactNode } from "react"
import { useParams, useRouter } from "next/navigation"
import {
  ArrowLeft,
  Bell,
  Clock,
  Gift,
  Loader2,
  MapPin,
  Pencil,
  RefreshCw,
  Sparkles,
  Tag,
  Trash2,
  Truck,
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
import { AdCard } from "@/components/ad-card"
import { GiftWatchSheet } from "@/components/gift-watch-sheet"
import { GIFT_VEHICLE_LABELS } from "@/components/gift-watch-form"
import { ContentReveal } from "@/components/content-reveal"
import { Skeleton } from "@/components/ui/skeleton"
import {
  checkGiftWatchNow,
  deleteGiftWatch,
  fetchAdsPaginated,
  fetchGiftWatch,
  updateGiftWatch,
} from "@/lib/api"
import type { Ad, GiftWatch } from "@/lib/types"
import { formatScrapeInterval, timeAgo } from "@/lib/format"
import { toast } from "sonner"
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

export default function FundgrubeDetailPage() {
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = Number(params?.id)
  const { setTitle, setTitleSuffix } = usePageHead()

  const [watch, setWatch] = useState<GiftWatch | null>(null)
  const [ads, setAds] = useState<Ad[]>([])
  const [loading, setLoading] = useState(true)
  const [adsLoading, setAdsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [isChecking, setIsChecking] = useState(false)

  const loadAds = useCallback(async (adsearchId: number | null) => {
    if (adsearchId == null) {
      setAds([])
      return
    }
    setAdsLoading(true)
    try {
      const res = await fetchAdsPaginated({
        adsearch_id: adsearchId,
        sort: "score",
        is_analyzed: true,
        limit: 100,
      })
      setAds(res.items)
    } catch {
      // Funde sind nachrangig — Fehler hier nicht als Seiten-Fehler behandeln.
      setAds([])
    } finally {
      setAdsLoading(false)
    }
  }, [])

  const load = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (Number.isNaN(id)) return
      if (!opts?.silent) {
        setLoading(true)
        setError(null)
      }
      try {
        const w = await fetchGiftWatch(id)
        setWatch(w)
        await loadAds(w.adsearch_id)
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Fundgrube konnte nicht geladen werden."
        if (!opts?.silent) {
          setError(msg)
          setWatch(null)
        }
      } finally {
        setLoading(false)
      }
    },
    [id, loadAds],
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
      const updated = await updateGiftWatch(id, { is_active: !watch.is_active })
      setWatch(updated)
      toast.success(updated.is_active ? "Fundgrube aktiviert" : "Fundgrube pausiert")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Aktualisierung fehlgeschlagen.")
    } finally {
      setIsToggling(false)
    }
  }

  async function handleCheckNow() {
    setIsChecking(true)
    try {
      const updated = await checkGiftWatchNow(id)
      setWatch(updated)
      toast.success("Prüfung gestartet — neue Funde erscheinen gleich.")
      // Neue Funde werden im Hintergrund analysiert; kurz darauf still nachladen.
      setTimeout(() => load({ silent: true }), 5000)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Prüfung fehlgeschlagen.")
    } finally {
      setIsChecking(false)
    }
  }

  async function handleDelete() {
    setIsDeleting(true)
    try {
      await deleteGiftWatch(id)
      toast.success("Fundgrube gelöscht")
      router.push("/fundgrube")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Löschen fehlgeschlagen.")
      setIsDeleting(false)
    }
  }

  function handleSaved() {
    // Das Formular meldet den Erfolg bereits per Toast — hier nur schließen und neu laden.
    setIsEditOpen(false)
    load({ silent: true })
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
        <p className="text-muted-foreground">{error || "Fundgrube nicht gefunden."}</p>
        <Button variant="outline" onClick={() => router.push("/fundgrube")} className="cursor-pointer">
          Zurück zur Übersicht
        </Button>
      </ContentReveal>
    )
  }

  const profile = watch.interest_profile?.trim()
  const focus = watch.focus_keywords?.trim()
  const exclude = watch.exclude_keywords?.trim()

  return (
    <ContentReveal className="flex flex-col gap-6">
      {/* Kopfzeile */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => router.push("/fundgrube")}
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
                <AlertDialogTitle>Fundgrube löschen?</AlertDialogTitle>
                <AlertDialogDescription>
                  Die Fundgrube &ldquo;{watch.name}&rdquo; und alle darüber gefundenen Angebote
                  werden unwiderruflich gelöscht.
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

      {/* Einstellungen kompakt */}
      <Card className="border-border/80 bg-card/95 py-0 shadow-sm">
        <CardContent className="p-4 sm:p-5">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            <DetailField icon={MapPin} label="Standort">
              PLZ {watch.postal_code} · {watch.radius_km} km
            </DetailField>
            <DetailField icon={Truck} label="Transport">
              {GIFT_VEHICLE_LABELS[watch.vehicle]}
              {watch.can_carry_heavy && (
                <span className="text-muted-foreground"> · kann schwer heben</span>
              )}
            </DetailField>
            <DetailField icon={Bell} label="Benachrichtigung">
              ab Score {watch.min_score_notify}
            </DetailField>
            <DetailField icon={RefreshCw} label="Intervall">
              {formatScrapeInterval(watch.scrape_interval_minutes)}
            </DetailField>
            <DetailField icon={Clock} label="Zuletzt geprüft">
              {timeAgo(watch.last_scraped_at)}
            </DetailField>
            <DetailField icon={Sparkles} label="Interessensprofil" className="md:col-span-2 lg:col-span-3">
              {profile ? (
                <span className="whitespace-pre-wrap">{profile}</span>
              ) : (
                <span className="text-muted-foreground">Kein Profil hinterlegt</span>
              )}
            </DetailField>
            {focus && (
              <DetailField icon={Tag} label="Schwerpunkte" className="md:col-span-2 lg:col-span-3">
                {focus}
              </DetailField>
            )}
            {exclude && (
              <DetailField icon={Tag} label="Ausschluss" className="md:col-span-2 lg:col-span-3">
                {exclude}
              </DetailField>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Funde */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Funde
        </h2>
        {adsLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
            <Skeleton className="h-80 rounded-xl" />
            <Skeleton className="h-80 rounded-xl" />
            <Skeleton className="h-80 rounded-xl" />
          </div>
        ) : ads.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border/70 py-16 text-center">
            <Gift className="size-10 text-muted-foreground/40" aria-hidden />
            <p className="max-w-sm text-sm text-muted-foreground">
              Noch keine Funde — die erste Prüfung läuft im Hintergrund.
            </p>
          </div>
        ) : (
          <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
            {ads.map((ad) => (
              <li key={ad.id} className="min-w-0">
                <AdCard ad={ad} gift />
              </li>
            ))}
          </ul>
        )}
      </div>

      <GiftWatchSheet
        open={isEditOpen}
        onOpenChange={setIsEditOpen}
        initial={watch}
        onSaved={handleSaved}
      />
    </ContentReveal>
  )
}
