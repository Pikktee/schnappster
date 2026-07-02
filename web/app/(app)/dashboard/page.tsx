"use client"

import { useEffect, useState, useMemo, useCallback } from "react"
import Link from "next/link"
import { Search, Package, Clock, Sparkles, Settings, TrendingDown, X } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ResultStream } from "@/components/result-stream"
import { ContentReveal } from "@/components/content-reveal"
import {
  fetchSearchOrders,
  fetchAdsPaginated,
  fetchPriceWatches,
  fetchNotifications,
} from "@/lib/api"
import type { Ad, Notification, PriceWatch, SearchOrder } from "@/lib/types"
import { timeAgo } from "@/lib/format"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { useAuth } from "@/components/auth-provider"
import { usePageHead } from "../page-head-context"

const WELCOME_DISMISSED_KEY = "schnappster-welcome-dismissed"
const LAST_VISIT_KEY = "schnappster-last-visit"
const STREAM_FILTERS_KEY = "schnappster-stream-filters"

/** Ab diesem Score gilt eine Anzeige als "Schnäppchen" (für die Begrüßungszeile). */
const SCHNAEPPCHEN_MIN_SCORE = 8
/** So viele aktuelle Schnäppchen für die "seit letztem Besuch"-Zählung laden. */
const DEALS_FETCH_LIMIT = 24

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

  const [orders, setOrders] = useState<SearchOrder[]>([])
  const [deals, setDeals] = useState<Ad[]>([])
  const [priceWatches, setPriceWatches] = useState<PriceWatch[]>([])
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [welcomeDismissed, setWelcomeDismissed] = useState(false)
  const [greeting, setGreeting] = useState("")
  const [previousVisitMs, setPreviousVisitMs] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  // Einmal beim Öffnen: Begrüßung + Baseline "letzter Besuch" (siehe Kommentar oben).
  useEffect(() => {
    if (typeof window === "undefined") return
    setGreeting(greetingForHour(new Date().getHours()))
    setWelcomeDismissed(localStorage.getItem(WELCOME_DISMISSED_KEY) === "true")
    if (capturedPreviousVisitMs === undefined) {
      const previous = localStorage.getItem(LAST_VISIT_KEY)
      capturedPreviousVisitMs = previous ? toMs(previous) : null
      localStorage.setItem(LAST_VISIT_KEY, new Date().toISOString())
    }
    setPreviousVisitMs(capturedPreviousVisitMs)
  }, [])

  const load = useCallback(async () => {
    try {
      const [orderList, dealsRes, watches, notes] = await Promise.all([
        fetchSearchOrders().catch(() => [] as SearchOrder[]),
        fetchAdsPaginated({
          min_score: SCHNAEPPCHEN_MIN_SCORE,
          sort: "date",
          limit: DEALS_FETCH_LIMIT,
        }).catch(() => ({ items: [] as Ad[], total: 0 })),
        fetchPriceWatches().catch(() => [] as PriceWatch[]),
        fetchNotifications().catch(() => [] as Notification[]),
      ])
      setOrders(orderList)
      setDeals(dealsRes.items)
      setPriceWatches(watches)
      setNotifications(notes)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useRefetchOnFocus(load)

  const activeOrders = useMemo(() => orders.filter((o) => o.is_active).length, [orders])
  const activePriceWatches = useMemo(
    () => priceWatches.filter((w) => w.is_active).length,
    [priceWatches],
  )
  const totalFinds = useMemo(
    () => orders.reduce((sum, o) => sum + o.ad_count + o.deal_count, 0),
    [orders],
  )
  const lastUpdate = useMemo(() => {
    const known = orders.map((o) => o.last_checked_at).filter(Boolean) as string[]
    return known.sort((a, b) => toMs(b) - toMs(a))[0] ?? null
  }, [orders])

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
    if (previousVisitMs === null) return "Alle neuen Funde deiner Suchen und Alarme auf einen Blick."
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

  useEffect(() => {
    if (loading || !greetingTitle) return
    setTitle(greetingTitle, substance)
  }, [loading, greetingTitle, substance, setTitle])

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-9 w-full max-w-xl" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    )
  }

  const showWelcome = orders.length === 0 && priceWatches.length === 0

  return (
    <ContentReveal className="flex flex-col gap-6">
      {/* Willkommen – nur ohne Suchen/Alarme, schließbar */}
      {showWelcome && !welcomeDismissed && (
        <Card className="relative overflow-hidden border-primary/20 bg-gradient-to-br from-background via-background to-primary/[0.06] shadow-sm">
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-2 right-2 size-8 shrink-0 cursor-pointer rounded-full text-muted-foreground hover:bg-primary/10 hover:text-foreground"
            onClick={() => {
              setWelcomeDismissed(true)
              if (typeof window !== "undefined") localStorage.setItem(WELCOME_DISMISSED_KEY, "true")
            }}
            aria-label="Willkommens-Hinweis schließen"
          >
            <X className="size-4" aria-hidden />
          </Button>
          <CardContent className="pt-5 pb-5">
            <div className="flex flex-col gap-4 pr-8 sm:flex-row sm:items-start">
              <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary ring-1 ring-primary/20">
                <Sparkles className="size-6" aria-hidden />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-lg font-semibold tracking-tight text-foreground">
                  Willkommen bei Schnappster!
                </h2>
                <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-muted-foreground">
                  Ein Suchauftrag durchsucht Kleinanzeigen, eBay und MyDealz gleichzeitig nach
                  Schnäppchen; Preis-Alarme überwachen beliebige Shop-Seiten auf Preissenkungen.
                  Alles Neue läuft hier auf der Startseite zusammen.
                </p>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <Link href="/searches/">
                    <Button size="default" className="cursor-pointer bg-primary text-primary-foreground shadow-sm hover:bg-primary/90">
                      <Search className="mr-2 size-4" aria-hidden />
                      Suchauftrag erstellen
                    </Button>
                  </Link>
                  <Link href="/price-alerts/">
                    <Button size="default" variant="outline" className="cursor-pointer">
                      <TrendingDown className="mr-2 size-4" aria-hidden />
                      Preis-Alarm erstellen
                    </Button>
                  </Link>
                  <Link
                    href="/settings/"
                    className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
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

      {/* Der Ergebnis-Stream: alle Quellen, chronologisch */}
      <ResultStream storageKey={STREAM_FILTERS_KEY} />

      {/* Betriebs-Status – bewusst dezent in der Fußzeile */}
      {!showWelcome && (
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t pt-4 text-xs text-muted-foreground">
          <Link href="/searches/" className="inline-flex items-center gap-1.5 transition-colors hover:text-foreground">
            <Search className="size-3.5" aria-hidden />
            {countPart(activeOrders, "aktiver Suchauftrag", "aktive Suchaufträge")}
          </Link>
          <span className="text-muted-foreground/40">·</span>
          <Link href="/price-alerts/" className="inline-flex items-center gap-1.5 transition-colors hover:text-foreground">
            <TrendingDown className="size-3.5" aria-hidden />
            {countPart(activePriceWatches, "aktiver Preis-Alarm", "aktive Preis-Alarme")}
          </Link>
          <span className="text-muted-foreground/40">·</span>
          <span className="inline-flex items-center gap-1.5">
            <Package className="size-3.5" aria-hidden />
            {countPart(totalFinds, "Fund erfasst", "Funde erfasst")}
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
