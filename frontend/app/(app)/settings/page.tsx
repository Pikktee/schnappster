"use client"

import { useEffect, useState } from "react"
import { AlertTriangle, Eye, EyeOff, Save } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { PageHeader } from "@/components/page-header"
import { fetchSettings, updateSetting } from "@/lib/api"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

const AI_MODELS = [
  { value: "anthropic/claude-3.5-sonnet", label: "Claude 3.5 Sonnet" },
  { value: "anthropic/claude-3-haiku", label: "Claude 3 Haiku" },
  { value: "openai/gpt-4o", label: "GPT-4o" },
  { value: "openai/gpt-4o-mini", label: "GPT-4o Mini" },
  { value: "google/gemini-pro-1.5", label: "Gemini Pro 1.5" },
  { value: "google/gemini-2.0-flash-001", label: "Gemini 2.0 Flash" },
  { value: "meta-llama/llama-3.1-70b-instruct", label: "Llama 3.1 70B" },
]

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState("")
  const [model, setModel] = useState(AI_MODELS[0].value)
  const [showApiKey, setShowApiKey] = useState(false)
  const [loading, setLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const list = await fetchSettings()
        const apiKeyEntry = list.find((s: { key: string; value: string }) => s.key === "openrouter_api_key")
        const modelEntry = list.find((s: { key: string; value: string }) => s.key === "openrouter_ai_model")
        if (apiKeyEntry) setApiKey(apiKeyEntry.value ?? "")
        if (modelEntry) setModel(modelEntry.value ?? AI_MODELS[0].value)
      } catch {
        // Backend may not expose openrouter keys yet; keep defaults
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  async function handleSave() {
    setIsSaving(true)
    try {
      await updateSetting("openrouter_api_key", apiKey)
      await updateSetting("openrouter_ai_model", model)
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
        <PageHeader title="Einstellungen" subtitle="App-Konfiguration und API-Zugaenge" />
        <Skeleton className="h-48 max-w-2xl" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Einstellungen" subtitle="App-Konfiguration und API-Zugaenge" />

      {!apiKey && (
        <Alert className="border-amber-200 bg-amber-50">
          <AlertTriangle className="size-4 text-amber-600" />
          <AlertTitle className="text-amber-900">OpenRouter API Key erforderlich</AlertTitle>
          <AlertDescription className="text-amber-800">
            Fuer die KI-Analyse deiner Angebote wird ein OpenRouter API Key benoetigt.
            Du kannst dir einen kostenlosen Key auf{" "}
            <a
              href="https://openrouter.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="underline font-medium text-amber-900 hover:text-amber-700"
            >
              openrouter.ai
            </a>{" "}
            erstellen.
          </AlertDescription>
        </Alert>
      )}

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>KI-Konfiguration</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="api-key">OpenRouter API Key</Label>
            <div className="relative">
              <Input
                id="api-key"
                type={showApiKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-or-..."
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer transition-colors p-1"
                aria-label={showApiKey ? "Key verstecken" : "Key anzeigen"}
              >
                {showApiKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ai-model">KI-Modell</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger id="ai-model" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AI_MODELS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Das Modell wird fuer die Analyse der Kleinanzeigen verwendet.
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
