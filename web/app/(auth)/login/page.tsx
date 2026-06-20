"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/components/auth-provider"
import { login } from "@/lib/auth"

export default function LoginPage() {
  const router = useRouter()
  const { refresh } = useAuth()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await login(email, password)
      await refresh()
      router.replace("/dashboard")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Anmeldung fehlgeschlagen.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="shadow-md">
      <CardHeader>
        <CardTitle>Anmelden</CardTitle>
        <CardDescription>
          Willkommen zurück bei Schnappster. Bitte melde dich an um fortzufahren.
        </CardDescription>
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
              autoComplete="current-password"
              required
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <Button className="w-full" disabled={loading} type="submit">
            {loading ? "Anmeldung..." : "Einloggen"}
          </Button>
        </form>
        <div className="text-sm">
          <Link href="/register" className="underline underline-offset-4">
            Konto erstellen
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}
