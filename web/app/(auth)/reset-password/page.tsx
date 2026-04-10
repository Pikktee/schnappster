"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { supabase } from "@/lib/supabase"
import { PasswordStrengthIndicator } from "@/components/password-strength-indicator"
import { isPasswordValid } from "@/lib/password-validation"

export default function ResetPasswordPage() {
  const router = useRouter()
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!isPasswordValid(password)) {
      toast.error("Passwort erfuellt nicht alle Anforderungen.")
      return
    }
    if (!supabase) {
      toast.error("Passwort-Reset ist derzeit nicht verfuegbar.")
      return
    }
    setLoading(true)
    const { error } = await supabase.auth.updateUser({ password })
    setLoading(false)
    if (error) {
      toast.error(error.message)
      return
    }
    toast.success("Passwort aktualisiert.")
    router.replace("/login")
  }

  return (
    <Card className="shadow-md">
      <CardHeader>
        <CardTitle>Passwort zuruecksetzen</CardTitle>
        <CardDescription>Wähle ein neues Passwort für dein Konto.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-3" onSubmit={onSubmit}>
          <div className="space-y-2">
            <Label htmlFor="password">Neues Passwort</Label>
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
            {loading ? "Speichern..." : "Neues Passwort speichern"}
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
