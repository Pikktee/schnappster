"use client"

import Image from "next/image"
import Link from "next/link"
import { ArrowLeft, Copy } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { toast } from "sonner"

const MCP_ENDPOINT = process.env.NEXT_PUBLIC_MCP_ENDPOINT_URL?.trim() ?? ""

export default function McpConnectPage() {
  const copyEndpoint = async () => {
    if (!MCP_ENDPOINT) return
    try {
      await navigator.clipboard.writeText(MCP_ENDPOINT)
      toast.success("MCP-URL in die Zwischenablage kopiert.")
    } catch {
      toast.error("Kopieren fehlgeschlagen — URL manuell markieren.")
    }
  }

  return (
    <main className="min-h-svh bg-gradient-to-b from-background to-muted/30">
      <div className="mx-auto flex min-h-svh w-full max-w-2xl flex-col justify-center gap-6 px-4 py-10">
        <Button variant="ghost" size="sm" className="w-fit gap-2" asChild>
          <Link href="/">
            <ArrowLeft className="size-4" />
            Zurück
          </Link>
        </Button>
        <Card>
          <CardHeader className="space-y-4">
            <div className="flex items-center gap-3">
              <Image
                src="/icon.png"
                alt="Schnappster Logo"
                width={32}
                height={32}
                className="rounded-md"
              />
              <p className="text-sm text-muted-foreground">Schnappster</p>
            </div>
            <CardTitle className="text-xl">Cursor &amp; MCP verbinden</CardTitle>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Wenn du Schnappster-Daten in Cursor (oder einem anderen MCP-Client) nutzen willst,
              verbindest du dich mit unserem <strong>Remote-MCP</strong>. Die Authentifizierung
              läuft über <strong>Supabase</strong> — dasselbe Konto wie in dieser Web-App, sofern
              dein Client den Login im Browser unterstützt. Es werden nur die für die Tools nötigen
              API-Zugriffe ausgeführt.
            </p>
          </CardHeader>
          <CardContent className="space-y-8 text-sm leading-relaxed">
            <section className="space-y-3">
              <h2 className="text-base font-medium">1. MCP-Endpunkt (HTTPS)</h2>
              <p className="text-muted-foreground">
                Trage in Cursor unter den MCP-Einstellungen die <strong>öffentliche URL</strong>{" "}
                deines Schnappster-MCP ein (inkl. Pfad, meist mit <code className="text-foreground">/mcp</code>
                am Ende).
              </p>
              {MCP_ENDPOINT ? (
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <code className="block flex-1 break-all rounded-md border bg-muted/50 px-3 py-2 text-xs">
                    {MCP_ENDPOINT}
                  </code>
                  <Button type="button" variant="secondary" size="sm" className="shrink-0" onClick={copyEndpoint}>
                    <Copy className="size-4" />
                    Kopieren
                  </Button>
                </div>
              ) : (
                <p className="rounded-md border border-dashed bg-muted/30 px-3 py-2 text-muted-foreground">
                  Für diese Installation ist noch keine öffentliche MCP-URL hinterlegt. Der
                  Betreiber kann in der Web-App-Umgebung{" "}
                  <code className="text-foreground">NEXT_PUBLIC_MCP_ENDPOINT_URL</code> setzen
                  (z.&nbsp;B. nach Deployment des MCP oder nach einem Tunnel-Test).
                </p>
              )}
            </section>

            <section className="space-y-3">
              <h2 className="text-base font-medium">2. In Cursor eintragen</h2>
              <ol className="list-decimal space-y-2 pl-5 text-muted-foreground">
                <li>Cursor öffnen: Einstellungen → MCP (Bezeichnung je nach Version).</li>
                <li>Neuen Server hinzufügen und die URL von oben einfügen.</li>
                <li>
                  Wenn Cursor nach Anmeldung fragt: im Browser mit deinem Schnappster-Konto
                  anmelden (Supabase). Nach erfolgreicher Verbindung meldet Cursor in der Regel,
                  dass du den Tab schließen kannst.
                </li>
                <li>
                  Falls <strong>kein</strong> Browser-Login erscheint: prüfe die MCP-Doku im
                  Repository (<code className="text-foreground">mcp-server/README.md</code>) zum
                  manuellen Bearer-Token — das ist ein Fallback, kein zweiter Login-Server.
                </li>
              </ol>
            </section>

            <section className="space-y-3">
              <h2 className="text-base font-medium">Für Entwickler: lokal testen</h2>
              <p className="text-muted-foreground">
                Zum lokalen MCP inkl. TryCloudflare-Tunnel siehe die technische Anleitung im
                Schnappster-Repository unter{" "}
                <code className="text-foreground">mcp-server/README.md</code> (Befehl{" "}
                <code className="text-foreground">uv run mcp-server --tunnel</code>). Das betrifft
                nicht die öffentliche Seite hier, sondern nur deine Maschine.
              </p>
            </section>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
