"use client"

import Link from "next/link"
import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { supabase } from "@/lib/supabase"

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase) {
      toast.error("Passwort-Reset ist derzeit nicht verfuegbar.")
      return
    }
    setLoading(true)
    const redirectTo = `${window.location.origin}/reset-password`
    await supabase.auth.resetPasswordForEmail(email, { redirectTo })
    setLoading(false)
    toast.success("Wenn die E-Mail existiert, wurde ein Reset-Link versendet.")
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Passwort vergessen</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-3" onSubmit={onSubmit}>
          <div className="space-y-2">
            <Label htmlFor="email">E-Mail</Label>
            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <Button className="w-full" disabled={loading} type="submit">
            {loading ? "Senden..." : "Reset-Link senden"}
          </Button>
        </form>
        <p className="text-sm">
          <Link href="/login" className="underline underline-offset-4">
            Zurueck zum Login
          </Link>
        </p>
      </CardContent>
    </Card>
  )
}
