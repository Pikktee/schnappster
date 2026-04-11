"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Suspense, useEffect, useState } from "react"
import { toast } from "sonner"
import { Check, CheckCircle2, ExternalLink, Loader2, User, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"
import { buildLoginUrlWithConnectReturn } from "@/lib/connect-return-path"
import { supabase } from "@/lib/supabase"
import { cn } from "@/lib/utils"
import type { OAuthAuthorizationDetails } from "@supabase/auth-js"

type ConsentPhase = "load" | "ready" | "busy" | "approved" | "denied"

const SCOPE_LINES = [
  "Einstellungen abrufen und ändern",
  "Suchaufträge anlegen, ändern und löschen",
  "Schnäppchen & Anzeigen",
] as const

const CARD =
  "overflow-hidden rounded-2xl border border-stone-200/90 bg-card shadow-[0_8px_30px_-12px_rgba(28,25,23,0.12)] dark:border-stone-700/80"

const FOOTER_BTN = "min-h-11 w-full px-5 text-[15px] sm:w-auto sm:min-w-[9.5rem]"

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
    <li className="flex gap-3 rounded-lg py-2 pl-1 pr-2 sm:py-2.5">
      <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
        <Check className="size-3 stroke-[2.5]" aria-hidden />
      </span>
      <span className="text-sm leading-snug text-foreground">{children}</span>
    </li>
  )
}

