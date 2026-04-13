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
      controllerRef.current?.abort()
      controllerRef.current = null
    }
  }, [])

  return useCallback(() => {
    const previousController = controllerRef.current
    if (previousController) {
      previousController.abort()
    }
    const controller = new AbortController()
    controllerRef.current = controller
    return controller.signal
  }, [])
}
