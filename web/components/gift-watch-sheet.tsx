"use client"

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { GiftWatchForm } from "@/components/gift-watch-form"
import type { GiftWatch } from "@/lib/types"

interface GiftWatchSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Vorhandene Fundgrube → Bearbeiten-Modus; ohne → Anlegen. */
  initial?: GiftWatch
  onSaved: () => void
}

/**
 * Von rechts einfahrendes Panel für Anlegen/Bearbeiten einer Fundgrube.
 * Feste Kopfzeile; das Formular bringt Body (scrollend) und Fuß-Leiste selbst mit.
 */
export function GiftWatchSheet({ open, onOpenChange, initial, onSaved }: GiftWatchSheetProps) {
  const isEdit = !!initial?.id

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
        <SheetHeader className="shrink-0 space-y-1 border-b px-6 py-4 text-left">
          <SheetTitle>{isEdit ? "Fundgrube bearbeiten" : "Neue Fundgrube"}</SheetTitle>
          <SheetDescription>
            Beobachte die „Zu verschenken“-Kategorie im Umkreis und lass Funde nach deinen eigenen
            Regeln bewerten.
          </SheetDescription>
        </SheetHeader>
        {/* key = frische Formularzustände beim Wechsel zwischen Anlegen und einzelnen Fundgruben */}
        <GiftWatchForm
          key={initial?.id ?? "new"}
          initial={initial}
          onSaved={onSaved}
          onCancel={() => onOpenChange(false)}
        />
      </SheetContent>
    </Sheet>
  )
}
