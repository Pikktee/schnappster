"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Suspense, useEffect, useState } from "react"
import { toast } from "sonner"
import {
  CheckCircle2,
  ExternalLink,
  LayoutList,
  Loader2,
  Search,
  Settings2,
  Shield,
  XCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Spinner } from "@/components/ui/spinner"
import { buildLoginUrlWithConnectReturn } from "@/lib/connect-return-path"
import { supabase } from "@/lib/supabase"
import { cn } from "@/lib/utils"
import type { OAuthAuthorizationDetails } from "@supabase/auth-js"

type ConsentPhase = "load" | "ready" | "busy" | "approved" | "denied"

const CONNECT_CARD_CLASS =
  "overflow-hidden rounded-xl border border-border/80 bg-card shadow-lg shadow-stone-900/[0.06] ring-1 ring-stone-900/[0.03]"

function PermissionItem({ icon: Icon, title, description }: { icon: typeof Shield; title: string; description: string }) {
  return (
    <li className="flex gap-3 rounded-lg border border-border/60 bg-muted/25 px-3 py-3 sm:px-4">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-accent/80 text-accent-foreground">
        <Icon className="size-4" aria-hidden />
      </span>
      <div className="min-w-0 pt-0.5">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">{description}</p>
      </div>
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
      <Card className={CONNECT_CARD_CLASS}>
        <CardHeader className="space-y-1 pb-2">
          <CardTitle className="text-lg font-semibold tracking-tight">Link unvollständig</CardTitle>
          <CardDescription className="text-pretty text-sm leading-relaxed">
            Diese Seite enthält keine gültigen Verbindungsdaten. Bitte nutze den Link aus der App, mit der
            du dich verbinden möchtest.
          </CardDescription>
        </CardHeader>
        <CardFooter className="pt-2">
          <Button asChild variant="outline" className="w-full sm:w-auto">
            <Link href="/">Zur Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (!supabase) {
    return (
      <Card className={CONNECT_CARD_CLASS}>
        <CardHeader className="space-y-1 pb-2">
          <CardTitle className="text-lg font-semibold tracking-tight">Anmeldung nicht verfügbar</CardTitle>
          <CardDescription className="text-pretty text-sm leading-relaxed">
            Schnappster ist hier nicht korrekt konfiguriert. Bitte prüfe die Umgebungsvariablen.
          </CardDescription>
        </CardHeader>
        <CardFooter className="pt-2">
          <Button asChild variant="outline" className="w-full sm:w-auto">
            <Link href="/">Zur Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (phase === "load" || (phase === "ready" && !details)) {
    return (
      <Card className={CONNECT_CARD_CLASS}>
        <CardContent className="flex flex-col items-center gap-5 py-14 sm:py-16">
          <Spinner className="size-9 text-primary" />
          <div className="max-w-xs text-center">
            <p className="text-sm font-medium text-foreground">
              {phase === "load" ? "Anfrage wird geladen …" : "Anfrage nicht verfügbar"}
            </p>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              {phase === "load"
                ? "Einen Moment bitte. Wir holen die Details zur Verbindungsanfrage."
                : "Die Verbindungsdaten konnten nicht geladen werden oder sind abgelaufen."}
            </p>
          </div>
          {!details && phase === "ready" ? (
            <Button asChild variant="outline" className="mt-1">
              <Link href="/">Zur Startseite</Link>
            </Button>
          ) : null}
        </CardContent>
      </Card>
    )
  }

  if (phase === "approved") {
    const clientName = details?.client.name ?? "Die Anwendung"
    return (
      <Card className={CONNECT_CARD_CLASS}>
        <CardHeader className="space-y-4 pb-2 text-center sm:text-left">
          <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-emerald-500/12 text-emerald-700 sm:mx-0 dark:text-emerald-400">
            <CheckCircle2 className="size-8" aria-hidden />
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Erfolg</p>
            <CardTitle className="text-xl font-semibold tracking-tight sm:text-2xl">Verbindung hergestellt</CardTitle>
            <CardDescription className="text-pretty text-base leading-relaxed text-muted-foreground">
              <span className="font-medium text-foreground">{clientName}</span> ist mit deinem Schnappster-Konto
              verbunden. Du kannst zur App zurückkehren oder Schnappster im Browser weiter nutzen.
            </CardDescription>
          </div>
        </CardHeader>
        <CardFooter className="flex flex-col gap-2 pt-2 sm:flex-row sm:justify-end">
          <Button asChild variant="outline" className="w-full sm:w-auto">
            <Link href="/">Zur Schnappster-Startseite</Link>
          </Button>
          {postConsentRedirectUrl ? (
            <Button type="button" className="w-full sm:w-auto" onClick={() => window.location.assign(postConsentRedirectUrl)}>
              Weiter zu {clientName}
            </Button>
          ) : null}
        </CardFooter>
      </Card>
    )
  }

  if (phase === "denied") {
    return (
      <Card className={CONNECT_CARD_CLASS}>
        <CardHeader className="space-y-4 pb-2 text-center sm:text-left">
          <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground sm:mx-0">
            <XCircle className="size-8" aria-hidden />
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Abgelehnt</p>
            <CardTitle className="text-xl font-semibold tracking-tight sm:text-2xl">Zugriff nicht freigegeben</CardTitle>
            <CardDescription className="text-pretty text-base leading-relaxed text-muted-foreground">
              Es wurde keine Verbindung hergestellt. Die anfragende App wurde über deine Entscheidung informiert und
              erhält keinen Zugriff auf dein Konto.
            </CardDescription>
          </div>
        </CardHeader>
        <CardFooter className="flex flex-col gap-2 pt-2 sm:flex-row sm:justify-end">
          <Button asChild variant="outline" className="w-full sm:w-auto">
            <Link href="/">Zur Startseite</Link>
          </Button>
          {postConsentRedirectUrl ? (
            <Button type="button" variant="secondary" className="w-full sm:w-auto" onClick={() => window.location.assign(postConsentRedirectUrl)}>
              Zurück zur App
            </Button>
          ) : null}
        </CardFooter>
      </Card>
    )
  }

  const clientName = details.client.name
  const busy = phase === "busy"

  return (
    <Card className={CONNECT_CARD_CLASS}>
      <CardHeader className="space-y-5 pb-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Zugriffsanfrage</p>
          <h1
            className="mt-2 text-balance break-words text-3xl font-bold leading-[1.15] tracking-tight text-foreground sm:text-4xl"
            id="connect-app-title"
          >
            {clientName}
          </h1>
          <p className="mt-3 text-pretty text-base leading-relaxed text-muted-foreground sm:text-[1.05rem]">
            <span className="font-semibold text-foreground">{clientName}</span> fordert Zugriff auf dein
            Schnappster-Konto an. Prüfe die folgenden Punkte und erteile die Freigabe nur, wenn du der Anwendung
            vertraust.
          </p>
        </div>

        {details.user?.email ? (
          <div
            className="flex items-center gap-2 rounded-lg border border-dashed border-border bg-muted/30 px-3 py-2.5 text-sm text-muted-foreground"
            role="status"
          >
            <Shield className="size-4 shrink-0 text-foreground/70" aria-hidden />
            <span>
              Du bist angemeldet als{" "}
              <span className="font-medium text-foreground">{details.user.email}</span>
            </span>
          </div>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-4 px-6 pb-2 sm:px-8">
        <Separator className="bg-border/80" />
        <div>
          <h2 className="text-sm font-semibold text-foreground">Was wird bei Zustimmung freigegeben?</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Die App kann über Schnappster im Namen deines Kontos folgende Aktionen ausführen:
          </p>
          <ul className="mt-4 space-y-2.5" aria-labelledby="connect-app-title">
            <PermissionItem
              icon={Settings2}
              title="Einstellungen"
              description="Laufende Einstellungen lesen und ändern (z. B. Benachrichtigungen, Filter, API-Anbindung)."
            />
            <PermissionItem
              icon={Search}
              title="Suchaufträge"
              description="Suchaufträge anlegen, bearbeiten und löschen sowie Scraping-Zeitpläne steuern."
            />
            <PermissionItem
              icon={LayoutList}
              title="Schnäppchen & Anzeigen"
              description="Gefundene Anzeigen und Schnäppchen einsehen, inklusive Details und Bewertungen aus der KI-Analyse."
            />
          </ul>
        </div>

        {details.client.uri ? (
          <>
            <Separator className="bg-border/80" />
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Website der Anwendung</span>
              <a
                className="mt-1 flex items-center gap-1.5 break-all text-link underline decoration-link/30 underline-offset-4 transition-colors hover:decoration-link"
                href={details.client.uri}
                target="_blank"
                rel="noopener noreferrer"
              >
                {details.client.uri}
                <ExternalLink className="size-3.5 shrink-0 opacity-80" aria-hidden />
              </a>
            </p>
          </>
        ) : null}
      </CardContent>

      <CardFooter className="flex flex-col gap-3 border-t border-border/60 bg-muted/15 px-6 py-5 sm:flex-row sm:justify-end sm:gap-3 sm:px-8">
        <Button
          type="button"
          variant="outline"
          className={cn("w-full sm:order-1 sm:w-auto sm:min-w-[8.5rem]", busy && "pointer-events-none opacity-60")}
          disabled={busy}
          onClick={() => void onDeny()}
        >
          Ablehnen
        </Button>
        <Button
          type="button"
          className="w-full sm:order-2 sm:w-auto sm:min-w-[10rem]"
          disabled={busy}
          onClick={() => void onApprove()}
          aria-busy={busy}
        >
          {busy ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden />
              Bitte warten …
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
    <main className="min-h-svh bg-gradient-to-b from-background via-background to-muted/40">
      <div className="mx-auto flex min-h-svh w-full max-w-lg flex-col justify-center gap-8 px-4 py-12 sm:gap-10 sm:py-16">
        <div className="flex flex-col items-center">
          {/* eslint-disable-next-line @next/next/no-img-element -- static logo SVG */}
          <img
            src="/logo.svg"
            alt="Schnappster"
            className="h-14 w-auto max-w-full object-contain sm:h-16"
            width={220}
            height={66}
          />
        </div>
        <Suspense
          fallback={
            <Card className={CONNECT_CARD_CLASS}>
              <CardContent className="flex justify-center py-16">
                <Spinner className="size-9 text-primary" />
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
