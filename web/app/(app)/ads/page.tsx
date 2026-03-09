"use client"

import { Suspense, useEffect, useState, useCallback } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { LayoutGrid, TableIcon, SlidersHorizontal, ChevronLeft, ChevronRight, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
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
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { PageHeader } from "@/components/page-header"
import { AdCard } from "@/components/ad-card"
import { ScoreBadge } from "@/components/score-badge"
import { EmptyState } from "@/components/empty-state"
import { fetchAdsPaginated, fetchSearches } from "@/lib/api"
import type { Ad, AdSearch } from "@/lib/types"
import { formatPrice, timeAgo } from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

type SortOption = "date" | "price-asc" | "price-desc" | "score-desc"
type ViewMode = "cards" | "table"

const PAGE_SIZE = 24

export default function AdsPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col gap-6">
        <PageHeader title="Anzeigen" subtitle="Alle gefundenen Kleinanzeigen-Angebote" />
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    }>
      <AdsPageContent />
    </Suspense>
  )
}

function AdsPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [ads, setAds] = useState<Ad[]>([])
  const [total, setTotal] = useState(0)
  const [searches, setSearches] = useState<AdSearch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [minScore, setMinScore] = useState<string>(searchParams.get("minScore") || "8")
  const [searchId, setSearchId] = useState<string>(searchParams.get("search") || "all")
  const [sortBy, setSortBy] = useState<SortOption>((searchParams.get("sort") as SortOption) || "date")
  const [viewMode, setViewMode] = useState<ViewMode>((searchParams.get("view") as ViewMode) || "cards")
  const [page, setPage] = useState(Number(searchParams.get("page")) || 1)

  const updateUrl = useCallback((params: Record<string, string>) => {
    const sp = new URLSearchParams(searchParams.toString())
    for (const [key, value] of Object.entries(params)) {
      if (value && value !== "0" && value !== "8" && value !== "all" && value !== "date" && value !== "cards") {
        sp.set(key, value)
      } else {
        sp.delete(key)
      }
    }
    const qs = sp.toString()
    router.replace(`/ads${qs ? `?${qs}` : ""}`, { scroll: false })
  }, [searchParams, router])

  const loadAds = useCallback(async (p: number, score: string, search: string, sort: string) => {
    setLoading(true)
    setError(null)
    try {
      const [result, s] = await Promise.all([
        fetchAdsPaginated({
          min_score: Number(score) || undefined,
          adsearch_id: search !== "all" ? Number(search) : undefined,
          sort,
          limit: PAGE_SIZE,
          offset: (p - 1) * PAGE_SIZE,
        }),
        fetchSearches(),
      ])
      setAds(result.items)
      setTotal(result.total)
      setSearches(s)
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Angebote konnten nicht geladen werden."
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadAds(page, minScore, searchId, sortBy) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function reload(newPage: number, newScore?: string, newSearch?: string, newSort?: string) {
    const s = newScore ?? minScore
    const sid = newSearch ?? searchId
    const so = newSort ?? sortBy
    loadAds(newPage, s, sid, so)
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const safePage = Math.min(page, totalPages)

  function goToPage(p: number) {
    setPage(p)
    updateUrl({ page: p === 1 ? "0" : String(p) })
    reload(p)
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Anzeigen" subtitle="Alle gefundenen Kleinanzeigen-Angebote" />
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
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
        <div className="flex flex-col items-center gap-4 py-12">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" onClick={load} className="cursor-pointer">
            Erneut laden
          </Button>
        </div>
      </div>
    )
  }

  const activeFilterCount = [
    minScore !== "8",
    searchId !== "all",
    sortBy !== "date",
  ].filter(Boolean).length

  const hasActiveFilters = activeFilterCount > 0

  function resetFilters() {
    setMinScore("8")
    setSearchId("all")
    setSortBy("date")
    setPage(1)
    updateUrl({ minScore: "8", search: "all", sort: "date", page: "0" })
    reload(1, "8", "all", "date")
  }

  const filterControls = (
    <>
      <div className="flex flex-col gap-1.5">
        <Label className="text-xs text-muted-foreground">Mindest-Score</Label>
        <Select
          value={minScore}
          onValueChange={(v) => {
            setMinScore(v)
            setPage(1)
            updateUrl({ minScore: v, page: "0" })
            reload(1, v)
          }}
        >
          <SelectTrigger className="w-full md:w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="0">Alle</SelectItem>
            {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
              <SelectItem key={n} value={String(n)}>
                {"\u2265"} {n}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label className="text-xs text-muted-foreground">Suchauftrag</Label>
        <Select
          value={searchId}
          onValueChange={(v) => {
            setSearchId(v)
            setPage(1)
            updateUrl({ search: v, page: "0" })
            reload(1, undefined, v)
          }}
        >
          <SelectTrigger className="w-full md:w-48">
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
        <Select
          value={sortBy}
          onValueChange={(v) => {
            setSortBy(v as SortOption)
            setPage(1)
            updateUrl({ sort: v, page: "0" })
            reload(1, undefined, undefined, v)
          }}
        >
          <SelectTrigger className="w-full md:w-44">
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
    </>
  )

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/">Start</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>Anzeigen</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <PageHeader title="Anzeigen" subtitle="Alle gefundenen Kleinanzeigen-Angebote" />

      {/* Desktop filters */}
      <div className="hidden md:flex flex-wrap items-end gap-4">
        {filterControls}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={resetFilters}
            className="cursor-pointer text-muted-foreground hover:text-foreground"
            aria-label="Filter und Sortierung zurücksetzen"
          >
            <RotateCcw className="size-3.5 mr-1.5" />
            Zurücksetzen
          </Button>
        )}
        <div className="flex items-center gap-2 ml-auto">
          {activeFilterCount > 0 && (
            <span className="text-xs text-muted-foreground">
              {total} Angebote
            </span>
          )}
          <div className="flex gap-1">
            <Button
              variant={viewMode === "cards" ? "default" : "outline"}
              size="icon"
              onClick={() => {
                setViewMode("cards")
                updateUrl({ view: "cards" })
              }}
              className="cursor-pointer"
              aria-label="Karten-Ansicht"
            >
              <LayoutGrid className="size-4" />
            </Button>
            <Button
              variant={viewMode === "table" ? "default" : "outline"}
              size="icon"
              onClick={() => {
                setViewMode("table")
                updateUrl({ view: "table" })
              }}
              className="cursor-pointer"
              aria-label="Tabellen-Ansicht"
            >
              <TableIcon className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile filter bar */}
      <div className="flex md:hidden items-center gap-2">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm" className="cursor-pointer">
              <SlidersHorizontal className="size-4" />
              Filter
              {activeFilterCount > 0 && (
                <span className="ml-1 inline-flex items-center justify-center size-5 rounded-full bg-primary text-primary-foreground text-[10px] font-bold">
                  {activeFilterCount}
                </span>
              )}
            </Button>
          </SheetTrigger>
          <SheetContent side="bottom" className="max-h-[80vh]">
            <SheetHeader>
              <SheetTitle>Filter &amp; Sortierung</SheetTitle>
            </SheetHeader>
            <div className="flex flex-col gap-4 p-4 overflow-y-auto">
              {filterControls}
              {hasActiveFilters && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={resetFilters}
                  className="cursor-pointer w-full mt-2"
                  aria-label="Filter und Sortierung zurücksetzen"
                >
                  <RotateCcw className="size-3.5 mr-1.5" />
                  Zurücksetzen
                </Button>
              )}
            </div>
          </SheetContent>
        </Sheet>
        <span className="text-xs text-muted-foreground ml-auto">
          {total} Angebote
        </span>
        <div className="flex gap-1">
          <Button
            variant={viewMode === "cards" ? "default" : "outline"}
            size="icon"
            onClick={() => {
              setViewMode("cards")
              updateUrl({ view: "cards" })
            }}
            className="cursor-pointer min-h-11 min-w-11"
            aria-label="Karten-Ansicht"
          >
            <LayoutGrid className="size-4" />
          </Button>
          <Button
            variant={viewMode === "table" ? "default" : "outline"}
            size="icon"
            onClick={() => {
              setViewMode("table")
              updateUrl({ view: "table" })
            }}
            className="cursor-pointer min-h-11 min-w-11"
            aria-label="Tabellen-Ansicht"
          >
            <TableIcon className="size-4" />
          </Button>
        </div>
      </div>

      {ads.length === 0 ? (
        <EmptyState message="Keine Angebote gefunden. Passe die Filter an oder erstelle neue Suchaufträge." />
      ) : viewMode === "cards" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {ads.map((ad) => (
            <AdCard key={ad.id} ad={ad} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border bg-card overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Titel</TableHead>
                <TableHead>Preis</TableHead>
                <TableHead>Score</TableHead>
                <TableHead className="hidden md:table-cell">Standort</TableHead>
                <TableHead>Gefunden</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ads.map((ad) => (
                <TableRow
                  key={ad.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/ads/${ad.id}`)}
                >
                  <TableCell className="font-medium max-w-[300px] truncate" title={ad.title}>
                    {ad.title}
                  </TableCell>
                  <TableCell>{formatPrice(ad.price)}</TableCell>
                  <TableCell>
                    <ScoreBadge score={ad.bargain_score} size="sm" />
                  </TableCell>
                  <TableCell className="text-muted-foreground hidden md:table-cell">
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Zeige {(safePage - 1) * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE, total)} von {total}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              disabled={safePage <= 1}
              onClick={() => goToPage(safePage - 1)}
              className="cursor-pointer"
              aria-label="Vorherige Seite"
            >
              <ChevronLeft className="size-4" />
            </Button>
            <span className="text-sm px-3">
              {safePage} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="icon"
              disabled={safePage >= totalPages}
              onClick={() => goToPage(safePage + 1)}
              className="cursor-pointer"
              aria-label="Nächste Seite"
            >
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
