"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Suspense, useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"
import { buildLoginUrlWithConnectReturn } from "@/lib/connect-return-path"
import { supabase } from "@/lib/supabase"
import type { OAuthAuthorizationDetails } from "@supabase/auth-js"

function ConnectConsentBody() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const authorizationId = searchParams.get("authorization_id")?.trim() ?? ""

  const [phase, setPhase] = useState<"load" | "ready" | "busy">("load")
  const [details, setDetails] = useState<OAuthAuthorizationDetails | null>(null)

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

  async function onApprove() {
    if (!supabase || !authorizationId) return
    setPhase("busy")
    const { error } = await supabase.auth.oauth.approveAuthorization(authorizationId)
    if (error) {
      toast.error(error.message)
      setPhase("ready")
    }
  }

  async function onDeny() {
    if (!supabase || !authorizationId) return
    setPhase("busy")
    const { error } = await supabase.auth.oauth.denyAuthorization(authorizationId)
    if (error) {
      toast.error(error.message)
      setPhase("ready")
    }
  }

  if (!authorizationId) {
    return (
      <Card className="shadow-md">
        <CardHeader>
          <CardTitle>Link unvollständig</CardTitle>
          <CardDescription>
            Diese Seite wurde ohne gültige Verbindungsdaten aufgerufen. Bitte nutze den Link aus der
            Anwendung, mit der du dich verbinden möchtest.
          </CardDescription>
        </CardHeader>
        <CardFooter>
          <Button asChild variant="outline">
            <Link href="/">Zur Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (!supabase) {
    return (
      <Card className="shadow-md">
        <CardHeader>
          <CardTitle>Konfiguration</CardTitle>
          <CardDescription>Anmeldung ist derzeit nicht verfügbar.</CardDescription>
        </CardHeader>
        <CardFooter>
          <Button asChild variant="outline">
            <Link href="/">Zur Startseite</Link>
          </Button>
        </CardFooter>
      </Card>
    )
  }

  if (phase === "load" || (phase === "ready" && !details)) {
    return (
      <Card className="shadow-md">
        <CardContent className="flex flex-col items-center gap-4 py-12">
          <Spinner className="size-8" />
          <p className="text-center text-sm text-muted-foreground">
            {phase === "load"
              ? "Verbindung wird vorbereitet…"
              : "Die Verbindungsdaten konnten nicht geladen werden."}
          </p>
          {!details && phase === "ready" && (
            <Button asChild variant="outline">
              <Link href="/">Zur Startseite</Link>
            </Button>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="shadow-md">
      <CardHeader>
        <CardTitle>Verbindung bestätigen</CardTitle>
        <CardDescription>
          Prüfe, welche Anwendung sich verbinden möchte, und ob du den Zugriff erlauben willst.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="rounded-md border bg-muted/40 p-3">
          <p className="font-medium text-foreground">{details.client.name}</p>
          {details.client.uri ? (
            <p className="text-muted-foreground">
              Website:{" "}
              <a className="underline underline-offset-2" href={details.client.uri}>
                {details.client.uri}
              </a>
            </p>
          ) : null}
          {details.user?.email ? (
            <p className="mt-2 text-muted-foreground">
              <span className="font-medium text-foreground">Angemeldet als:</span> {details.user.email}
            </p>
          ) : null}
        </div>
        <p className="text-muted-foreground leading-relaxed">
          Bei Zulassung besteht Zugriff auf dein Schnappster-Konto, einschließlich der
          Benutzereinstellungen, dem Anlegen, Bearbeiten und Löschen von Suchaufträgen sowie der
          Schnäppchenliste.
        </p>
      </CardContent>
      <CardFooter className="flex flex-col gap-2 sm:flex-row sm:justify-end">
        <Button type="button" variant="outline" disabled={phase === "busy"} onClick={() => void onDeny()}>
          Ablehnen
        </Button>
        <Button type="button" disabled={phase === "busy"} onClick={() => void onApprove()}>
          {phase === "busy" ? "Bitte warten…" : "Zulassen"}
        </Button>
      </CardFooter>
    </Card>
  )
}

export default function ConnectPage() {
  return (
    <main className="min-h-svh bg-gradient-to-b from-background to-muted/30">
      <div className="mx-auto flex min-h-svh w-full max-w-md flex-col justify-center gap-6 px-4 py-10">
        <div className="flex flex-col items-center gap-3 text-center">
          {/* eslint-disable-next-line @next/next/no-img-element -- static logo SVG */}
          <img
            src="/logo.svg"
            alt="Schnappster"
            className="h-12 w-auto max-w-full object-contain"
            width={200}
            height={60}
          />
          <p className="text-xs text-muted-foreground">Verbindung mit Schnappster</p>
        </div>
        <Suspense
          fallback={
            <Card className="shadow-md">
              <CardContent className="flex justify-center py-12">
                <Spinner className="size-8" />
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
