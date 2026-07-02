import { redirect } from "next/navigation"

/** Deal-Alarme sind in den vereinheitlichten Suchaufträgen aufgegangen. */
export default function DealAlarmsPage() {
  redirect("/searches")
}
