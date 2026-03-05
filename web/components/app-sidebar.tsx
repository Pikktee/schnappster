"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Home, Search, Tag, List, Settings, Flame } from "lucide-react"
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

const navItems = [
  { label: "Start", href: "/", icon: Home },
  { label: "Suchauftraege", href: "/searches/", icon: Search },
  { label: "Anzeigen", href: "/ads/", icon: Tag },
  { label: "Logs", href: "/logs/", icon: List },
  { label: "Einstellungen", href: "/settings/", icon: Settings },
]

export function AppSidebar() {
  const pathname = usePathname()

  function isActive(href: string) {
    const path = pathname.replace(/\/$/, "") || "/"
    const base = href.replace(/\/$/, "") || "/"
    if (base === "/") return path === "/"
    return path === base || path.startsWith(base + "/")
  }

  return (
    <Sidebar>
      <SidebarHeader className="px-4 py-4">
        <Link href="/" className="flex items-center gap-2 cursor-pointer">
          <div className="flex items-center justify-center size-8 rounded-lg bg-amber-500">
            <Flame className="size-4 text-white" />
          </div>
          <span className="text-lg font-bold text-foreground">Schnappster</span>
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
                    <Link href={item.href}>
                      <item.icon className="size-4" />
                      <span>{item.label}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="px-4 py-3">
        <span className="text-xs text-muted-foreground">Version v0.1.0</span>
      </SidebarFooter>
    </Sidebar>
  )
}
