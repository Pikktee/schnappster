"use client"

import { useEffect, useState } from "react"
import { Save, User, Bell, Shield, Trash2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import {
  changePassword,
  deleteMyAccount,
  fetchMe,
  fetchMySettings,
  fetchSetting,
  fetchTelegramConfigured,
  updateMe,
  updateMySettings,
  updateSetting,
} from "@/lib/api"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { ContentReveal } from "@/components/content-reveal"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { supabase } from "@/lib/supabase"

export default function SettingsPage() {
  const [displayName, setDisplayName] = useState("")
  const [email, setEmail] = useState("")
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [notifyTelegram, setNotifyTelegram] = useState(false)
  const [notifyEmail, setNotifyEmail] = useState(false)
  const [notifyMinScore, setNotifyMinScore] = useState("8")
  const [notifyMode, setNotifyMode] = useState<"instant" | "daily_summary">("instant")
  const [telegramChatId, setTelegramChatId] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [deleteConfirmation, setDeleteConfirmation] = useState("")
  const [excludeCommercialSellers, setExcludeCommercialSellers] = useState(false)
  const [minSellerRating, setMinSellerRating] = useState("0")
  const [telegramConfigured, setTelegramConfigured] = useState(false)
  const [loading, setLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [profile, userSettings, telegramConfig] = await Promise.all([
          fetchMe(),
          fetchMySettings(),
          fetchTelegramConfigured(),
        ])
        setDisplayName(profile.display_name)
        setEmail(profile.email ?? "")
        setAvatarUrl(profile.avatar_url)
        setIsAdmin(profile.role === "admin")
        setNotifyTelegram(userSettings.notify_telegram)
        setNotifyEmail(userSettings.notify_email)
        setNotifyMinScore(String(userSettings.notify_min_score))
        setNotifyMode(userSettings.notify_mode)
        setTelegramChatId(userSettings.telegram_chat_id ?? "")
        setTelegramConfigured(telegramConfig.configured)
        if (profile.role === "admin") {
          const [exclude, minRating] = await Promise.all([
            fetchSetting("exclude_commercial_sellers"),
            fetchSetting("min_seller_rating"),
          ])
          setExcludeCommercialSellers(exclude.value === "true")
          setMinSellerRating(minRating.value)
        }
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
      await Promise.all([
        updateMe({ display_name: displayName }),
        updateMySettings({
          display_name: displayName,
          notify_telegram: notifyTelegram,
          notify_email: notifyEmail,
          notify_min_score: Number(notifyMinScore),
          notify_mode: notifyMode,
          telegram_chat_id: telegramChatId || null,
        }),
      ])
      if (isAdmin) {
        await Promise.all([
          updateSetting("exclude_commercial_sellers", excludeCommercialSellers ? "true" : "false"),
          updateSetting("min_seller_rating", minSellerRating),
        ])
      }
      toast.success("Einstellungen gespeichert")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Speichern fehlgeschlagen."
      toast.error(msg)
    } finally {
      setIsSaving(false)
    }
  }

  async function handleChangePassword() {
    if (!newPassword.trim()) return
    try {
      await changePassword(newPassword.trim())
      setNewPassword("")
      toast.success("Passwort aktualisiert.")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Passwort konnte nicht geaendert werden.")
    }
  }

  async function handleDeleteAccount() {
    if (deleteConfirmation.trim().toLowerCase() !== "loeschen") return
    setIsDeleting(true)
    try {
      await deleteMyAccount()
      await supabase?.auth.signOut()
      window.location.href = "/login"
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Konto konnte nicht geloescht werden.")
    } finally {
      setIsDeleting(false)
      setOpenDeleteDialog(false)
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
          <CardTitle className="flex items-center gap-2">
            <User className="size-5" />
            Profil
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          {avatarUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={avatarUrl} alt="Avatar" className="size-14 rounded-full border" />
          )}
          <div className="flex flex-col gap-2">
            <Label htmlFor="display-name">Anzeigename</Label>
            <Input id="display-name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">E-Mail</Label>
            <Input id="email" value={email} readOnly />
          </div>
        </CardContent>
      </Card>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="size-5" />
            Benachrichtigungen
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          {!telegramConfigured && (
            <div className="space-y-2 text-sm leading-relaxed text-muted-foreground">
              <p>
                Telegram ist nicht konfiguriert. Setze{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 text-[0.8em]">TELEGRAM_BOT_TOKEN</code>{" "}
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
                Telegram-Benachrichtigungen bei Angeboten
              </Label>
              <p className="text-sm leading-relaxed text-muted-foreground">
                Bei passenden Angeboten eine Nachricht an den hinterlegten Telegram-Chat senden.
              </p>
            </div>
            <Switch
              id="telegram-notifications"
              checked={notifyTelegram}
              onCheckedChange={setNotifyTelegram}
              disabled={!telegramConfigured}
              className={!telegramConfigured ? "opacity-60" : undefined}
            />
          </div>
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <Label htmlFor="notify-email">E-Mail-Benachrichtigungen</Label>
            </div>
            <Switch id="notify-email" checked={notifyEmail} onCheckedChange={setNotifyEmail} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="telegram-chat-id">Telegram Chat-ID (pro Nutzer)</Label>
            <Input
              id="telegram-chat-id"
              value={telegramChatId}
              onChange={(e) => setTelegramChatId(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="notify-min-score">Mindest-Score</Label>
            <Select value={notifyMinScore} onValueChange={setNotifyMinScore}>
              <SelectTrigger id="notify-min-score" className="w-full max-w-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 11 }).map((_, score) => (
                  <SelectItem key={score} value={String(score)}>
                    {score}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="notify-mode">Modus</Label>
            <Select
              value={notifyMode}
              onValueChange={(v) => setNotifyMode(v as "instant" | "daily_summary")}
            >
              <SelectTrigger id="notify-mode" className="w-full max-w-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="instant">Sofort</SelectItem>
                <SelectItem value="daily_summary">Tageszusammenfassung</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {isAdmin && (
        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="size-5" />
              Admin-Einstellungen
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-6">
            <div className="flex items-center justify-between gap-4">
              <div className="space-y-1">
                <Label htmlFor="exclude-commercial">Gewerbliche Verkaeufer ausschliessen</Label>
              </div>
              <Switch
                id="exclude-commercial"
                checked={excludeCommercialSellers}
                onCheckedChange={setExcludeCommercialSellers}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="min-seller-rating">Mindest-Verkaeuferbewertung</Label>
              <Select value={minSellerRating} onValueChange={setMinSellerRating}>
                <SelectTrigger id="min-seller-rating" className="w-full max-w-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">Na ja</SelectItem>
                  <SelectItem value="1">OK</SelectItem>
                  <SelectItem value="2">TOP</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Passwort aendern</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="new-password">Neues Passwort</Label>
            <Input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <div>
            <Button variant="outline" onClick={handleChangePassword}>
              Passwort speichern
            </Button>
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

      <Card className="max-w-2xl border-destructive/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="size-5" />
            Danger Zone
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            Konto und zugehoerige App-Daten dauerhaft loeschen.
          </p>
          <div className="flex flex-col gap-2">
            <Label htmlFor="delete-confirmation">Zur Bestaetigung &quot;loeschen&quot; eingeben</Label>
            <Input
              id="delete-confirmation"
              value={deleteConfirmation}
              onChange={(e) => setDeleteConfirmation(e.target.value)}
            />
          </div>
          <AlertDialog open={openDeleteDialog} onOpenChange={setOpenDeleteDialog}>
            <Button
              variant="destructive"
              onClick={() => setOpenDeleteDialog(true)}
              disabled={deleteConfirmation.trim().toLowerCase() !== "loeschen" || isDeleting}
            >
              Konto loeschen
            </Button>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Konto wirklich loeschen?</AlertDialogTitle>
                <AlertDialogDescription>
                  Diese Aktion kann nicht rueckgaengig gemacht werden.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Abbrechen</AlertDialogCancel>
                <AlertDialogAction onClick={handleDeleteAccount}>
                  {isDeleting ? "Loesche..." : "Ja, loeschen"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </ContentReveal>
  )
}
