"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import type { AdSearch } from "@/lib/types"

interface SearchFormProps {
  initial?: Partial<AdSearch>
  onSubmit: (data: Partial<AdSearch>) => void
  onCancel: () => void
  isLoading?: boolean
}

export function SearchForm({ initial, onSubmit, onCancel, isLoading }: SearchFormProps) {
  const [name, setName] = useState(initial?.name || "")
  const [url, setUrl] = useState(initial?.url || "")
  const [interval, setInterval] = useState(initial?.scrape_interval_minutes || 60)
  const [minPrice, setMinPrice] = useState<string>(initial?.min_price?.toString() || "")
  const [maxPrice, setMaxPrice] = useState<string>(initial?.max_price?.toString() || "")
  const [blacklist, setBlacklist] = useState(initial?.blacklist_keywords || "")
  const [promptAddition, setPromptAddition] = useState(initial?.prompt_addition || "")
  const [excludeImages, setExcludeImages] = useState(initial?.is_exclude_images || false)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit({
      name,
      url,
      scrape_interval_minutes: interval,
      min_price: minPrice ? Number(minPrice) : null,
      max_price: maxPrice ? Number(maxPrice) : null,
      blacklist_keywords: blacklist || null,
      prompt_addition: promptAddition || null,
      is_exclude_images: excludeImages,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="search-name">Name *</Label>
        <Input
          id="search-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="z.B. iPhone Angebote Berlin"
          required
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="search-url">Kleinanzeigen URL *</Label>
        <Input
          id="search-url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.kleinanzeigen.de/s-..."
          type="url"
          required
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="search-interval">Scrape-Intervall (Minuten)</Label>
        <Input
          id="search-interval"
          type="number"
          value={interval}
          onChange={(e) => setInterval(Number(e.target.value))}
          min={5}
          max={1440}
        />
      </div>

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
          />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="search-blacklist">Blacklist-Keywords (kommagetrennt)</Label>
        <Input
          id="search-blacklist"
          value={blacklist}
          onChange={(e) => setBlacklist(e.target.value)}
          placeholder="defekt, kaputt, bastler"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="search-prompt">Prompt-Ergaenzung</Label>
        <Textarea
          id="search-prompt"
          value={promptAddition}
          onChange={(e) => setPromptAddition(e.target.value)}
          placeholder="Zusaetzliche Anweisungen fuer die KI-Analyse..."
          rows={3}
        />
      </div>

      <div className="flex items-center gap-3">
        <Switch
          id="search-exclude-images"
          checked={excludeImages}
          onCheckedChange={setExcludeImages}
        />
        <Label htmlFor="search-exclude-images" className="cursor-pointer">
          Bilder ausschliessen
        </Label>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="outline" onClick={onCancel} className="cursor-pointer">
          Abbrechen
        </Button>
        <Button type="submit" disabled={isLoading || !name || !url} className="cursor-pointer">
          {isLoading ? "Speichern..." : initial?.id ? "Aktualisieren" : "Erstellen"}
        </Button>
      </div>
    </form>
  )
}
