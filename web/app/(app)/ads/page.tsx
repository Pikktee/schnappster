"use client"

import { useEffect, useState, useMemo } from "react"
import { useRouter } from "next/navigation"
import { LayoutGrid, TableIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { PageHeader } from "@/components/page-header"
import { AdCard } from "@/components/ad-card"
import { ScoreBadge } from "@/components/score-badge"
import { EmptyState } from "@/components/empty-state"
import { fetchAds, fetchSearches } from "@/lib/api"
import type { Ad, AdSearch } from "@/lib/types"
import { formatPrice, timeAgo } from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

type SortOption = "date" | "price-asc" | "price-desc" | "score-desc"
type ViewMode = "cards" | "table"

export default function AdsPage() {
  const router = useRouter()
  const [ads, setAds] = useState<Ad[]>([])
  const [searches, setSearches] = useState<AdSearch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [minScore, setMinScore] = useState<string>("0")
  const [searchId, setSearchId] = useState<string>("all")
  const [sortBy, setSortBy] = useState<SortOption>("date")
  const [viewMode, setViewMode] = useState<ViewMode>("cards")

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [a, s] = await Promise.all([fetchAds(), fetchSearches()])
        setAds(a)
        setSearches(s)
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Angebote konnten nicht geladen werden."
        setError(msg)
        toast.error(msg)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const filteredAds = useMemo(() => {
    let list = [...ads]

    const minScoreNum = Number(minScore) || 0
    if (minScoreNum > 0) {
      list = list.filter((a) => a.bargain_score !== null && a.bargain_score >= minScoreNum)
    }

    if (searchId !== "all") {
      list = list.filter((a) => a.adsearch_id === Number(searchId))
    }

    switch (sortBy) {
      case "date":
        list.sort((a, b) => new Date(b.first_seen_at).getTime() - new Date(a.first_seen_at).getTime())
        break
      case "price-asc":
        list.sort((a, b) => (a.price ?? 0) - (b.price ?? 0))
        break
      case "price-desc":
        list.sort((a, b) => (b.price ?? 0) - (a.price ?? 0))
        break
      case "score-desc":
        list.sort((a, b) => (b.bargain_score ?? 0) - (a.bargain_score ?? 0))
        break
    }

    return list
  }, [ads, minScore, searchId, sortBy])

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Anzeigen" subtitle="Alle gefundenen Kleinanzeigen-Angebote" />
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 min-[1920px]:grid-cols-6 gap-4">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Anzeigen" subtitle="Alle gefundenen Kleinanzeigen-Angebote" />
        <p className="text-destructive">{error}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Anzeigen" subtitle="Alle gefundenen Kleinanzeigen-Angebote" />

      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1.5">
          <Label className="text-xs text-muted-foreground">Mindest-Score</Label>
          <Input
            type="number"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            min={0}
            max={10}
            step={0.5}
            className="w-24"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label className="text-xs text-muted-foreground">Suchauftrag</Label>
          <Select value={searchId} onValueChange={setSearchId}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Alle</SelectItem>
              {searches.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>
                  {s.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label className="text-xs text-muted-foreground">Sortierung</Label>
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date">Datum (neueste)</SelectItem>
              <SelectItem value="price-asc">Preis aufsteigend</SelectItem>
              <SelectItem value="price-desc">Preis absteigend</SelectItem>
              <SelectItem value="score-desc">Score absteigend</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex gap-1 ml-auto">
          <Button
            variant={viewMode === "cards" ? "default" : "outline"}
            size="icon"
            onClick={() => setViewMode("cards")}
            className="cursor-pointer"
            aria-label="Karten-Ansicht"
          >
            <LayoutGrid className="size-4" />
          </Button>
          <Button
            variant={viewMode === "table" ? "default" : "outline"}
            size="icon"
            onClick={() => setViewMode("table")}
            className="cursor-pointer"
            aria-label="Tabellen-Ansicht"
          >
            <TableIcon className="size-4" />
          </Button>
        </div>
      </div>

      {filteredAds.length === 0 ? (
        <EmptyState message="Keine Angebote gefunden. Passe die Filter an oder erstelle neue Suchauftraege." />
      ) : viewMode === "cards" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 min-[1920px]:grid-cols-6 gap-4">
          {filteredAds.map((ad) => (
            <AdCard key={ad.id} ad={ad} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Titel</TableHead>
                <TableHead>Preis</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Standort</TableHead>
                <TableHead>Gefunden</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAds.map((ad) => (
                <TableRow
                  key={ad.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/ads/${ad.id}`)}
                >
                  <TableCell className="font-medium max-w-[300px] truncate">
                    {ad.title}
                  </TableCell>
                  <TableCell>{formatPrice(ad.price)}</TableCell>
                  <TableCell>
                    <ScoreBadge score={ad.bargain_score} size="sm" />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {ad.postal_code} {ad.city}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {timeAgo(ad.first_seen_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