function ConnectConsentBody() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const authorizationId = searchParams.get("authorization_id")?.trim() ?? ""

  const [phase, setPhase] = useState<ConsentPhase>("load")
  const [details, setDetails] = useState<OAuthAuthorizationDetails | null>(null)
  const [postConsentRedirectUrl, setPostConsentRedirectUrl] = useState<string | null>(null)
  /** Schlüssel der zuletzt fehlgeschlagenen Logo-URL (Authorization + URI). */
  const [brokenClientLogoKey, setBrokenClientLogoKey] = useState<string | null>(null)

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
        toast.error(error.message)
        setPhase("ready")
        return
      }
      if (!data) {
        toast.error("Diese Verbindungsanfrage ist ungültig oder abgelaufen.")
        setPhase("ready")
        return
      }
      if ("redirect_url" in data && !("authorization_id" in data)) {
        window.location.assign(data.redirect_url)
        return
      }
      if ("authorization_id" in data) {
        setDetails(data)
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
      toast.error(error.message)
      setPhase("ready")
      return
    }
    setPostConsentRedirectUrl(readOAuthRedirectUrl(data))
    setPhase("approved")
  }

  async function onDeny() {
    if (!supabase || !authorizationId) return
    setPhase("busy")
    const { data, error } = await supabase.auth.oauth.denyAuthorization(authorizationId, {
      skipBrowserRedirect: true,
    })
    if (error) {
      toast.error(error.message)
      setPhase("ready")
      return
    }
    setPostConsentRedirectUrl(readOAuthRedirectUrl(data))
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

  if (phase === "load" || (phase === "ready" && !details)) {
    return (
      <Card className={CARD}>
        <CardContent className="flex flex-col items-center gap-5 px-6 py-14 sm:px-8">
          <Spinner className="size-9 text-primary" aria-hidden />
          <div className="max-w-sm text-center">
            <p className="text-sm font-medium text-foreground">
              {phase === "load" ? "Anfrage wird geladen" : "Anfrage nicht möglich"}
            </p>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              {phase === "load"
                ? "Wir holen die Angaben zu dieser Verbindung. Das dauert nur einen Moment."
                : "Die Anfrage ist abgelaufen oder ungültig. Starte die Verbindung in der App erneut."}
            </p>
          </div>
          {!details && phase === "ready" ? (
            <Button asChild variant="outline" className={FOOTER_BTN}>
              <Link href="/">Zur Startseite</Link>
            </Button>
          ) : null}
        </CardContent>
      </Card>
    )
  }

  if (phase === "approved") {
    const clientName = details?.client.name ?? "Die App"
    return (
      <Card className={CARD}>
        <CardHeader className="space-y-4 px-6 pb-0 pt-8 text-center sm:px-8 sm:text-left">
          <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-primary/12 text-primary sm:mx-0">
            <CheckCircle2 className="size-8" aria-hidden />
          </div>
          <div className="space-y-2">
            <CardTitle className="text-xl font-semibold tracking-tight sm:text-2xl">Verbindung hergestellt</CardTitle>
            <CardDescription className="text-base leading-relaxed text-pretty text-muted-foreground">
              <span className="font-medium text-foreground">{clientName}</span> darf nun im Namen deines Kontos auf
              Schnappster zugreifen.
            </CardDescription>
          </div>
        </CardHeader>
        <CardFooter className="flex flex-col gap-3 px-6 pb-8 pt-6 sm:flex-row sm:justify-end sm:px-8">
          <Button asChild variant="outline" className={FOOTER_BTN}>
            <Link href="/">Schnappster öffnen</Link>
          </Button>
          {postConsentRedirectUrl ? (
            <Button type="button" className={FOOTER_BTN} onClick={() => window.location.assign(postConsentRedirectUrl)}>
              Weiter zu {clientName}
            </Button>
          ) : null}
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
              Es wurde kein Zugriff gewährt. Du kannst die App schließen oder es später erneut versuchen.
            </CardDescription>
          </div>
        </CardHeader>
        <CardFooter className="flex flex-col gap-3 px-6 pb-8 pt-6 sm:flex-row sm:justify-end sm:px-8">
          <Button asChild variant="outline" className={FOOTER_BTN}>
            <Link href="/">Zur Startseite</Link>
          </Button>
          {postConsentRedirectUrl ? (
            <Button type="button" variant="secondary" className={FOOTER_BTN} onClick={() => window.location.assign(postConsentRedirectUrl)}>
              Zurück zur App
            </Button>
          ) : null}
        </CardFooter>
      </Card>
    )
  }

  const clientName = details.client.name
  const busy = phase === "busy"
  const logoUri = details.client.logo_uri?.trim() ?? ""
  const websiteUri = details.client.uri?.trim() ?? ""
  const clientLogoKey = `${authorizationId}|${logoUri}`
  const showClientLogo = Boolean(logoUri) && brokenClientLogoKey !== clientLogoKey
  const logoAlt = `Logo: ${clientName}`

  return (
    <Card className={CARD}>
      <CardHeader className="relative space-y-5 border-b border-border/60 px-6 pb-6 pt-8 sm:px-8">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-0.5 bg-primary/70" aria-hidden />

        <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start sm:gap-5">
          <div className="shrink-0">
            {showClientLogo ? (
              // eslint-disable-next-line @next/next/no-img-element -- OAuth-Client-Logo von beliebiger URL
              <img
                src={logoUri}
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
              Diese App fordert Zugriff auf dein Schnappster-Konto an. Vergleiche Logo und Website mit dem, was du
              erwartest. Lasse die Verbindung nur zu, wenn du dir sicher bist.
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

      <CardContent className="px-6 pb-2 pt-6 sm:px-8">
        <p id="connect-scopes-label" className="text-sm font-semibold text-foreground">
          Mit Zulassen erlaubst du
        </p>
        <ul className="mt-3 space-y-0.5" aria-labelledby="connect-scopes-label connect-heading">
          {SCOPE_LINES.map((line) => (
            <ScopeRow key={line}>{line}</ScopeRow>
          ))}
        </ul>
      </CardContent>

      <CardFooter className="flex flex-col gap-3 border-t border-border/50 bg-muted/15 px-6 py-6 sm:flex-row sm:justify-end sm:px-8">
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
          <ConnectConsentBody />
        </Suspense>
      </div>
    </main>
  )
}
