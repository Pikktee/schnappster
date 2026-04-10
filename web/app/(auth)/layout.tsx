"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { useAuth } from "@/components/auth-provider"
import { Spinner } from "@/components/ui/spinner"

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { session, loading } = useAuth()

  useEffect(() => {
    if (!loading && session) {
      router.replace("/")
    }
  }, [loading, session, router])

  if (loading) {
    return (
      <div className="flex h-svh items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return (
    <main className="min-h-svh bg-gradient-to-b from-background to-muted/30">
      <div className="mx-auto flex min-h-svh w-full max-w-md flex-col justify-center gap-6 px-4 py-10">
        {children}
        <p className="text-center text-xs text-muted-foreground">
          Mit der Anmeldung akzeptierst du die{" "}
          <Link href="/datenschutz" className="underline underline-offset-4 hover:text-foreground">
            Datenschutzerklaerung
          </Link>
          .
        </p>
      </div>
    </main>
  )
}
