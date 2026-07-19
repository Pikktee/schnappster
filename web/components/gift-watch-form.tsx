"use client"

import { useState } from "react"
import {
  Bell,
  ChevronDown,
  ChevronUp,
  Clock,
  HelpCircle,
  MapPin,
  SlidersHorizontal,
  Sparkles,
  Truck,
  type LucideIcon,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
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
import { ScoreBadge } from "@/components/score-badge"
import { createGiftWatch, updateGiftWatch } from "@/lib/api"
import type { GiftVehicle, GiftWatch, GiftWatchCreate } from "@/lib/types"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

const RADIUS_PRESETS = [5, 10, 20, 30, 50]
const INTERVAL_PRESETS = [
  { label: "5 Min", value: 5 },
  { label: "15 Min", value: 15 },
  { label: "30 Min", value: 30 },
  { label: "1 Std", value: 60 },
  { label: "6 Std", value: 360 },
  { label: "Täglich", value: 1440 },
]

/** Deutsche Labels der Transport-Optionen — auch in der Detailseite verwendet. */
export const GIFT_VEHICLE_LABELS: Record<GiftVehicle, string> = {
  bike: "Fahrrad",
  small_car: "Kleinwagen",
  estate: "Kombi/SUV",
  van: "Transporter/Anhänger",
}

const VEHICLE_ORDER: GiftVehicle[] = ["bike", "small_car", "estate", "van"]

const DEFAULT_RADIUS_KM = 20
const DEFAULT_MIN_SCORE = 6
const DEFAULT_INTERVAL_MINUTES = 60

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

interface GiftWatchFormProps {
  /** Vorhandene Fundgrube → Bearbeiten-Modus; ohne → Anlegen. */
  initial?: GiftWatch
  onSaved: () => void
  onCancel: () => void
}

/**
 * Formular zum Anlegen/Bearbeiten einer Fundgrube. Ruft selbst die API und meldet Erfolg
 * per Toast; Fehler werden inline angezeigt. Bringt eigene Fuß-Leiste mit, füllt so das Sheet.
 */
export function GiftWatchForm({ initial, onSaved, onCancel }: GiftWatchFormProps) {
  const isEdit = !!initial?.id

  const [postalCode, setPostalCode] = useState(initial?.postal_code ?? "")
  const [radiusKm, setRadiusKm] = useState<number>(initial?.radius_km ?? DEFAULT_RADIUS_KM)
  const [interestProfile, setInterestProfile] = useState(initial?.interest_profile ?? "")
  const [focusKeywords, setFocusKeywords] = useState(initial?.focus_keywords ?? "")
  const [excludeKeywords, setExcludeKeywords] = useState(initial?.exclude_keywords ?? "")
  const [excludeCategories, setExcludeCategories] = useState(initial?.exclude_categories ?? "")
  const [vehicle, setVehicle] = useState<GiftVehicle>(initial?.vehicle ?? "small_car")
  const [canCarryHeavy, setCanCarryHeavy] = useState(initial?.can_carry_heavy ?? false)
  const [minScore, setMinScore] = useState<number>(initial?.min_score_notify ?? DEFAULT_MIN_SCORE)
  const [interval, setInterval] = useState(
    initial?.scrape_interval_minutes ?? DEFAULT_INTERVAL_MINUTES,
  )
  const [name, setName] = useState(initial?.name ?? "")
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const plz = postalCode.trim()
    if (!/^\d{5}$/.test(plz)) {
      setError("Bitte eine gültige 5-stellige Postleitzahl eingeben.")
      return
    }
    setError(null)
    setSaving(true)
    const payload: GiftWatchCreate = {
      name: name.trim() || undefined,
      postal_code: plz,
      radius_km: radiusKm,
      interest_profile: interestProfile.trim() || null,
      focus_keywords: focusKeywords.trim() || null,
      exclude_keywords: excludeKeywords.trim() || null,
      exclude_categories: excludeCategories.trim() || null,
      vehicle,
      can_carry_heavy: canCarryHeavy,
      min_score_notify: minScore,
      scrape_interval_minutes: interval,
    }
    try {
      if (initial) {
        await updateGiftWatch(initial.id, payload)
        toast.success("Fundgrube aktualisiert")
      } else {
        await createGiftWatch(payload)
        toast.success("Fundgrube angelegt — die erste Prüfung läuft im Hintergrund.")
      }
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen.")
      setSaving(false)
    }
  }

  // Gemeinsame Klasse für eine durch eine Hairline abgesetzte Folge-Sektion (entboxt).
  const section = "mt-6 border-t border-border/60 pt-6"

  return (
    <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto overscroll-contain px-6 py-6">
        {/* Wo? — Mittelpunkt und Umkreis der Verschenken-Suche */}
        <div className="flex flex-col gap-4">
          <SectionHead
            icon={MapPin}
            title="Wo suchst du?"
            subtitle="Mittelpunkt und Umkreis der Verschenken-Suche"
          />
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="gift-plz" className="flex items-center gap-1.5">
              <span>Postleitzahl *</span>
              <HelpTip text="Mittelpunkt der Umkreissuche. Aus der PLZ berechnen wir auch die Entfernung zu den Funden." />
            </Label>
            <Input
              id="gift-plz"
              value={postalCode}
              onChange={(e) => setPostalCode(e.target.value)}
              placeholder="z.B. 50667"
              inputMode="numeric"
              maxLength={5}
              autoFocus={!isEdit}
              className="h-11 text-base"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label className="font-normal text-muted-foreground">Umkreis</Label>
            <div className="grid grid-cols-5 gap-1.5">
              {RADIUS_PRESETS.map((r) => (
                <Button
                  key={r}
                  type="button"
                  variant={radiusKm === r ? "default" : "outline"}
                  size="sm"
                  onClick={() => setRadiusKm(r)}
                  className="h-9 cursor-pointer px-1.5 text-xs"
                >
                  {r} km
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Interessensprofil — die eigenen Regeln fürs Bewerten */}
        <section className={section}>
          <SectionHead
            icon={Sparkles}
            title="Interessensprofil"
            subtitle="Deine eigenen Regeln — danach wird jeder Fund bewertet"
          />
          <div className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="gift-profile" className="font-normal text-muted-foreground">
                Interessensprofil
              </Label>
              <Textarea
                id="gift-profile"
                value={interestProfile}
                onChange={(e) => setInterestProfile(e.target.value)}
                placeholder="z.B. Werkzeug, Vintage-HiFi, Massivholzmöbel"
                rows={4}
              />
              <p className="text-xs text-muted-foreground">
                Was interessiert dich? Freitext, z.B. „Werkzeug, Vintage-HiFi, Massivholzmöbel“.
              </p>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label
                htmlFor="gift-focus"
                className="flex items-center gap-1.5 font-normal text-muted-foreground"
              >
                <span>Schwerpunkte (kommen eher durch)</span>
                <HelpTip text="Kommagetrennte Begriffe, die bevorzugt gemeldet werden." />
              </Label>
              <Input
                id="gift-focus"
                value={focusKeywords}
                onChange={(e) => setFocusKeywords(e.target.value)}
                placeholder="z.B. Bosch, Teak, Schallplatten"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label
                htmlFor="gift-exclude"
                className="flex items-center gap-1.5 font-normal text-muted-foreground"
              >
                <span>Ausschluss-Keywords</span>
                <HelpTip text="Funde mit diesen Begriffen werden gar nicht erst geladen." />
              </Label>
              <Input
                id="gift-exclude"
                value={excludeKeywords}
                onChange={(e) => setExcludeKeywords(e.target.value)}
                placeholder="z.B. Katze, Klavier, Sperrmüll"
              />
            </div>
          </div>
        </section>

        {/* Transport — wie viel Aufwand die Abholung wert ist */}
        <section className={section}>
          <SectionHead
            icon={Truck}
            title="Transport"
            subtitle="Fließt in den Abhol-Lohn ein — was passt in dein Fahrzeug?"
          />
          <div className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="gift-vehicle" className="font-normal text-muted-foreground">
                Fahrzeug
              </Label>
              <Select value={vehicle} onValueChange={(v) => setVehicle(v as GiftVehicle)}>
                <SelectTrigger id="gift-vehicle" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {VEHICLE_ORDER.map((key) => (
                    <SelectItem key={key} value={key}>
                      {GIFT_VEHICLE_LABELS[key]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <label
              htmlFor="gift-heavy"
              className="flex cursor-pointer items-center justify-between gap-3"
            >
              <span className="text-sm text-foreground">Kann schwer heben / habe Helfer</span>
              <Switch id="gift-heavy" checked={canCarryHeavy} onCheckedChange={setCanCarryHeavy} />
            </label>
          </div>
        </section>

        {/* Benachrichtigung — ab welchem Abhol-Lohn gemeldet wird */}
        <section className={section}>
          <SectionHead
            icon={Bell}
            title="Benachrichtigung"
            subtitle="Ab welchem Abhol-Lohn (0–10) du eine Meldung bekommst"
          />
          <div className="mt-4 flex flex-col gap-3">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor="gift-score" className="font-normal text-muted-foreground">
                Ab welchem Score benachrichtigen
              </Label>
              <div className="flex items-center gap-2">
                <ScoreBadge score={minScore} size="sm" />
                <span className="w-10 text-right text-sm font-medium tabular-nums text-foreground">
                  {minScore} / 10
                </span>
              </div>
            </div>
            <Slider
              id="gift-score"
              min={0}
              max={10}
              step={1}
              value={[minScore]}
              onValueChange={(v) => setMinScore(v[0] ?? DEFAULT_MIN_SCORE)}
              aria-label="Ab welchem Score benachrichtigen"
              className="py-1"
            />
          </div>
        </section>

        {/* Prüf-Intervall */}
        <section className={section}>
          <SectionHead
            icon={Clock}
            title="Prüf-Intervall"
            subtitle="Wie oft die Verschenken-Kategorie geprüft wird"
          />
          <div className="mt-4 grid grid-cols-3 gap-1.5 sm:grid-cols-6">
            {INTERVAL_PRESETS.map((preset) => (
              <Button
                key={preset.value}
                type="button"
                variant={interval === preset.value ? "default" : "outline"}
                size="sm"
                onClick={() => setInterval(preset.value)}
                className="h-9 cursor-pointer px-1.5 text-xs"
              >
                {preset.label}
              </Button>
            ))}
          </div>
        </section>

        {/* Erweitert: eigener Name + harter Kategorie-Ausschluss */}
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
              <h3 className="text-sm font-medium leading-tight text-foreground">Erweitert</h3>
              <p className="text-xs text-muted-foreground">Eigener Name, Kategorie-Ausschluss</p>
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
                <Label htmlFor="gift-name" className="font-normal text-muted-foreground">
                  Eigener Name
                </Label>
                <Input
                  id="gift-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Wird sonst aus der PLZ übernommen."
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label
                  htmlFor="gift-exclude-cat"
                  className="flex items-center gap-1.5 font-normal text-muted-foreground"
                >
                  <span>Ausschluss-Kategorien</span>
                  <HelpTip text="Ganze Unterkategorien hart ausschließen, kommagetrennt (z.B. Tiere, Dienstleistungen)." />
                </Label>
                <Input
                  id="gift-exclude-cat"
                  value={excludeCategories}
                  onChange={(e) => setExcludeCategories(e.target.value)}
                  placeholder="z.B. Tiere, Dienstleistungen"
                />
              </div>
            </div>
          )}
        </section>
      </div>

      <div className="flex shrink-0 flex-col gap-3 border-t px-6 py-4">
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onCancel} className="cursor-pointer">
            Abbrechen
          </Button>
          <Button type="submit" disabled={saving} className="cursor-pointer">
            {saving ? "Speichern…" : isEdit ? "Aktualisieren" : "Erstellen"}
          </Button>
        </div>
      </div>
    </form>
  )
}
