"use client"

import { useEffect, useState } from "react"
import { Save } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { PageHeader } from "@/components/page-header"
import { fetchSettings, updateSetting } from "@/lib/api"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

const MIN_SELLER_RATING_OPTIONS = [
  { value: "0", label: "Na ja" },
  { value: "1", label: "OK" },
  { value: "2", label: "TOP" },
] as const

export default function SettingsPage() {
  const [excludeCommercialSellers, setExcludeCommercialSellers] = useState(false)
  const [minSellerRating, setMinSellerRating] = useState("0")
  const [loading, setLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const list = await fetchSettings()
        const excludeEntry = list.find(
          (s: { key: string; value: string }) => s.key === "exclude_commercial_sellers"
        )
        const ratingEntry = list.find(
          (s: { key: string; value: string }) => s.key === "min_seller_rating"
        )
        if (excludeEntry) setExcludeCommercialSellers(excludeEntry.value === "true")
        if (ratingEntry) setMinSellerRating(ratingEntry.value ?? "0")
      } catch {
        toast.error("Einstellungen konnten nicht geladen werden.")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  async function handleSave() {
    setIsSaving(true)
    try {
      await updateSetting(
        "exclude_commercial_sellers",
        excludeCommercialSellers ? "true" : "false"
      )
      await updateSetting("min_seller_rating", minSellerRating)
      toast.success("Einstellungen gespeichert")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Speichern fehlgeschlagen."
      toast.error(msg)
    } finally {
      setIsSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Einstellungen" subtitle="Globale App-Einstellungen" />
        <Skeleton className="h-48 max-w-2xl" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Einstellungen" subtitle="Globale App-Einstellungen" />

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Verkäufer-Filter</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label htmlFor="exclude-commercial">Gewerbliche Verkäufer ausschließen</Label>
              <p className="text-xs text-muted-foreground">
                Angebote von gewerblichen Verkäufern werden bei Suchen ausgeblendet.
              </p>
            </div>
            <Switch
              id="exclude-commercial"
              checked={excludeCommercialSellers}
              onCheckedChange={setExcludeCommercialSellers}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="min-seller-rating">Mindest-Verkäuferbewertung</Label>
            <Select value={minSellerRating} onValueChange={setMinSellerRating}>
              <SelectTrigger id="min-seller-rating" className="w-full max-w-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MIN_SELLER_RATING_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Nur Angebote von Verkäufern mit mindestens dieser Bewertung anzeigen.
            </p>
          </div>

          <div className="pt-2">
            <Button onClick={handleSave} disabled={isSaving} className="cursor-pointer">
              <Save className="size-4" />
              {isSaving ? "Speichern..." : "Einstellungen speichern"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
