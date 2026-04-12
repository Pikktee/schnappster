"use client"

import { useEffect, useMemo, useState } from "react"
import { Save, User, Bell, Shield, Trash2, Lock, HelpCircle } from "lucide-react"
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
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
import {
  DISPLAY_NAME_MAX_LENGTH,
  getSettingsSaveValidationErrors,
  humanizeSettingsSaveApiError,
  settingsSaveHasErrors,
} from "@/lib/settings-validation"
import { cn } from "@/lib/utils"
import { PasswordStrengthIndicator } from "@/components/password-strength-indicator"
import { isPasswordValid } from "@/lib/password-validation"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export default function SettingsPage() {
  const [displayName, setDisplayName] = useState("")
  const [email, setEmail] = useState("")
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [notifyTelegram, setNotifyTelegram] = useState(false)
  const [notifyMinScore, setNotifyMinScore] = useState("8")
  const [telegramChatId, setTelegramChatId] = useState("")
  const [oldPassword, setOldPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
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
        setNotifyMinScore(String(userSettings.notify_min_score))
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

  const settingsValidation = useMemo(
    () =>
      getSettingsSaveValidationErrors({
        displayName,
        notifyTelegram,
        telegramConfigured,
        telegramChatId,
      }),
    [displayName, notifyTelegram, telegramConfigured, telegramChatId],
  )

  const settingsFormInvalid = settingsSaveHasErrors(settingsValidation)

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

  async function handleSave() {
    if (settingsFormInvalid) {
      toast.error("Bitte korrigiere die markierten Felder, dann kann gespeichert werden.")
      return
    }
    const nameTrimmed = displayName.trim()
    const chatTrimmed = telegramChatId.trim()
    setIsSaving(true)
    try {
      await Promise.all([
        updateMe({ display_name: nameTrimmed }),
        updateMySettings({
          display_name: nameTrimmed,
          notify_telegram: notifyTelegram,
          notify_min_score: Number(notifyMinScore),
          telegram_chat_id: chatTrimmed || null,
        }),
      ])
      if (isAdmin) {
        await Promise.all([
          updateSetting("exclude_commercial_sellers", excludeCommercialSellers ? "true" : "false"),
          updateSetting("min_seller_rating", minSellerRating),
        ])
      }
      window.dispatchEvent(
        new CustomEvent("schnappster-profile-updated", {
          detail: { display_name: nameTrimmed },
        }),
      )
      toast.success("Einstellungen gespeichert")
    } catch (e) {
      const raw = e instanceof Error ? e.message : "Speichern fehlgeschlagen."
      toast.error(humanizeSettingsSaveApiError(raw))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleChangePassword() {
    const oldPw = oldPassword
    const newPw = newPassword.trim()
    if (!oldPw || !newPw) return
    if (!isPasswordValid(newPw)) {
      toast.error("Neues Passwort erfuellt nicht alle Anforderungen.")
      return
    }
    if (newPw !== confirmPassword.trim()) {
      toast.error("Neues Passwort und Bestätigung stimmen nicht überein.")
      return
    }
    try {
      await changePassword(oldPw, newPw)
      setOldPassword("")
      setNewPassword("")
      setConfirmPassword("")
      toast.success("Passwort aktualisiert.")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Passwort konnte nicht geändert werden.")
    }
  }

  async function handleDeleteAccount() {
    const emailNorm = (email ?? "").trim().toLowerCase()
    if (!emailNorm || deleteConfirmation.trim().toLowerCase() !== emailNorm) return
    setIsDeleting(true)
    try {
      await deleteMyAccount(deleteConfirmation.trim())
      await supabase?.auth.signOut()
      window.location.href = "/login"
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Konto konnte nicht gelöscht werden.")
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
    <ContentReveal className="max-w-2xl">
      <Tabs defaultValue="general">
        <TabsList className="w-full sm:w-auto inline-flex h-auto p-0 gap-0 border-b-2 border-border bg-muted/40 rounded-none min-h-[3rem]">
          <TabsTrigger
            value="general"
            className="flex items-center gap-2 cursor-pointer rounded-t-lg rounded-b-none border-b-[3px] border-transparent bg-transparent px-5 py-3 -mb-[2px] text-sm font-medium text-muted-foreground data-[state=active]:text-foreground data-[state=active]:border-primary data-[state=active]:border-b-2 data-[state=active]:bg-background data-[state=active]:shadow-sm data-[state=active]:ring-1 data-[state=active]:ring-border data-[state=active]:rounded-b-none shadow-none transition-all duration-200 hover:text-foreground"
          >
            <User className="size-4" />
            Profil & Benachrichtigungen
          </TabsTrigger>
          <TabsTrigger
            value="security"
            className="flex items-center gap-2 cursor-pointer rounded-t-lg rounded-b-none border-b-[3px] border-transparent bg-transparent px-5 py-3 -mb-[2px] text-sm font-medium text-muted-foreground data-[state=active]:text-foreground data-[state=active]:border-primary data-[state=active]:border-b-2 data-[state=active]:bg-background data-[state=active]:shadow-sm data-[state=active]:ring-1 data-[state=active]:ring-border data-[state=active]:rounded-b-none shadow-none transition-all duration-200 hover:text-foreground"
          >
            <Lock className="size-4" />
            Sicherheit & Konto
          </TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="flex flex-col gap-6 pt-4">
          <Card>
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
                <Label htmlFor="email">E-Mail</Label>
                <Input
                  id="email"
                  value={email}
                  readOnly
                  tabIndex={-1}
                  aria-readonly="true"
                  className="cursor-default border-transparent bg-muted shadow-none focus-visible:ring-0"
                />
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-baseline justify-between gap-2">
                  <Label htmlFor="display-name" className="cursor-pointer">
                    Name{" "}
                    <span className="font-normal text-muted-foreground">(optional)</span>
                  </Label>
                  <span className="text-xs tabular-nums text-muted-foreground" aria-live="polite">
                    {displayName.length}/{DISPLAY_NAME_MAX_LENGTH}
                  </span>
                </div>
                <Input
                  id="display-name"
                  name="display_name"
                  value={displayName}
                  maxLength={DISPLAY_NAME_MAX_LENGTH}
                  autoComplete="name"
                  aria-invalid={Boolean(settingsValidation.displayName)}
                  aria-describedby={
                    settingsValidation.displayName ? "display-name-error" : "display-name-hint"
                  }
                  onChange={(e) => setDisplayName(e.target.value)}
                  className={cn(
                    settingsValidation.displayName &&
                      "border-destructive focus-visible:ring-destructive/30",
                  )}
                />
                {settingsValidation.displayName ? (
                  <p id="display-name-error" role="alert" className="text-sm text-destructive">
                    {settingsValidation.displayName}
                  </p>
                ) : null}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="size-5" />
                Benachrichtigungen
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-6">
              {!telegramConfigured && (
                <p className="text-sm leading-relaxed text-amber-900 dark:text-amber-200">
                  Telegram-Benachrichtigungen sind derzeit systemweit deaktiviert.
                </p>
              )}
              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label
                    htmlFor="telegram-notifications"
                    className={cn(
                      "flex items-center gap-1.5",
                      !telegramConfigured && "opacity-60",
                    )}
                  >
                    <span>Auf Telegram benachrichtigen</span>
                    <HelpTip text="Sendet dir eine Telegram-Nachricht zu passenden Angeboten." />
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
              <div className="flex flex-col gap-2">
                <Label htmlFor="telegram-chat-id" className="flex items-center gap-1.5">
                  <span>Telegram Chat-ID</span>
                  <HelpTip text="Deine persönliche Chat-ID. Wird genutzt, wenn Telegram-Benachrichtigungen aktiv sind." />
                </Label>
                <Input
                  id="telegram-chat-id"
                  name="telegram_chat_id"
                  inputMode="text"
                  value={telegramChatId}
                  autoComplete="off"
                  aria-invalid={Boolean(settingsValidation.telegramChatId)}
                  aria-describedby={
                    settingsValidation.telegramChatId ? "telegram-chat-id-error" : undefined
                  }
                  onChange={(e) => setTelegramChatId(e.target.value)}
                  className={cn(
                    settingsValidation.telegramChatId &&
                      "border-destructive focus-visible:ring-destructive/30",
                  )}
                />
                {settingsValidation.telegramChatId ? (
                  <p id="telegram-chat-id-error" role="alert" className="text-sm text-destructive">
                    {settingsValidation.telegramChatId}
                  </p>
                ) : null}
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="notify-min-score" className="flex items-center gap-1.5">
                  <span>Mindest-Score</span>
                  <HelpTip text="Nur Angebote ab diesem KI-Score lösen Benachrichtigungen aus." />
                </Label>
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
            </CardContent>
          </Card>

          {isAdmin && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="size-5" />
                  Admin-Einstellungen
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-6">
                <div className="flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <Label htmlFor="exclude-commercial">
                      Gewerbliche Verkaeufer ausschliessen
                    </Label>
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

          <div className="pt-2">
            <Button
              onClick={handleSave}
              disabled={isSaving || settingsFormInvalid}
              className="cursor-pointer gap-2 px-5"
            >
              <Save className="size-4" />
              {isSaving ? "Speichern..." : "Einstellungen speichern"}
            </Button>
          </div>

        </TabsContent>

        <TabsContent value="security" className="flex flex-col gap-6 pt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lock className="size-5" />
                Passwort ändern
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="old-password">Altes Passwort</Label>
                <Input
                  id="old-password"
                  type="password"
                  value={oldPassword}
                  autoComplete="current-password"
                  onChange={(e) => setOldPassword(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="new-password">Neues Passwort</Label>
                <Input
                  id="new-password"
                  type="password"
                  value={newPassword}
                  autoComplete="new-password"
                  onChange={(e) => setNewPassword(e.target.value)}
                />
                <PasswordStrengthIndicator password={newPassword} />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="confirm-password">Neues Passwort bestätigen</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  autoComplete="new-password"
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
              <div className="pt-2">
                <Button variant="outline" onClick={handleChangePassword}>
                  Passwort speichern
                </Button>
              </div>
            </CardContent>
          </Card>

          <Separator />

          <Card className="border-destructive/40">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <Trash2 className="size-5" />
                Account löschen
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <p className="text-sm text-muted-foreground">
                Konto und zugehörige App-Daten dauerhaft löschen.
              </p>
              <div className="flex flex-col gap-2">
                <Label htmlFor="delete-confirmation">
                  E-Mail-Adresse zur Bestätigung eingeben
                </Label>
                <Input
                  id="delete-confirmation"
                  type="email"
                  autoComplete="email"
                  placeholder={email || "ihre@email.de"}
                  value={deleteConfirmation}
                  onChange={(e) => setDeleteConfirmation(e.target.value)}
                />
              </div>
              <AlertDialog open={openDeleteDialog} onOpenChange={setOpenDeleteDialog}>
                <Button
                  variant="destructive"
                  onClick={() => setOpenDeleteDialog(true)}
                  disabled={
                    !email?.trim() ||
                    deleteConfirmation.trim().toLowerCase() !== email.trim().toLowerCase() ||
                    isDeleting
                  }
                >
                  Konto löschen
                </Button>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Konto wirklich löschen?</AlertDialogTitle>
                    <AlertDialogDescription>
                      Diese Aktion kann nicht rückgängig gemacht werden.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Abbrechen</AlertDialogCancel>
                    <AlertDialogAction onClick={handleDeleteAccount}>
                      {isDeleting ? "Lösche..." : "Ja, löschen"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </ContentReveal>
  )
}
