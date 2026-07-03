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
import { SearchOrderCard } from "@/components/search-order-card"
import { SearchOrderForm } from "@/components/search-order-form"
import { EmptyState } from "@/components/empty-state"
import { ContentReveal } from "@/components/content-reveal"
import {
  fetchSearchOrders,
  createSearchOrder,
  deleteSearchOrder,
  updateSearchOrder,
  checkSearchOrderNow,
} from "@/lib/api"
import type { SearchOrder, SearchOrderCreate } from "@/lib/types"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { useRefetchOnFocus } from "@/hooks/use-refetch-on-focus"
import { usePageHead } from "../page-head-context"

export default function SearchesPage() {
  const [orders, setOrders] = useState<SearchOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [checkingId, setCheckingId] = useState<number | null>(null)
  const { setHeaderActions } = usePageHead()

  async function loadOrders(opts?: { silent?: boolean }) {
    if (!opts?.silent) {
      setLoading(true)
      setError(null)
    }
    try {
      const data = await fetchSearchOrders()
      setOrders(data)
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
    loadOrders()
  }, [])

  useRefetchOnFocus(() => loadOrders({ silent: true }))

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

  async function handleCreate(data: SearchOrderCreate) {
    setIsCreating(true)
    try {
      const created = await createSearchOrder(data)
      setOrders((prev) => [created, ...prev])
      setIsCreateOpen(false)
      toast.success("Suchauftrag erstellt — erste Ergebnisse erscheinen in wenigen Minuten.")
    } finally {
      setIsCreating(false)
    }
    // Fehler propagieren ins Formular, das sie inline anzeigt.
  }

  async function handleDelete(id: number) {
    setDeletingId(id)
    try {
      await deleteSearchOrder(id)
      setOrders((prev) => prev.filter((o) => o.id !== id))
      toast.success("Suchauftrag gelöscht")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Löschen fehlgeschlagen.")
    } finally {
      setDeletingId(null)
    }
  }

  async function handleToggleActive(order: SearchOrder, active: boolean) {
    // Optimistisch schalten; bei Fehlern den alten Zustand wiederherstellen.
    setOrders((prev) => prev.map((o) => (o.id === order.id ? { ...o, is_active: active } : o)))
    try {
      const updated = await updateSearchOrder(order.id, { is_active: active })
      setOrders((prev) => prev.map((o) => (o.id === order.id ? updated : o)))
      toast.success(active ? "Suchauftrag aktiviert" : "Suchauftrag pausiert")
    } catch (e) {
      setOrders((prev) => prev.map((o) => (o.id === order.id ? order : o)))
      toast.error(e instanceof Error ? e.message : "Umschalten fehlgeschlagen.")
    }
  }

  async function handleCheckNow(order: SearchOrder) {
    setCheckingId(order.id)
    try {
      await checkSearchOrderNow(order.id)
      toast.success("Prüfung gestartet — neue Funde erscheinen gleich im Stream.")
      // Der Check läuft im Hintergrund; "Zuletzt geprüft" kurz darauf still nachziehen.
      setTimeout(() => loadOrders({ silent: true }), 5000)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Prüfung konnte nicht gestartet werden.")
    } finally {
      setCheckingId(null)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 xl:grid-cols-3 2xl:grid-cols-4">
          <Skeleton className="h-[196px] rounded-xl" />
          <Skeleton className="h-[196px] rounded-xl" />
          <Skeleton className="h-[196px] rounded-xl" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <ContentReveal className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-4 py-12">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" onClick={() => loadOrders()} className="cursor-pointer">
            Erneut laden
          </Button>
        </div>
      </ContentReveal>
    )
  }

  return (
    <ContentReveal className="flex flex-col gap-6">
      {orders.length === 0 ? (
        <EmptyState
          message="Erstelle deinen ersten Suchauftrag — ein Suchbegriff, auf Wunsch über Kleinanzeigen, eBay und MyDealz gleichzeitig."
          icon={<SearchX className="size-12 text-muted-foreground/50" />}
        />
      ) : (
        <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 xl:grid-cols-3 2xl:grid-cols-4">
          {orders.map((order) => (
            <li key={order.id} className="min-w-0">
              <SearchOrderCard
                order={order}
                onDelete={handleDelete}
                onToggleActive={handleToggleActive}
                onCheckNow={handleCheckNow}
                isDeleting={deletingId === order.id}
                isChecking={checkingId === order.id}
              />
            </li>
          ))}
        </ul>
      )}

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent
          className="max-h-[calc(100dvh-2rem)] overflow-y-auto overscroll-y-contain sm:max-w-3xl"
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>Neuen Suchauftrag erstellen</DialogTitle>
          </DialogHeader>
          <SearchOrderForm
            onSubmit={handleCreate}
            onCancel={() => setIsCreateOpen(false)}
            isLoading={isCreating}
          />
        </DialogContent>
      </Dialog>
    </ContentReveal>
  )
}
