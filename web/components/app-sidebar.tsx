"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import {
  ChevronsUpDown,
  Home,
  List,
  LogOut,
  Search,
  Settings,
  Tag,
  TrendingDown,
  Users,
} from "lucide-react"
import { BrandLogo, OwlMark } from "@/components/brand-logo"
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
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { fetchErrorLogs, fetchMe, fetchVersion } from "@/lib/api"
import { useAuth } from "@/components/auth-provider"

const navItems = [
  { label: "Start", href: "/dashboard", icon: Home },
  { label: "Angebote", href: "/ads/", icon: Tag },
  { label: "Suchaufträge", href: "/searches/", icon: Search },
  { label: "Preis-Alarme", href: "/price-alerts/", icon: TrendingDown },
  { label: "Logs", href: "/logs/", icon: List },
  { label: "Benutzer", href: "/users/", icon: Users },
]

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("")
}

function truncateDisplayName(name: string, maxLength: number): string {
  if (name.length <= maxLength) return name
  return `${name.slice(0, maxLength).trimEnd()}...`
}

export function AppSidebar() {
  const router = useRouter()
  const pathname = usePathname()
  const { isMobile } = useSidebar()
  const { user, logout } = useAuth()
  const isAdmin = user?.role === "admin"
  const [versionLabel, setVersionLabel] = useState("v…")
  const [errorCount, setErrorCount] = useState<number>(0)
  const [profileDisplayName, setProfileDisplayName] = useState<string | null>(null)

  useEffect(() => {
    fetchVersion()
      .then(({ version: v }) => setVersionLabel(`v${v}`))
      .catch(() => setVersionLabel("—"))
  }, [])

  useEffect(() => {
    if (!user) {
      setProfileDisplayName(null)
      return
    }
    fetchMe()
      .then((profile) => setProfileDisplayName(profile.display_name))
      .catch(() => setProfileDisplayName(null))
  }, [user?.id])

  useEffect(() => {
    const onProfileUpdated = (event: Event) => {
      const customEvent = event as CustomEvent<{ display_name?: string }>
      const displayName = customEvent.detail?.display_name?.trim()
      if (displayName) {
        setProfileDisplayName(displayName)
      }
    }
    window.addEventListener("schnappster-profile-updated", onProfileUpdated)
    return () => window.removeEventListener("schnappster-profile-updated", onProfileUpdated)
  }, [])

  useEffect(() => {
    if (!isAdmin) return
    fetchErrorLogs({ limit: 100 })
      .then((logs) => setErrorCount(logs.length))
      .catch(() => setErrorCount(0))
  }, [isAdmin])

  useEffect(() => {
    const onCleared = () => setErrorCount(0)
    window.addEventListener("schnappster-error-logs-cleared", onCleared)
    return () => window.removeEventListener("schnappster-error-logs-cleared", onCleared)
  }, [])

  function isActive(href: string) {
    const path = pathname.replace(/\/$/, "") || "/"
    const base = href.replace(/\/$/, "") || "/"
    if (base === "/") return path === "/"
    return path === base || path.startsWith(base + "/")
  }

  const adminOnlyHrefs = new Set(["/logs/", "/users/"])
  const visibleItems = navItems.filter((item) => !adminOnlyHrefs.has(item.href) || isAdmin)
  const userDisplayName =
    profileDisplayName?.trim() ||
    user?.display_name?.trim() ||
    user?.email ||
    "Unbekannter Nutzer"
  const userRoleLabel = isAdmin ? "Administrator" : "Mitglied"
  const shortUserDisplayName = truncateDisplayName(userDisplayName, 24)
  const initials = getInitials(userDisplayName)

  function handleLogout() {
    // logout() löscht das Token und navigiert per harter Weiterleitung zu /login,
    // sodass der Auth-Gate-Effekt des App-Layouts nicht mit uns um die Route konkurriert.
    logout()
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-4 group-data-[collapsible=icon]:px-2 group-data-[collapsible=icon]:py-3">
        <Link href="/dashboard" className="flex items-center cursor-pointer">
          <BrandLogo owlSize={36} className="group-data-[collapsible=icon]:hidden" />
          <OwlMark size={32} className="hidden group-data-[collapsible=icon]:block" />
        </Link>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {visibleItems.map((item) => (
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
                      {item.href === "/logs/" && isAdmin && errorCount > 0 && (
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

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  tooltip={userDisplayName}
                  className="cursor-pointer"
                >
                  <Avatar className="size-7 shrink-0">
                    <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-medium" title={userDisplayName}>
                      {shortUserDisplayName}
                    </span>
                    <span className="truncate text-xs text-muted-foreground">{userRoleLabel}</span>
                  </div>
                  <ChevronsUpDown className="ml-auto size-4 text-muted-foreground" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56"
                side={isMobile ? "bottom" : "right"}
                align="end"
                sideOffset={4}
              >
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col gap-1">
                    <p className="text-sm font-medium leading-none" title={userDisplayName}>
                      {shortUserDisplayName}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem className="cursor-pointer" onSelect={() => router.push("/settings/")}>
                    <Settings />
                    Einstellungen
                  </DropdownMenuItem>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="cursor-pointer">
                  <LogOut />
                  Abmelden
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
        <div className="mx-3 flex flex-wrap items-center justify-center gap-x-1.5 gap-y-0.5 border-t border-border/40 pt-2 pb-0.5 text-[10px] tracking-wide text-muted-foreground/50 group-data-[collapsible=icon]:hidden">
          <Link href="/impressum" className="transition-colors hover:text-muted-foreground">
            Impressum
          </Link>
          <span>·</span>
          <span className="tabular-nums">{versionLabel}</span>
        </div>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}
