"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Suspense, useEffect, useState } from "react"
import { toast } from "sonner"
import { AlertCircle, CalendarClock, Check, CheckCircle2, ExternalLink, Loader2, User, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"
import { buildLoginUrlWithConnectReturn } from "@/lib/connect-return-path"
import { supabase } from "@/lib/supabase"
import { cn } from "@/lib/utils"
import type { OAuthAuthorizationDetails } from "@supabase/auth-js"

type ConsentPhase = "load" | "ready" | "busy" | "approved" | "denied"

/** Abgelaufen / unbekannte OAuth-Authorization vs. sonstiger Ladefehler. */
type ConnectLoadIssue = "expired" | "error" | null

/** API-Meldungen (z. B. GoTrue), die für Nutzer als „abgelaufen / ungültig“ gelten sollen. */
function isExpiredOrMissingAuthorizationMessage(message: string): boolean {
  const m = message.trim().toLowerCase()
  if (!m) {
    return false
  }
  if (m.includes("authorization not found")) {
    return true
  }
  if (m.includes("not found") && m.includes("authorization")) {
    return true
  }
  if (m.includes("authorization") && (m.includes("expired") || m.includes("invalid"))) {
    return true
  }
  if (m.includes("grant") && m.includes("invalid")) {
    return true
  }
  if (m.includes("already been used") || m.includes("already used")) {
    return true
  }
  return false
}

function oauthActionErrorGerman(message: string): string {
  if (isExpiredOrMissingAuthorizationMessage(message)) {
    return "Diese Freigabe ist nicht mehr gültig. Bitte starte die Verbindung in der App erneut."
  }
  return "Die Aktion konnte nicht ausgeführt werden. Bitte versuche es erneut."
}

const SCOPE_LINES = [
  "Einstellungen abrufen und ändern",
  "Suchaufträge anlegen, ändern und löschen",
  "Schnäppchen & Anzeigen abrufen",
] as const

/**
 * Logo-URL für die Anzeige: zuerst Supabase `logo_uri` (OAuth-Client-Registrierung).
 * Wenn die API keins liefert — z. B. bei dynamisch registrierten MCP-Clients — optional Fallback
 * für bekannte Namen (Anthropic setzt oft kein `logo_uri`).
 */
function resolveOAuthClientLogoSrc(clientName: string, logoUriFromApi: string): string {
  const trimmed = logoUriFromApi.trim()
  if (trimmed) {
    return trimmed
  }
  if (clientName.toLowerCase().includes("claude")) {
    return "https://claude.ai/apple-touch-icon.png"
  }
  return ""
}

const CARD =
  "overflow-hidden rounded-2xl border border-stone-200/90 bg-card shadow-[0_8px_30px_-12px_rgba(28,25,23,0.12)] dark:border-stone-700/80"

const FOOTER_BTN = "min-h-11 w-full px-5 text-[15px] sm:w-auto sm:min-w-[9.5rem]"

/** Kurz Erfolg anzeigen, dann OAuth-`redirect_url` öffnen (vollständige Verbindung in der App). */
const APPROVE_SUCCESS_REDIRECT_DELAY_MS = 2200

/** Kurzer Link-Text (Hostname), volle URL bleibt im href und title. */
function websiteLinkLabel(href: string): string {
  try {
    return new URL(href).hostname
  } catch {
    return href
  }
}

function ScopeRow({ children }: { children: string }) {
  return (
    <li className="flex gap-3 rounded-lg py-1.5 pl-1 pr-2 sm:py-2">
      <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
        <Check className="size-3 stroke-[2.5]" aria-hidden />
      </span>
      <span className="text-sm leading-snug text-foreground">{children}</span>
    </li>
  )
}

function ConnectConsentBody({ authorizationId }: { authorizationId: string }) {
  const router = useRouter()

  const [phase, setPhase] = useState<ConsentPhase>("load")
  const [details, setDetails] = useState<OAuthAuthorizationDetails | null>(null)
  const [loadIssue, setLoadIssue] = useState<ConnectLoadIssue>(null)
  /** Nach Zulassen: OAuth-Rückleitung zur App (wenn von der API geliefert). */
  const [postApproveRedirectUrl, setPostApproveRedirectUrl] = useState<string | null>(null)
  /** Schlüssel der zuletzt fehlgeschlagenen Logo-URL (Authorization + URI). */
  const [brokenClientLogoKey, setBrokenClientLogoKey] = useState<string | null>(null)

  useEffect(() => {
    if (phase !== "approved" || !postApproveRedirectUrl) {
      return
    }
    const url = postApproveRedirectUrl
    const id = window.setTimeout(() => {
      window.location.assign(url)
    }, APPROVE_SUCCESS_REDIRECT_DELAY_MS)
    return () => window.clearTimeout(id)
  }, [phase, postApproveRedirectUrl])

  useEffect(() => {
    if (!authorizationId || !supabase) {
      return
    }

    let cancelled = false

    void (async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession()
      if (cancelled) {
        return
      }
      if (!session) {
        router.replace(buildLoginUrlWithConnectReturn(authorizationId))
        return
      }

      const { data, error } = await supabase.auth.oauth.getAuthorizationDetails(authorizationId)
      if (cancelled) {
        return
      }
      if (error) {
        setLoadIssue(isExpiredOrMissingAuthorizationMessage(error.message) ? "expired" : "error")
        setPhase("ready")
        return
      }
      if (!data) {
        setLoadIssue("expired")
        setPhase("ready")
        return
      }
      if ("redirect_url" in data && !("authorization_id" in data)) {
        window.location.assign(data.redirect_url)
        return
      }
      if ("authorization_id" in data && "client" in data) {
        setDetails(data as OAuthAuthorizationDetails)
        setLoadIssue(null)
      }
      setPhase("ready")
    })()

    return () => {
      cancelled = true
    }
  }, [authorizationId, router])

  function readOAuthRedirectUrl(data: unknown): string | null {
    if (data && typeof data === "object" && "redirect_url" in data) {
      const url = (data as { redirect_url: unknown }).redirect_url
      return typeof url === "string" && url.length > 0 ? url : null
    }
    return null
  }

  async function onApprove() {
    if (!supabase || !authorizationId) return
    setPhase("busy")
    const { data, error } = await supabase.auth.oauth.approveAuthorization(authorizationId, {
      skipBrowserRedirect: true,
    })
    if (error) {
      toast.error(oauthActionErrorGerman(error.message))
      setPhase("ready")
      return
    }
    const redirectUrl = readOAuthRedirectUrl(data)
    setPostApproveRedirectUrl(redirectUrl)
    setPhase("approved")
  }

  async function onDeny() {
    if (!supabase || !authorizationId) return
    setPhase("busy")
    const { data, error } = await supabase.auth.oauth.denyAuthorization(authorizationId, {
      skipBrowserRedirect: true,
    })
    if (error) {
      toast.error(oauthActionErrorGerman(error.message))
      setPhase("ready")
      return
    }
    const redirectUrl = readOAuthRedirectUrl(data)
    if (redirectUrl) {
      window.location.assign(redirectUrl)
      return
    }
    setPhase("denied")
  }

  if (!authorizationId) {
    return (
      <Card className={CARD}>
        <CardHeader className="space-y-2 px-6 pb-0 pt-7 sm:px-8">
          <CardTitle className="text-lg font-semibold tracking-tight">Link unvollständig</CardTitle>
          <CardDescription className="text-sm leading-relaxed text-pretty">
            Öffne diese Seite über den Link aus der App, die sich mit Schnappster verbinden möchte.
          </CardDescription>
        </CardHeader>
        <CardFooter className="px-6 pb-7 pt-5 sm:px-8">
          <Button asChild variant="outline" className={FOOTER_BTN}>
            <Link href="/">Zur Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (!supabase) {
    return (
      <Card className={CARD}>
        <CardHeader className="space-y-2 px-6 pb-0 pt-7 sm:px-8">
          <CardTitle className="text-lg font-semibold tracking-tight">Anmeldung nicht verfügbar</CardTitle>
          <CardDescription className="text-sm leading-relaxed">
            Supabase ist nicht konfiguriert. Bitte Umgebungsvariablen prüfen.
          </CardDescription>
        </CardHeader>
        <CardFooter className="px-6 pb-7 pt-5 sm:px-8">
          <Button asChild variant="outline" className={FOOTER_BTN}>
            <Link href="/">Zur Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (phase === "load") {
    return (
      <Card className={CARD}>
        <CardContent className="flex flex-col items-center gap-5 px-6 py-14 sm:px-8">
          <Spinner className="size-9 text-primary" aria-hidden />
          <div className="max-w-sm text-center">
            <p className="text-sm font-medium text-foreground">Anfrage wird geladen</p>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              Wir holen die Angaben zu dieser Verbindung. Das dauert nur einen Moment.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (phase === "ready" && loadIssue === "expired") {
    return (
      <Card className={CARD}>
        <CardHeader className="space-y-4 px-6 pb-0 pt-8 text-center sm:px-8 sm:text-left">
          <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-primary/12 text-primary sm:mx-0">
            <CalendarClock className="size-8" aria-hidden />
          </div>
          <div className="space-y-2">
            <CardTitle className="text-xl font-semibold tracking-tight sm:text-2xl">Anfrage nicht mehr gültig</CardTitle>
            <CardDescription className="text-base leading-relaxed text-pretty text-muted-foreground">
              Dieser Verbindungslink ist abgelaufen oder wurde bereits verwendet. Das passiert z. B., wenn du die Seite
              zu spät geöffnet hast oder die Freigabe schon in einem anderen Tab abgeschlossen hast.
            </CardDescription>
          </div>
        </CardHeader>
        <CardFooter className="px-6 pb-8 pt-6 sm:px-8">
          <Button asChild variant="outline" className={FOOTER_BTN}>
            <Link href="/">Zur Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (phase === "ready" && loadIssue === "error") {
    return (
      <Card className={CARD}>
        <CardHeader className="space-y-4 px-6 pb-0 pt-8 text-center sm:px-8 sm:text-left">
          <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground sm:mx-0">
            <AlertCircle className="size-8" aria-hidden />
          </div>
          <div className="space-y-2">
            <CardTitle className="text-xl font-semibold tracking-tight sm:text-2xl">Anfrage konnte nicht geladen werden</CardTitle>
            <CardDescription className="text-base leading-relaxed text-pretty text-muted-foreground">
              Beim Abrufen der Verbindungsdaten ist ein Fehler aufgetreten. Bitte versuche es erneut oder starte die
              Verbindung in der App noch einmal.
            </CardDescription>
          </div>
        </CardHeader>
        <CardFooter className="px-6 pb-8 pt-6 sm:px-8">
          <Button asChild variant="outline" className={FOOTER_BTN}>
            <Link href="/">Zur Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (phase === "ready" && !details) {
    return null
  }

  if (phase === "approved") {
    const clientName = details?.client.name ?? "Die App"
    const willAutoRedirect = Boolean(postApproveRedirectUrl)
    return (
      <Card className={CARD}>
        <CardHeader className="space-y-4 px-6 pb-0 pt-8 text-center sm:px-8 sm:text-left">
          <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-primary/12 text-primary sm:mx-0">
            <CheckCircle2 className="size-8" aria-hidden />
          </div>
          <div className="space-y-2">
            <CardTitle className="text-xl font-semibold tracking-tight sm:text-2xl">
              {willAutoRedirect ? "Verbindung hergestellt" : "Freigabe gespeichert"}
            </CardTitle>
            <CardDescription className="text-base leading-relaxed text-pretty text-muted-foreground">
              {willAutoRedirect ? (
                <>
                  <span className="font-medium text-foreground">{clientName}</span> ist mit deinem Schnappster-Konto
                  verbunden. Du wirst in wenigen Sekunden automatisch zur App weitergeleitet, damit die Verbindung dort
                  abgeschlossen werden kann.
                </>
              ) : (
                <>
                  <span className="font-medium text-foreground">{clientName}</span> ist mit deinem Schnappster-Konto
                  verbunden. Die Anwendung konnte nicht automatisch geöffnet werden — du kannst sie selbst wechseln oder
                  Schnappster hier nutzen.
                </>
              )}
            </CardDescription>
            {willAutoRedirect ? (
              <p className="flex items-center justify-center gap-2 pt-1 text-sm text-muted-foreground sm:justify-start">
                <Loader2 className="size-4 animate-spin text-primary" aria-hidden />
                Weiterleitung …
              </p>
            ) : null}
          </div>
        </CardHeader>
        <CardFooter className="px-6 pb-8 pt-6 sm:px-8">
          <Button asChild variant="outline" className={FOOTER_BTN}>
            <Link href="/">Schnappster öffnen</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (phase === "denied") {
    return (
      <Card className={CARD}>
        <CardHeader className="space-y-4 px-6 pb-0 pt-8 text-center sm:px-8 sm:text-left">
          <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground sm:mx-0">
            <XCircle className="size-8" aria-hidden />
          </div>
          <div className="space-y-2">
            <CardTitle className="text-xl font-semibold tracking-tight sm:text-2xl">Nicht verbunden</CardTitle>
            <CardDescription className="text-base leading-relaxed text-pretty text-muted-foreground">
              Es wurde kein Zugriff gewährt. Die Anwendung konnte nicht automatisch geöffnet werden — du kannst dieses
              Fenster schließen oder es später erneut versuchen.
            </CardDescription>
          </div>
        </CardHeader>
        <CardFooter className="px-6 pb-8 pt-6 sm:px-8">
          <Button asChild variant="outline" className={FOOTER_BTN}>
            <Link href="/">Zur Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (!details) {
    return null
  }

  const clientName = details.client.name
  const busy = phase === "busy"
  const logoSrc = resolveOAuthClientLogoSrc(clientName, details.client.logo_uri ?? "")
  const websiteUri = details.client.uri?.trim() ?? ""
  const clientLogoKey = `${authorizationId}|${logoSrc}`
  const showClientLogo = Boolean(logoSrc) && brokenClientLogoKey !== clientLogoKey
  const logoAlt = `Logo: ${clientName}`

  return (
    <Card className={CARD}>
      <CardHeader className="space-y-5 border-b border-border/60 px-6 pb-4 pt-8 sm:px-8">
        <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start sm:gap-5">
          <div className="shrink-0">
            {showClientLogo ? (
              // eslint-disable-next-line @next/next/no-img-element -- OAuth-Client-Logo von beliebiger URL
              <img
                src={logoSrc}
                alt={logoAlt}
                width={64}
                height={64}
                className="size-16 rounded-2xl border border-border/80 bg-white object-contain p-1.5 shadow-sm dark:bg-stone-950"
                onError={() => setBrokenClientLogoKey(clientLogoKey)}
              />
            ) : (
              <div
                className="flex size-16 items-center justify-center rounded-2xl border border-border/80 bg-muted text-lg font-bold uppercase tracking-wide text-muted-foreground"
                aria-hidden
              >
                {Array.from(clientName)[0] ?? "?"}
              </div>
            )}
          </div>

          <div className="min-w-0 flex-1 space-y-2 text-center sm:text-left">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Zugriffsanfrage</p>
            <h1
              className="text-balance break-words text-2xl font-bold leading-tight tracking-tight text-foreground sm:text-3xl"
              id="connect-heading"
            >
              {clientName}
            </h1>
            <p className="text-pretty text-sm leading-relaxed text-muted-foreground sm:text-[0.9375rem]">
              fordert Zugriff auf dein Schnappster-Konto an. Lasse die Verbindung nur zu, wenn du der App vertraust.
            </p>
          </div>
        </div>

        {websiteUri ? (
          <div className="rounded-xl border border-border/70 bg-muted/30 p-4">
            <p className="text-xs font-semibold text-foreground">Website des Betreibers</p>
            <a
              className={cn(
                "mt-3 flex min-h-11 items-center justify-between gap-3 rounded-lg border border-transparent px-3 py-2.5",
                "text-sm font-medium text-link transition-colors",
                "hover:border-border hover:bg-background/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              )}
              href={websiteUri}
              target="_blank"
              rel="noopener noreferrer"
              title={websiteUri}
            >
              <span className="min-w-0 truncate">{websiteLinkLabel(websiteUri)}</span>
              <ExternalLink className="size-4 shrink-0 opacity-80" aria-hidden />
            </a>
            <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
              Öffnet in einem neuen Tab. Prüfe die Adresse in der Adresszeile deines Browsers.
            </p>
          </div>
        ) : null}

        {details.user?.email ? (
          <div className="flex gap-3 rounded-xl border border-dashed border-border/80 bg-background/60 px-4 py-3 sm:items-center">
            <User className="mt-0.5 size-4 shrink-0 text-muted-foreground sm:mt-0" aria-hidden />
            <div className="min-w-0 text-left">
              <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Dein Konto</p>
              <p className="truncate text-sm font-medium text-foreground">{details.user.email}</p>
            </div>
          </div>
        ) : null}
      </CardHeader>

      <CardContent className="px-6 pb-1 pt-3 sm:px-8">
        <p id="connect-scopes-label" className="text-sm font-semibold text-foreground">
          Mit Zulassen erlaubst du
        </p>
        <ul className="mt-2 space-y-0.5" aria-labelledby="connect-scopes-label connect-heading">
          {SCOPE_LINES.map((line) => (
            <ScopeRow key={line}>{line}</ScopeRow>
          ))}
        </ul>
      </CardContent>

      <CardFooter className="flex flex-col gap-3 border-t border-border/50 bg-muted/15 px-6 py-5 sm:flex-row sm:justify-end sm:px-8">
        <Button
          type="button"
          variant="outline"
          className={cn(FOOTER_BTN, busy && "pointer-events-none opacity-50")}
          disabled={busy}
          onClick={() => void onDeny()}
        >
          Ablehnen
        </Button>
        <Button
          type="button"
          className={FOOTER_BTN}
          disabled={busy}
          onClick={() => void onApprove()}
          aria-busy={busy}
        >
          {busy ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden />
              Wird gespeichert …
            </>
          ) : (
            "Zulassen"
          )}
        </Button>
      </CardFooter>
    </Card>
  )
}

function ConnectConsentRoute() {
  const searchParams = useSearchParams()
  const authorizationId = searchParams.get("authorization_id")?.trim() ?? ""
  return <ConnectConsentBody key={authorizationId} authorizationId={authorizationId} />
}

export default function ConnectPage() {
  return (
    <main className="min-h-svh bg-background">
      <div className="mx-auto flex min-h-svh w-full max-w-md flex-col justify-center gap-8 px-4 py-10 sm:max-w-lg sm:gap-9 sm:py-14">
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
        <Suspense
          fallback={
            <Card className={CARD}>
              <CardContent className="flex justify-center py-14">
                <Spinner className="size-9 text-primary" aria-hidden />
              </CardContent>
            </Card>
          }
        >
          <ConnectConsentRoute />
        </Suspense>
      </div>
    </main>
  )
}
