"use client"

import { useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
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
} from "@/components/ui/alert-dialog"
import { PageHeader } from "@/components/page-header"
import { SearchCard } from "@/components/search-card"
import { SearchForm } from "@/components/search-form"
import { EmptyState } from "@/components/empty-state"
import { fetchSearches, createSearch, deleteSearch, triggerScrape } from "@/lib/api"
import type { AdSearch } from "@/lib/types"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

export default function SearchesPage() {
  const [searches, setSearches] = useState<AdSearch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [formDirty, setFormDirty] = useState(false)
  const [confirmClose, setConfirmClose] = useState(false)

  async function loadSearches() {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSearches()
      setSearches(data)
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Suchaufträge konnten nicht geladen werden."
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSearches()
  }, [])

  async function handleCreate(data: Partial<AdSearch>) {
    setIsCreating(true)
    try {
      const newSearch = await createSearch({
        name: data.name || "",
        url: data.url || "",
        prompt_addition: data.prompt_addition ?? null,
        min_price: data.min_price ?? null,
        max_price: data.max_price ?? null,
        blacklist_keywords: data.blacklist_keywords || null,
        is_exclude_images: data.is_exclude_images ?? false,
        is_active: true,
        scrape_interval_minutes: data.scrape_interval_minutes ?? 60,
      })
      setSearches((prev) => [newSearch, ...prev])
      setIsCreateOpen(false)
      toast.success("Suchauftrag erstellt — erste Ergebnisse erscheinen in wenigen Minuten.")
      triggerScrape(newSearch.id).catch(() => {})
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erstellen fehlgeschlagen."
      toast.error(msg)
    } finally {
      setIsCreating(false)
    }
  }

  async function handleDelete(id: number) {
    setDeletingId(id)
    try {
      await deleteSearch(id)
      setSearches((prev) => prev.filter((s) => s.id !== id))
      toast.success("Suchauftrag gelöscht")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Löschen fehlgeschlagen."
      toast.error(msg)
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Suchaufträge" subtitle="Verwalte deine Kleinanzeigen-Suchen" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Suchaufträge" subtitle="Verwalte deine Kleinanzeigen-Suchen" />
        <div className="flex flex-col items-center gap-4 py-12">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" onClick={loadSearches} className="cursor-pointer">
            Erneut laden
          </Button>
        </div>
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
            <BreadcrumbPage>Suchaufträge</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <PageHeader title="Suchaufträge" subtitle="Verwalte deine Kleinanzeigen-Suchen">
        <Button onClick={() => setIsCreateOpen(true)} className="cursor-pointer">
          <Plus className="size-4" />
          Neue Suche erstellen
        </Button>
      </PageHeader>

      {searches.length === 0 ? (
        <EmptyState
          message="Noch keine Suchaufträge. Erstelle deinen ersten!"
          actionLabel="Neue Suche erstellen"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {searches.map((search) => (
            <SearchCard
              key={search.id}
              search={search}
              onDelete={handleDelete}
              isDeleting={deletingId === search.id}
            />
          ))}
        </div>
      )}

      <Dialog open={isCreateOpen} onOpenChange={(open) => {
        if (!open && formDirty) {
          setConfirmClose(true)
          return
        }
        setIsCreateOpen(open)
        if (!open) setFormDirty(false)
      }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Neue Suche erstellen</DialogTitle>
          </DialogHeader>
          <SearchForm
            onSubmit={handleCreate}
            onCancel={() => {
              if (formDirty) {
                setConfirmClose(true)
                return
              }
              setIsCreateOpen(false)
              setFormDirty(false)
            }}
            isLoading={isCreating}
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
                setIsCreateOpen(false)
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
