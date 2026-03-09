"use client"

import { useState } from "react"
import Link from "next/link"
import { Trash2, Loader2, Power, ExternalLink } from "lucide-react"
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
} from "@/components/ui/alert-dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Switch } from "@/components/ui/switch"
import type { AdSearch } from "@/lib/types"
import { timeAgo, truncateUrl } from "@/lib/format"
import { toast } from "sonner"
import { updateSearch } from "@/lib/api"

interface SearchCardProps {
  search: AdSearch
  onDelete: (id: number) => Promise<void> | void
  onToggleActive?: (id: number, newActive: boolean) => Promise<void> | void
  isDeleting?: boolean
}

export function SearchCard({ search, onDelete, onToggleActive, isDeleting }: SearchCardProps) {
  const [open, setOpen] = useState(false)
  const [toggling, setToggling] = useState(false)

  async function handleToggleActive(checked: boolean) {
    if (!onToggleActive) return
    setToggling(true)
    try {
      await updateSearch(search.id, { is_active: checked })
      await onToggleActive(search.id, checked)
      toast.success(checked ? "Suchauftrag aktiviert" : "Suchauftrag deaktiviert")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Status konnte nicht geändert werden."
      toast.error(msg)
    } finally {
      setToggling(false)
    }
  }

  return (
    <Card className="group relative transition-all hover:shadow-md hover:-translate-y-1 card-lift cursor-pointer overflow-hidden">
      <Link href={`/searches/${search.id}`} className="absolute inset-0 z-0" aria-label={`Details für ${search.name}`} />

      {/* Status indicator bar */}
      <div className={`absolute top-0 left-0 w-1 h-full ${search.is_active ? 'bg-emerald-500' : 'bg-muted-foreground/30'}`} />

      <CardContent className="flex flex-col gap-3 p-5 pl-6">
        <div className="flex items-start justify-between gap-2 relative z-10">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-foreground truncate" title={search.name}>{search.name}</h3>
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <p className="text-xs text-muted-foreground truncate mt-0.5 flex items-center gap-1 cursor-help">
                    <ExternalLink className="size-3 opacity-50" />
                    {truncateUrl(search.url)}
                  </p>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-md text-xs break-all">
                  {search.url}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <div className="flex items-center gap-2 shrink-0 relative z-20">
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Switch
                    checked={search.is_active}
                    onCheckedChange={handleToggleActive}
                    disabled={toggling}
                    onClick={(e) => e.stopPropagation()}
                    className="data-[state=checked]:bg-emerald-500"
                    aria-label={search.is_active ? "Deaktivieren" : "Aktivieren"}
                  />
                </TooltipTrigger>
                <TooltipContent side="left">
                  {search.is_active ? "Deaktivieren" : "Aktivieren"}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs text-muted-foreground relative z-10">
          <div className="flex items-center gap-1.5">
            <Power className={`size-3 ${search.is_active ? 'text-emerald-500' : 'text-muted-foreground/50'}`} />
            <span>Alle {search.scrape_interval_minutes} Min.</span>
          </div>
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
