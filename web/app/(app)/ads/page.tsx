import { redirect } from "next/navigation"

/** Die Angebote-Liste ist im Ergebnis-Stream der Startseite aufgegangen. */
export default function AdsPage() {
  redirect("/dashboard")
}
