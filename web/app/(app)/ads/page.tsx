"use client"

import { Suspense, useEffect, useState, useCallback, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { LayoutGrid, TableIcon, SlidersHorizontal, ChevronLeft, ChevronRight, RotateCcw, Euro, Star, MapPin, Clock, SearchX } from "lucide-react"
import { Button } from "@/components/ui/button"
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
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { AdCard } from "@/components/ad-card"
import { ScoreBadge } from "@/components/score-badge"
import { EmptyState } from "@/components/empty-state"
import { ExternalLink } from "@/components/external-link"
import { ContentReveal } from "@/components/content-reveal"
import { fetchAdsPaginated, fetchSearches, ApiAbortError } from "@/lib/api"
import type { Ad, AdSearch } from "@/lib/types"
import { formatPrice, timeAgo } from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { useAbortSignal } from "@/hooks/use-abort-signal"

type SortOption = "date" | "price-asc" | "price-desc" | "score-desc"
type ViewMode = "cards" | "table"

const PAGE_SIZE = 24

const ADS_FILTERS_KEY = "schnappster-ads-filters"

type StoredFilters = {
  minScore: string
  searchId: string
  sortBy: SortOption
  viewMode: ViewMode
  page: number
}

function loadStoredFilters(): Partial<StoredFilters> | null {
  if (typeof window === "undefined") return null
  try {
    const raw = window.localStorage.getItem(ADS_FILTERS_KEY)
    if (!raw) return null
    return JSON.parse(raw) as Partial<StoredFilters>
  } catch {
    return null
  }
}

function saveStoredFilters(f: StoredFilters) {
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(ADS_FILTERS_KEY, JSON.stringify(f))
  } catch {
    // ignore
  }
}

