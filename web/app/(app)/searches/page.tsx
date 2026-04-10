"use client"

import { useEffect, useState } from "react"
import { Plus, SearchX } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { SearchCard } from "@/components/search-card"
import { SearchForm } from "@/components/search-form"
import { EmptyState } from "@/components/empty-state"
import { ContentReveal } from "@/components/content-reveal"
import { fetchSearches, createSearch, deleteSearch } from "@/lib/api"
import type { AdSearch } from "@/lib/types"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { usePageHead } from "../page-head-context"

export default function SearchesPage() {
  const [searches, setSearches] = useState<AdSearch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [formDirty, setFormDirty] = useState(false)
  const { setHeaderActions } = usePageHead()

  async function loadSearches(opts?: { silent?: boolean }) {
    if (!opts?.silent) {
      setLoading(true)
      setError(null)
    }
    try {
      const data = await fetchSearches()
      setSearches(data)
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Suchaufträge konnten nicht geladen werden."
      if (!opts?.silent) {
        setError(msg)
        toast.error(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSearches()
  }, [])

  useRefetchOnFocus(() => loadSearches({ silent: true }))

  useEffect(() => {
    if (!loading && !error) {
      setHeaderActions(
        <Button onClick={() => setIsCreateOpen(true)} className="cursor-pointer">
          <Plus className="size-4" />
          Neuer Suchauftrag
        </Button>
      )
    } else {
      setHeaderActions(null)
    }
    return () => setHeaderActions(null)
  }, [loading, error, setHeaderActions])

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
    } finally {
      setIsCreating(false)
    }
    // Errors propagate to SearchForm which shows them inline
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 2xl:grid-cols-4 gap-4 sm:gap-5">
          <Skeleton className="h-[140px] rounded-xl" />
          <Skeleton className="h-[140px] rounded-xl" />
          <Skeleton className="h-[140px] rounded-xl" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <ContentReveal className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-4 py-12">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" onClick={loadSearches} className="cursor-pointer">
            Erneut laden
          </Button>
        </div>
      </ContentReveal>
    )
  }

  return (
    <ContentReveal className="flex flex-col gap-6">
      {searches.length === 0 ? (
        <EmptyState
          message="Erstelle deinen ersten Suchauftrag, um automatisch nach Schnäppchen zu suchen."
          icon={<SearchX className="size-12 text-muted-foreground/50" />}
        />
      ) : (
        <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 2xl:grid-cols-4 gap-4 sm:gap-5 list-none p-0 m-0">
          {searches.map((search) => (
            <li key={search.id} className="min-w-0">
              <SearchCard
                search={search}
                onDelete={handleDelete}
                isDeleting={deletingId === search.id}
              />
            </li>
          ))}
        </ul>
      )}

      <Dialog open={isCreateOpen} onOpenChange={(open) => {
        setIsCreateOpen(open)
        if (!open) setFormDirty(false)
      }}>
        <DialogContent className="sm:max-w-xl" onInteractOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>Neuen Suchauftrag erstellen</DialogTitle>
          </DialogHeader>
          <SearchForm
            onSubmit={handleCreate}
            onCancel={() => {
              setIsCreateOpen(false)
              setFormDirty(false)
            }}
            isLoading={isCreating}
            onDirtyChange={setFormDirty}
          />
        </DialogContent>
      </Dialog>
    </ContentReveal>
  )
}
