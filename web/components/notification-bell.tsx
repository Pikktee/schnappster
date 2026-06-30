"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Bell, BellOff, Check, Target, TrendingDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationsRead,
} from "@/lib/api"
import type { Notification } from "@/lib/types"
import { timeAgo } from "@/lib/format"
import { cn } from "@/lib/utils"

const POLL_INTERVAL_MS = 45_000

function NotificationIcon({ type }: { type: string }) {
  if (type === "price_below_threshold") {
    return (
      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
        <Target className="size-4" aria-hidden />
      </span>
    )
  }
  return (
    <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-600">
      <TrendingDown className="size-4" aria-hidden />
    </span>
  )
}

export function NotificationBell() {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [unread, setUnread] = useState(0)
  const [items, setItems] = useState<Notification[]>([])
  const [loading, setLoading] = useState(false)

  const loadCount = useCallback(() => {
    fetchUnreadCount()
      .then(({ count }) => setUnread(count))
      .catch(() => {})
  }, [])

  const loadItems = useCallback(() => {
    setLoading(true)
    fetchNotifications()
      .then(setItems)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // Initial laden + regelmäßiges Polling der ungelesenen Anzahl.
  useEffect(() => {
    loadCount()
    const id = window.setInterval(loadCount, POLL_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [loadCount])

  // Beim Öffnen die Liste laden.
  useEffect(() => {
    if (open) loadItems()
  }, [open, loadItems])

  async function handleClick(notification: Notification) {
    if (!notification.is_read) {
      setItems((prev) =>
        prev.map((n) => (n.id === notification.id ? { ...n, is_read: true } : n)),
      )
      setUnread((c) => Math.max(0, c - 1))
      markNotificationsRead([notification.id]).catch(() => {})
    }
    setOpen(false)
    if (notification.link) router.push(notification.link)
  }

  async function handleMarkAll() {
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })))
    setUnread(0)
    await markAllNotificationsRead().catch(() => {})
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative size-9 cursor-pointer text-muted-foreground hover:text-foreground"
          aria-label={unread > 0 ? `${unread} ungelesene Benachrichtigungen` : "Benachrichtigungen"}
        >
          <Bell className="size-5" />
          {unread > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold leading-4 text-primary-foreground shadow-sm ring-2 ring-background">
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" sideOffset={8} className="w-[22rem] max-w-[calc(100vw-1.5rem)] p-0">
        <div className="flex items-center justify-between border-b px-4 py-2.5">
          <span className="text-sm font-semibold">Benachrichtigungen</span>
          {items.some((n) => !n.is_read) && (
            <button
              type="button"
              onClick={handleMarkAll}
              className="flex cursor-pointer items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              <Check className="size-3" /> Alle gelesen
            </button>
          )}
        </div>

        <div className="max-h-[22rem] overflow-y-auto overscroll-contain">
          {loading && items.length === 0 ? (
            <div className="px-4 py-10 text-center text-sm text-muted-foreground">Lädt…</div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
              <BellOff className="size-7 text-muted-foreground/40" aria-hidden />
              <p className="text-sm text-muted-foreground">Noch keine Benachrichtigungen.</p>
            </div>
          ) : (
            <ul className="m-0 list-none p-0">
              {items.map((n) => (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => handleClick(n)}
                    className={cn(
                      "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/60",
                      !n.is_read && "bg-primary/[0.04]",
                    )}
                  >
                    <NotificationIcon type={n.type} />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-1.5">
                        {!n.is_read && (
                          <span className="size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                        )}
                        <span className="truncate text-sm font-medium text-foreground">{n.title}</span>
                      </span>
                      {n.body && (
                        <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                          {n.body}
                        </span>
                      )}
                      <span className="mt-0.5 block text-[0.68rem] text-muted-foreground/70">
                        {timeAgo(n.created_at)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}
