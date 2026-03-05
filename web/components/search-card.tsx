"use client"

import Link from "next/link"
import { Trash2 } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { AdSearch } from "@/lib/types"
import { timeAgo, truncateUrl } from "@/lib/format"

interface SearchCardProps {
  search: AdSearch
  onDelete: (id: number) => void
}

export function SearchCard({ search, onDelete }: SearchCardProps) {
  return (
    <Card className="group relative transition-all hover:shadow-md hover:-translate-y-0.5 cursor-pointer">
      <Link href={`/searches/${search.id}`} className="absolute inset-0 z-0" aria-label={`Details fuer ${search.name}`} />
      <CardContent className="flex flex-col gap-3 p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="font-semibold text-foreground truncate">{search.name}</h3>
            <p className="text-xs text-muted-foreground truncate mt-0.5">
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
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              if (window.confirm("Suchauftrag wirklich loeschen?")) {
                onDelete(search.id)
              }
            }}
            className="text-muted-foreground hover:text-destructive cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity"
            aria-label="Loeschen"
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
