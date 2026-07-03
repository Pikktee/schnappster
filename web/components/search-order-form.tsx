"use client"

import { useCallback, useEffect, useState } from "react"
import {
  Check,
  ChevronDown,
  ChevronUp,
  Clock,
  Flame,
  HelpCircle,
  ShoppingBag,
  SlidersHorizontal,
  Store,
  X,
  type LucideIcon,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { SearchOrder, SearchOrderCreate } from "@/lib/types"
import { cn } from "@/lib/utils"

const RADIUS_PRESETS = [5, 10, 25, 50, 100, 200]
const INTERVAL_PRESETS = [
  { label: "5 Min", value: 5 },
  { label: "15 Min", value: 15 },
  { label: "30 Min", value: 30 },
  { label: "1 Std", value: 60 },
  { label: "6 Std", value: 360 },
  { label: "Täglich", value: 1440 },
]
const TEMPERATURE_PRESETS: { label: string; value: number | null }[] = [
  { label: "Alle", value: null },
  { label: "100°", value: 100 },
  { label: "200°", value: 200 },
  { label: "300°", value: 300 },
  { label: "500°", value: 500 },
]
const VELOCITY_PRESETS: { label: string; value: number | null }[] = [
  { label: "Aus", value: null },
  { label: "50°/h", value: 50 },
  { label: "100°/h", value: 100 },
  { label: "200°/h", value: 200 },
]

interface SourceOption {
  key: "kleinanzeigen" | "ebay" | "mydealz"
  label: string
  hint: string
  icon: LucideIcon
}

const SOURCES: SourceOption[] = [
  { key: "kleinanzeigen", label: "Kleinanzeigen", hint: "Gebraucht, lokal", icon: Store },
  { key: "ebay", label: "eBay", hint: "Gebraucht, Versand", icon: ShoppingBag },
  { key: "mydealz", label: "MyDealz", hint: "Neuware-Deals", icon: Flame },
]

function HelpTip({ text }: { text: string }) {
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <HelpCircle className="size-3.5 cursor-help text-muted-foreground/60" />
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs text-xs">
          {text}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

/** Sektionskopf: farbig hinterlegtes Icon + Titel + optionaler Unterzeile — gliedert ohne Kasten. */
function SectionHead({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: LucideIcon
  title: string
  subtitle?: string
}) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="size-4" aria-hidden />
      </span>
      <div className="min-w-0">
        <h3 className="text-sm font-medium leading-tight text-foreground">{title}</h3>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>
    </div>
  )
}

function parseKeywords(str: string): string[] {
  return str
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
}

interface SearchOrderFormProps {
  initial?: SearchOrder
  onSubmit: (data: SearchOrderCreate) => Promise<void> | void
  onCancel: () => void
  isLoading?: boolean
  onDirtyChange?: (dirty: boolean) => void
}

