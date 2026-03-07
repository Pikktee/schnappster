"use client"

import { useState } from "react"
import Link from "next/link"
import { Trash2, Loader2 } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import type { AdSearch } from "@/lib/types"
import { timeAgo, truncateUrl } from "@/lib/format"

interface SearchCardProps {
  search: AdSearch
  onDelete: (id: number) => Promise<void> | void
  isDeleting?: boolean
}

export function SearchCard({ search, onDelete, isDeleting }: SearchCardProps) {
  const [open, setOpen] = useState(false)

  return (
    <Card className="group relative transition-all hover:shadow-md hover:-translate-y-0.5 cursor-pointer">
      <Link href={`/searches/${search.id}`} className="absolute inset-0 z-0" aria-label={`Details für ${search.name}`} />
      <CardContent className="flex flex-col gap-3 p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="font-semibold text-foreground truncate" title={search.name}>{search.name}</h3>
            <p className="text-xs text-muted-foreground truncate mt-0.5" title={search.url}>
              {truncateUrl(search.url)}
            </p>
          </div>
          <Badge
            variant="secondary"
            className={
              search.is_active
                ? "bg-emerald-100 text-emerald-700 border-emerald-200 shrink-0"
                : "bg-muted text-muted-foreground shrink-0"
            }
          >
            {search.is_active ? "Aktiv" : "Inaktiv"}
          </Badge>
        </div>

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Alle {search.scrape_interval_minutes} Min.</span>
          <span>Letzte Suche: {timeAgo(search.last_scraped_at)}</span>
        </div>

        <div className="flex justify-end relative z-10">
          <AlertDialog open={open} onOpenChange={setOpen}>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setOpen(true)
              }}
              disabled={isDeleting}
              className="text-muted-foreground hover:text-destructive cursor-pointer"
              aria-label="Löschen"
            >
              {isDeleting ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
            </Button>
            <AlertDialogContent onClick={(e) => e.stopPropagation()}>
              <AlertDialogHeader>
                <AlertDialogTitle>Suchauftrag löschen?</AlertDialogTitle>
                <AlertDialogDescription>
                  Der Suchauftrag &ldquo;{search.name}&rdquo; wird unwiderruflich gelöscht.
                  Bereits gefundene Angebote bleiben erhalten.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel className="cursor-pointer">Abbrechen</AlertDialogCancel>
                <AlertDialogAction
                  onClick={(e) => {
                    e.preventDefault()
                    onDelete(search.id)
                    setOpen(false)
                  }}
                  className="bg-destructive text-white hover:bg-destructive/90 cursor-pointer"
                >
                  Löschen
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  )
}
