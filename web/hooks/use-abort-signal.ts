"use client"

import { useCallback, useEffect, useRef } from "react"

/**
 * Returns a `getSignal` function that provides an AbortSignal for API calls.
 * Each call to `getSignal()` aborts the previous signal and creates a fresh one.
 * The signal is also aborted when the component unmounts, which cancels any
 * in-flight requests and prevents pool exhaustion on the backend.
 */
export function useAbortSignal(): () => AbortSignal {
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    return () => {
      // #region agent log
      fetch("http://127.0.0.1:7779/ingest/bfe3bd6e-2abc-4ac9-b804-18a979d98c6d", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "af5e93" },
        body: JSON.stringify({
          sessionId: "af5e93",
          runId: "frontend-round2",
          hypothesisId: "H6",
          location: "web/hooks/use-abort-signal.ts:cleanup",
          message: "abort on unmount",
          data: {
            hadController: Boolean(controllerRef.current),
          },
          timestamp: Date.now(),
        }),
      }).catch(() => {})
      // #endregion
      controllerRef.current?.abort()
      controllerRef.current = null
    }
  }, [])

  return useCallback(() => {
    const previousController = controllerRef.current
    if (previousController) {
      previousController.abort()
    }
    // #region agent log
    fetch("http://127.0.0.1:7779/ingest/bfe3bd6e-2abc-4ac9-b804-18a979d98c6d", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "af5e93" },
      body: JSON.stringify({
        sessionId: "af5e93",
        runId: "frontend-round2",
        hypothesisId: "H6",
        location: "web/hooks/use-abort-signal.ts:getSignal",
        message: "replace abort controller",
        data: {
          hadController: Boolean(previousController),
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {})
    // #endregion
    const controller = new AbortController()
    controllerRef.current = controller
    return controller.signal
  }, [])
}
