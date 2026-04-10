"use client"

import { usePathname } from "next/navigation"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { Spinner } from "@/components/ui/spinner"
import { useAuth } from "@/components/auth-provider"
import { PageHeadProvider } from "./page-head-context"
import { AppPageHead } from "./app-page-head"

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { session, loading } = useAuth()

  useEffect(() => {
    if (!loading && !session) {
      router.replace("/login")
    }
  }, [loading, session, router])

  if (loading || !session) {
    return (
      <div className="flex h-svh items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return (
    <PageHeadProvider pathname={pathname}>
      <SidebarProvider className="h-svh">
        <AppSidebar />
        <SidebarInset className="min-h-0">
          <header className="flex h-12 items-center gap-2 border-b px-4 md:hidden">
            <SidebarTrigger />
            <span className="text-sm font-semibold text-foreground">Schnappster</span>
          </header>
          <main id="main-content" className="main-scroll flex-1 overflow-y-scroll overflow-x-hidden p-6 lg:p-8">
            <div className="w-full ltr">
              <div className="w-full max-w-7xl flex flex-col gap-6">
                <AppPageHead />
                {children}
              </div>
            </div>
          </main>
        </SidebarInset>
      </SidebarProvider>
    </PageHeadProvider>
  )
}
