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
import { fetchSettings, fetchTelegramConfigured, updateSetting } from "@/lib/api"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { ContentReveal } from "@/components/content-reveal"

const MIN_SELLER_RATING_OPTIONS = [
  { value: "0", label: "Na ja" },
  { value: "1", label: "OK" },
  { value: "2", label: "TOP" },
] as const

const AUTO_DELETE_OPTIONS = [
  { value: "0", label: "Deaktiviert" },
  { value: "7", label: "7 Tage" },
  { value: "14", label: "14 Tage" },
  { value: "31", label: "31 Tage" },
] as const

export default function SettingsPage() {
  const [excludeCommercialSellers, setExcludeCommercialSellers] = useState(false)
  const [minSellerRating, setMinSellerRating] = useState("0")
  const [telegramNotificationsEnabled, setTelegramNotificationsEnabled] = useState(false)
  const [autoDeleteAdsDays, setAutoDeleteAdsDays] = useState("7")
  const [telegramConfigured, setTelegramConfigured] = useState(false)
  const [loading, setLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [list, telegramConfig] = await Promise.all([
          fetchSettings(),
          fetchTelegramConfigured(),
        ])
        setTelegramConfigured(telegramConfig.configured)
        const excludeEntry = list.find(
          (s: { key: string; value: string }) => s.key === "exclude_commercial_sellers"
        )
        const ratingEntry = list.find(
          (s: { key: string; value: string }) => s.key === "min_seller_rating"
        )
        const telegramEntry = list.find(
          (s: { key: string; value: string }) => s.key === "telegram_notifications_enabled"
        )
        const autoDeleteEntry = list.find(
          (s: { key: string; value: string }) => s.key === "auto_delete_ads_days"
        )
        if (excludeEntry) setExcludeCommercialSellers(excludeEntry.value === "true")
        if (ratingEntry) setMinSellerRating(ratingEntry.value ?? "0")
        if (telegramEntry) setTelegramNotificationsEnabled(telegramEntry.value === "true")
        if (autoDeleteEntry) setAutoDeleteAdsDays(autoDeleteEntry.value ?? "7")
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
      await updateSetting(
        "telegram_notifications_enabled",
        telegramNotificationsEnabled ? "true" : "false"
      )
      await updateSetting("auto_delete_ads_days", autoDeleteAdsDays)
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
      <div className="flex flex-col gap-8">
        <Skeleton className="h-48 max-w-2xl" />
      </div>
    )
  }

  return (
    <ContentReveal className="flex flex-col gap-8">
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Verkäufer-Filter</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <Label htmlFor="exclude-commercial">Gewerbliche Verkäufer ausschließen</Label>
              <p className="text-sm leading-relaxed text-muted-foreground">
                Angebote von gewerblichen Verkäufern werden bei Suchen ausgeblendet.
              </p>
            </div>
            <Switch
              id="exclude-commercial"
              checked={excludeCommercialSellers}
              onCheckedChange={setExcludeCommercialSellers}
            />
          </div>

          <div className="flex flex-col gap-2">
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
            <p className="text-sm leading-relaxed text-muted-foreground">
              Nur Angebote von Verkäufern mit mindestens dieser Bewertung anzeigen.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Benachrichtigungen</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          {!telegramConfigured && (
            <div className="space-y-2 text-sm leading-relaxed text-muted-foreground">
              <p>
                Telegram ist nicht konfiguriert. Setze{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 text-[0.8em]">TELEGRAM_BOT_TOKEN</code>{" "}
                und <code className="rounded bg-muted px-1.5 py-0.5 text-[0.8em]">TELEGRAM_CHAT_ID</code>{" "}
                in der .env-Datei.
              </p>
              <p>
                <a
                  href="https://core.telegram.org/bots#how-do-i-create-a-bot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-link hover:underline"
                >
                  Anleitung: Telegram Bot erstellen &rarr;
                </a>
              </p>
            </div>
          )}
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <Label
                htmlFor="telegram-notifications"
                className={!telegramConfigured ? "opacity-60" : undefined}
              >
                Telegram-Benachrichtigungen bei Schnäppchen
              </Label>
              <p className="text-sm leading-relaxed text-muted-foreground">
                Bei identifizierten Schnäppchen (Score ≥ 8) eine Nachricht an
                den konfigurierten Telegram-Chat senden.
              </p>
            </div>
            <Switch
              id="telegram-notifications"
              checked={telegramNotificationsEnabled}
              onCheckedChange={setTelegramNotificationsEnabled}
              disabled={!telegramConfigured}
              className={!telegramConfigured ? "opacity-60" : undefined}
            />
          </div>
        </CardContent>
      </Card>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Datenverwaltung</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <Label htmlFor="auto-delete-ads">Alte Anzeigen automatisch löschen</Label>
            <Select value={autoDeleteAdsDays} onValueChange={setAutoDeleteAdsDays}>
              <SelectTrigger id="auto-delete-ads" className="w-full max-w-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AUTO_DELETE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Anzeigen werden nach der gewählten Anzahl von Tagen automatisch gelöscht.
              Bei &quot;Deaktiviert&quot; werden keine Anzeigen gelöscht.
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="max-w-2xl pt-2">
        <Button
          onClick={handleSave}
          disabled={isSaving}
          className="cursor-pointer gap-2 px-5"
        >
          <Save className="size-4" />
          {isSaving ? "Speichern..." : "Einstellungen speichern"}
        </Button>
      </div>
    </ContentReveal>
  )
}