export function SearchOrderForm({
  initial,
  onSubmit,
  onCancel,
  isLoading,
  onDirtyChange,
}: SearchOrderFormProps) {
  const anyAdChild = initial?.kleinanzeigen ?? initial?.ebay ?? null
  const isEdit = !!initial?.id
  // Adoptierte URL-Alt-Suchen haben keinen Suchbegriff; der bleibt dann leer (URL läuft weiter).
  const isUrlLegacy = isEdit && !initial?.query

  const [query, setQuery] = useState(initial?.query || "")
  const [name, setName] = useState(initial?.name || "")
  const [useKleinanzeigen, setUseKleinanzeigen] = useState(
    initial ? !!initial.kleinanzeigen : true,
  )
  const [useEbay, setUseEbay] = useState(!!initial?.ebay)
  const [useMydealz, setUseMydealz] = useState(!!initial?.mydealz)
  const [postalCode, setPostalCode] = useState(initial?.kleinanzeigen?.postal_code || "")
  const [radiusKm, setRadiusKm] = useState<string>(
    initial?.kleinanzeigen?.radius_km?.toString() || "",
  )
  const [minPrice, setMinPrice] = useState<string>(anyAdChild?.min_price?.toString() || "")
  const [maxPrice, setMaxPrice] = useState<string>(anyAdChild?.max_price?.toString() || "")
  const [mydealzMaxPrice, setMydealzMaxPrice] = useState<string>(
    initial?.mydealz?.max_price?.toString() || "",
  )
  const [minTemperature, setMinTemperature] = useState<number | null>(
    initial ? (initial.mydealz?.min_temperature ?? null) : 200,
  )
  const [minVelocity, setMinVelocity] = useState<number | null>(
    initial?.mydealz?.min_heating_velocity ?? null,
  )
  const [interval, setInterval] = useState(
    anyAdChild?.scrape_interval_minutes ?? initial?.mydealz?.scrape_interval_minutes ?? 60,
  )
  const [keywords, setKeywords] = useState<string[]>(
    anyAdChild?.blacklist_keywords ? parseKeywords(anyAdChild.blacklist_keywords) : [],
  )
  const [keywordInput, setKeywordInput] = useState("")
  const [promptAddition, setPromptAddition] = useState(anyAdChild?.prompt_addition || "")
  const [excludeImages, setExcludeImages] = useState(anyAdChild?.is_exclude_images || false)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)

  const markDirty = useCallback(() => setDirty(true), [])
  useEffect(() => {
    onDirtyChange?.(dirty)
  }, [dirty, onDirtyChange])

  const usedAdSource = useKleinanzeigen || useEbay
  const anySource = usedAdSource || useMydealz
  const usedLabel =
    useEbay && useKleinanzeigen
      ? "Kleinanzeigen & eBay"
      : useEbay
        ? "eBay"
        : "Kleinanzeigen"

  function toggleSource(key: SourceOption["key"]) {
    markDirty()
    if (key === "kleinanzeigen") setUseKleinanzeigen((v) => !v)
    if (key === "ebay") setUseEbay((v) => !v)
    if (key === "mydealz") setUseMydealz((v) => !v)
  }

  const isSelected: Record<SourceOption["key"], boolean> = {
    kleinanzeigen: useKleinanzeigen,
    ebay: useEbay,
    mydealz: useMydealz,
  }

  const addKeyword = useCallback(() => {
    const trimmed = keywordInput.trim()
    if (trimmed && !keywords.includes(trimmed)) {
      setKeywords((prev) => [...prev, trimmed])
      markDirty()
    }
    setKeywordInput("")
  }, [keywordInput, keywords, markDirty])

  function handleKeywordKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      addKeyword()
    }
    if (e.key === "Backspace" && keywordInput === "" && keywords.length > 0) {
      setKeywords((prev) => prev.slice(0, -1))
      markDirty()
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim() && !isUrlLegacy) {
      setError("Bitte einen Suchbegriff eingeben.")
      return
    }
    if (!anySource) {
      setError("Bitte mindestens eine Quelle auswählen.")
      return
    }
    if (minPrice && maxPrice && Number(minPrice) > Number(maxPrice)) {
      setError("Der Max-Preis muss größer als der Min-Preis sein.")
      return
    }
    setError(null)
    try {
      await onSubmit({
        name: name.trim() || undefined,
        query: query.trim() || (isUrlLegacy ? initial?.name || "URL-Suche" : ""),
        scrape_interval_minutes: interval,
        use_kleinanzeigen: useKleinanzeigen,
        use_ebay: useEbay,
        use_mydealz: useMydealz,
        postal_code: postalCode.trim() || null,
        radius_km: postalCode.trim() && radiusKm ? Number(radiusKm) : null,
        min_price: minPrice ? Number(minPrice) : null,
        max_price: maxPrice ? Number(maxPrice) : null,
        blacklist_keywords: keywords.length > 0 ? keywords.join(", ") : null,
        prompt_addition: promptAddition || null,
        is_exclude_images: excludeImages,
        mydealz_max_price: mydealzMaxPrice ? Number(mydealzMaxPrice) : null,
        mydealz_min_temperature: minTemperature,
        mydealz_min_heating_velocity: minVelocity,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Speichern.")
    }
  }

  // Gemeinsame Klasse für eine durch eine Hairline abgesetzte Folge-Sektion (entboxt).
  const section = "mt-6 border-t border-border/60 pt-6"

  return (
    <form onSubmit={handleSubmit} className="flex flex-col">
      {/* Kopf: Suchbegriff + Quellenauswahl — das „Was & Wo“ */}
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="order-query" className="flex items-center gap-1.5">
            <span>Suchbegriff {isUrlLegacy ? "" : "*"}</span>
            <HelpTip text="Wonach suchst du? Daraus bauen wir die Suchen aller gewählten Quellen automatisch." />
          </Label>
          <Input
            id="order-query"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              markDirty()
            }}
            placeholder={
              isUrlLegacy ? "Alt-Suche über URL — Begriff optional" : "z.B. LEGO Millennium Falcon"
            }
            autoFocus={!isEdit}
            className="h-11 text-base"
          />
          {isUrlLegacy && (
            <p className="text-xs text-muted-foreground">
              Diese Suche wurde über eine Kleinanzeigen-URL angelegt und läuft unverändert weiter.
            </p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <Label>Wo suchen?</Label>
          <div className="grid grid-cols-3 gap-2">
            {SOURCES.map((source) => {
              const selected = isSelected[source.key]
              return (
                <button
                  key={source.key}
                  type="button"
                  onClick={() => toggleSource(source.key)}
                  aria-pressed={selected}
                  className={cn(
                    "relative flex cursor-pointer flex-col items-start gap-1 rounded-xl border p-3 text-left transition-all",
                    selected
                      ? "border-primary/60 bg-primary/[0.06] shadow-sm"
                      : "border-border bg-muted/30 opacity-75 hover:opacity-100",
                  )}
                >
                  <span
                    className={cn(
                      "absolute right-2 top-2 flex size-4 items-center justify-center rounded-full border",
                      selected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-muted-foreground/30 bg-background",
                    )}
                  >
                    {selected && <Check className="size-3" aria-hidden />}
                  </span>
                  <source.icon
                    className={cn("size-4", selected ? "text-primary" : "text-muted-foreground")}
                    aria-hidden
                  />
                  <span className="text-sm font-medium leading-none">{source.label}</span>
                  <span className="text-[11px] leading-tight text-muted-foreground">
                    {source.hint}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Gebraucht: gemeinsame Preisspanne + Standort (nur Kleinanzeigen) */}
      {usedAdSource && (
        <section className={section}>
          <SectionHead icon={Store} title="Gebraucht" subtitle={usedLabel} />
          <div className="mt-4 flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="order-min-price" className="font-normal text-muted-foreground">
                  Preis von
                </Label>
                <Input
                  id="order-min-price"
                  type="number"
                  min={0}
                  value={minPrice}
                  onChange={(e) => {
                    setMinPrice(e.target.value)
                    markDirty()
                  }}
                  placeholder="0 €"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="order-max-price" className="font-normal text-muted-foreground">
                  bis
                </Label>
                <Input
                  id="order-max-price"
                  type="number"
                  min={0}
                  value={maxPrice}
                  onChange={(e) => {
                    setMaxPrice(e.target.value)
                    markDirty()
                  }}
                  placeholder="beliebig"
                />
              </div>
            </div>
            {useKleinanzeigen && (
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label
                    htmlFor="order-plz"
                    className="flex items-center gap-1.5 font-normal text-muted-foreground"
                  >
                    <span>PLZ</span>
                    <HelpTip text="Mittelpunkt der Kleinanzeigen-Umkreissuche. Leer = deutschlandweit. eBay ist immer bundesweit." />
                  </Label>
                  <Input
                    id="order-plz"
                    value={postalCode}
                    onChange={(e) => {
                      setPostalCode(e.target.value)
                      markDirty()
                    }}
                    placeholder="z.B. 50667"
                    inputMode="numeric"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="order-radius" className="font-normal text-muted-foreground">
                    Umkreis
                  </Label>
                  <Select
                    value={radiusKm || "any"}
                    onValueChange={(v) => {
                      setRadiusKm(v === "any" ? "" : v)
                      markDirty()
                    }}
                    disabled={!postalCode.trim()}
                  >
                    <SelectTrigger id="order-radius" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="any">Egal</SelectItem>
                      {RADIUS_PRESETS.map((r) => (
                        <SelectItem key={r} value={String(r)}>
                          {r} km
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* MyDealz: eigenes Budget (Neuware) + Alarm-Schwellen */}
      {useMydealz && (
        <section className={section}>
          <SectionHead icon={Flame} title="MyDealz" subtitle="Neuware-Deals" />
          <div className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="order-mydealz-max" className="font-normal text-muted-foreground">
                Höchstpreis
              </Label>
              <Input
                id="order-mydealz-max"
                type="number"
                min={0}
                value={mydealzMaxPrice}
                onChange={(e) => {
                  setMydealzMaxPrice(e.target.value)
                  markDirty()
                }}
                placeholder="beliebig"
              />
              <p className="text-xs text-muted-foreground">
                Neuware darf teurer sein als Gebrauchtes — eigene Obergrenze.
              </p>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="font-normal text-muted-foreground">Alarm ab Temperatur</Label>
              <div className="grid grid-cols-5 gap-1.5">
                {TEMPERATURE_PRESETS.map((preset) => (
                  <Button
                    key={preset.label}
                    type="button"
                    variant={minTemperature === preset.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => {
                      setMinTemperature(preset.value)
                      markDirty()
                    }}
                    className="cursor-pointer px-2 text-xs"
                  >
                    {preset.label}
                  </Button>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Wie „heiß“ ein Deal per Community-Votes sein muss, um gemeldet zu werden.
              </p>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="font-normal text-muted-foreground">Frühwarnung</Label>
              <div className="grid grid-cols-4 gap-1.5">
                {VELOCITY_PRESETS.map((preset) => (
                  <Button
                    key={preset.label}
                    type="button"
                    variant={minVelocity === preset.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => {
                      setMinVelocity(preset.value)
                      markDirty()
                    }}
                    className="cursor-pointer px-2 text-xs"
                  >
                    {preset.label}
                  </Button>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Meldet Deals, die schnell aufheizen — noch bevor sie die Schwelle erreichen.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Prüf-Intervall */}
      <section className={section}>
        <SectionHead icon={Clock} title="Prüf-Intervall" subtitle="Wie oft alle Quellen geprüft werden" />
        <div className="mt-4 grid grid-cols-3 gap-1.5 sm:grid-cols-6">
          {INTERVAL_PRESETS.map((preset) => (
            <Button
              key={preset.value}
              type="button"
              variant={interval === preset.value ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setInterval(preset.value)
                markDirty()
              }}
              className="h-9 cursor-pointer px-1.5 text-xs"
            >
              {preset.label}
            </Button>
          ))}
        </div>
      </section>

      {/* Erweiterte Optionen: Name immer, KI-/Filter-Felder nur für Gebraucht-Quellen */}
      <section className={section}>
        <button
          type="button"
          onClick={() => setAdvancedOpen((v) => !v)}
          aria-expanded={advancedOpen}
          className="flex w-full cursor-pointer items-center gap-2.5 text-left"
        >
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <SlidersHorizontal className="size-4" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-medium leading-tight text-foreground">Erweiterte Optionen</h3>
            <p className="text-xs text-muted-foreground">Name, Ausschluss-Wörter, KI-Feinschliff</p>
          </div>
          {advancedOpen ? (
            <ChevronUp className="size-4 text-muted-foreground" aria-hidden />
          ) : (
            <ChevronDown className="size-4 text-muted-foreground" aria-hidden />
          )}
        </button>
        {advancedOpen && (
          <div className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="order-name" className="font-normal text-muted-foreground">
                Eigener Name
              </Label>
              <Input
                id="order-name"
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  markDirty()
                }}
                placeholder="Wird sonst aus dem Suchbegriff übernommen."
              />
            </div>
            {usedAdSource && (
              <>
                <div className="flex flex-col gap-1.5">
                  <Label className="flex items-center gap-1.5 font-normal text-muted-foreground">
                    <span>Ausschluss-Keywords</span>
                    <HelpTip text="Gebraucht-Angebote mit diesen Begriffen werden nicht geladen." />
                  </Label>
                  <div className="flex gap-2">
                    <Input
                      value={keywordInput}
                      onChange={(e) => setKeywordInput(e.target.value)}
                      onKeyDown={handleKeywordKeyDown}
                      placeholder="Wort eingeben, Enter drücken"
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={addKeyword}
                      className="cursor-pointer"
                    >
                      Hinzufügen
                    </Button>
                  </div>
                  {keywords.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {keywords.map((kw) => (
                        <span
                          key={kw}
                          className="inline-flex items-center gap-1 rounded-md border border-border bg-muted px-2 py-0.5 text-xs font-medium text-foreground"
                        >
                          {kw}
                          <button
                            type="button"
                            onClick={() => {
                              setKeywords((prev) => prev.filter((k) => k !== kw))
                              markDirty()
                            }}
                            className="cursor-pointer text-muted-foreground hover:text-destructive"
                            aria-label={`${kw} entfernen`}
                          >
                            <X className="size-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label
                    htmlFor="order-prompt"
                    className="flex items-center gap-1.5 font-normal text-muted-foreground"
                  >
                    <span>Zusätzliche KI-Anweisungen</span>
                    <HelpTip text="Zusätzliche Hinweise für die KI-Bewertung der Gebraucht-Angebote." />
                  </Label>
                  <Textarea
                    id="order-prompt"
                    value={promptAddition}
                    onChange={(e) => {
                      setPromptAddition(e.target.value)
                      markDirty()
                    }}
                    placeholder="z.B. Bevorzuge unbenutzte Artikel mit Originalverpackung"
                    rows={2}
                  />
                </div>
                <label
                  htmlFor="order-exclude-images"
                  className="flex cursor-pointer items-center justify-between gap-3"
                >
                  <span className="text-sm text-foreground">Anzeigen-Bilder nicht an die KI senden</span>
                  <Switch
                    id="order-exclude-images"
                    checked={excludeImages}
                    onCheckedChange={(v) => {
                      setExcludeImages(v)
                      markDirty()
                    }}
                  />
                </label>
              </>
            )}
          </div>
        )}
      </section>

      {error && (
        <p role="alert" className="mt-4 text-sm text-destructive">
          {error}
        </p>
      )}

      {/* Aktionsleiste bleibt beim Scrollen sichtbar. Der Seiten-Scrollbereich (main.main-scroll)
          hat unten p-6 / lg:p-8 Padding; der solide box-shadow füllt genau dieses Padding mit
          Hintergrundfarbe, sodass kein Inhalt unter der Leiste durchscheint. */}
      <div className="sticky bottom-0 z-10 mt-8 flex justify-end gap-2 border-t bg-background py-4 shadow-[0_1.5rem_0_0_var(--background)] lg:shadow-[0_2rem_0_0_var(--background)]">
        <Button type="button" variant="outline" onClick={onCancel} className="cursor-pointer">
          Abbrechen
        </Button>
        <Button type="submit" disabled={isLoading} className="cursor-pointer">
          {isLoading ? "Speichern..." : isEdit ? "Aktualisieren" : "Erstellen"}
        </Button>
      </div>
    </form>
  )
}
