"use client"

import { useEffect, useState } from "react"
import { Plus, TrendingDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { PriceWatchCard } from "@/components/price-watch-card"
import { PriceWatchWizard } from "@/components/price-watch-wizard"
import { EmptyState } from "@/components/empty-state"
import { ContentReveal } from "@/components/content-reveal"
import { Skeleton } from "@/components/ui/skeleton"
import {
  deletePriceWatch,
  fetchPriceWatch,
  fetchPriceWatches,
  updatePriceWatch,
} from "@/lib/api"
import type { PriceWatch } from "@/lib/types"
import { toast } from "sonner"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { usePageHead } from "../page-head-context"

export default function PriceAlertsPage() {
  const [watches, setWatches] = useState<PriceWatch[]>([])
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
      setWatches(await fetchPriceWatches())
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Preis-Alarme konnten nicht geladen werden."
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
          Neuer Preis-Alarm
        </Button>,
      )
    } else {
      setHeaderActions(null)
    }
    return () => setHeaderActions(null)
  }, [loading, error, setHeaderActions])

  function handleCreated(watch: PriceWatch) {
    setWatches((prev) => [watch, ...prev])
    setIsCreateOpen(false)
    toast.success("Preis-Alarm erstellt — der erste Preis wird gleich geprüft.")
    void pollUntilChecked(watch.id)
  }

  // Der erste Preis-Check läuft im Hintergrund. Hier den neuen Watch nachziehen, bis der Check
  // durch ist (last_checked_at gesetzt), damit "Wird geprüft…" ohne Reload aktualisiert wird.
  async function pollUntilChecked(id: number) {
    const MAX_ATTEMPTS = 20
    const INTERVAL_MS = 2500
    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, INTERVAL_MS))
      let updated: PriceWatch
      try {
        updated = await fetchPriceWatch(id)
      } catch {
        return // z.B. inzwischen gelöscht (404) → Polling beenden
      }
      setWatches((prev) => prev.map((w) => (w.id === id ? updated : w)))
      if (updated.last_checked_at != null) return // Check ist durch (Preis oder Fehler steht)
    }
  }

  async function handleDelete(id: number) {
    setDeletingId(id)
    try {
      await deletePriceWatch(id)
      setWatches((prev) => prev.filter((w) => w.id !== id))
      toast.success("Preis-Alarm gelöscht")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Löschen fehlgeschlagen.")
    } finally {
      setDeletingId(null)
    }
  }

  async function handleToggleActive(watch: PriceWatch, active: boolean) {
    // Optimistisch schalten; bei Fehlern den alten Zustand wiederherstellen.
    setWatches((prev) => prev.map((w) => (w.id === watch.id ? { ...w, is_active: active } : w)))
    try {
      const updated = await updatePriceWatch(watch.id, { is_active: active })
      setWatches((prev) => prev.map((w) => (w.id === watch.id ? updated : w)))
      toast.success(active ? "Preis-Alarm aktiviert" : "Preis-Alarm pausiert")
    } catch (e) {
      setWatches((prev) => prev.map((w) => (w.id === watch.id ? watch : w)))
      toast.error(e instanceof Error ? e.message : "Umschalten fehlgeschlagen.")
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
          message="Überwache beliebige Webseiten auf Preisänderungen. Lege deinen ersten Preis-Alarm an."
          icon={<TrendingDown className="size-12 text-muted-foreground/50" />}
          actionLabel="Neuer Preis-Alarm"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : (
        <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 2xl:grid-cols-4">
          {watches.map((watch) => (
            <li key={watch.id} className="min-w-0">
              <PriceWatchCard
                watch={watch}
                onDelete={handleDelete}
                onToggleActive={handleToggleActive}
                isDeleting={deletingId === watch.id}
              />
            </li>
          ))}
        </ul>
      )}

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent
          className="max-h-[calc(100dvh-2rem)] overflow-y-auto overscroll-y-contain sm:max-w-xl"
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>Neuen Preis-Alarm erstellen</DialogTitle>
          </DialogHeader>
          <PriceWatchWizard onCreated={handleCreated} onCancel={() => setIsCreateOpen(false)} />
        </DialogContent>
      </Dialog>
    </ContentReveal>
  )
}
