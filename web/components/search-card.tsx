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
import { cn } from "@/lib/utils"

interface SearchCardProps {
  search: AdSearch
  onDelete: (id: number) => Promise<void> | void
  isDeleting?: boolean
}

export function SearchCard({ search, onDelete, isDeleting }: SearchCardProps) {
  const [open, setOpen] = useState(false)
  const statusLabel = search.is_active ? "Aktiv" : "Pausiert"

  return (
    <Link
      href={`/searches/${search.id}`}
      className="block min-w-0 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      aria-label={`Details für ${search.name}`}
    >
      <Card className="group relative h-full min-h-[148px] cursor-pointer overflow-hidden border border-border/80 bg-card py-0 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-md">
        <CardContent className="flex h-full flex-col p-4 sm:p-5">
          <div className="flex min-h-0 flex-1 items-start justify-between gap-3">
            <div className="flex min-w-0 flex-1 flex-col gap-2.5">
              <div className="flex min-w-0 items-start gap-2">
                <div className="min-w-0 flex-1">
                  <h3
                    className="line-clamp-2 text-base font-semibold leading-snug text-foreground"
                    title={search.name}
                  >
                    {search.name}
                  </h3>
                  <p
                    className="mt-1 flex min-w-0 items-center gap-1.5 truncate text-xs text-muted-foreground"
                    title={search.url}
                  >
                    <ExternalLink className="size-3 shrink-0 opacity-50" aria-hidden />
                    <span className="truncate">{truncateUrl(search.url, 42)}</span>
                  </p>
                </div>
              </div>

              <span
                className={cn(
                  "inline-flex w-fit items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium",
                  search.is_active
                    ? "border-primary/25 bg-primary/10 text-accent-foreground"
                    : "border-border bg-muted/70 text-muted-foreground"
                )}
              >
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    search.is_active ? "bg-primary" : "bg-muted-foreground/50"
                  )}
                  aria-hidden
                />
                {statusLabel}
              </span>
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
                className="size-8 shrink-0 cursor-pointer rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive sm:size-9"
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

          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-border/70 pt-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Power className="size-3 shrink-0 opacity-70" aria-hidden />
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
