import Link from "next/link"

export default function DatenschutzPage() {
  return (
    <main className="mx-auto w-full max-w-3xl space-y-6 px-4 py-10">
      <h1 className="text-3xl font-semibold">Datenschutzerklaerung</h1>
      <p className="text-muted-foreground">
        Diese Seite beschreibt die Verarbeitung personenbezogener Daten in Schnappster.
      </p>

      <section className="space-y-2">
        <h2 className="text-xl font-medium">Verantwortlicher</h2>
        <p>Der Betreiber von Schnappster ist fuer die Datenverarbeitung verantwortlich.</p>
      </section>

      <section className="space-y-2">
        <h2 className="text-xl font-medium">Verarbeitete Daten</h2>
        <p>
          Wir verarbeiten Authentifizierungsdaten (Supabase), Profilname, Suchauftraege, Anzeigen, sowie
          optional Benachrichtigungsdaten wie Telegram-Chat-ID.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-xl font-medium">Zweck und Rechtsgrundlage</h2>
        <p>
          Die Verarbeitung erfolgt zur Bereitstellung der Anwendung, Kontofuehrung und optionaler
          Benachrichtigungen.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-xl font-medium">Konto-Loeschung</h2>
        <p>
          Du kannst dein Konto in den Einstellungen loeschen. Zugehoerige App-Daten werden entfernt; technische
          System-Logs koennen aus Betriebsgruenden getrennt vorgehalten werden.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-xl font-medium">Dienstleister</h2>
        <p>
          Eingesetzte Subprozessoren umfassen u. a. Supabase (Auth/DB), Hosting und optional
          Benachrichtigungsdienste.
        </p>
      </section>

      <p className="text-sm text-muted-foreground">
        Zurueck zur{" "}
        <Link href="/login" className="underline underline-offset-4">
          Anmeldung
        </Link>
      </p>
    </main>
  )
}
