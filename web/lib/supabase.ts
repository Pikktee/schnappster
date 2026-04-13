import { createClient } from "@supabase/supabase-js"
import type { Session } from "@supabase/supabase-js"

function preferNonEmpty(...values: Array<string | undefined>) {
  return values.find((value) => typeof value === "string" && value.trim()) || ""
}

const supabaseUrl = preferNonEmpty(process.env.NEXT_PUBLIC_SUPABASE_URL)
const supabasePublishableKey = preferNonEmpty(process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY)

if (!supabaseUrl || !supabasePublishableKey) {
  // Dev-only hint for configuration issues without leaking secrets.
  if (process.env.NODE_ENV !== "production") {
    console.warn("Auth-Konfiguration unvollstaendig", {
      hasSupabaseUrl: Boolean(supabaseUrl),
      hasPublishableKey: Boolean(supabasePublishableKey),
    })
  }
}

export const supabase =
  supabaseUrl && supabasePublishableKey
    ? createClient(supabaseUrl, supabasePublishableKey)
    : null

const SESSION_TIMEOUT_MS = 5000

export async function getSessionWithTimeout(
  timeoutMs: number = SESSION_TIMEOUT_MS,
): Promise<Session | null> {
  if (!supabase) return null

  return new Promise<Session | null>((resolve) => {
    const timeoutId = window.setTimeout(() => {
      resolve(null)
    }, timeoutMs)

    supabase.auth
      .getSession()
      .then(({ data }) => {
        resolve(data.session ?? null)
      })
      .catch(() => {
        resolve(null)
      })
      .finally(() => {
        window.clearTimeout(timeoutId)
      })
  })
}
