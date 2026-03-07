"use client"

import { useState, useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"
import {
  ArrowLeft,
  Pencil,
  Trash2,
  Loader2,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
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
  const [isDeleting, setIsDeleting] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [formDirty, setFormDirty] = useState(false)
  const [confirmClose, setConfirmClose] = useState(false)

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
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-muted-foreground">{error || "Suchauftrag nicht gefunden."}</p>
        <Button variant="outline" onClick={() => router.push("/searches")} className="cursor-pointer">
          Zurück zur Übersicht
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/">Start</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink href="/searches">Suchaufträge</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{search.name}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon-sm" onClick={() => router.push("/searches")} className="cursor-pointer" aria-label="Zurück">
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
                disabled={isToggling}
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
                <span className="text-muted-foreground">Prompt-Ergänzung</span>
                <p className="mt-0.5 text-foreground">{search.prompt_addition}</p>
              </div>
            )}
            <div>
              <span className="text-muted-foreground">Bilder ausschließen</span>
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
            <EmptyState
              message={
                search.last_scraped_at
                  ? "Noch keine Angebote für diese Suche."
                  : "Deine Suche laeuft — erste Ergebnisse erscheinen in wenigen Minuten."
              }
            />
          ) : (
            <div className="overflow-x-auto">
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
                    <TableRow key={ad.id} className="cursor-pointer" onClick={() => router.push(`/ads/${ad.id}`)}>
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
        </CardContent>
      </Card>

      <Dialog open={isEditOpen} onOpenChange={(open) => {
        if (!open && formDirty) {
          setConfirmClose(true)
          return
        }
        setIsEditOpen(open)
        if (!open) setFormDirty(false)
      }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Suche bearbeiten</DialogTitle>
          </DialogHeader>
          <SearchForm
            initial={search}
            onSubmit={handleUpdate}
            onCancel={() => {
              if (formDirty) {
                setConfirmClose(true)
                return
              }
              setIsEditOpen(false)
              setFormDirty(false)
            }}
            onDirtyChange={setFormDirty}
          />
        </DialogContent>
      </Dialog>

      <AlertDialog open={confirmClose} onOpenChange={setConfirmClose}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Ungespeicherte Änderungen</AlertDialogTitle>
            <AlertDialogDescription>
              Du hast ungespeicherte Änderungen. Wirklich schließen?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="cursor-pointer">Abbrechen</AlertDialogCancel>
            <AlertDialogAction
              className="cursor-pointer"
              onClick={() => {
                setIsEditOpen(false)
                setFormDirty(false)
              }}
            >
              Schließen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
