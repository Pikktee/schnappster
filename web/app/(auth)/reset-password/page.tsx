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

export default function ResetPasswordPage() {
  const router = useRouter()
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
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
            <p className="text-xs text-muted-foreground">Mindestens 8 Zeichen empfohlen.</p>
          </div>
          <Button className="w-full" disabled={loading} type="submit">
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
