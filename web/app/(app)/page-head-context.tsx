"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"

type PageHeadState = {
  title: string
  subtitle: string
  headerActions: ReactNode
  titleSuffix: ReactNode
}

const defaultTitles: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Dashboard", subtitle: "Übersicht über deine Angebots-Suchergebnisse" },
  "/ads": {
    title: "Angebote",
    subtitle: "Von der KI bewertete Angebote aus deinen Suchen",
  },
  "/searches": {
    title: "Suchaufträge",
    subtitle: "Verwalte deine Kleinanzeigen-Suchen",
  },
  "/settings": {
    title: "Einstellungen",
    subtitle: "Globale App-Einstellungen",
  },
  "/logs": {
    title: "Logs",
    subtitle: "Scraper-Durchläufe, Fehlerprotokolle und AI-Analysen",
  },
}

function getDefaultForPath(pathname: string): { title: string; subtitle: string } {
  const normalized = pathname.replace(/\/$/, "") || "/"
  return defaultTitles[normalized] ?? { title: "Laden…", subtitle: "" }
}

type PageHeadContextValue = PageHeadState & {
  setTitle: (title: string, subtitle?: string) => void
  setHeaderActions: (node: ReactNode) => void
  setTitleSuffix: (node: ReactNode) => void
}

const PageHeadContext = createContext<PageHeadContextValue | null>(null)

export function PageHeadProvider({
  pathname,
  children,
}: {
  pathname: string
  children: ReactNode
}) {
  const defaults = getDefaultForPath(pathname)
  const [title, setTitleState] = useState(defaults.title)
  const [subtitle, setSubtitleState] = useState(defaults.subtitle)
  const [headerActions, setHeaderActionsState] = useState<ReactNode>(null)
  const [titleSuffix, setTitleSuffixState] = useState<ReactNode>(null)

  useEffect(() => {
    const d = getDefaultForPath(pathname)
    setTitleState(d.title)
    setSubtitleState(d.subtitle)
    setHeaderActionsState(null)
    setTitleSuffixState(null)
  }, [pathname])

  const setTitle = useCallback((t: string, s?: string) => {
    setTitleState(t)
    setSubtitleState(s ?? "")
  }, [])

  const setHeaderActions = useCallback((node: ReactNode) => {
    setHeaderActionsState(node)
  }, [])

  const setTitleSuffix = useCallback((node: ReactNode) => {
    setTitleSuffixState(node)
  }, [])

  const value = useMemo<PageHeadContextValue>(
    () => ({
      title,
      subtitle,
      headerActions,
      titleSuffix,
      setTitle,
      setHeaderActions,
      setTitleSuffix,
    }),
    [title, subtitle, headerActions, titleSuffix, setTitle, setHeaderActions, setTitleSuffix]
  )

  return (
    <PageHeadContext.Provider value={value}>{children}</PageHeadContext.Provider>
  )
}

export function usePageHead() {
  const ctx = useContext(PageHeadContext)
  if (!ctx) throw new Error("usePageHead must be used within PageHeadProvider")
  return ctx
}
