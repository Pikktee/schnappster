"use client"

import { useState } from "react"
import Link from "next/link"
import {
  Clock,
  Euro,
  ExternalLink,
  Loader2,
  RefreshCw,
  Trash2,
  type LucideIcon,
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { SearchStatusBadge } from "@/components/search-status-badge"
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
import { formatScrapeInterval, formatSearchPriceRange, timeAgo, truncateUrl } from "@/lib/format"

interface SearchCardProps {
  search: AdSearch
  onDelete: (id: number) => Promise<void> | void
  isDeleting?: boolean
}

interface SearchMetaItemProps {
  icon: LucideIcon
  label: string
  value: string
}

function SearchMetaItem({ icon: Icon, label, value }: SearchMetaItemProps) {
  return (
    <span className="flex min-w-0 items-center gap-2 rounded-lg bg-muted/45 px-2.5 py-2">
      <Icon className="size-3.5 shrink-0 text-muted-foreground/75" aria-hidden />
      <span className="min-w-0">
        <span className="block text-[0.68rem] font-medium uppercase tracking-[0.1em] text-muted-foreground/70">
          {label}
        </span>
        <span className="block truncate text-xs font-medium text-foreground">{value}</span>
      </span>
    </span>
  )
}

export function SearchCard({ search, onDelete, isDeleting }: SearchCardProps) {
  const [open, setOpen] = useState(false)

  return (
    <Card className="group relative h-full min-h-[196px] overflow-hidden border-border/80 bg-card/95 py-0 shadow-sm transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-md">
      <Link
        href={`/searches/${search.id}`}
        className="absolute inset-0 z-10 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        aria-label={`Details für ${search.name}`}
        prefetch={false}
      />

      <CardContent className="pointer-events-none relative z-20 flex h-full flex-col p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <SearchStatusBadge isActive={search.is_active} className="mb-3" />
            <h3
              className="line-clamp-2 text-pretty text-base font-semibold leading-snug text-foreground"
              title={search.name}
            >
              {search.name}
            </h3>
            <p
              className="mt-1.5 flex min-w-0 items-center gap-1.5 truncate text-xs text-muted-foreground"
              title={search.url}
            >
              <ExternalLink className="size-3 shrink-0 opacity-55" aria-hidden />
              <span className="truncate">{truncateUrl(search.url, 46)}</span>
            </p>
          </div>

          <div className="pointer-events-auto shrink-0">
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
                className="size-8 cursor-pointer rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive sm:size-9"
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
                    className="cursor-pointer bg-destructive text-white hover:bg-destructive/90"
                  >
                    Löschen
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>

        <div className="mt-auto grid grid-cols-1 gap-2 border-t border-border/70 pt-4 min-[380px]:grid-cols-2">
          <SearchMetaItem
            icon={RefreshCw}
            label="Intervall"
            value={formatScrapeInterval(search.scrape_interval_minutes)}
          />
          <SearchMetaItem icon={Clock} label="Zuletzt" value={timeAgo(search.last_scraped_at)} />
          <div className="min-[380px]:col-span-2">
            <SearchMetaItem icon={Euro} label="Preisrahmen" value={formatSearchPriceRange(search)} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
