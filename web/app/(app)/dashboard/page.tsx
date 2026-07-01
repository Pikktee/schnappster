"use client"

import { useEffect, useState, useMemo, useCallback } from "react"
import Link from "next/link"
import { Search, Package, Clock, Sparkles, Settings, TrendingDown, X, ArrowRight, SearchX } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { DealHero } from "@/components/deal-hero"
import { AdCard } from "@/components/ad-card"
import { CardEmptyState } from "@/components/card-empty-state"
import { ContentReveal } from "@/components/content-reveal"
import {
  fetchSearches,
  fetchAdsPaginated,
  fetchScrapeRuns,
  fetchPriceWatches,
  fetchNotifications,
} from "@/lib/api"
import type { Ad, AdSearch, Notification, PriceWatch, ScrapeRun } from "@/lib/types"
import { timeAgo } from "@/lib/format"
import { toast } from "sonner"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { useAuth } from "@/components/auth-provider"
import { usePageHead } from "../page-head-context"

const WELCOME_DISMISSED_KEY = "schnappster-welcome-dismissed"
const LAST_VISIT_KEY = "schnappster-last-visit"

/** Ab diesem Score gilt eine Anzeige als "Schnäppchen". */
const SCHNAEPPCHEN_MIN_SCORE = 8
/** So viele aktuelle Schnäppchen laden (für Hero, Galerie und "seit letztem Besuch"). */
const DEALS_FETCH_LIMIT = 24
/** So viele Karten in der Galerie unter dem Top-Fund zeigen. */
const GALLERY_SIZE = 8

/** Benachrichtigungstypen, die einen Preis-Alarm darstellen. */
const PRICE_ALERT_TYPES = new Set(["price_drop", "price_below_threshold"])

/**
 * Zeitpunkt des vorherigen Besuchs, pro Seitenladen genau einmal erfasst.
 * Modul-Ebene (statt State/Ref), damit Reacts StrictMode-Doppel-Mount und ein
 * Refetch bei Fokuswechsel den frisch gesetzten Baseline-Wert nicht wieder als
 * "vorherigen Besuch" einlesen. `undefined` = in diesem Seitenladen noch nicht erfasst.
 */
let capturedPreviousVisitMs: number | null | undefined

/** Parst einen (ggf. zeitzonenlosen) Backend-Timestamp robust zu Millisekunden. */
function toMs(dateStr: string | null): number {
  if (!dateStr) return 0
  const normalized = dateStr.includes("+") || dateStr.endsWith("Z") ? dateStr : dateStr + "Z"
  const t = new Date(normalized).getTime()
  return Number.isNaN(t) ? 0 : t
}

function greetingForHour(hour: number): string {
  if (hour < 5) return "Guten Abend"
  if (hour < 11) return "Guten Morgen"
  if (hour < 18) return "Guten Tag"
  return "Guten Abend"
}