export default function AdsPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col gap-6">
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

  const [minScore, setMinScore] = useState<string>(searchParams.get("minScore") ?? "0")
  const [searchId, setSearchId] = useState<string>(searchParams.get("search") || "all")
  const [sortBy, setSortBy] = useState<SortOption>((searchParams.get("sort") as SortOption) || "date")
  const [viewMode, setViewMode] = useState<ViewMode>((searchParams.get("view") as ViewMode) || "cards")
  const [page, setPage] = useState(Number(searchParams.get("page")) || 1)
  const loadRequestIdRef = useRef(0)
  const getSignal = useAbortSignal()

  const updateUrl = useCallback((params: Record<string, string>) => {
    const sp = new URLSearchParams(searchParams.toString())
    for (const [key, value] of Object.entries(params)) {
      if (value && value !== "0" && value !== "all" && value !== "date" && value !== "cards") {
        sp.set(key, value)
      } else {
        sp.delete(key)
      }
    }
    const qs = sp.toString()
    router.replace(`/ads${qs ? `?${qs}` : ""}`, { scroll: false })
  }, [searchParams, router])

  const loadAds = useCallback(async (p: number, score: string, search: string, sort: string) => {
    const requestId = ++loadRequestIdRef.current
    const signal = getSignal()
    setLoading(true)
    setError(null)
    try {
      const [result, s] = await Promise.all([
        fetchAdsPaginated({
          min_score: Number(score) || undefined,
          adsearch_id: search !== "all" ? Number(search) : undefined,
          is_analyzed: true,
          sort,
          limit: PAGE_SIZE,
          offset: (p - 1) * PAGE_SIZE,
          signal,
        }),
        fetchSearches({ signal }),
      ])
      setAds(result.items)
      setTotal(result.total)
      setSearches(s)
    } catch (e) {
      if (e instanceof ApiAbortError) return
      const msg = e instanceof Error ? e.message : "Angebote konnten nicht geladen werden."
      setError(msg)
      toast.error(msg)
    } finally {
      if (requestId === loadRequestIdRef.current && !signal.aborted) setLoading(false)
    }
  }, [getSignal])

  useEffect(() => {
    const stored = loadStoredFilters()
    const defaultSort: SortOption = "date"
    const defaultView: ViewMode = "cards"
    const validSort = (v: unknown): v is SortOption =>
      v === "date" || v === "price-asc" || v === "price-desc" || v === "score-desc"
    const validView = (v: unknown): v is ViewMode => v === "cards" || v === "table"
    const effective = {
      minScore: stored?.minScore ?? searchParams.get("minScore") ?? "0",
      searchId: stored?.searchId ?? searchParams.get("search") ?? "all",
      sortBy: validSort(stored?.sortBy) ? stored.sortBy : (searchParams.get("sort") as SortOption) || defaultSort,
      viewMode: validView(stored?.viewMode) ? stored.viewMode : (searchParams.get("view") as ViewMode) || defaultView,
      page: stored?.page ?? (Number(searchParams.get("page")) || 1),
    }
    setMinScore(effective.minScore)
    setSearchId(effective.searchId)
    setSortBy(effective.sortBy)
    setViewMode(effective.viewMode)
    setPage(effective.page)
    updateUrl({
      minScore: effective.minScore,
      search: effective.searchId,
      sort: effective.sortBy,
      view: effective.viewMode,
      page: effective.page === 1 ? "0" : String(effective.page),
    })
    loadAds(effective.page, effective.minScore, effective.searchId, effective.sortBy)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useRefetchOnFocus(() => loadAds(page, minScore, searchId, sortBy))

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
    saveFilters({ minScore, searchId, sortBy, viewMode, page: p })
    reload(p)
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
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
      <ContentReveal className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-4 py-12">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" onClick={() => loadAds(page, minScore, searchId, sortBy)} className="cursor-pointer">
            Erneut laden
          </Button>
        </div>
      </ContentReveal>
    )
  }

  const activeFilterCount = [
    minScore !== "0",
    searchId !== "all",
    sortBy !== "date",
  ].filter(Boolean).length

  const hasActiveFilters = activeFilterCount > 0

  function saveFilters(f: { minScore: string; searchId: string; sortBy: SortOption; viewMode: ViewMode; page: number }) {
    saveStoredFilters(f)
  }

  function resetFilters() {
    setMinScore("0")
    setSearchId("all")
    setSortBy("date")
    setPage(1)
    updateUrl({ minScore: "0", search: "all", sort: "date", page: "0" })
    saveFilters({ minScore: "0", searchId: "all", sortBy: "date", viewMode, page: 1 })
    reload(1, "0", "all", "date")
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
            saveFilters({ minScore: v, searchId, sortBy, viewMode, page: 1 })
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
            saveFilters({ minScore, searchId: v, sortBy, viewMode, page: 1 })
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
            saveFilters({ minScore, searchId, sortBy: v as SortOption, viewMode, page: 1 })
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
    <ContentReveal className="flex flex-col gap-6">
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
          <span className="text-xs text-muted-foreground">
            {total} Angebote
          </span>
          <div className="flex gap-1">
            <Button
              variant={viewMode === "cards" ? "default" : "outline"}
              size="icon"
              onClick={() => {
                setViewMode("cards")
                updateUrl({ view: "cards" })
                saveFilters({ minScore, searchId, sortBy, viewMode: "cards", page })
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
                saveFilters({ minScore, searchId, sortBy, viewMode: "table", page })
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
              saveFilters({ minScore, searchId, sortBy, viewMode: "cards", page })
            }}
          >
            <LayoutGrid className="size-4" />
          </Button>
          <Button
            variant={viewMode === "table" ? "default" : "outline"}
            size="icon"
            onClick={() => {
              setViewMode("table")
              updateUrl({ view: "table" })
              saveFilters({ minScore, searchId, sortBy, viewMode: "table", page })
            }}
            className="cursor-pointer min-h-11 min-w-11"
            aria-label="Tabellen-Ansicht"
          >
            <TableIcon className="size-4" />
          </Button>
        </div>
      </div>

      {ads.length === 0 ? (
        <EmptyState
          message="Keine Angebote gefunden. Passe die Filter an oder warte auf neue Analysen."
          icon={<SearchX className="size-12 text-muted-foreground/50" />}
        />
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
                <TableHead>
                  <div className="flex items-center gap-1.5">
                    <Euro className="size-3.5" />
                    Preis
                  </div>
                </TableHead>
                <TableHead>
                  <div className="flex items-center gap-1.5">
                    <Star className="size-3.5" />
                    Score
                  </div>
                </TableHead>
                <TableHead className="hidden lg:table-cell">
                  <div className="flex items-center gap-1.5">
                    <MapPin className="size-3.5" />
                    Standort
                  </div>
                </TableHead>
                <TableHead>
                  <div className="flex items-center gap-1.5">
                    <Clock className="size-3.5" />
                    Gefunden
                  </div>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ads.map((ad) => (
                <TableRow
                  key={ad.id}
                  className="cursor-pointer hover:bg-accent/50"
                  onClick={() => router.push(`/ads/${ad.id}`)}
                >
                  <TableCell className="max-w-[300px] truncate text-muted-foreground" title={ad.title}>
                    {ad.title}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatPrice(ad.price)}
                  </TableCell>
                  <TableCell>
                    <ScoreBadge score={ad.bargain_score} size="sm" />
                  </TableCell>
                  <TableCell className="hidden lg:table-cell">
                    <span onClick={(e) => e.stopPropagation()} className="inline-flex items-center min-w-0">
                      <ExternalLink
                        href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(ad.postal_code + " " + ad.city)}`}
                        className="inline-flex items-center gap-1 min-w-0 max-w-[150px]"
                        title={`Auf Google Maps öffnen: ${ad.postal_code} ${ad.city}`}
                      >
                        <MapPin className="size-3.5 shrink-0" />
                        <span className="truncate">{ad.postal_code} {ad.city}</span>
                      </ExternalLink>
                    </span>
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
    </ContentReveal>
  )
}
