"use client"

import Link from "next/link"
import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { supabase } from "@/lib/supabase"

export default function RegisterPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase) {
      toast.error("Registrierung ist derzeit nicht verfuegbar.")
      return
    }
    setLoading(true)
    const redirectTo = `${window.location.origin}/reset-password`
    const { error } = await supabase.auth.signUp({ email, password, options: { emailRedirectTo: redirectTo } })
    setLoading(false)
    if (error) {
      toast.error(error.message)
      return
    }
    toast.success("Registrierung erfolgreich. Bitte E-Mail bestaetigen.")
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Registrieren</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-3" onSubmit={onSubmit}>
          <div className="space-y-2">
            <Label htmlFor="email">E-Mail</Label>
            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Passwort</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <Button className="w-full" disabled={loading} type="submit">
            {loading ? "Registrierung..." : "Konto erstellen"}
          </Button>
        </form>
        <p className="text-sm">
          Bereits ein Konto?{" "}
          <Link href="/login" className="underline underline-offset-4">
            Zum Login
          </Link>
        </p>
      </CardContent>
    </Card>
  )
}
