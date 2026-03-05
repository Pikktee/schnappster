"use client"

import { useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { PageHeader } from "@/components/page-header"
import { SearchCard } from "@/components/search-card"
import { SearchForm } from "@/components/search-form"
import { EmptyState } from "@/components/empty-state"
import { fetchSearches, createSearch, deleteSearch } from "@/lib/api"
import type { AdSearch } from "@/lib/types"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

export default function SearchesPage() {
  const [searches, setSearches] = useState<AdSearch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)

  async function loadSearches() {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchSearches()
      setSearches(data)
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Suchauftraege konnten nicht geladen werden."
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
      toast.success("Suchauftrag erstellt")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erstellen fehlgeschlagen."
      toast.error(msg)
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteSearch(id)
      setSearches((prev) => prev.filter((s) => s.id !== id))
      toast.success("Suchauftrag geloescht")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Loeschen fehlgeschlagen."
      toast.error(msg)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Suchauftraege" subtitle="Verwalte deine Kleinanzeigen-Suchen" />
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
        <PageHeader title="Suchauftraege" subtitle="Verwalte deine Kleinanzeigen-Suchen" />
        <p className="text-destructive">{error}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Suchauftraege" subtitle="Verwalte deine Kleinanzeigen-Suchen">
        <Button onClick={() => setIsCreateOpen(true)} className="cursor-pointer">
          <Plus className="size-4" />
          Neue Suche erstellen
        </Button>
      </PageHeader>

      {searches.length === 0 ? (
        <EmptyState
          message="Noch keine Suchauftraege. Erstelle deinen ersten!"
          actionLabel="Neue Suche erstellen"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {searches.map((search) => (
            <SearchCard key={search.id} search={search} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Neue Suche erstellen</DialogTitle>
          </DialogHeader>
          <SearchForm
            onSubmit={handleCreate}
            onCancel={() => setIsCreateOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
