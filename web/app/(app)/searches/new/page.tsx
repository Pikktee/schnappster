"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { SearchOrderForm } from "@/components/search-order-form"
import { ContentReveal } from "@/components/content-reveal"
import { createSearchOrder } from "@/lib/api"
import type { SearchOrderCreate } from "@/lib/types"
import { toast } from "sonner"
import { usePageHead } from "../../page-head-context"

export default function NewSearchOrderPage() {
  const router = useRouter()
  const { setTitle } = usePageHead()
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    setTitle(
      "Neuer Suchauftrag",
      "Ein Suchbegriff — auf Wunsch über Kleinanzeigen, eBay und MyDealz gleichzeitig",
    )
  }, [setTitle])

  async function handleCreate(data: SearchOrderCreate) {
    setIsCreating(true)
    try {
      const created = await createSearchOrder(data)
      toast.success("Suchauftrag erstellt — erste Ergebnisse erscheinen in wenigen Minuten.")
      router.push(`/searches/${created.id}`)
    } finally {
      setIsCreating(false)
    }
    // Fehler propagieren ins Formular, das sie inline anzeigt.
  }

  return (
    <ContentReveal className="mx-auto w-full max-w-2xl">
      <SearchOrderForm
        onSubmit={handleCreate}
        onCancel={() => router.push("/searches")}
        isLoading={isCreating}
      />
    </ContentReveal>
  )
}
