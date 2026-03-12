"use client"

import { useEffect, useState, useMemo, useCallback } from "react"
import { Search, Package, Clock, Sparkles, Zap, Settings, X } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/stat-card"
import { LatestDeals } from "@/components/latest-deals"
import { ContentReveal } from "@/components/content-reveal"
import { fetchSearches, fetchAdsPaginated, fetchScrapeRuns } from "@/lib/api"
import type { Ad, AdSearch, ScrapeRun } from "@/lib/types"
import { timeAgo } from "@/lib/format"
import { toast } from "sonner"
import Link from "next/link"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"

const WELCOME_DISMISSED_KEY = "schnappster-welcome-dismissed"

export default function DashboardPage() {
  const [searches, setSearches] = useState<AdSearch[]>([])
  const [totalAds, setTotalAds] = useState<number>(0)
  const [latestDeals, setLatestDeals] = useState<Ad[]>([])
  const [scraperuns, setScraperuns] = useState<ScrapeRun[]>([])
  const [welcomeDismissed, setWelcomeDismissed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (typeof window === "undefined") return
    setWelcomeDismissed(localStorage.getItem(WELCOME_DISMISSED_KEY) === "true")
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [s, countRes, dealsRes, r] = await Promise.all([
        fetchSearches(),
        fetchAdsPaginated({ limit: 1 }),
        fetchAdsPaginated({ min_score: 8, sort: "date", limit: 5 }),
        fetchScrapeRuns({ limit: 100 }),
      ])
      setSearches(s)
      setTotalAds(countRes.total)
      setLatestDeals(dealsRes.items)
      setScraperuns(r)
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

  const activeSearches = useMemo(
    () => searches.filter((s) => s.is_active).length,
    [searches]
  )

  const lastUpdate = useMemo(() => {
    const finishedRuns = scraperuns
      .filter((r) => r.finished_at)
      .sort((a, b) => new Date(b.finished_at!).getTime() - new Date(a.finished_at!).getTime())
    return finishedRuns.length > 0 ? finishedRuns[0].finished_at : null
  }, [scraperuns])

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Letzte Schnäppchen</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-48" />
          </CardContent>
        </Card>
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

  const showWelcome = searches.length === 0 || totalAds === 0

  return (
    <ContentReveal className="flex flex-col gap-6">
      {/* Welcome – nur bei noch keinen Suchaufträgen, schließbar */}
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
                  {searches.length === 0 ? "Willkommen bei Schnappster!" : "Bereit für die erste Suche?"}
                </h2>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground max-w-xl">
                  {searches.length === 0
                    ? "Erstelle deinen ersten Suchauftrag und lass uns automatisch nach Schnäppchen auf Kleinanzeigen suchen."
                    : "Deine Suchaufträge sind eingerichtet. Die ersten Ergebnisse werden in Kürze erscheinen."}
                </p>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  {searches.length === 0 && (
                    <Link href="/searches/">
                      <Button size="default" className="cursor-pointer bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm">
                        <Search className="size-4 mr-2" aria-hidden />
                        Suchauftrag erstellen
                      </Button>
                    </Link>
                  )}
                  <Link
                    href="/settings/"
                    className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors underline-offset-4 hover:underline cursor-pointer"
                  >
                    <Settings className="size-4 shrink-0" aria-hidden />
                    Einstellungen — z. B. Telegram-Benachrichtigungen
                  </Link>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 reveal-stagger">
        <StatCard
          label="Aktive Suchaufträge"
          value={activeSearches}
          icon={Search}
          iconBgColor="bg-emerald-50"
          iconTextColor="text-emerald-600"
        />
        <StatCard
          label="Anzeigen insgesamt"
          value={totalAds}
          icon={Package}
          iconBgColor="bg-amber-50"
          iconTextColor="text-amber-600"
        />
        <StatCard
          label="Letzte Aktualisierung"
          value={lastUpdate ? timeAgo(lastUpdate) : "Noch nie"}
          icon={Clock}
          iconBgColor="bg-blue-50"
          iconTextColor="text-blue-600"
        />
      </div>

      <Card className="reveal-stagger gap-0">
        <CardHeader className="pb-0">
          <CardTitle className="flex items-center gap-2">
            <Zap className="size-5 text-primary" />
            Letzte Schnäppchen
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <LatestDeals ads={latestDeals} />
        </CardContent>
      </Card>
    </ContentReveal>
  )
}
