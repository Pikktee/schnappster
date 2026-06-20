import { formatFastApiDetail } from "./api"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""

export const TOKEN_KEY = "schnappster_token"

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  return window.localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return
  window.localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  if (typeof window === "undefined") return
  window.localStorage.removeItem(TOKEN_KEY)
}

/** Wirft einen Error mit dem FastAPI-`detail`-Text, falls die Antwort nicht ok ist. */
async function postAuth(path: string, body: { email: string; password: string }): Promise<unknown> {
  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  } catch {
    throw new Error("Keine Verbindung zum Server — bitte Internetverbindung prüfen.")
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = formatFastApiDetail((data as { detail?: unknown }).detail)
    throw new Error(detail || `Anfrage fehlgeschlagen (${res.status})`)
  }
  return data
}

export async function login(email: string, password: string): Promise<void> {
  const data = (await postAuth("/auth/login", { email, password })) as {
    access_token?: string
  }
  if (!data.access_token) {
    throw new Error("Server lieferte kein gültiges Token.")
  }
  setToken(data.access_token)
}

export async function register(email: string, password: string): Promise<void> {
  await postAuth("/auth/register", { email, password })
}

export function logout(): void {
  clearToken()
  if (typeof window !== "undefined") {
    window.location.href = "/login"
  }
}
