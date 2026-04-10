import path from "node:path"
import { fileURLToPath } from "node:url"

import nextEnv from "@next/env"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, "..")

const { loadEnvConfig } = nextEnv
const preferNonEmpty = (...values) => values.find((value) => typeof value === "string" && value.trim())

// Zentralisierte Root-.env laden, damit Frontend und Backend dieselbe Quelle nutzen.
loadEnvConfig(repoRoot)

process.env.NEXT_PUBLIC_SUPABASE_URL = preferNonEmpty(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_URL
) ?? ""
process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = preferNonEmpty(
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
  process.env.SUPABASE_PUBLISHABLE_KEY
) ?? ""

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  env: {
    NEXT_PUBLIC_SUPABASE_URL: preferNonEmpty(
      process.env.NEXT_PUBLIC_SUPABASE_URL,
      process.env.SUPABASE_URL
    ) ?? "",
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:
      preferNonEmpty(
        process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
        process.env.SUPABASE_PUBLISHABLE_KEY
      ) ?? "",
  },
  images: {
    unoptimized: true,
  },
  // Static export only for production build (FastAPI serves web/out). Omit in dev so dynamic routes work on localhost:3000.
  ...(process.env.NODE_ENV === "production" && { output: "export" }),
  trailingSlash: true,
}

export default nextConfig
