"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { useAuth } from "@/components/auth-provider"
import { BrandLogo } from "@/components/brand-logo"
import { Spinner } from "@/components/ui/spinner"

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { user, loading } = useAuth()

  useEffect(() => {
    if (!loading && user) {
      router.replace("/dashboard")
    }
  }, [loading, user, router])

  if (loading || user) {
    return (
      <div className="flex h-svh items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return (
    <main className="min-h-svh bg-gradient-to-b from-background to-muted/30">
      <div className="mx-auto flex min-h-svh w-full max-w-md flex-col justify-center gap-6 px-4 py-10">
        <div className="flex flex-col items-center gap-3 text-center">
          <BrandLogo owlSize={48} textClassName="text-2xl" />
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">
              Deals finden. Bewerten lassen. Schnell reagieren.
            </p>
          </div>
        </div>
        {children}
        <p className="text-center text-xs text-muted-foreground">
          <Link href="/impressum" className="underline underline-offset-4 hover:text-foreground">
            Impressum
          </Link>
          {" · "}
          <Link href="/datenschutz" className="underline underline-offset-4 hover:text-foreground">
            Datenschutz
          </Link>
        </p>
      </div>
    </main>
  )
}
