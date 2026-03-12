"use client"

import { useState } from "react"
import Link from "next/link"
import { Trash2, Loader2, Power, ExternalLink, Clock } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
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
} from "@/components/ui/alert-dialog"
import type { AdSearch } from "@/lib/types"
import { timeAgo, truncateUrl, formatScrapeInterval } from "@/lib/format"

interface SearchCardProps {
  search: AdSearch
  onDelete: (id: number) => Promise<void> | void
  isDeleting?: boolean
}

export function SearchCard({ search, onDelete, isDeleting }: SearchCardProps) {
  const [open, setOpen] = useState(false)

  return (
    <Link
      href={`/searches/${search.id}`}
      className="block min-w-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-xl"
      aria-label={`Details für ${search.name}`}
    >
      <Card className="group relative h-full min-h-[132px] py-0 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 card-lift cursor-pointer overflow-hidden border border-border/80 bg-card">
        {/* Status-Balken links */}
        <div
          className={`absolute top-0 left-0 w-1 h-full rounded-l-xl ${search.is_active ? "bg-emerald-500" : "bg-muted-foreground/25"}`}
          aria-hidden
        />

        <CardContent className="flex flex-col h-full gap-0 p-0 pl-5 pr-4 pt-4 pb-3 sm:pl-6 sm:pr-5 sm:pt-5 sm:pb-4">
          {/* Kopfzeile: Titel + Löschen */}
          <div className="flex items-start justify-between gap-3 min-h-0 flex-1">
            <div className="min-w-0 flex-1 pt-0.5">
              <h3
                className="font-semibold text-foreground text-base leading-tight truncate"
                title={search.name}
              >
                {search.name}
              </h3>
              <p
                className="text-xs text-muted-foreground truncate mt-1 flex items-center gap-1 min-w-0"
                title={search.url}
              >
                <ExternalLink className="size-3 shrink-0 opacity-50" aria-hidden />
                <span className="truncate">{truncateUrl(search.url, 42)}</span>
              </p>
            </div>
            <AlertDialog open={open} onOpenChange={setOpen}>
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  setOpen(true)
                }}
                disabled={isDeleting}
                className="shrink-0 size-8 sm:size-9 text-muted-foreground hover:text-primary hover:bg-primary/10 cursor-pointer rounded-md"
                aria-label="Suchauftrag löschen"
              >
                {isDeleting ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Trash2 className="size-4" aria-hidden />
                )}
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

          {/* Meta-Zeile: Intervall + letzte Suche – responsive gestapelt auf sehr kleinen Screens */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 pt-3 border-t border-border/60 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Power
                className={`size-3 shrink-0 ${search.is_active ? "text-emerald-500" : "text-muted-foreground/60"}`}
                aria-hidden
              />
              <span>{formatScrapeInterval(search.scrape_interval_minutes)}</span>
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="size-3 shrink-0 opacity-70" aria-hidden />
              <span className="whitespace-nowrap">
                {timeAgo(search.last_scraped_at)}
              </span>
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
