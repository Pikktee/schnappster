"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/components/auth-provider"
import { Spinner } from "@/components/ui/spinner"
import { LandingPage } from "@/components/landing/LandingPage"

export default function RootPage() {
  const router = useRouter()
  const { user, loading } = useAuth()

  useEffect(() => {
    if (!loading && user) {
      router.replace("/dashboard")
    }
  }, [loading, user, router])

  // While auth is resolving, or while redirecting an authenticated user,
  // show a spinner instead of flashing the landing page.
  if (loading || user) {
    return (
      <div className="flex h-svh items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return <LandingPage />
}
