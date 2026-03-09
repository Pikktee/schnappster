"use client"

import { useState, useCallback, useEffect } from "react"
import { X, HelpCircle, ChevronDown, ChevronUp } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import type { AdSearch } from "@/lib/types"

interface SearchFormProps {
  initial?: Partial<AdSearch>
  onSubmit: (data: Partial<AdSearch>) => Promise<void> | void
  onCancel: () => void
  isLoading?: boolean
  onDirtyChange?: (dirty: boolean) => void
}

const INTERVAL_PRESETS = [
  { label: "5 Min", value: 5 },
  { label: "10 Min", value: 10 },
  { label: "30 Min", value: 30 },
  { label: "1 Std", value: 60 },
  { label: "6 Std", value: 360 },
  { label: "Täglich", value: 1440 },
]

function HelpTip({ text }: { text: string }) {
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <HelpCircle className="size-3.5 text-muted-foreground/60 cursor-help" />
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs text-xs">
          {text}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

function parseKeywords(str: string): string[] {
  return str
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
}

export function SearchForm({ initial, onSubmit, onCancel, isLoading, onDirtyChange }: SearchFormProps) {
  const [name, setName] = useState(initial?.name || "")
  const [url, setUrl] = useState(initial?.url || "")
  const [interval, setInterval] = useState(initial?.scrape_interval_minutes || 60)
  const [minPrice, setMinPrice] = useState<string>(initial?.min_price?.toString() || "")
  const [maxPrice, setMaxPrice] = useState<string>(initial?.max_price?.toString() || "")
  const [keywords, setKeywords] = useState<string[]>(
    initial?.blacklist_keywords ? parseKeywords(initial.blacklist_keywords) : []
  )
  const [keywordInput, setKeywordInput] = useState("")
  const [promptAddition, setPromptAddition] = useState(initial?.prompt_addition || "")
  const [excludeImages, setExcludeImages] = useState(initial?.is_exclude_images || false)
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const [errors, setErrors] = useState<Record<string, string>>({})

  const isDirty = name !== (initial?.name || "") ||
    url !== (initial?.url || "") ||
    interval !== (initial?.scrape_interval_minutes || 60) ||
    minPrice !== (initial?.min_price?.toString() || "") ||
    maxPrice !== (initial?.max_price?.toString() || "") ||
    promptAddition !== (initial?.prompt_addition || "") ||
    excludeImages !== (initial?.is_exclude_images || false) ||
    keywords.join(", ") !== (initial?.blacklist_keywords || "")

  useEffect(() => {
    onDirtyChange?.(isDirty)
  }, [isDirty, onDirtyChange])

  const addKeyword = useCallback(() => {
    const trimmed = keywordInput.trim()
    if (trimmed && !keywords.includes(trimmed)) {
      setKeywords((prev) => [...prev, trimmed])
    }
    setKeywordInput("")
  }, [keywordInput, keywords])

  function removeKeyword(kw: string) {
    setKeywords((prev) => prev.filter((k) => k !== kw))
  }

  function handleKeywordKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      addKeyword()
    }
    if (e.key === "Backspace" && keywordInput === "" && keywords.length > 0) {
      setKeywords((prev) => prev.slice(0, -1))
    }
  }

  const SEARCH_PREFIX = "https://www.kleinanzeigen.de/s-"
  const DETAIL_PREFIX = "https://www.kleinanzeigen.de/s-anzeige/"

  function validateUrl(value: string): string | null {
    if (!value.trim()) return "URL ist erforderlich."
    if (!value.startsWith(SEARCH_PREFIX))
      return "Nur Kleinanzeigen.de-Suchergebnislisten sind erlaubt (URL muss mit https://www.kleinanzeigen.de/s- beginnen)."
    if (value.startsWith(DETAIL_PREFIX))
      return "Bitte keine Anzeigen-Detailseite eingeben — nur Suchergebnislisten sind erlaubt."
    const remainder = value.slice(SEARCH_PREFIX.length).replace(/^\/+|\/+$/g, "")
    if (!remainder)
      return "Bitte eine vollständige Suchergebnisliste-URL eingeben, nicht nur das Präfix."
    return null
  }

  function validate(): boolean {
    const newErrors: Record<string, string> = {}

    const urlError = validateUrl(url)
    if (urlError) newErrors.url = urlError

    if (minPrice && maxPrice && Number(minPrice) > Number(maxPrice)) {
      newErrors.maxPrice = "Max-Preis muss größer als Min-Preis sein."
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return
    try {
      await onSubmit({
        name: name.trim() || undefined,
        url,
        scrape_interval_minutes: interval,
        min_price: minPrice ? Number(minPrice) : null,
        max_price: maxPrice ? Number(maxPrice) : null,
        blacklist_keywords: keywords.length > 0 ? keywords.join(", ") : null,
        prompt_addition: promptAddition || null,
        is_exclude_images: excludeImages,
      })
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Fehler beim Speichern."
      setErrors((prev) => ({ ...prev, url: msg }))
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="search-url" className="flex items-center gap-1.5">
          <span>Kleinanzeigen URL *</span>
          <HelpTip text="Führe eine Suche auf kleinanzeigen.de durch und kopiere die URL der Suchergebnisseite hierher." />
        </Label>
        <Input
          id="search-url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.kleinanzeigen.de/s-..."
          type="url"
          aria-invalid={!!errors.url}
          autoFocus
        />
        {errors.url && <p className="text-xs text-destructive">{errors.url}</p>}
      </div>

      {/* Progressive disclosure: Advanced options */}
      <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
        <CollapsibleTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="w-full justify-between cursor-pointer text-muted-foreground hover:text-foreground -mx-2"
          >
            <span className="text-sm">Erweiterte Optionen</span>
            {advancedOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="flex flex-col gap-4 pt-2">
          {/* Name */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="search-name">Name (optional)</Label>
            <Input
              id="search-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Wird automatisch aus der URL generiert"
            />
          </div>

          {/* Interval Selector - Visual */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-1.5">
              <Label htmlFor="search-interval">Scrape-Intervall</Label>
              <HelpTip text="Wie oft soll nach neuen Angeboten gesucht werden? Kürzere Intervalle finden Schnäppchen schneller, belasten aber den Server mehr." />
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {INTERVAL_PRESETS.map((preset) => (
                <Button
                  key={preset.value}
                  type="button"
                  variant={interval === preset.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setInterval(preset.value)}
                  className="cursor-pointer text-xs px-2 h-9"
                >
                  {preset.label}
                </Button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <Input
                id="search-interval"
                type="number"
                value={interval}
                onChange={(e) => setInterval(Number(e.target.value))}
                min={5}
                max={1440}
                className="w-24"
              />
              <span className="text-sm text-muted-foreground">Minuten (benutzerdefiniert)</span>
            </div>
          </div>

          {/* Price Range */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="search-min-price">Min-Preis</Label>
              <Input
                id="search-min-price"
                type="number"
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value)}
                placeholder="0"
                min={0}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="search-max-price">Max-Preis</Label>
              <Input
                id="search-max-price"
                type="number"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                placeholder="9999"
                min={0}
                aria-invalid={!!errors.maxPrice}
              />
              {errors.maxPrice && <p className="text-xs text-destructive">{errors.maxPrice}</p>}
            </div>
          </div>

          {/* Blacklist Keywords with Chips */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-1.5">
              <Label htmlFor="search-blacklist">Blacklist-Keywords</Label>
              <HelpTip text="Angebote mit diesen Begriffen in Titel oder Beschreibung werden herausgefiltert." />
            </div>
            <div className="flex flex-wrap gap-1.5 min-h-[2rem] p-2 border rounded-lg bg-muted/30">
              {keywords.map((kw) => (
                <span
                  key={kw}
                  className="inline-flex items-center gap-1 rounded-md bg-primary/10 text-primary-foreground px-2 py-0.5 text-xs font-medium border border-primary/20 transition-colors hover:bg-primary/20"
                >
                  {kw}
                  <button
                    type="button"
                    onClick={() => removeKeyword(kw)}
                    className="text-primary-foreground/70 hover:text-destructive cursor-pointer"
                    aria-label={`${kw} entfernen`}
                  >
                    <X className="size-3" />
                  </button>
                </span>
              ))}
              {keywords.length === 0 && (
                <span className="text-xs text-muted-foreground">Keine Keywords hinzugefügt</span>
              )}
            </div>
            <div className="flex gap-2">
              <Input
                id="search-blacklist"
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyDown={handleKeywordKeyDown}
                placeholder="Keyword eingeben und Enter drücken..."
                className="flex-1"
              />
              <Button type="button" variant="outline" onClick={addKeyword} className="cursor-pointer">
                Hinzufügen
              </Button>
            </div>
            {keywords.length > 0 && (
              <p className="text-xs text-muted-foreground">{keywords.length} Keyword{keywords.length !== 1 ? "s" : ""} aktiv</p>
            )}
          </div>

          {/* Prompt Addition */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-1.5">
              <Label htmlFor="search-prompt">Prompt-Ergänzung</Label>
              <HelpTip text="Zusätzliche Anweisungen für die KI-Bewertung, z.B. 'Bevorzuge unbenutzte Artikel' oder 'Achte besonders auf den Zustand'." />
            </div>
            <Textarea
              id="search-prompt"
              value={promptAddition}
              onChange={(e) => setPromptAddition(e.target.value)}
              placeholder="z.B. 'Bevorzuge unbenutzte Artikel' oder 'Achte auf Originalverpackung'"
              rows={3}
            />
          </div>

          {/* Exclude Images */}
          <div className="flex items-center gap-3 pt-2">
            <Switch
              id="search-exclude-images"
              checked={excludeImages}
              onCheckedChange={setExcludeImages}
            />
            <Label htmlFor="search-exclude-images" className="cursor-pointer">
              Bilder ausschließen
            </Label>
          </div>
        </CollapsibleContent>
      </Collapsible>

      <div className="flex justify-end gap-2 pt-2 border-t">
        <Button type="button" variant="outline" onClick={onCancel} className="cursor-pointer">
          Abbrechen
        </Button>
        <Button type="submit" disabled={isLoading || !url} className="cursor-pointer">
          {isLoading ? "Speichern..." : initial?.id ? "Aktualisieren" : "Erstellen"}
        </Button>
      </div>
    </form>
  )
}
