"use client"

import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { SearchOrderForm } from "@/components/search-order-form"
import type { SearchOrder, SearchOrderCreate } from "@/lib/types"

const FORM_ID = "search-order-form"

interface SearchOrderSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Vorhandener Auftrag → Bearbeiten-Modus; ohne → Anlegen. */
  initial?: SearchOrder
  onSubmit: (data: SearchOrderCreate) => Promise<void> | void
  isLoading?: boolean
}

/**
 * Von rechts einfahrendes Panel für Anlegen/Bearbeiten eines Suchauftrags.
 * Feste Kopf-/Fußzeile, nur der Formular-Body scrollt — Speichern bleibt immer sichtbar.
 */
export function SearchOrderSheet({
  open,
  onOpenChange,
  initial,
  onSubmit,
  isLoading,
}: SearchOrderSheetProps) {
  const isEdit = !!initial?.id

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
        <SheetHeader className="shrink-0 space-y-1 border-b px-6 py-4 text-left">
          <SheetTitle>{isEdit ? "Suchauftrag bearbeiten" : "Neuer Suchauftrag"}</SheetTitle>
          <SheetDescription>
            Ein Suchbegriff — auf Wunsch über Kleinanzeigen, eBay und MyDealz gleichzeitig.
          </SheetDescription>
        </SheetHeader>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-6">
          <SearchOrderForm id={FORM_ID} initial={initial} onSubmit={onSubmit} />
        </div>

        <SheetFooter className="shrink-0 flex-row justify-end gap-2 border-t px-6 py-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="cursor-pointer"
          >
            Abbrechen
          </Button>
          <Button type="submit" form={FORM_ID} disabled={isLoading} className="cursor-pointer">
            {isLoading ? "Speichern..." : isEdit ? "Aktualisieren" : "Erstellen"}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
