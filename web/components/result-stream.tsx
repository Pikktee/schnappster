"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  Flame,
  LayoutGrid,
  Loader2,
  RotateCcw,
  SearchX,
  SlidersHorizontal,
  TableIcon,
  TrendingDown,
} from "lucide-react"
import { Button } from "@/components/ui/button"
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
import { AdCard } from "@/components/ad-card"
import { DealCard } from "@/components/deal-card"
import { PriceEventCard } from "@/components/price-event-card"
import { ScoreBadge } from "@/components/score-badge"
import { EmptyState } from "@/components/empty-state"
import { fetchFeed } from "@/lib/api"
import type { FeedItem } from "@/lib/types"
import { formatPrice, getAdSource, timeAgo } from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { cn } from "@/lib/utils"

const PAGE_SIZE = 24

type SortOption = "date" | "price-asc" | "price-desc" | "score-desc"
type ViewMode = "cards" | "table"

const SOURCE_CHIPS: { key: string; label: string }[] = [
  { key: "all", label: "Alle" },
  { key: "kleinanzeigen", label: "Kleinanzeigen" },
  { key: "ebay", label: "eBay" },
  { key: "mydealz", label: "MyDealz" },
  { key: "price", label: "Preis-Alarme" },
]

interface StoredFilters {
  source: string
  sortBy: SortOption
  viewMode: ViewMode
}

function loadStored(key: string): Partial<StoredFilters> | null {
  if (typeof window === "undefined") return null
  try {
    const raw = window.localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as Partial<StoredFilters>) : null
  } catch {
    return null
  }
}

/** Datums-Gruppe eines Stream-Elements (nur bei chronologischer Sortierung genutzt). */
function groupLabel(iso: string): string {
  const normalized = iso.includes("+") || iso.endsWith("Z") ? iso : iso + "Z"
  const then = new Date(normalized)
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const startOfThen = new Date(then.getFullYear(), then.getMonth(), then.getDate()).getTime()
  const diffDays = Math.round((startOfToday - startOfThen) / 86_400_000)
  if (diffDays <= 0) return "Heute"
  if (diffDays === 1) return "Gestern"
  if (diffDays < 7) return "Diese Woche"
  return "Früher"
}

function itemKey(item: FeedItem): string {
  if (item.ad) return `ad-${item.ad.id}`
  if (item.deal) return `deal-${item.deal.external_id}`
  if (item.price_event) return `price-${item.price_event.watch_id}-${item.price_event.recorded_at}`
  return item.occurred_at
}

interface ResultStreamProps {
  /** Begrenzt den Stream auf einen Suchauftrag (Detail-Seite); blendet Preis-Alarme aus. */
  searchOrderId?: number
  /** localStorage-Schlüssel für Filter-Persistenz (nur auf der Startseite gesetzt). */
  storageKey?: string
  /**
   * Serverseitiger Mindest-Score für Anzeigen (aus den Einstellungen).
   * Deals und Preis-Ereignisse haben eigene Kriterien und bleiben sichtbar.
   */
  minScore?: number
  /**
   * Beschränkt die Quellen-Filter auf die tatsächlich genutzten Plattformen eines Suchauftrags
   * (z. B. `["kleinanzeigen", "ebay"]`). Bei ≤1 Quelle entfällt der Filter komplett.
   * Ohne Angabe (Startseite) werden alle Quellen angeboten.
   */
  availableSources?: string[]
}

