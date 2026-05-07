"use client"

import { useState, useEffect, useCallback, type ReactNode } from "react"
import { usePathname, useRouter } from "next/navigation"
import {
  ArrowLeft,
  Pencil,
  Trash2,
  Loader2,
  MapPin,
  Clock,
  ExternalLink as ExternalLinkIcon,
  Tag,
  Euro,
  Star,
  Image as ImageIcon,
  type LucideIcon,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { SearchForm } from "@/components/search-form"
import { SearchStatusBadge } from "@/components/search-status-badge"
import { ScoreBadge } from "@/components/score-badge"
import { ExternalLink } from "@/components/external-link"
import { EmptyState } from "@/components/empty-state"
import { fetchSearch, fetchAds, updateSearch, deleteSearch } from "@/lib/api"
import type { Ad, AdSearch } from "@/lib/types"
import {
  formatPrice,
  formatScrapeInterval,
  formatSearchPriceRange,
  timeAgo,
  truncateUrl,
} from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { ContentReveal } from "@/components/content-reveal"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { cn } from "@/lib/utils"
import { usePageHead } from "../../page-head-context"

interface SearchDetailFieldProps {
  icon: LucideIcon
  label: string
  children: ReactNode
  className?: string
}

function SearchDetailField({ icon: Icon, label, children, className }: SearchDetailFieldProps) {
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

export function SearchDetailPage() {
  const router = useRouter()
  const pathname = usePathname()
  const { setTitle, setTitleSuffix } = usePageHead()
  const [id, setId] = useState<number>(NaN)

  useEffect(() => {
    const match = window.location.pathname.match(/\/(\d+)\/?$/)
    if (match) setId(Number(match[1]))
  }, [pathname])

  const [search, setSearch] = useState<AdSearch | null>(null)
  const [ads, setAds] = useState<Ad[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [formDirty, setFormDirty] = useState(false)

  const load = useCallback(async (opts?: { silent?: boolean }) => {
    if (Number.isNaN(id)) return
    if (!opts?.silent) {
      setLoading(true)
      setError(null)
    }
    try {
      const [s, a] = await Promise.all([
        fetchSearch(id),
        fetchAds({ adsearch_id: id }),
      ])
      setSearch(s)
      setAds(a.sort((x, y) => new Date(y.first_seen_at).getTime() - new Date(x.first_seen_at).getTime()))
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Daten konnten nicht geladen werden."
      if (!opts?.silent) {
        setError(msg)
        toast.error(msg)
        setSearch(null)
        setAds([])
      }
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  useRefetchOnFocus(() => load({ silent: true }))

  useEffect(() => {
    if (search) {
      setTitle(search.name)
      setTitleSuffix(<SearchStatusBadge isActive={search.is_active} />)
    }
    return () => setTitleSuffix(null)
  }, [search, setTitle, setTitleSuffix])

  async function handleUpdate(data: Partial<AdSearch>) {
    if (!search) return
    const updated = await updateSearch(id, data)
    setSearch(updated)
    setIsEditOpen(false)
    toast.success("Suchauftrag aktualisiert")
    // Errors propagate to SearchForm which shows them inline
  }

  async function handleDelete() {
    setIsDeleting(true)
    try {
      await deleteSearch(id)
      toast.success("Suchauftrag gelöscht")
      router.push("/searches")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Löschen fehlgeschlagen."
      toast.error(msg)
      setIsDeleting(false)
    }
  }

  async function handleToggleActive() {
    if (!search) return
    setIsToggling(true)
    try {
      const updated = await updateSearch(id, { is_active: !search.is_active })
      setSearch(updated)
      toast.success(updated.is_active ? "Suchauftrag aktiviert" : "Suchauftrag deaktiviert")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Aktualisierung fehlgeschlagen."
      toast.error(msg)
    } finally {
      setIsToggling(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-40" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (error || !search) {
    return (
      <ContentReveal className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-muted-foreground">{error || "Suchauftrag nicht gefunden."}</p>
        <Button variant="outline" onClick={() => router.push("/searches")} className="cursor-pointer">
          Zurück zur Übersicht
        </Button>
      </ContentReveal>
    )
  }

  return (
    <ContentReveal className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon-sm" onClick={() => router.push("/searches")} className="cursor-pointer" aria-label="Zurück">
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex-1 flex items-center justify-end gap-4 flex-wrap">
          <div className="flex items-center gap-2 mr-2">
            <Switch
              id="active-toggle"
              checked={search.is_active}
              onCheckedChange={handleToggleActive}
              disabled={isToggling}
              className="data-[state=checked]:border-primary data-[state=checked]:bg-primary"
            />
            <Label htmlFor="active-toggle" className="text-sm cursor-pointer">
              {search.is_active ? "Läuft" : "Pausiert"}
            </Label>
          </div>
          <Button variant="outline" size="sm" onClick={() => setIsEditOpen(true)} className="cursor-pointer">
              <Pencil className="size-3.5" />
              Bearbeiten
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="sm" disabled={isDeleting} className="cursor-pointer">
                  {isDeleting ? <Loader2 className="size-3.5 animate-spin" /> : <Trash2 className="size-3.5" />}
                  Löschen
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Suchauftrag löschen?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Der Suchauftrag &ldquo;{search.name}&rdquo; wird unwiderruflich gelöscht.
                    Bereits gefundene Angebote bleiben erhalten.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="cursor-pointer">Abbrechen</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handleDelete}
                    className="bg-destructive text-white hover:bg-destructive/90 cursor-pointer"
                  >
                    Löschen
                  </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <Card className="border-border/80 bg-card/95 py-0 shadow-sm">
        <CardContent className="p-4 sm:p-5">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            <SearchDetailField icon={ExternalLinkIcon} label="URL" className="md:col-span-2 lg:col-span-3">
              <ExternalLink href={search.url} className="break-all text-sm">
                {truncateUrl(search.url, 96)}
              </ExternalLink>
            </SearchDetailField>

            <SearchDetailField icon={Clock} label="Intervall">
              {formatScrapeInterval(search.scrape_interval_minutes)}
            </SearchDetailField>

            <SearchDetailField icon={Euro} label="Preisbereich">
              {formatSearchPriceRange(search)}
            </SearchDetailField>

            <SearchDetailField icon={Tag} label="Ausschluss">
              <div className="flex flex-wrap gap-1.5">
                {search.blacklist_keywords ? (
                  search.blacklist_keywords.split(",").map((kw, index) => (
                    <span
                      key={`${kw.trim()}-${index}`}
                      className="inline-flex items-center rounded-full border border-border/70 bg-card px-2 py-0.5 text-xs font-medium"
                    >
                      {kw.trim()}
                    </span>
                  ))
                ) : (
                  <span className="text-muted-foreground">Keine Keywords</span>
                )}
              </div>
            </SearchDetailField>

            {search.prompt_addition && (
              <SearchDetailField
                icon={Star}
                label="AI-Anweisungen"
                className="md:col-span-2 lg:col-span-3"
              >
                <p className="text-sm leading-relaxed">{search.prompt_addition}</p>
              </SearchDetailField>
            )}

            <SearchDetailField icon={ImageIcon} label="Bilder">
              {search.is_exclude_images ? "Ausgeschlossen" : "Eingeschlossen"}
            </SearchDetailField>

            <SearchDetailField icon={Clock} label="Letzte Suche">
              {timeAgo(search.last_scraped_at)}
            </SearchDetailField>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Tag className="size-5" />
              Angebote ({ads.length})
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {ads.length === 0 ? (
            <EmptyState
              message={
                search.last_scraped_at
                  ? "Noch keine Angebote für diese Suche."
                  : "Deine Suche läuft — erste Ergebnisse erscheinen in wenigen Minuten."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[250px]">Titel</TableHead>
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
                    <TableRow key={ad.id} className="cursor-pointer hover:bg-accent/50" onClick={() => router.push(`/ads/${ad.id}`)}>
                      <TableCell className="max-w-[250px] truncate text-muted-foreground" title={ad.title}>
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
        </CardContent>
      </Card>

      <Dialog open={isEditOpen} onOpenChange={(open) => {
        setIsEditOpen(open)
        if (!open) setFormDirty(false)
      }}>
        <DialogContent
          className="sm:max-w-xl max-h-[calc(100dvh-2rem)] overflow-y-auto overscroll-y-contain"
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>Suche bearbeiten</DialogTitle>
          </DialogHeader>
          <SearchForm
            initial={search}
            onSubmit={handleUpdate}
            onCancel={() => {
              setIsEditOpen(false)
              setFormDirty(false)
            }}
            onDirtyChange={setFormDirty}
          />
        </DialogContent>
      </Dialog>
    </ContentReveal>
  )
}
