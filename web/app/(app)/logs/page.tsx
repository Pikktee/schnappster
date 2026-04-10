"use client"

import { useEffect, useState, Fragment } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/empty-state"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  fetchSearches,
  fetchScrapeRuns,
  fetchErrorLogs,
  fetchAIAnalysisLogs,
  clearScrapeRuns,
  clearErrorLogs,
  clearAIAnalysisLogs,
} from "@/lib/api"
import type { AdSearch, ScrapeRun, ErrorLog, AIAnalysisLog } from "@/lib/types"
import { timeAgo } from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import {
  ChevronRight,
  Trash2,
  Loader2,
  RefreshCw,
  AlertCircle,
  Sparkles,
  Clock,
  Search,
  List,
  PlusCircle,
  Tag,
  MessageSquare,
  Star,
  FileText,
} from "lucide-react"
import { ContentReveal } from "@/components/content-reveal"
import { usePageHead } from "../page-head-context"

const LIMIT = 100

export default function LogsPage() {
  const [searches, setSearches] = useState<AdSearch[]>([])
  const [scraperuns, setScraperuns] = useState<ScrapeRun[]>([])
  const [errorLogs, setErrorLogs] = useState<ErrorLog[]>([])
  const [aiLogs, setAILogs] = useState<AIAnalysisLog[]>([])
  const [loading, setLoading] = useState(true)
  const [clearing, setClearing] = useState<"runs" | "errors" | "ai" | null>(null)
  const [activeTab, setActiveTab] = useState<"runs" | "errors" | "ai">("runs")
  const [expandedErrors, setExpandedErrors] = useState<Set<number>>(new Set())
  const [expandedAi, setExpandedAi] = useState<Set<number>>(new Set())
  const { setHeaderActions } = usePageHead()

  function load() {
    setLoading(true)
    Promise.all([
      fetchSearches(),
      fetchScrapeRuns({ limit: LIMIT }),
      fetchErrorLogs({ limit: LIMIT }),
      fetchAIAnalysisLogs({ limit: LIMIT }),
    ])
      .then(([s, r, e, a]) => {
        setSearches(s)
        setScraperuns(r)
        setErrorLogs(e)
        setAILogs(a)
      })
      .catch((err) => {
        toast.error(err instanceof Error ? err.message : "Logs konnten nicht geladen werden.")
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    if (!loading) {
      setHeaderActions(
        <Button variant="outline" size="sm" onClick={load} className="cursor-pointer">
          <RefreshCw className="size-4 mr-2" />
          Aktualisieren
        </Button>
      )
    } else {
      setHeaderActions(null)
    }
    return () => setHeaderActions(null)
  }, [loading, setHeaderActions])

  const searchMap = new Map(searches.map((s) => [s.id, s]))

  function toggleError(id: number) {
    setExpandedErrors((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  function toggleAi(id: number) {
    setExpandedAi((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleClearRuns() {
    setClearing("runs")
    try {
      await clearScrapeRuns()
      setScraperuns([])
      toast.success("Scraper-Durchläufe geleert")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Leeren fehlgeschlagen")
    } finally {
      setClearing(null)
    }
  }

  async function handleClearErrors() {
    setClearing("errors")
    try {
      await clearErrorLogs()
      setErrorLogs([])
      window.dispatchEvent(new CustomEvent("schnappster-error-logs-cleared"))
      toast.success("Fehlerprotokolle geleert")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Leeren fehlgeschlagen")
    } finally {
      setClearing(null)
    }
  }

  async function handleClearAI() {
    setClearing("ai")
    try {
      await clearAIAnalysisLogs()
      setAILogs([])
      toast.success("AI-Analysen-Protokoll geleert")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Leeren fehlgeschlagen")
    } finally {
      setClearing(null)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  return (
    <ContentReveal className="flex flex-col gap-6 min-w-0">
      <div>
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "runs" | "errors" | "ai")} className="w-full min-w-0">
        <TabsList className="w-full sm:w-auto inline-flex h-auto p-0 gap-0 border-b-2 border-border bg-muted/40 rounded-none min-h-[3rem]">
          <TabsTrigger
            value="runs"
            className="flex items-center gap-2 cursor-pointer rounded-t-lg rounded-b-none border-b-[3px] border-transparent bg-transparent px-5 py-3 -mb-[2px] text-sm font-medium text-muted-foreground data-[state=active]:text-foreground data-[state=active]:border-primary data-[state=active]:border-b-2 data-[state=active]:bg-background data-[state=active]:shadow-sm data-[state=active]:ring-1 data-[state=active]:ring-border data-[state=active]:rounded-b-none shadow-none transition-all duration-200 hover:text-foreground"
          >
            <RefreshCw className="size-4" />
            Scraper-Durchläufe
          </TabsTrigger>
          <TabsTrigger
            value="ai"
            className="flex items-center gap-2 cursor-pointer rounded-t-lg rounded-b-none border-b-[3px] border-transparent bg-transparent px-5 py-3 -mb-[2px] text-sm font-medium text-muted-foreground data-[state=active]:text-foreground data-[state=active]:border-primary data-[state=active]:border-b-2 data-[state=active]:bg-background data-[state=active]:shadow-sm data-[state=active]:ring-1 data-[state=active]:ring-border data-[state=active]:rounded-b-none shadow-none transition-all duration-200 hover:text-foreground"
          >
            <Sparkles className="size-4" />
            AI-Analysen
          </TabsTrigger>
          <TabsTrigger
            value="errors"
            className="flex items-center gap-2 cursor-pointer rounded-t-lg rounded-b-none border-b-[3px] border-transparent bg-transparent px-5 py-3 -mb-[2px] text-sm font-medium text-muted-foreground data-[state=active]:text-foreground data-[state=active]:border-primary data-[state=active]:border-b-2 data-[state=active]:bg-background data-[state=active]:shadow-sm data-[state=active]:ring-1 data-[state=active]:ring-border data-[state=active]:rounded-b-none shadow-none transition-all duration-200 hover:text-foreground"
          >
            <AlertCircle className="size-4" />
            Fehler
            {errorLogs.length > 0 && (
              <Badge variant="destructive" className="ml-1 size-5 shrink-0 p-0 justify-center text-[10px]">
                {errorLogs.length > 99 ? "99+" : errorLogs.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="runs" className="mt-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-2">
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <RefreshCw className="size-5 text-primary/80" />
                Scraper-Durchläufe
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearRuns}
                disabled={scraperuns.length === 0 || clearing !== null}
                className="cursor-pointer text-muted-foreground hover:text-destructive"
              >
                {clearing === "runs" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4 mr-1.5" />
                )}
                Leeren
              </Button>
            </div>
            {scraperuns.length === 0 ? (
              <EmptyState message="Keine Scraper-Durchläufe." />
            ) : (
              <div className="overflow-x-auto -mx-1">
                <table className="w-full min-w-[320px] text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <Clock className="size-3.5" />
                          Zeitpunkt
                        </span>
                      </th>
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <Search className="size-3.5" />
                          Suchauftrag
                        </span>
                      </th>
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <List className="size-3.5" />
                          Gefunden
                        </span>
                      </th>
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <Tag className="size-3.5" />
                          Gefiltert
                        </span>
                      </th>
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <PlusCircle className="size-3.5" />
                          Neu
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {scraperuns.map((run) => {
                      const search = searchMap.get(run.adsearch_id)
                      return (
                        <tr
                          key={run.id}
                          className="border-b border-border/80 last:border-0 hover:bg-muted/20 transition-colors"
                        >
                          <td className="py-3 px-3 text-muted-foreground whitespace-nowrap">
                            {timeAgo(run.started_at)}
                          </td>
                          <td className="py-3 px-3">
                            {search ? (
                              <Link
                                href={`/searches/${run.adsearch_id}`}
                                className="text-primary hover:underline font-medium cursor-pointer"
                              >
                                {search.name}
                              </Link>
                            ) : (
                              <span className="text-muted-foreground">Suchauftrag #{run.adsearch_id}</span>
                            )}
                          </td>
                          <td className="py-3 px-3">{run.ads_found}</td>
                          <td className="py-3 px-3">{run.ads_filtered}</td>
                          <td className="py-3 px-3">
                            {run.ads_new > 0 ? (
                              <span className="text-emerald-600 font-semibold">+{run.ads_new}</span>
                            ) : (
                              <span className="text-muted-foreground">0</span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="errors" className="mt-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-2">
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <AlertCircle className="size-5 text-destructive/80" />
                Fehlerprotokolle
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearErrors}
                disabled={errorLogs.length === 0 || clearing !== null}
                className="cursor-pointer text-muted-foreground hover:text-destructive"
              >
                {clearing === "errors" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4 mr-1.5" />
                )}
                Leeren
              </Button>
            </div>
            {errorLogs.length === 0 ? (
              <EmptyState message="Keine Fehler." />
            ) : (
              <div className="overflow-x-auto -mx-1">
                <table className="w-full min-w-[320px] text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="w-9 py-3 px-1" aria-label="Aufklappen" />
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <Clock className="size-3.5" />
                          Zeitpunkt
                        </span>
                      </th>
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <Tag className="size-3.5" />
                          Typ
                        </span>
                      </th>
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 min-w-[140px]">
                        <span className="inline-flex items-center gap-1.5">
                          <MessageSquare className="size-3.5" />
                          Nachricht
                        </span>
                      </th>
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <Search className="size-3.5" />
                          Suchauftrag
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {errorLogs.map((log) => {
                      const isOpen = expandedErrors.has(log.id)
                      return (
                        <Fragment key={log.id}>
                          <tr className="border-b border-border/80 hover:bg-muted/20 transition-colors">
                            <td className="align-top py-3 px-1 w-9">
                              <button
                                type="button"
                                onClick={() => toggleError(log.id)}
                                className="p-1 rounded cursor-pointer hover:bg-muted/40 transition-colors inline-flex items-center justify-center"
                                aria-expanded={isOpen}
                              >
                                <ChevronRight
                                  className={`size-4 text-muted-foreground transition-transform ${isOpen ? "rotate-90" : ""}`}
                                />
                              </button>
                            </td>
                            <td className="align-top py-3 px-3 text-muted-foreground whitespace-nowrap">
                              {timeAgo(log.created_at)}
                            </td>
                            <td className="align-top py-3 px-3 whitespace-nowrap">
                              <span className="inline-flex rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-foreground">
                                {log.error_type}
                              </span>
                            </td>
                            <td className="align-top py-3 px-3 min-w-0">
                              <span className="text-foreground line-clamp-2">{log.message}</span>
                            </td>
                            <td className="align-top py-3 px-3 whitespace-nowrap">
                              {log.adsearch_id != null ? (
                                <Link
                                  href={`/searches/${log.adsearch_id}`}
                                  className="text-primary hover:underline text-sm cursor-pointer"
                                >
                                  {searchMap.get(log.adsearch_id)?.name ?? `Suchauftrag #${log.adsearch_id}`}
                                </Link>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </td>
                          </tr>
                          {isOpen && (
                            <tr className="border-b border-border/80 bg-muted/20">
                              <td colSpan={5} className="py-3 px-4">
                                <div className="rounded-md border border-border/60 bg-background p-4">
                                  <p className="text-sm font-medium text-muted-foreground mb-2">Fehlerdetails</p>
                                  <pre className="text-sm text-muted-foreground whitespace-pre-wrap break-words font-mono leading-relaxed">
                                    {log.details ?? log.message}
                                  </pre>
                                </div>
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="ai" className="mt-4">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-2">
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <Sparkles className="size-5 text-primary/80" />
                AI-Analysen
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearAI}
                disabled={aiLogs.length === 0 || clearing !== null}
                className="cursor-pointer text-muted-foreground hover:text-destructive"
              >
                {clearing === "ai" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Trash2 className="size-4 mr-1.5" />
                )}
                Leeren
              </Button>
            </div>
            {aiLogs.length === 0 ? (
              <EmptyState message="Keine AI-Analysen." />
            ) : (
              <div className="overflow-x-auto -mx-1 min-w-0">
                <table className="w-full min-w-[400px] text-sm border-collapse table-fixed">
                  <colgroup>
                    <col className="w-8" />
                    <col className="w-[7rem]" />
                    <col className="w-[35%]" />
                    <col className="w-[28%]" />
                    <col className="w-14" />
                  </colgroup>
                  <thead>
                    <tr className="border-b border-border">
                      <th className="py-3 px-1 text-left" aria-label="Aufklappen" />
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <Clock className="size-3.5" />
                          Zeitpunkt
                        </span>
                      </th>
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 overflow-hidden">
                        <span className="inline-flex items-center gap-1.5 min-w-0 truncate" title="Anzeige">
                          <FileText className="size-3.5 shrink-0" />
                          Anzeige
                        </span>
                      </th>
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 overflow-hidden">
                        <span className="inline-flex items-center gap-1.5 min-w-0 truncate" title="Suchauftrag">
                          <Search className="size-3.5 shrink-0" />
                          Suchauftrag
                        </span>
                      </th>
                      <th className="text-left font-medium text-muted-foreground py-3 px-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1.5">
                          <Star className="size-3.5" />
                          Score
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {aiLogs.map((log) => {
                      const isOpen = expandedAi.has(log.id)
                      const search = log.adsearch_id != null ? searchMap.get(log.adsearch_id) : null
                      return (
                        <Fragment key={log.id}>
                          <tr className="border-b border-border/80 hover:bg-muted/20 transition-colors">
                            <td className="align-top py-3 px-1 w-8">
                              <button
                                type="button"
                                onClick={() => toggleAi(log.id)}
                                className="p-1 rounded cursor-pointer hover:bg-muted/40 transition-colors inline-flex items-center justify-center"
                                aria-expanded={isOpen}
                              >
                                <ChevronRight
                                  className={`size-4 text-muted-foreground transition-transform ${isOpen ? "rotate-90" : ""}`}
                                />
                              </button>
                            </td>
                            <td className="align-top py-3 px-3 text-muted-foreground whitespace-nowrap">
                              {timeAgo(log.created_at)}
                            </td>
                            <td className="align-top py-3 px-3 overflow-hidden">
                              {log.ad_id != null ? (
                                <Link
                                  href={`/ads/${log.ad_id}`}
                                  className="text-primary hover:underline font-medium cursor-pointer block min-w-0 truncate"
                                  title={log.ad_title ?? undefined}
                                >
                                  {log.ad_title || "—"}
                                </Link>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </td>
                            <td className="align-top py-3 px-3 overflow-hidden">
                              {log.adsearch_id != null ? (
                                <Link
                                  href={`/searches/${log.adsearch_id}`}
                                  className="text-primary hover:underline text-sm cursor-pointer block min-w-0 truncate"
                                  title={search?.name ?? `Suchauftrag #${log.adsearch_id}`}
                                >
                                  {search?.name ?? `Suchauftrag #${log.adsearch_id}`}
                                </Link>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </td>
                            <td className="align-top py-3 px-3 whitespace-nowrap font-medium">
                              {Math.round(log.score)}
                            </td>
                          </tr>
                          {isOpen && (
                            <tr className="border-b border-border/80 bg-muted/20">
                              <td colSpan={5} className="py-3 px-4">
                                <div className="rounded-md border border-border/60 bg-background p-4">
                                  <p className="text-sm font-medium text-muted-foreground mb-2">Prompt</p>
                                  <pre className="text-sm text-muted-foreground whitespace-pre-wrap break-words font-mono leading-relaxed">
                                    {log.prompt_text}
                                  </pre>
                                </div>
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
      </div>
    </ContentReveal>
  )
}
