"use client"

import { useEffect, useState } from "react"
import { Flame, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { DealWatchCard } from "@/components/deal-watch-card"
import { DealWatchForm } from "@/components/deal-watch-form"
import { EmptyState } from "@/components/empty-state"
import { ContentReveal } from "@/components/content-reveal"
import { Skeleton } from "@/components/ui/skeleton"
import { deleteDealWatch, fetchDealWatch, fetchDealWatches } from "@/lib/api"
import type { DealWatch } from "@/lib/types"
import { toast } from "sonner"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { usePageHead } from "../page-head-context"

export default function DealAlarmsPage() {
  const [watches, setWatches] = useState<DealWatch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const { setHeaderActions } = usePageHead()

  async function loadWatches(opts?: { silent?: boolean }) {
    if (!opts?.silent) {
      setLoading(true)
      setError(null)
    }
    try {
      setWatches(await fetchDealWatches())
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Deal-Alarme konnten nicht geladen werden."
      if (!opts?.silent) {
        setError(msg)
        toast.error(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadWatches()
  }, [])

  useRefetchOnFocus(() => loadWatches({ silent: true }))

  useEffect(() => {
    if (!loading && !error) {
      setHeaderActions(
        <Button onClick={() => setIsCreateOpen(true)} className="cursor-pointer">
          <Plus className="size-4" />
          Neuer Deal-Alarm
        </Button>,
      )
    } else {
      setHeaderActions(null)
    }
    return () => setHeaderActions(null)
  }, [loading, error, setHeaderActions])

  function handleCreated(watch: DealWatch) {
    setWatches((prev) => [watch, ...prev])
    setIsCreateOpen(false)
    toast.success("Deal-Alarm erstellt — die ersten Deals werden gleich geladen.")
    void pollUntilChecked(watch.id)
  }

  // Der erste (stille) Check läuft im Hintergrund; nachziehen bis last_checked_at gesetzt ist.
  async function pollUntilChecked(id: number) {
    const MAX_ATTEMPTS = 20
    const INTERVAL_MS = 2500
    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, INTERVAL_MS))
      let updated: DealWatch
      try {
        updated = await fetchDealWatch(id)
      } catch {
        return
      }
      setWatches((prev) => prev.map((w) => (w.id === id ? updated : w)))
      if (updated.last_checked_at != null) return
    }
  }

  async function handleDelete(id: number) {
    setDeletingId(id)
    try {
      await deleteDealWatch(id)
      setWatches((prev) => prev.filter((w) => w.id !== id))
      toast.success("Deal-Alarm gelöscht")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Löschen fehlgeschlagen.")
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 2xl:grid-cols-4">
        <Skeleton className="h-[208px] rounded-xl" />
        <Skeleton className="h-[208px] rounded-xl" />
        <Skeleton className="h-[208px] rounded-xl" />
      </div>
    )
  }

  if (error) {
    return (
      <ContentReveal className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-4 py-12">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" onClick={() => loadWatches()} className="cursor-pointer">
            Erneut laden
          </Button>
        </div>
      </ContentReveal>
    )
  }

  return (
    <ContentReveal className="flex flex-col gap-6">
      {watches.length === 0 ? (
        <EmptyState
          message="Überwache MyDealz-Suchbegriffe auf neue heiße Deals. Lege deinen ersten Deal-Alarm an."
          icon={<Flame className="size-12 text-muted-foreground/50" />}
          actionLabel="Neuer Deal-Alarm"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : (
        <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 2xl:grid-cols-4">
          {watches.map((watch) => (
            <li key={watch.id} className="min-w-0">
              <DealWatchCard
                watch={watch}
                onDelete={handleDelete}
                isDeleting={deletingId === watch.id}
              />
            </li>
          ))}
        </ul>
      )}

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent
          className="max-h-[calc(100dvh-2rem)] overflow-y-auto overscroll-y-contain sm:max-w-lg"
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>Neuen Deal-Alarm erstellen</DialogTitle>
          </DialogHeader>
          <DealWatchForm onCreated={handleCreated} onCancel={() => setIsCreateOpen(false)} />
        </DialogContent>
      </Dialog>
    </ContentReveal>
  )
}
