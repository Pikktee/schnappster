"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Suspense, useEffect, useState } from "react"
import { toast } from "sonner"
import { CheckCircle2, ExternalLink, Loader2, XCircle } from "lucide-react"
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

function ConnectConsentBody() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const authorizationId = searchParams.get("authorization_id")?.trim() ?? ""

  const [phase, setPhase] = useState<ConsentPhase>("load")
  const [details, setDetails] = useState<OAuthAuthorizationDetails | null>(null)
  const [postConsentRedirectUrl, setPostConsentRedirectUrl] = useState<string | null>(null)

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
        <CardHeader className="space-y-1.5 px-6 pb-0 pt-6 sm:px-8">
          <CardTitle className="text-lg font-semibold tracking-tight">Link unvollständig</CardTitle>
          <CardDescription className="text-sm leading-relaxed">
            Bitte den Link aus der verbindenden App verwenden.
          </CardDescription>
        </CardHeader>
        <CardFooter className="px-6 pb-6 pt-4 sm:px-8">
          <Button asChild variant="outline" size="sm" className="w-full sm:w-auto">
            <Link href="/">Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (!supabase) {
    return (
      <Card className={CARD}>
        <CardHeader className="space-y-1.5 px-6 pb-0 pt-6 sm:px-8">
          <CardTitle className="text-lg font-semibold tracking-tight">Anmeldung nicht verfügbar</CardTitle>
          <CardDescription className="text-sm leading-relaxed">Konfiguration prüfen (Supabase-Variablen).</CardDescription>
        </CardHeader>
        <CardFooter className="px-6 pb-6 pt-4 sm:px-8">
          <Button asChild variant="outline" size="sm" className="w-full sm:w-auto">
            <Link href="/">Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (phase === "load" || (phase === "ready" && !details)) {
    return (
      <Card className={CARD}>
        <CardContent className="flex flex-col items-center gap-4 px-6 py-12 sm:px-8">
          <Spinner className="size-8 text-primary" />
          <p className="text-center text-sm text-muted-foreground">
            {phase === "load" ? "Wird geladen …" : "Anfrage ungültig oder abgelaufen."}
          </p>
          {!details && phase === "ready" ? (
            <Button asChild variant="outline" size="sm">
              <Link href="/">Startseite</Link>
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
        <CardHeader className="space-y-3 px-6 pb-0 pt-7 text-center sm:px-8 sm:text-left">
          <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary/12 text-primary sm:mx-0">
            <CheckCircle2 className="size-7" aria-hidden />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-xl font-semibold tracking-tight">Verbunden</CardTitle>
            <CardDescription className="text-sm leading-relaxed">
              {clientName} hat Zugriff. Du kannst zurück zur App oder zu Schnappster wechseln.
            </CardDescription>
          </div>
        </CardHeader>
        <CardFooter className="flex flex-col gap-2 px-6 pb-7 pt-5 sm:flex-row sm:justify-end sm:px-8">
          <Button asChild variant="outline" size="sm" className="w-full sm:w-auto">
            <Link href="/">Schnappster</Link>
          </Button>
          {postConsentRedirectUrl ? (
            <Button type="button" size="sm" className="w-full sm:w-auto" onClick={() => window.location.assign(postConsentRedirectUrl)}>
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
        <CardHeader className="space-y-3 px-6 pb-0 pt-7 text-center sm:px-8 sm:text-left">
          <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground sm:mx-0">
            <XCircle className="size-7" aria-hidden />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-xl font-semibold tracking-tight">Abgelehnt</CardTitle>
            <CardDescription className="text-sm leading-relaxed">Keine Verbindung. Die App wurde informiert.</CardDescription>
          </div>
        </CardHeader>
        <CardFooter className="flex flex-col gap-2 px-6 pb-7 pt-5 sm:flex-row sm:justify-end sm:px-8">
          <Button asChild variant="outline" size="sm" className="w-full sm:w-auto">
            <Link href="/">Startseite</Link>
          </Button>
          {postConsentRedirectUrl ? (
            <Button type="button" variant="secondary" size="sm" className="w-full sm:w-auto" onClick={() => window.location.assign(postConsentRedirectUrl)}>
              Zur App
            </Button>
          ) : null}
        </CardFooter>
      </Card>
    )
  }

  const clientName = details.client.name
  const busy = phase === "busy"

  return (
    <Card className={CARD}>
      <CardHeader className="relative space-y-4 px-6 pb-0 pt-7 sm:px-8">
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary/0 via-primary/70 to-primary/0"
          aria-hidden
        />
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Zugriff</p>
          <h1
            className="text-balance break-words text-2xl font-bold leading-none tracking-tight text-foreground sm:text-[1.75rem]"
            id="connect-heading"
          >
            {clientName}
          </h1>
          <p className="max-w-prose text-pretty text-sm leading-relaxed text-muted-foreground">
            Fordert Zugriff auf dein Schnappster-Konto. Nur freigeben, wenn du der App vertraust.
          </p>
        </div>
        {details.user?.email ? (
          <p className="text-xs text-muted-foreground">
            Konto: <span className="font-medium text-foreground">{details.user.email}</span>
          </p>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-4 px-6 pb-1 pt-5 sm:px-8">
        <div>
          <p className="text-xs font-medium text-foreground/80">Freigabe umfasst</p>
          <ul className="mt-2.5 space-y-1.5 border-l-2 border-primary/40 pl-4" aria-labelledby="connect-heading">
            {SCOPE_LINES.map((line) => (
              <li key={line} className="text-[0.8125rem] leading-snug text-foreground/90 sm:text-sm">
                {line}
              </li>
            ))}
          </ul>
        </div>

        {details.client.uri ? (
          <a
            className="inline-flex max-w-full items-center gap-1 text-xs text-link underline-offset-4 hover:underline"
            href={details.client.uri}
            target="_blank"
            rel="noopener noreferrer"
          >
            <span className="truncate">{details.client.uri}</span>
            <ExternalLink className="size-3 shrink-0 opacity-70" aria-hidden />
          </a>
        ) : null}
      </CardContent>

      <CardFooter className="flex flex-col gap-2 border-t border-border/50 bg-muted/20 px-6 py-4 sm:flex-row sm:justify-end sm:px-8">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className={cn("w-full sm:order-1 sm:w-auto", busy && "pointer-events-none opacity-50")}
          disabled={busy}
          onClick={() => void onDeny()}
        >
          Ablehnen
        </Button>
        <Button
          type="button"
          size="sm"
          className="w-full sm:order-2 sm:min-w-[7.5rem] sm:w-auto"
          disabled={busy}
          onClick={() => void onApprove()}
          aria-busy={busy}
        >
          {busy ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden />
              Warten …
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
    <main className="min-h-svh bg-[radial-gradient(ellipse_120%_80%_at_50%_-20%,theme(colors.primary/0.12),transparent)]">
      <div className="mx-auto flex min-h-svh w-full max-w-md flex-col justify-center gap-7 px-4 py-10 sm:gap-8 sm:py-14">
        <div className="flex justify-center">
          {/* eslint-disable-next-line @next/next/no-img-element -- static logo SVG */}
          <img
            src="/logo.svg"
            alt="Schnappster"
            className="h-12 w-auto max-w-full object-contain opacity-95 sm:h-14"
            width={200}
            height={60}
          />
        </div>
        <Suspense
          fallback={
            <Card className={CARD}>
              <CardContent className="flex justify-center py-12">
                <Spinner className="size-8 text-primary" />
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
