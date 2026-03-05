"use client"

import { useState, useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"
import {
  ArrowLeft,
  Pencil,
  Trash2,
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
import { fetchSearch, fetchAds, updateSearch, deleteSearch } from "@/lib/api"
import type { Ad, AdSearch } from "@/lib/types"
import { formatPrice, timeAgo, truncateUrl } from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

export function SearchDetailPage() {
  const router = useRouter()
  const pathname = usePathname()
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

  useEffect(() => {
    if (Number.isNaN(id)) return
    async function load() {
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
    }
    load()
  }, [id])

  async function handleUpdate(data: Partial<AdSearch>) {
    if (!search) return
    try {
      const updated = await updateSearch(id, data)
      setSearch(updated)
      setIsEditOpen(false)
      toast.success("Suchauftrag aktualisiert")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Aktualisierung fehlgeschlagen."
      toast.error(msg)
    }
  }

  async function handleDelete() {
    if (!window.confirm("Suchauftrag wirklich loeschen?")) return
    try {
      await deleteSearch(id)
      toast.success("Suchauftrag geloescht")
      router.push("/searches")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Loeschen fehlgeschlagen."
      toast.error(msg)
    }
  }

  async function handleToggleActive() {
    if (!search) return
    try {
      const updated = await updateSearch(id, { is_active: !search.is_active })
      setSearch(updated)
      toast.success(updated.is_active ? "Suchauftrag aktiviert" : "Suchauftrag deaktiviert")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Aktualisierung fehlgeschlagen."
      toast.error(msg)
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
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-muted-foreground">{error || "Suchauftrag nicht gefunden."}</p>
        <Button variant="outline" onClick={() => router.push("/searches")} className="cursor-pointer">
          Zurueck zur Uebersicht
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon-sm" onClick={() => router.push("/searches")} className="cursor-pointer">
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex-1 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{search.name}</h1>
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
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 mr-2">
              <Switch
                id="active-toggle"
                checked={search.is_active}
                onCheckedChange={handleToggleActive}
              />
              <Label htmlFor="active-toggle" className="text-sm cursor-pointer">
                {search.is_active ? "Aktiv" : "Inaktiv"}
              </Label>
            </div>
            <Button variant="outline" size="sm" onClick={() => setIsEditOpen(true)} className="cursor-pointer">
              <Pencil className="size-3.5" />
              Bearbeiten
            </Button>
            <Button variant="destructive" size="sm" onClick={handleDelete} className="cursor-pointer">
              <Trash2 className="size-3.5" />
              Loeschen
            </Button>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Konfiguration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">URL</span>
              <div className="mt-0.5">
                <ExternalLink href={search.url}>{truncateUrl(search.url, 60)}</ExternalLink>
              </div>
            </div>
            <div>
              <span className="text-muted-foreground">Intervall</span>
              <p className="mt-0.5 text-foreground">Alle {search.scrape_interval_minutes} Minuten</p>
            </div>
            <div>
              <span className="text-muted-foreground">Preisbereich</span>
              <p className="mt-0.5 text-foreground">
                {search.min_price !== null || search.max_price !== null
                  ? `${search.min_price ?? 0} - ${search.max_price ?? "unbegrenzt"} EUR`
                  : "Nicht eingeschraenkt"}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Blacklist</span>
              <p className="mt-0.5 text-foreground">{search.blacklist_keywords || "Keine"}</p>
            </div>
            {search.prompt_addition && (
              <div className="md:col-span-2">
                <span className="text-muted-foreground">Prompt-Ergaenzung</span>
                <p className="mt-0.5 text-foreground">{search.prompt_addition}</p>
              </div>
            )}
            <div>
              <span className="text-muted-foreground">Bilder ausschliessen</span>
              <p className="mt-0.5 text-foreground">{search.is_exclude_images ? "Ja" : "Nein"}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Letzte Suche</span>
              <p className="mt-0.5 text-foreground">{timeAgo(search.last_scraped_at)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Angebote ({ads.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {ads.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              Noch keine Angebote fuer diese Suche.
            </p>
          ) : (
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
                {ads.map((ad) => (
                  <TableRow key={ad.id} className="cursor-pointer" onClick={() => router.push(`/ads/${ad.id}`)}>
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
          )}
        </CardContent>
      </Card>

      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Suche bearbeiten</DialogTitle>
          </DialogHeader>
          <SearchForm
            initial={search}
            onSubmit={handleUpdate}
            onCancel={() => setIsEditOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
