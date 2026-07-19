"use client"

import { useEffect, useState } from "react"
import { Gift, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { GiftWatchCard } from "@/components/gift-watch-card"
import { GiftWatchSheet } from "@/components/gift-watch-sheet"
import { EmptyState } from "@/components/empty-state"
import { ContentReveal } from "@/components/content-reveal"
import { Skeleton } from "@/components/ui/skeleton"
import {
  checkGiftWatchNow,
  deleteGiftWatch,
  fetchGiftWatches,
  updateGiftWatch,
} from "@/lib/api"
import type { GiftWatch } from "@/lib/types"
import { toast } from "sonner"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { usePageHead } from "../page-head-context"

export default function FundgrubePage() {
  const [watches, setWatches] = useState<GiftWatch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [checkingId, setCheckingId] = useState<number | null>(null)
  const { setHeaderActions } = usePageHead()

  async function loadWatches(opts?: { silent?: boolean }) {
    if (!opts?.silent) {
      setLoading(true)
      setError(null)
    }
    try {
      setWatches(await fetchGiftWatches())
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Fundgruben konnten nicht geladen werden."
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
          Neue Fundgrube
        </Button>,
      )
    } else {
      setHeaderActions(null)
    }
    return () => setHeaderActions(null)
  }, [loading, error, setHeaderActions])

  function handleSaved() {
    setIsCreateOpen(false)
    loadWatches({ silent: true })
  }

  async function handleDelete(id: number) {
    setDeletingId(id)
    try {
      await deleteGiftWatch(id)
      setWatches((prev) => prev.filter((w) => w.id !== id))
      toast.success("Fundgrube gelöscht")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Löschen fehlgeschlagen.")
    } finally {
      setDeletingId(null)
    }
  }

  async function handleToggleActive(watch: GiftWatch, active: boolean) {
    // Optimistisch schalten; bei Fehlern den alten Zustand wiederherstellen.
    setWatches((prev) => prev.map((w) => (w.id === watch.id ? { ...w, is_active: active } : w)))
    try {
      const updated = await updateGiftWatch(watch.id, { is_active: active })
      setWatches((prev) => prev.map((w) => (w.id === watch.id ? updated : w)))
      toast.success(active ? "Fundgrube aktiviert" : "Fundgrube pausiert")
    } catch (e) {
      setWatches((prev) => prev.map((w) => (w.id === watch.id ? watch : w)))
      toast.error(e instanceof Error ? e.message : "Umschalten fehlgeschlagen.")
    }
  }

  async function handleCheckNow(watch: GiftWatch) {
    setCheckingId(watch.id)
    try {
      await checkGiftWatchNow(watch.id)
      toast.success("Prüfung gestartet — neue Funde erscheinen gleich.")
      // Der Check läuft im Hintergrund; "Zuletzt geprüft" kurz darauf still nachziehen.
      setTimeout(() => loadWatches({ silent: true }), 5000)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Prüfung konnte nicht gestartet werden.")
    } finally {
      setCheckingId(null)
    }
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 2xl:grid-cols-4">
        <Skeleton className="h-[188px] rounded-xl" />
        <Skeleton className="h-[188px] rounded-xl" />
        <Skeleton className="h-[188px] rounded-xl" />
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
          message="Beobachte die „Zu verschenken“-Kategorie im Umkreis und lass Funde nach deinen eigenen Regeln bewerten. Lege deine erste Fundgrube an."
          icon={<Gift className="size-12 text-muted-foreground/50" />}
          actionLabel="Neue Fundgrube"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : (
        <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 2xl:grid-cols-4">
          {watches.map((watch) => (
            <li key={watch.id} className="min-w-0">
              <GiftWatchCard
                watch={watch}
                onDelete={handleDelete}
                onToggleActive={handleToggleActive}
                onCheckNow={handleCheckNow}
                isDeleting={deletingId === watch.id}
                isChecking={checkingId === watch.id}
              />
            </li>
          ))}
        </ul>
      )}

      <GiftWatchSheet open={isCreateOpen} onOpenChange={setIsCreateOpen} onSaved={handleSaved} />
    </ContentReveal>
  )
}
