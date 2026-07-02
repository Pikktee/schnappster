"use client"

import { useState } from "react"
import { Flame } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { createDealWatch } from "@/lib/api"
import type { DealWatch } from "@/lib/types"

const TEMPERATURE_PRESETS: { label: string; value: number | null }[] = [
  { label: "Alle", value: null },
  { label: "100°", value: 100 },
  { label: "200°", value: 200 },
  { label: "300°", value: 300 },
  { label: "500°", value: 500 },
]

const INTERVAL_PRESETS = [
  { label: "15 Min", value: 15 },
  { label: "30 Min", value: 30 },
  { label: "1 Std", value: 60 },
  { label: "6 Std", value: 360 },
  { label: "Täglich", value: 1440 },
]

interface DealWatchFormProps {
  onCreated: (watch: DealWatch) => void
  onCancel: () => void
}

export function DealWatchForm({ onCreated, onCancel }: DealWatchFormProps) {
  const [name, setName] = useState("")
  const [query, setQuery] = useState("")
  const [minTemperature, setMinTemperature] = useState<number | null>(200)
  const [interval, setInterval] = useState(30)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) {
      setError("Bitte einen Suchbegriff eingeben.")
      return
    }
    setIsSaving(true)
    setError(null)
    try {
      const watch = await createDealWatch({
        name: name.trim() || undefined,
        query: query.trim(),
        min_temperature: minTemperature,
        scrape_interval_minutes: interval,
      })
      onCreated(watch)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deal-Alarm konnte nicht angelegt werden.")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="deal-query">Suchbegriff *</Label>
        <Input
          id="deal-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="z.B. LEGO Millennium Falcon"
          aria-invalid={!!error}
          autoFocus
        />
        <p className="text-xs text-muted-foreground">
          Wir überwachen MyDealz auf neue Deals zu diesem Begriff.
        </p>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label className="flex items-center gap-1.5">
          <Flame className="size-3.5 text-muted-foreground/70" aria-hidden />
          Ab welcher Temperatur benachrichtigen?
        </Label>
        <div className="grid grid-cols-5 gap-1.5">
          {TEMPERATURE_PRESETS.map((preset) => (
            <Button
              key={preset.label}
              type="button"
              variant={minTemperature === preset.value ? "default" : "outline"}
              size="sm"
              onClick={() => setMinTemperature(preset.value)}
              className="cursor-pointer text-xs"
            >
              {preset.label}
            </Button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          {`Die Community-Temperatur (Grad) zeigt, wie gut ein Deal ankommt. „Alle" meldet jeden neuen Deal.`}
        </p>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label>Prüf-Intervall</Label>
        <div className="grid grid-cols-5 gap-1.5">
          {INTERVAL_PRESETS.map((preset) => (
            <Button
              key={preset.value}
              type="button"
              variant={interval === preset.value ? "default" : "outline"}
              size="sm"
              onClick={() => setInterval(preset.value)}
              className="cursor-pointer text-xs px-2"
            >
              {preset.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="deal-name" className="font-normal">
          Name (optional)
        </Label>
        <Input
          id="deal-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Wird aus dem Suchbegriff übernommen."
        />
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex justify-end gap-2 pt-1">
        <Button type="button" variant="outline" onClick={onCancel} className="cursor-pointer">
          Abbrechen
        </Button>
        <Button type="submit" disabled={isSaving || !query.trim()} className="cursor-pointer">
          {isSaving ? "Speichern..." : "Erstellen"}
        </Button>
      </div>
    </form>
  )
}
