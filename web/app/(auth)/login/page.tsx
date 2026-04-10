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

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase) {
      toast.error("Anmeldung ist derzeit nicht verfuegbar.")
      return
    }
    setLoading(true)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    setLoading(false)
    if (error) {
      toast.error(error.message)
      return
    }
    router.replace("/")
  }

  async function socialLogin(provider: "google" | "facebook") {
    if (!supabase) {
      toast.error("Anmeldung ist derzeit nicht verfuegbar.")
      return
    }
    const redirectTo = `${window.location.origin}/`
    const { error } = await supabase.auth.signInWithOAuth({ provider, options: { redirectTo } })
    if (error) toast.error(error.message)
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
        <div className="grid grid-cols-2 gap-2">
          <Button type="button" variant="outline" onClick={() => socialLogin("google")}>
            Google
          </Button>
          <Button type="button" variant="outline" onClick={() => socialLogin("facebook")}>
            Facebook
          </Button>
        </div>
        <div className="relative py-1">
          <div className="h-px w-full bg-border" />
          <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-2 text-xs text-muted-foreground">
            oder
          </span>
        </div>
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
              autoComplete="current-password"
              required
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <Button className="w-full" disabled={loading} type="submit">
            {loading ? "Anmeldung..." : "Einloggen"}
          </Button>
        </form>
        <div className="flex justify-between text-sm">
          <Link href="/register" className="underline underline-offset-4">
            Konto erstellen
          </Link>
          <Link href="/forgot-password" className="underline underline-offset-4">
            Passwort vergessen?
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}
