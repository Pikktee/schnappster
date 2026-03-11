"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { Home, Search, Tag, List, Settings } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { Badge } from "@/components/ui/badge"
import { fetchVersion, fetchErrorLogs } from "@/lib/api"

const navItems = [
  { label: "Start", href: "/", icon: Home },
  { label: "Suchaufträge", href: "/searches/", icon: Search },
  { label: "Schnäppchen", href: "/ads/", icon: Tag },
  { label: "Logs", href: "/logs/", icon: List },
  { label: "Einstellungen", href: "/settings/", icon: Settings },
]

export function AppSidebar() {
  const pathname = usePathname()
  const [versionLabel, setVersionLabel] = useState<string>("v…")
  const [errorCount, setErrorCount] = useState<number>(0)

  useEffect(() => {
    fetchVersion()
      .then(({ version: v }) => setVersionLabel(`v${v}`))
      .catch(() => setVersionLabel("—"))
  }, [])

  useEffect(() => {
    fetchErrorLogs({ limit: 100 })
      .then((logs) => setErrorCount(logs.length))
      .catch(() => setErrorCount(0))
  }, [])

  function isActive(href: string) {
    const path = pathname.replace(/\/$/, "") || "/"
    const base = href.replace(/\/$/, "") || "/"
    if (base === "/") return path === "/"
    return path === base || path.startsWith(base + "/")
  }

  return (
    <Sidebar>
      <SidebarHeader className="px-4 py-4">
        <Link href="/" className="flex items-center cursor-pointer">
          {/* eslint-disable-next-line @next/next/no-img-element -- static logo SVG */}
          <img
            src="/logo.svg"
            alt="Schnappster"
            className="h-12 w-auto max-w-full object-contain"
            width={200}
            height={60}
          />
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive(item.href)}
                    tooltip={item.label}
                    className="cursor-pointer"
                  >
                    <Link href={item.href} className="flex w-full items-center gap-2">
                      <item.icon className="size-4 shrink-0" />
                      <span className="min-w-0 flex-1 truncate">{item.label}</span>
                      {item.href === "/logs/" && errorCount > 0 && (
                        <Badge variant="destructive" className="ml-auto size-5 shrink-0 p-0 justify-center text-[10px]">
                          {errorCount > 99 ? "99+" : errorCount}
                        </Badge>
                      )}
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="px-4 py-3">
        <span className="text-xs text-muted-foreground">Version {versionLabel}</span>
      </SidebarFooter>
    </Sidebar>
  )
}
