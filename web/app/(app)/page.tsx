"use client"

import { useEffect, useState, useMemo } from "react"
import { Search, Package, Clock, Sparkles, TrendingUp, Zap } from "lucide-react"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { PageHeader } from "@/components/page-header"
import { StatCard } from "@/components/stat-card"
import { LatestDeals } from "@/components/latest-deals"
import { fetchSearches, fetchAdsPaginated, fetchScrapeRuns } from "@/lib/api"
import type { Ad, AdSearch, ScrapeRun } from "@/lib/types"
import { timeAgo } from "@/lib/format"
import { toast } from "sonner"
import Link from "next/link"

export default function DashboardPage() {
  const [searches, setSearches] = useState<AdSearch[]>([])
  const [totalAds, setTotalAds] = useState<number>(0)
  const [latestDeals, setLatestDeals] = useState<Ad[]>([])
  const [scraperuns, setScraperuns] = useState<ScrapeRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
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
    }
    load()
  }, [])

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
        <PageHeader
          title="Dashboard"
          subtitle="Übersicht über deine Schnäppchen-Suchergebnisse"
        />
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
      <div className="flex flex-col gap-6">
        <PageHeader
          title="Dashboard"
          subtitle="Übersicht über deine Schnäppchen-Suchergebnisse"
        />
        <div className="flex flex-col items-center gap-4 py-12">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" onClick={() => window.location.reload()} className="cursor-pointer">
            Erneut laden
          </Button>
        </div>
      </div>
    )
  }

  const showWelcome = searches.length === 0 || totalAds === 0

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>Start</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <PageHeader
        title="Dashboard"
        subtitle="Übersicht über deine Schnäppchen-Suchergebnisse"
      />

      {/* Welcome / Quick Actions */}
      {showWelcome && (
        <Card className="gradient-subtle border-primary/20">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="size-12 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center shrink-0">
                <Sparkles className="size-6 text-primary" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-foreground">
                  {searches.length === 0 ? "Willkommen bei Schnappster!" : "Bereit für die erste Suche?"}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {searches.length === 0
                    ? "Erstelle deinen ersten Suchauftrag und lass uns automatisch nach Schnäppchen auf Kleinanzeigen suchen."
                    : "Deine Suchaufträge sind eingerichtet. Die ersten Ergebnisse werden in Kürze erscheinen."}
                </p>
                <div className="flex flex-wrap gap-2 mt-4">
                  {searches.length === 0 && (
                    <Link href="/searches/">
                      <Button className="cursor-pointer bg-primary hover:bg-primary/90">
                        <Search className="size-4 mr-2" />
                        Suchauftrag erstellen
                      </Button>
                    </Link>
                  )}
                  {totalAds === 0 && (
                    <Link href="/ads/">
                      <Button variant="outline" className="cursor-pointer">
                        <TrendingUp className="size-4 mr-2" />
                        Anzeigen durchsuchen
                      </Button>
                    </Link>
                  )}
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
          label="Angebote gesamt"
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
    </div>
  )
}