/** Deutsche Pluralisierung als kurzer Satzteil, z.B. "3 neue Schnäppchen". */
function countPart(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`
}

export default function DashboardPage() {
  const { user } = useAuth()
  const { setTitle } = usePageHead()

  const [searches, setSearches] = useState<AdSearch[]>([])
  const [totalAds, setTotalAds] = useState<number>(0)
  const [deals, setDeals] = useState<Ad[]>([])
  const [scraperuns, setScraperuns] = useState<ScrapeRun[]>([])
  const [priceWatches, setPriceWatches] = useState<PriceWatch[]>([])
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [welcomeDismissed, setWelcomeDismissed] = useState(false)
  const [greeting, setGreeting] = useState("")
  const [previousVisitMs, setPreviousVisitMs] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Einmal beim Öffnen: Begrüßung, letzter Besuch (Baseline für "seit letztem Besuch"),
  // dann sofort die neue Baseline setzen. Bewusst getrennt von load(), damit ein
  // Refetch bei Fokuswechsel die Zählung nicht auf null zurücksetzt.
  useEffect(() => {
    if (typeof window === "undefined") return
    setGreeting(greetingForHour(new Date().getHours()))
    setWelcomeDismissed(localStorage.getItem(WELCOME_DISMISSED_KEY) === "true")
    // Baseline nur einmal pro Seitenladen erfassen und sofort auf "jetzt" fortschreiben.
    if (capturedPreviousVisitMs === undefined) {
      const previous = localStorage.getItem(LAST_VISIT_KEY)
      capturedPreviousVisitMs = previous ? toMs(previous) : null
      localStorage.setItem(LAST_VISIT_KEY, new Date().toISOString())
    }
    setPreviousVisitMs(capturedPreviousVisitMs)
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [s, countRes, dealsRes, r, watches, notes] = await Promise.all([
        fetchSearches(),
        fetchAdsPaginated({ limit: 1 }),
        fetchAdsPaginated({ min_score: SCHNAEPPCHEN_MIN_SCORE, sort: "date", limit: DEALS_FETCH_LIMIT }),
        fetchScrapeRuns({ limit: 100 }),
        // Neue Bereiche dürfen das Dashboard bei Fehlern nicht blockieren.
        fetchPriceWatches().catch(() => [] as PriceWatch[]),
        fetchNotifications().catch(() => [] as Notification[]),
      ])
      setSearches(s)
      setTotalAds(countRes.total)
      setDeals(dealsRes.items)
      setScraperuns(r)
      setPriceWatches(watches)
      setNotifications(notes)
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Daten konnten nicht geladen werden."
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useRefetchOnFocus(load)

  const activeSearches = useMemo(() => searches.filter((s) => s.is_active).length, [searches])
  const activePriceWatches = useMemo(() => priceWatches.filter((w) => w.is_active).length, [priceWatches])

  const lastUpdate = useMemo(() => {
    const finished = scraperuns
      .filter((r) => r.finished_at)
      .sort((a, b) => toMs(b.finished_at) - toMs(a.finished_at))
    return finished.length > 0 ? finished[0].finished_at : null
  }, [scraperuns])

  // Bester aktueller Fund = höchster Score (Gleichstand: größere Ersparnis).
  const { hero, galleryDeals } = useMemo(() => {
    if (deals.length === 0) return { hero: null as Ad | null, galleryDeals: [] as Ad[] }
    const best = [...deals].sort((a, b) => {
      const byScore = (b.bargain_score ?? 0) - (a.bargain_score ?? 0)
      if (byScore !== 0) return byScore
      return (b.price_delta_percent ?? 0) - (a.price_delta_percent ?? 0)
    })[0]
    return { hero: best, galleryDeals: deals.filter((d) => d.id !== best.id).slice(0, GALLERY_SIZE) }
  }, [deals])

  // "Seit deinem letzten Besuch": neue Schnäppchen + ausgelöste Preis-Alarme.
  const { newDealCount, newDropCount } = useMemo(() => {
    if (previousVisitMs === null) return { newDealCount: 0, newDropCount: 0 }
    const newDeals = deals.filter((d) => toMs(d.first_seen_at) > previousVisitMs).length
    const newDrops = notifications.filter(
      (n) => PRICE_ALERT_TYPES.has(n.type) && toMs(n.created_at) > previousVisitMs,
    ).length
    return { newDealCount: newDeals, newDropCount: newDrops }
  }, [deals, notifications, previousVisitMs])

  const substance = useMemo(() => {
    if (previousVisitMs === null) return "Schön, dass du da bist — hier sind deine besten Funde."
    if (newDealCount === 0 && newDropCount === 0) {
      return "Seit deinem letzten Besuch nichts Neues — deine Suchen und Alarme laufen weiter."
    }
    const parts: string[] = []
    if (newDealCount > 0) parts.push(countPart(newDealCount, "neues Schnäppchen", "neue Schnäppchen"))
    if (newDropCount > 0) parts.push(countPart(newDropCount, "Preissenkung", "Preissenkungen"))
    return `${parts.join(" und ")}, seit du zuletzt hier warst.`
  }, [previousVisitMs, newDealCount, newDropCount])

  const greetingTitle = useMemo(() => {
    if (!greeting) return ""
    const firstName = user?.display_name?.trim().split(/\s+/)[0] ?? ""
    return firstName ? `${greeting}, ${firstName}` : greeting
  }, [greeting, user])

  // Begrüßung + Substanz-Satz ersetzen den generischen "Dashboard"-Seitentitel.
  useEffect(() => {
    if (loading || !greetingTitle) return
    setTitle(greetingTitle, substance)
  }, [loading, greetingTitle, substance, setTitle])

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-64 w-full" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <ContentReveal className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-4 py-12">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" onClick={() => window.location.reload()} className="cursor-pointer">
            Erneut laden
          </Button>
        </div>
      </ContentReveal>
    )
  }

  // Nur für wirklich neue Nutzer: noch kein Suchauftrag UND kein Preis-Alarm eingerichtet.
  const showWelcome = searches.length === 0 && priceWatches.length === 0

  return (
    <ContentReveal className="flex flex-col gap-6">
      {/* Willkommen – nur ohne Suchen/Alarme, schließbar */}
      {showWelcome && !welcomeDismissed && (
        <Card className="relative overflow-hidden border-primary/20 bg-gradient-to-br from-background via-background to-primary/[0.06] shadow-sm">
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-2 right-2 size-8 shrink-0 rounded-full text-muted-foreground hover:text-foreground hover:bg-primary/10 cursor-pointer"
            onClick={() => {
              setWelcomeDismissed(true)
              if (typeof window !== "undefined") localStorage.setItem(WELCOME_DISMISSED_KEY, "true")
            }}
            aria-label="Willkommens-Hinweis schließen"
          >
            <X className="size-4" aria-hidden />
          </Button>
          <CardContent className="pt-5 pb-5">
            <div className="flex flex-col sm:flex-row sm:items-start gap-4 pr-8">
              <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary ring-1 ring-primary/20">
                <Sparkles className="size-6" aria-hidden />
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="text-lg font-semibold tracking-tight text-foreground">
                  Willkommen bei Schnappster!
                </h2>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground max-w-xl">
                  Zwei Wege zum besten Preis: Wir durchsuchen Kleinanzeigen automatisch nach
                  Schnäppchen und überwachen beliebige Shop-Seiten auf Preissenkungen. Leg mit
                  einem der beiden los.
                </p>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <Link href="/searches/">
                    <Button size="default" className="cursor-pointer bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm">
                      <Search className="size-4 mr-2" aria-hidden />
                      Suchauftrag erstellen
                    </Button>
                  </Link>
                  <Link href="/price-alerts/">
                    <Button size="default" variant="outline" className="cursor-pointer">
                      <TrendingDown className="size-4 mr-2" aria-hidden />
                      Preis-Alarm erstellen
                    </Button>
                  </Link>
                  <Link
                    href="/settings/"
                    className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors underline-offset-4 hover:underline cursor-pointer"
                  >
                    <Settings className="size-4 shrink-0" aria-hidden />
                    Einstellungen
                  </Link>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Top-Fund: das beste aktuelle Schnäppchen */}
      {hero && <DealHero ad={hero} />}

      {/* Schnäppchen-Galerie mit Bildern zum Stöbern */}
      {galleryDeals.length > 0 && (
        <section className="flex flex-col gap-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Sparkles className="size-4 text-primary" aria-hidden />
              Weitere Schnäppchen
            </h2>
            <Link
              href="/ads/"
              className="group inline-flex items-center gap-1 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Alle Angebote
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 reveal-stagger">
            {galleryDeals.map((ad) => (
              <AdCard key={ad.id} ad={ad} />
            ))}
          </div>
        </section>
      )}

      {/* Noch keine Schnäppchen, aber schon Suchen/Alarme eingerichtet */}
      {!hero && !showWelcome && (
        <Card className="gap-0">
          <CardContent className="pt-6">
            <CardEmptyState
              icon={SearchX}
              title="Noch keine Schnäppchen gefunden"
              description="Sobald deine Suchaufträge Angebote mit hohem Score finden, erscheinen die besten hier."
              actionLabel="Suchauftrag anlegen"
              actionHref="/searches/"
            />
          </CardContent>
        </Card>
      )}

      {/* Betriebs-Status – bewusst dezent in der Fußzeile statt als KPI-Kacheln */}
      {!showWelcome && (
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t pt-4 text-xs text-muted-foreground">
          <Link href="/searches/" className="inline-flex items-center gap-1.5 transition-colors hover:text-foreground">
            <Search className="size-3.5" aria-hidden />
            {countPart(activeSearches, "aktiver Suchauftrag", "aktive Suchaufträge")}
          </Link>
          <span className="text-muted-foreground/40">·</span>
          <Link href="/price-alerts/" className="inline-flex items-center gap-1.5 transition-colors hover:text-foreground">
            <TrendingDown className="size-3.5" aria-hidden />
            {countPart(activePriceWatches, "aktiver Preis-Alarm", "aktive Preis-Alarme")}
          </Link>
          <span className="text-muted-foreground/40">·</span>
          <span className="inline-flex items-center gap-1.5">
            <Package className="size-3.5" aria-hidden />
            {countPart(totalAds, "Anzeige erfasst", "Anzeigen erfasst")}
          </span>
          <span className="text-muted-foreground/40">·</span>
          <span className="inline-flex items-center gap-1.5">
            <Clock className="size-3.5" aria-hidden />
            Aktualisiert {lastUpdate ? timeAgo(lastUpdate) : "noch nie"}
          </span>
        </div>
      )}
    </ContentReveal>
  )
}
