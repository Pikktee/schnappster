"use client"

import { useCallback, useState } from "react"
import { Gavel, RefreshCw, TrendingDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { getMarketReference } from "@/lib/api"
import { formatPrice } from "@/lib/format"
import type { MarketReference } from "@/lib/types"

interface MarketReferenceDialogProps {
  adId: number
  adPrice: number | null
}

/**
 * Zeigt den echten Marktwert aus verkauften eBay-Angeboten (Median + Spanne) und wie
 * dieses Angebot dazu steht. On-demand — kein automatischer Abruf pro Anzeige.
 */
export function MarketReferenceDialog({ adId, adPrice }: MarketReferenceDialogProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<MarketReference | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await getMarketReference(adId))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Der Abruf ist fehlgeschlagen.")
    } finally {
      setLoading(false)
    }
  }, [adId])

  const handleOpenChange = useCallback(
    (next: boolean) => {
      setOpen(next)
      if (next && !data && !loading) void load()
    },
    [data, loading, load]
  )

  const savingsPct =
    data?.median && adPrice ? Math.round(((data.median - adPrice) / data.median) * 100) : null

  return (
    <>
      <Button
        variant="outline"
        className="w-full cursor-pointer"
        onClick={() => handleOpenChange(true)}
      >
        <Gavel className="size-4" aria-hidden />
        Marktwert aus eBay-Verkäufen
      </Button>

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Gavel className="size-5 text-primary" aria-hidden />
              Echter Marktwert
            </DialogTitle>
            <DialogDescription>
              Median aus tatsächlich verkauften eBay-Angeboten — was vergleichbare Artikel
              wirklich gekostet haben, nicht bloß Wunschpreise.
            </DialogDescription>
          </DialogHeader>

          {loading ? (
            <div className="flex flex-col items-center gap-3 py-10 text-muted-foreground">
              <Spinner />
              <p className="text-sm">eBay-Verkäufe werden ausgewertet…</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-sm text-destructive">{error}</p>
              <Button variant="outline" onClick={load} className="cursor-pointer">
                <RefreshCw className="size-4" aria-hidden />
                Erneut versuchen
              </Button>
            </div>
          ) : data && data.count > 0 ? (
            <div className="flex flex-col gap-4">
              <div className="rounded-lg bg-primary/10 px-4 py-3 ring-1 ring-primary/15">
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-foreground">
                    {formatPrice(data.median)}
                  </span>
                  <span className="text-sm text-muted-foreground">Median</span>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  aus {data.count} Verkäufen · Spanne {formatPrice(data.low)}–{formatPrice(data.high)}
                </p>
              </div>

              {savingsPct !== null && adPrice !== null && (
                <p className="text-sm text-foreground">
                  Dieses Angebot: <span className="font-semibold">{formatPrice(adPrice)}</span> —{" "}
                  <span
                    className={savingsPct >= 0 ? "font-semibold text-emerald-600" : "font-semibold text-destructive"}
                  >
                    {Math.abs(savingsPct)}% {savingsPct >= 0 ? "unter" : "über"} dem Median
                  </span>
                </p>
              )}

              <ul className="m-0 flex list-none flex-col divide-y divide-border/50 p-0">
                {data.comps.map((comp, i) => (
                  <li key={i} className="flex items-center gap-3 py-2 text-sm">
                    <span className="w-20 shrink-0 font-semibold text-foreground">
                      {formatPrice(comp.price)}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-muted-foreground" title={comp.title}>
                      {comp.title}
                    </span>
                    {comp.sold_date && (
                      <span className="shrink-0 text-xs text-muted-foreground/70">{comp.sold_date}</span>
                    )}
                  </li>
                ))}
              </ul>

              <div className="flex items-center justify-between gap-2">
                <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
                  <TrendingDown className="size-3.5 shrink-0 mt-0.5" aria-hidden />
                  <span>
                    Suche „{data.query}“. Der Median dämpft Ausreißer — prüfe die Beispiele auf
                    Passung (Modell/Zustand).
                  </span>
                </p>
                <Button variant="ghost" size="sm" onClick={load} className="shrink-0 cursor-pointer">
                  <RefreshCw className="size-4" aria-hidden />
                  Neu
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 py-8 text-center">
              <p className="text-sm text-foreground">Keine belastbaren eBay-Verkäufe gefunden.</p>
              <p className="max-w-xs text-xs text-muted-foreground">
                Für „{data?.query}“ gab es zu wenige vergleichbare verkaufte Angebote.
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
