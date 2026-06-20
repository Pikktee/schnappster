"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { Copy, KeyRound } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { getToken } from "@/lib/auth"

const CARD =
  "overflow-hidden rounded-2xl border border-stone-200/90 bg-card shadow-[0_8px_30px_-12px_rgba(28,25,23,0.12)] dark:border-stone-700/80"

const SCOPE_LINES = [
  "Einstellungen abrufen und ändern",
  "Suchaufträge anlegen, ändern und löschen",
  "Schnäppchen & Anzeigen abrufen",
] as const

export default function ConnectPage() {
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    setToken(getToken())
  }, [])

  async function copyToken() {
    if (!token) return
    try {
      await navigator.clipboard.writeText(token)
      toast.success("Token kopiert.")
    } catch {
      toast.error("Token konnte nicht kopiert werden.")
    }
  }

  return (
    <main className="min-h-svh bg-background">
      <div className="mx-auto flex min-h-svh w-full max-w-md flex-col justify-center gap-8 px-4 py-10 sm:max-w-lg sm:py-14">
        <div className="flex justify-center">
          {/* eslint-disable-next-line @next/next/no-img-element -- static logo SVG */}
          <img
            src="/logo.svg"
            alt="Schnappster"
            className="h-12 w-auto max-w-full object-contain sm:h-[3.25rem]"
            width={200}
            height={60}
          />
        </div>

        <Card className={CARD}>
          <CardHeader className="space-y-2 px-6 pb-2 pt-7 sm:px-8">
            <div className="flex size-12 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <KeyRound className="size-6" aria-hidden />
            </div>
            <CardTitle className="text-lg font-semibold tracking-tight">
              MCP-Verbindung einrichten
            </CardTitle>
            <CardDescription className="text-sm leading-relaxed text-pretty">
              Der MCP-Server greift mit deinem persönlichen Schnappster-Token auf dein Konto zu.
              Hinterlege dieses Token in deinem MCP-Client (z. B. als{" "}
              <code className="rounded bg-muted px-1 py-0.5 text-xs">Authorization: Bearer …</code>
              ). So erlaubst du:
            </CardDescription>
          </CardHeader>

          <CardContent className="px-6 pb-2 pt-2 sm:px-8">
            <ul className="space-y-1 text-sm text-foreground">
              {SCOPE_LINES.map((line) => (
                <li key={line} className="flex gap-2">
                  <span className="text-primary">•</span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>

            {token ? (
              <div className="mt-5 space-y-2">
                <p className="text-xs font-semibold text-foreground">Dein Token</p>
                <div className="flex items-center gap-2">
                  <code className="min-w-0 flex-1 truncate rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs">
                    {token}
                  </code>
                  <Button type="button" variant="outline" size="icon" onClick={() => void copyToken()}>
                    <Copy className="size-4" aria-hidden />
                    <span className="sr-only">Token kopieren</span>
                  </Button>
                </div>
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  Behandle dieses Token wie ein Passwort. Gib es nur an Anwendungen weiter, denen du
                  vertraust.
                </p>
              </div>
            ) : (
              <div className="mt-5 rounded-lg border border-dashed border-border bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
                Du bist nicht angemeldet. Melde dich an, um dein Verbindungs-Token anzuzeigen.
              </div>
            )}
          </CardContent>

          <CardFooter className="px-6 pb-7 pt-4 sm:px-8">
            <Button asChild variant="outline" className="w-full sm:w-auto">
              <Link href={token ? "/dashboard" : "/login"}>
                {token ? "Zum Dashboard" : "Zum Login"}
              </Link>
            </Button>
          </CardFooter>
        </Card>
      </div>
    </main>
  )
}
