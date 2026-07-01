"use client"

import { useState } from "react"
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Loader2,
  Search,
  Sparkles,
  TriangleAlert,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { createPriceWatch, previewPriceWatch } from "@/lib/api"
import type { PriceCandidate, PriceWatch } from "@/lib/types"
import { formatPriceWithCurrency } from "@/lib/format"
import { cn } from "@/lib/utils"

interface PriceWatchWizardProps {
  onCreated: (watch: PriceWatch) => void
  onCancel: () => void
}

const INTERVAL_PRESETS = [
  { label: "30 Min", value: 30 },
  { label: "1 Std", value: 60 },
  { label: "6 Std", value: 360 },
  { label: "12 Std", value: 720 },
  { label: "Täglich", value: 1440 },
]

const SOURCE_LABELS: Record<string, string> = {
  jsonld: "aus strukturierten Daten",
  meta: "aus Meta-Daten",
  visible: "von der Seite",
}

// Standardmäßig nur die wahrscheinlichsten Preise zeigen; der Rest ist aufklappbar.
const VISIBLE_CANDIDATES = 3

export function PriceWatchWizard({ onCreated, onCancel }: PriceWatchWizardProps) {
  const [step, setStep] = useState<"url" | "select">("url")
  const [url, setUrl] = useState("")
  const [previewing, setPreviewing] = useState(false)
  const [candidates, setCandidates] = useState<PriceCandidate[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [name, setName] = useState("")
  const [interval, setInterval] = useState(360)
  const [threshold, setThreshold] = useState("")
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAllCandidates, setShowAllCandidates] = useState(false)

  const selected = candidates[selectedIndex]
  const currency = selected?.currency ?? null
  const hasMoreCandidates = candidates.length > VISIBLE_CANDIDATES
  const moreCount = candidates.length - VISIBLE_CANDIDATES
  const shownCandidates = showAllCandidates
    ? candidates
    : candidates.slice(0, VISIBLE_CANDIDATES)

  async function handlePreview(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!/^https?:\/\/.+/i.test(url.trim())) {
      setError("Bitte eine gültige Webadresse eingeben (beginnend mit http:// oder https://).")
      return
    }
    setPreviewing(true)
    try {
      const preview = await previewPriceWatch(url.trim())
      setCandidates(preview.candidates)
      const recommended = preview.candidates.findIndex((c) => c.recommended)
      const selectedIdx = recommended >= 0 ? recommended : 0
      setSelectedIndex(selectedIdx)
      // Liste aufgeklappt starten, falls der empfohlene Preis außerhalb der ersten drei liegt.
      setShowAllCandidates(selectedIdx >= VISIBLE_CANDIDATES)
      setName(preview.title ?? "")
      setStep("select")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Die Seite konnte nicht analysiert werden.")
    } finally {
      setPreviewing(false)
    }
  }

  async function handleCreate() {
    if (!selected) return
    setError(null)
    setCreating(true)
    try {
      const watch = await createPriceWatch({
        name: name.trim() || undefined,
        url: url.trim(),
        locator: selected.locator,
        currency: selected.currency,
        selected_label: selected.label,
        initial_price: selected.value,
        scrape_interval_minutes: interval,
        notify_threshold: threshold ? Number(threshold) : null,
      })
      onCreated(watch)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Der Preis-Alarm konnte nicht erstellt werden.")
    } finally {
      setCreating(false)
    }
  }

  // --- Schritt 1: URL ---
  if (step === "url") {
    return (
      <form onSubmit={handlePreview} className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          Gib die Adresse einer Produkt- oder Angebotsseite ein. Schnappster durchsucht die Seite
          nach Preisen, die du überwachen kannst. Bei geschützten Seiten (z. B. Amazon) kann die
          Analyse ~20–30 Sekunden dauern.
        </p>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="watch-url">Webadresse *</Label>
          <Input
            id="watch-url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://shop.example.com/produkt"
            type="url"
            autoFocus
            aria-invalid={!!error}
          />
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="outline" onClick={onCancel} className="cursor-pointer">
            Abbrechen
          </Button>
          <Button type="submit" disabled={previewing || !url.trim()} className="cursor-pointer">
            {previewing ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Analysiere Seite…
              </>
            ) : (
              <>
                <Search className="size-4" /> Preise suchen
              </>
            )}
          </Button>
        </div>
      </form>
    )
  }

  // --- Schritt 2: Preis wählen + Einstellungen ---
  return (
    <div className="flex flex-col gap-5">
      {candidates.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-8 text-center">
          <TriangleAlert className="size-8 text-amber-500" aria-hidden />
          <div>
            <p className="text-sm font-medium text-amber-900">Keine Preise gefunden</p>
            <p className="mt-1 text-xs text-amber-700">
              Auf dieser Seite konnte kein Preis erkannt werden. Möglicherweise lädt sie ihre Preise
              per JavaScript nach. Versuche eine direkte Produktseite.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-1.5">
            <Sparkles className="size-3.5 text-primary" aria-hidden />
            <Label className="font-normal">Welcher Preis soll überwacht werden?</Label>
          </div>
          <div className="flex flex-col gap-2">
            {shownCandidates.map((candidate, index) => {
              const isSelected = index === selectedIndex
              return (
                <button
                  key={index}
                  type="button"
                  onClick={() => setSelectedIndex(index)}
                  className={cn(
                    "flex items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors cursor-pointer",
                    isSelected
                      ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                      : "border-border bg-card hover:border-primary/40 hover:bg-muted/40",
                  )}
                  aria-pressed={isSelected}
                >
                  <span
                    className={cn(
                      "flex size-4 shrink-0 items-center justify-center rounded-full border",
                      isSelected ? "border-primary" : "border-muted-foreground/40",
                    )}
                    aria-hidden
                  >
                    {isSelected && <span className="size-2 rounded-full bg-primary" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline gap-2">
                      <span className="text-base font-semibold tabular-nums text-foreground">
                        {formatPriceWithCurrency(candidate.value, candidate.currency)}
                      </span>
                      <span className="truncate text-sm text-foreground/80">{candidate.label}</span>
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                      {SOURCE_LABELS[candidate.source] ?? candidate.source}
                      {candidate.raw ? ` · „${candidate.raw}"` : ""}
                    </span>
                  </span>
                  {candidate.recommended && (
                    <span className="shrink-0 rounded-full bg-primary/15 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-primary">
                      Empfohlen
                    </span>
                  )}
                </button>
              )
            })}
          </div>
          {hasMoreCandidates && (
            <button
              type="button"
              onClick={() => setShowAllCandidates((v) => !v)}
              aria-expanded={showAllCandidates}
              className="mt-0.5 flex items-center justify-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground cursor-pointer"
            >
              {showAllCandidates ? (
                <ChevronUp className="size-3.5" aria-hidden />
              ) : (
                <ChevronDown className="size-3.5" aria-hidden />
              )}
              {showAllCandidates
                ? "Weniger anzeigen"
                : moreCount === 1
                  ? "1 weiteren Preis anzeigen"
                  : `${moreCount} weitere Preise anzeigen`}
            </button>
          )}
        </div>
      )}

      {candidates.length > 0 && (
        <>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="watch-name" className="font-normal">
              Name
            </Label>
            <Input
              id="watch-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Wird von der Seite übernommen."
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label className="font-normal">Prüf-Intervall</Label>
            <div className="grid grid-cols-5 gap-1.5">
              {INTERVAL_PRESETS.map((preset) => (
                <Button
                  key={preset.value}
                  type="button"
                  variant={interval === preset.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setInterval(preset.value)}
                  className="h-9 cursor-pointer px-2 text-xs"
                >
                  {preset.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="watch-threshold" className="font-normal">
              Benachrichtigen unter (optional)
            </Label>
            <Input
              id="watch-threshold"
              type="number"
              inputMode="decimal"
              min={0}
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              placeholder={selected ? String(Math.floor(selected.value * 0.9)) : "z.B. 99"}
            />
            <p className="text-xs text-muted-foreground">
              Du wirst benachrichtigt, sobald der Preis diesen Wert unterschreitet. Leer = bei jeder
              Preissenkung.
            </p>
          </div>
        </>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}

      <div className="flex items-center justify-between gap-2 pt-1">
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            setStep("url")
            setError(null)
          }}
          className="cursor-pointer text-muted-foreground"
        >
          <ArrowLeft className="size-4" /> Zurück
        </Button>
        <Button
          type="button"
          onClick={handleCreate}
          disabled={creating || candidates.length === 0}
          className="cursor-pointer"
        >
          {creating ? (
            <>
              <Loader2 className="size-4 animate-spin" /> Erstellen…
            </>
          ) : (
            "Alarm erstellen"
          )}
        </Button>
      </div>
    </div>
  )
}
