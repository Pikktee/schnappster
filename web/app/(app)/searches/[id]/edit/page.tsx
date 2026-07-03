"use client"

import { useCallback, useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { SearchOrderForm } from "@/components/search-order-form"
import { ContentReveal } from "@/components/content-reveal"
import { fetchSearchOrder, updateSearchOrder } from "@/lib/api"
import type { SearchOrder, SearchOrderCreate } from "@/lib/types"
import { toast } from "sonner"
import { usePageHead } from "../../../page-head-context"

export default function EditSearchOrderPage() {
  const router = useRouter()
  const pathname = usePathname()
  const { setTitle } = usePageHead()
  const [id, setId] = useState<number>(NaN)
  const [order, setOrder] = useState<SearchOrder | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    const match = window.location.pathname.match(/searches\/(\d+)\/edit/)
    if (match) setId(Number(match[1]))
  }, [pathname])

  const load = useCallback(async () => {
    if (Number.isNaN(id)) return
    setLoading(true)
    setError(null)
    try {
      setOrder(await fetchSearchOrder(id))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Suchauftrag konnte nicht geladen werden.")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (order) setTitle(`„${order.name}“ bearbeiten`, "Änderungen greifen ab der nächsten Prüfung")
  }, [order, setTitle])

  async function handleUpdate(data: SearchOrderCreate) {
    setIsSaving(true)
    try {
      await updateSearchOrder(id, data)
      toast.success("Suchauftrag aktualisiert")
      router.push(`/searches/${id}`)
    } finally {
      setIsSaving(false)
    }
    // Fehler propagieren ins Formular, das sie inline anzeigt.
  }

  if (loading) {
    return (
      <div className="mx-auto w-full max-w-2xl">
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (error || !order) {
    return (
      <ContentReveal className="mx-auto flex w-full max-w-2xl flex-col items-center gap-4 py-16">
        <p className="text-muted-foreground">{error || "Suchauftrag nicht gefunden."}</p>
        <Button variant="outline" onClick={() => router.push("/searches")} className="cursor-pointer">
          Zurück zur Übersicht
        </Button>
      </ContentReveal>
    )
  }

  return (
    <ContentReveal className="mx-auto w-full max-w-2xl">
      <SearchOrderForm
        initial={order}
        onSubmit={handleUpdate}
        onCancel={() => router.push(`/searches/${id}`)}
        isLoading={isSaving}
      />
    </ContentReveal>
  )
}
