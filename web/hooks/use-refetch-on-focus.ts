"use client"

import { useEffect, useRef } from "react"

/**
 * Calls the given refetch callback whenever the document becomes visible again
 * (e.g. user switches back to the tab). Keeps data fresh without a full reload.
 */
export function useRefetchOnFocus(refetch: () => void): void {
  const refetchRef = useRef(refetch)
  refetchRef.current = refetch

  useEffect(() => {
    function onVisibilityChange() {
      if (document.visibilityState === "visible") {
        // #region agent log
        fetch("http://127.0.0.1:7779/ingest/bfe3bd6e-2abc-4ac9-b804-18a979d98c6d", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "af5e93" },
          body: JSON.stringify({
            sessionId: "af5e93",
            runId: "frontend-round2",
            hypothesisId: "H5",
            location: "web/hooks/use-refetch-on-focus.ts:onVisibilityChange",
            message: "refetch triggered by visibility",
            data: {},
            timestamp: Date.now(),
          }),
        }).catch(() => {})
        // #endregion
        refetchRef.current()
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange)
    return () => document.removeEventListener("visibilitychange", onVisibilityChange)
  }, [])
}
