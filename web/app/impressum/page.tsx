"use client"

import Image from "next/image"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function ImpressumPage() {
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
            <CardTitle>Impressum</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5 text-sm leading-relaxed">
            <div>
              <p className="font-medium">Angaben gemäß § 5 TMG</p>
              <p className="mt-2 whitespace-pre-line">
                {`Henrik Heil
Westendstr. 100
60325 Frankfurt`}
              </p>
            </div>
            <div>
              <p className="font-medium">Kontakt</p>
              <p className="mt-2">
                E-Mail:{" "}
                <a className="underline underline-offset-4" href="mailto:contact@henrikheil.net">
                  contact@henrikheil.net
                </a>
              </p>
            </div>

            <div>
              <p className="font-medium">Datenschutz</p>
              <p className="mt-2 text-muted-foreground">
                Nachfolgend findest du die Informationen zur Verarbeitung personenbezogener Daten bei
                der Nutzung von Schnappster.
              </p>
            </div>

            <section className="space-y-2">
              <h2 className="text-base font-medium">Verantwortlicher</h2>
              <p>Der Betreiber von Schnappster ist für die Datenverarbeitung verantwortlich.</p>
            </section>

            <section className="space-y-2">
              <h2 className="text-base font-medium">Verarbeitete Daten</h2>
              <p>
                Wir verarbeiten Authentifizierungsdaten (Supabase), Profilname, Suchaufträge,
                Anzeigen sowie optional Benachrichtigungsdaten wie Telegram-Chat-ID.
              </p>
            </section>

            <section className="space-y-2">
              <h2 className="text-base font-medium">Zweck und Rechtsgrundlage</h2>
              <p>
                Die Verarbeitung erfolgt zur Bereitstellung der Anwendung, Kontoführung, Auswertung
                deiner Suchaufträge und optionaler Benachrichtigungen. Rechtsgrundlagen sind Art. 6
                Abs. 1 lit. b DSGVO (Vertragserfüllung), Art. 6 Abs. 1 lit. a DSGVO (Einwilligung, z. B.
                bei optionalen Integrationen) sowie Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an
                Betriebssicherheit und Missbrauchsprävention).
              </p>
            </section>

            <section className="space-y-2">
              <h2 className="text-base font-medium">Supabase (Authentifizierung und Datenbank)</h2>
              <p>
                Für Login, Nutzerverwaltung und Datenhaltung wird Supabase als Auftragsverarbeiter
                eingesetzt. Dabei werden insbesondere Konto- und Sitzungsdaten, Nutzerkennungen und
                anwendungsbezogene Inhalte verarbeitet. Mit Supabase besteht ein Vertrag zur
                Auftragsverarbeitung nach Art. 28 DSGVO.
              </p>
            </section>

            <section className="space-y-2">
              <h2 className="text-base font-medium">Konto-Löschung</h2>
              <p>
                Du kannst dein Konto in den Einstellungen löschen. Zugehörige App-Daten werden
                entfernt; technische System-Logs können aus Betriebsgründen getrennt vorgehalten
                werden.
              </p>
            </section>

            <section className="space-y-2">
              <h2 className="text-base font-medium">Externe Dienste und Empfänger</h2>
              <p>
                Zur Bereitstellung von Schnappster können weitere Dienstleister eingesetzt werden, z. B.
                Hosting-Anbieter, KI-API-Anbieter für die Analyse von Anzeigen und optionale
                Benachrichtigungsdienste wie Telegram. Eine Weitergabe erfolgt nur, soweit dies zur
                Leistungserbringung erforderlich ist oder eine gesetzliche Pflicht besteht.
              </p>
            </section>

            <section className="space-y-2">
              <h2 className="text-base font-medium">Speicherdauer</h2>
              <p>
                Personenbezogene Daten werden nur so lange gespeichert, wie es für die genannten Zwecke
                erforderlich ist oder gesetzliche Aufbewahrungspflichten bestehen. Danach werden Daten
                gelöscht oder anonymisiert.
              </p>
            </section>

            <section className="space-y-2">
              <h2 className="text-base font-medium">Datenübermittlung in Drittländer</h2>
              <p>
                Soweit Dienstleister außerhalb der EU/des EWR eingesetzt werden, erfolgt die
                Datenübermittlung nur bei Vorliegen der gesetzlichen Voraussetzungen (z. B.
                Angemessenheitsbeschluss oder EU-Standardvertragsklauseln).
              </p>
            </section>

            <section className="space-y-2">
              <h2 className="text-base font-medium">Deine Rechte</h2>
              <p>
                Du hast nach der DSGVO das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung
                der Verarbeitung, Datenübertragbarkeit sowie Widerspruch gegen bestimmte
                Verarbeitungen. Erteilte Einwilligungen kannst du jederzeit mit Wirkung für die Zukunft
                widerrufen.
              </p>
            </section>

            <section className="space-y-2">
              <h2 className="text-base font-medium">Beschwerderecht</h2>
              <p>
                Du hast das Recht, dich bei einer Datenschutzaufsichtsbehörde zu beschweren, wenn du
                der Ansicht bist, dass die Verarbeitung deiner personenbezogenen Daten rechtswidrig
                erfolgt.
              </p>
            </section>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}