export function ResultStream({
  searchOrderId,
  storageKey,
  minScore,
  availableSources,
}: ResultStreamProps) {
  const router = useRouter()
  const [items, setItems] = useState<FeedItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [source, setSource] = useState("all")
  const [sortBy, setSortBy] = useState<SortOption>("date")
  const [viewMode, setViewMode] = useState<ViewMode>("cards")
  const [restored, setRestored] = useState(!storageKey)

  const chips = useMemo(() => {
    let list = SOURCE_CHIPS.filter((chip) => chip.key !== "price" || searchOrderId === undefined)
    if (availableSources) {
      list = list.filter((chip) => chip.key === "all" || availableSources.includes(chip.key))
    }
    return list
  }, [searchOrderId, availableSources])

  // Bei einem Suchauftrag mit nur einer Quelle ist der Filter sinnlos → ganz ausblenden.
  const showSourceFilter = availableSources ? availableSources.length > 1 : true

  const load = useCallback(
    async (opts: { offset: number; append: boolean; silent?: boolean }) => {
      if (!opts.append && !opts.silent) setLoading(true)
      if (opts.append) setLoadingMore(true)
      setError(null)
      try {
        const page = await fetchFeed({
          limit: PAGE_SIZE,
          offset: opts.offset,
          source,
          min_score: minScore || undefined,
          search_order_id: searchOrderId,
          sort: sortBy,
        })
        setItems((prev) => (opts.append ? [...prev, ...page.items] : page.items))
        setTotal(page.total)
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Der Stream konnte nicht geladen werden."
        if (!opts.silent) {
          setError(msg)
          toast.error(msg)
        }
      } finally {
        setLoading(false)
        setLoadingMore(false)
      }
    },
    [source, sortBy, minScore, searchOrderId],
  )

  // Persistierte Filter einmalig wiederherstellen, dann normal laden.
  useEffect(() => {
    if (!storageKey) return
    const stored = loadStored(storageKey)
    if (stored) {
      if (stored.source) setSource(stored.source)
      if (stored.sortBy) setSortBy(stored.sortBy)
      if (stored.viewMode) setViewMode(stored.viewMode)
    }
    setRestored(true)
  }, [storageKey])

  useEffect(() => {
    if (!restored) return
    if (storageKey && typeof window !== "undefined") {
      window.localStorage.setItem(storageKey, JSON.stringify({ source, sortBy, viewMode }))
    }
    load({ offset: 0, append: false })
  }, [restored, load]) // eslint-disable-line react-hooks/exhaustive-deps

  useRefetchOnFocus(() =>
    load({ offset: 0, append: false, silent: true }),
  )

  // Endless Scrolling: sobald der Sentinel am Listenende sichtbar wird, nächste Seite anhängen.
  // rootMargin lädt schon 600px vor Erreichen vor; der loadingMore-Guard verhindert Doppel-Laden.
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const hasMore = items.length < total

  useEffect(() => {
    const el = sentinelRef.current
    if (!el || !hasMore || loading) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !loadingMore) {
          load({ offset: items.length, append: true })
        }
      },
      { rootMargin: "600px" },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [hasMore, loading, loadingMore, items.length, load])

  const hasActiveFilters = source !== "all" || sortBy !== "date"

  function resetFilters() {
    setSource("all")
    setSortBy("date")
  }

  // Datumsgruppen nur bei Chronologie — bei Preis-/Score-Sortierung eine flache Liste.
  const groups = useMemo(() => {
    if (sortBy !== "date") return [{ label: null as string | null, items }]
    const result: { label: string | null; items: FeedItem[] }[] = []
    for (const item of items) {
      const label = groupLabel(item.occurred_at)
      const last = result[result.length - 1]
      if (last && last.label === label) last.items.push(item)
      else result.push({ label, items: [item] })
    }
    return result
  }, [items, sortBy])

  function rowTarget(item: FeedItem): { href?: string; external?: string } {
    if (item.ad) return { href: `/ads/${item.ad.id}` }
    if (item.deal) return { external: item.deal.url }
    if (item.price_event) return { href: `/price-alerts/${item.price_event.watch_id}` }
    return {}
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-4">
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

  if (error) {
    return (
      <div className="flex flex-col items-center gap-4 py-12">
        <p className="text-destructive">{error}</p>
        <Button
          variant="outline"
          onClick={() => load({ offset: 0, append: false })}
          className="cursor-pointer"
        >
          Erneut laden
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Filterleiste */}
      <div className="flex flex-wrap items-center gap-2">
        {showSourceFilter && (
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Quelle filtern">
            {chips.map((chip) => (
              <Button
                key={chip.key}
                type="button"
                variant={source === chip.key ? "default" : "outline"}
                size="sm"
                onClick={() => setSource(chip.key)}
                className="h-8 cursor-pointer rounded-full px-3 text-xs"
                aria-pressed={source === chip.key}
              >
                {chip.key === "mydealz" && <Flame className="size-3" aria-hidden />}
                {chip.key === "price" && <TrendingDown className="size-3" aria-hidden />}
                {chip.label}
              </Button>
            ))}
          </div>
        )}

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
            <SelectTrigger className="h-8 w-40 text-xs" aria-label="Sortierung">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date">Neueste zuerst</SelectItem>
              <SelectItem value="price-asc">Preis aufsteigend</SelectItem>
              <SelectItem value="price-desc">Preis absteigend</SelectItem>
              <SelectItem value="score-desc">Score absteigend</SelectItem>
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={resetFilters}
              className="h-8 cursor-pointer text-muted-foreground hover:text-foreground"
              aria-label="Filter zurücksetzen"
            >
              <RotateCcw className="size-3.5" />
            </Button>
          )}

          <div className="flex gap-1">
            <Button
              variant={viewMode === "cards" ? "default" : "outline"}
              size="icon"
              onClick={() => setViewMode("cards")}
              className="size-8 cursor-pointer"
              aria-label="Karten-Ansicht"
            >
              <LayoutGrid className="size-4" />
            </Button>
            <Button
              variant={viewMode === "table" ? "default" : "outline"}
              size="icon"
              onClick={() => setViewMode("table")}
              className="size-8 cursor-pointer"
              aria-label="Tabellen-Ansicht"
            >
              <TableIcon className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      <p className="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
        <span>
          {total} {total === 1 ? "Ergebnis" : "Ergebnisse"}
        </span>
        {(minScore ?? 0) > 0 && (
          <>
            <span aria-hidden>·</span>
            <Link
              href="/settings"
              className="inline-flex items-center gap-1 underline-offset-4 transition-colors hover:text-foreground hover:underline"
              title="Mindest-Score in den Einstellungen ändern"
            >
              <SlidersHorizontal className="size-3" aria-hidden />
              Angebote ab Score {minScore}
            </Link>
          </>
        )}
      </p>

      {items.length === 0 ? (
        <EmptyState
          message={
            (minScore ?? 0) > 0
              ? `Noch nichts Relevantes — Angebote erscheinen hier ab Score ${minScore}, dazu neue Deals und ausgelöste Preis-Alarme.`
              : "Noch keine Ergebnisse — sobald deine Suchaufträge und Alarme fündig werden, erscheint hier alles Neue."
          }
          icon={<SearchX className="size-12 text-muted-foreground/50" />}
        />
      ) : viewMode === "cards" ? (
        <div className="flex flex-col gap-5">
          {groups.map((group, gi) => (
            <section key={group.label ?? `flat-${gi}`} className="flex flex-col gap-3">
              {group.label && (
                <h2 className="flex items-center gap-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {group.label}
                  <span className="h-px flex-1 bg-border/70" aria-hidden />
                </h2>
              )}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {group.items.map((item) => (
                  <div key={itemKey(item)} className="min-w-0">
                    {item.ad && <AdCard ad={item.ad} />}
                    {item.deal && <DealCard deal={item.deal} />}
                    {item.price_event && <PriceEventCard event={item.price_event} />}
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Titel</TableHead>
                <TableHead>Preis</TableHead>
                <TableHead>Bewertung</TableHead>
                <TableHead className="hidden sm:table-cell">Quelle</TableHead>
                <TableHead>Zeit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => {
                const target = rowTarget(item)
                const title = item.ad?.title ?? item.deal?.title ?? item.price_event?.watch_name
                const price = item.ad?.price ?? item.deal?.price ?? item.price_event?.price
                const sourceLabel = item.ad
                  ? getAdSource(item.ad.url).label
                  : item.deal
                    ? "MyDealz"
                    : "Preis-Alarm"
                return (
                  <TableRow
                    key={itemKey(item)}
                    className="cursor-pointer hover:bg-accent/50"
                    onClick={() => {
                      if (target.href) router.push(target.href)
                      else if (target.external) window.open(target.external, "_blank", "noopener")
                    }}
                  >
                    <TableCell className="max-w-[320px] truncate text-muted-foreground" title={title}>
                      {title}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{formatPrice(price ?? null)}</TableCell>
                    <TableCell>
                      {item.ad ? (
                        <ScoreBadge score={item.ad.bargain_score} size="sm" />
                      ) : item.deal?.temperature != null ? (
                        <span
                          className={cn(
                            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums",
                            item.deal.temperature >= 300
                              ? "bg-red-500/15 text-red-600"
                              : item.deal.temperature >= 150
                                ? "bg-amber-500/15 text-amber-600"
                                : "bg-muted text-muted-foreground",
                          )}
                        >
                          <Flame className="size-3" aria-hidden />
                          {Math.round(item.deal.temperature)}°
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="hidden text-muted-foreground sm:table-cell">
                      {sourceLabel}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {timeAgo(item.occurred_at)}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {hasMore && (
        <div
          ref={sentinelRef}
          className="flex items-center justify-center gap-2 py-4 text-xs text-muted-foreground"
          aria-live="polite"
        >
          {loadingMore ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden />
              Weitere Ergebnisse werden geladen …
            </>
          ) : (
            <span className="tabular-nums">
              {items.length} von {total}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
