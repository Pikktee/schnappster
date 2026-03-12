"use client"

import { useState, useEffect, useCallback } from "react"
import { usePathname, useRouter } from "next/navigation"
import {
  ArrowLeft,
  Pencil,
  Trash2,
  Loader2,
  MapPin,
  Clock,
  Tag,
  Euro,
  Star,
  Image as ImageIcon,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
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
import { ScoreBadge } from "@/components/score-badge"
import { ExternalLink } from "@/components/external-link"
import { EmptyState } from "@/components/empty-state"
import { fetchSearch, fetchAds, updateSearch, deleteSearch } from "@/lib/api"
import type { Ad, AdSearch } from "@/lib/types"
import { formatPrice, timeAgo, truncateUrl } from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { ContentReveal } from "@/components/content-reveal"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { usePageHead } from "../../page-head-context"

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

  const load = useCallback(async () => {
    if (Number.isNaN(id)) return
    setLoading(true)
    setError(null)
    try {
      const [s, a] = await Promise.all([
        fetchSearch(id),
        fetchAds({ adsearch_id: id }),
      ])
      setSearch(s)
      setAds(a.sort((x, y) => new Date(y.first_seen_at).getTime() - new Date(x.first_seen_at).getTime()))
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Daten konnten nicht geladen werden."
      setError(msg)
      toast.error(msg)
      setSearch(null)
      setAds([])
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  useRefetchOnFocus(load)

  useEffect(() => {
    if (search) {
      setTitle(search.name)
      setTitleSuffix(
        <Badge
          variant="secondary"
          className={
            search.is_active
              ? "bg-emerald-100 text-emerald-700 border-emerald-200"
              : "bg-muted text-muted-foreground"
          }
        >
          {search.is_active ? "Aktiv" : "Inaktiv"}
        </Badge>
      )
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
              className="data-[state=checked]:bg-emerald-500 data-[state=checked]:border-emerald-600"
            />
            <Label htmlFor="active-toggle" className="text-sm cursor-pointer">
              {search.is_active ? "Aktiv" : "Inaktiv"}
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

      <Card>
        <CardContent className="pt-2">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* URL - Full width */}
            <div className="md:col-span-2 lg:col-span-3">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">URL</span>
              </div>
              <div className="p-3 rounded-lg bg-muted/50 border">
                <ExternalLink href={search.url} className="text-sm break-all">{truncateUrl(search.url, 80)}</ExternalLink>
              </div>
            </div>

            {/* Interval */}
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <Clock className="size-3.5 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Intervall</span>
              </div>
              <p className="text-foreground font-medium">Alle {search.scrape_interval_minutes} Min.</p>
            </div>

            {/* Price Range */}
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <Euro className="size-3.5 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Preisbereich</span>
              </div>
              <p className="text-foreground font-medium">
                {search.min_price !== null || search.max_price !== null
                  ? `${search.min_price ?? 0} – ${search.max_price ?? "unbegrenzt"} €`
                  : "Nicht eingeschränkt"}
              </p>
            </div>

            {/* Ausschluss-Keywords */}
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <Tag className="size-3.5 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Ausschluss-Keywords</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {search.blacklist_keywords ? (
                  search.blacklist_keywords.split(",").map((kw, i) => (
                    <span key={i} className="inline-flex items-center px-2 py-0.5 rounded-md bg-muted text-xs font-medium">
                      {kw.trim()}
                    </span>
                  ))
                ) : (
                  <span className="text-muted-foreground">Keine</span>
                )}
              </div>
            </div>

            {/* Prompt Addition - Full width */}
            {search.prompt_addition && (
              <div className="md:col-span-2 lg:col-span-3">
                <div className="flex items-center gap-2 mb-1.5">
                  <Star className="size-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Zusätzliche Anweisungen</span>
                </div>
                <p className="p-3 rounded-lg bg-muted/50 border text-sm leading-relaxed">{search.prompt_addition}</p>
              </div>
            )}

            {/* Exclude Images */}
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <ImageIcon className="size-3.5 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Bilder</span>
              </div>
              <p className="text-foreground font-medium">{search.is_exclude_images ? "Ausgeschlossen" : "Eingeschlossen"}</p>
            </div>

            {/* Last Scrape */}
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <Clock className="size-3.5 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Letzte Suche</span>
              </div>
              <p className="text-foreground font-medium">{timeAgo(search.last_scraped_at)}</p>
            </div>
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
                      <TableCell className="font-medium max-w-[250px] truncate" title={ad.title}>
                        <span className="line-clamp-2 leading-snug">{ad.title}</span>
                      </TableCell>
                      <TableCell className="font-semibold">
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
        <DialogContent className="sm:max-w-xl" onInteractOutside={(e) => e.preventDefault()}>
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
