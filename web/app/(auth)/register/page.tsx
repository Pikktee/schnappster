"use client"

import Link from "next/link"
import { useState } from "react"
import { toast } from "sonner"
import { CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { register } from "@/lib/auth"
import { PasswordStrengthIndicator } from "@/components/password-strength-indicator"
import { isPasswordValid } from "@/lib/password-validation"

export default function RegisterPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [registered, setRegistered] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!isPasswordValid(password)) {
      toast.error("Passwort erfuellt nicht alle Anforderungen.")
      return
    }
    setLoading(true)
    try {
      await register(email, password)
      setRegistered(true)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Registrierung fehlgeschlagen.")
    } finally {
      setLoading(false)
    }
  }

  if (registered) {
    return (
      <Card className="shadow-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="size-5 text-primary" />
            Konto angelegt
          </CardTitle>
          <CardDescription>
            Ein Administrator muss es noch freischalten. Du erhältst Zugang, sobald dein Konto
            aktiviert wurde.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm">
            <Link href="/login" className="underline underline-offset-4">
              Zum Login
            </Link>
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="shadow-md">
      <CardHeader>
        <CardTitle>Registrieren</CardTitle>
        <CardDescription>Erstelle ein Konto, um Schnappster zu nutzen.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-3" onSubmit={(e) => void onSubmit(e)}>
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
