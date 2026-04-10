import { createClient } from "@supabase/supabase-js"

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
