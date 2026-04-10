"use client"

import Link from "next/link"
import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { supabase } from "@/lib/supabase"
import { PasswordStrengthIndicator } from "@/components/password-strength-indicator"
import { isPasswordValid } from "@/lib/password-validation"

export default function RegisterPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!isPasswordValid(password)) {
      toast.error("Passwort erfuellt nicht alle Anforderungen.")
      return
    }
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
    <Card className="shadow-md">
      <CardHeader>
        <CardTitle>Registrieren</CardTitle>
        <CardDescription>Erstelle ein Konto, um Schnappster zu nutzen.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-3" onSubmit={onSubmit}>
          <div className="space-y-2">
            <Label htmlFor="email">E-Mail</Label>
            <Input
              id="email"
              type="email"
              value={email}
              autoComplete="email"
              inputMode="email"
              required
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Passwort</Label>
            <Input
              id="password"
              type="password"
              value={password}
              autoComplete="new-password"
              required
              onChange={(e) => setPassword(e.target.value)}
            />
            <PasswordStrengthIndicator password={password} />
          </div>
          <Button className="w-full" disabled={loading || !isPasswordValid(password)} type="submit">
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
