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
        refetchRef.current()
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange)
    return () => document.removeEventListener("visibilitychange", onVisibilityChange)
  }, [])
}
