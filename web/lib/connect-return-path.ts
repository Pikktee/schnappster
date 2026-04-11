/** Erlaubt nur interne Rückkehr zur Verbindungs-Freigabeseite `/connect` (Open-Redirect-Schutz). */

const CONNECT_PREFIX = "/connect"

function isAllowedConnectPath(decoded: string): boolean {
  if (!decoded.startsWith(CONNECT_PREFIX)) {
    return false
  }
  const rest = decoded.slice(CONNECT_PREFIX.length)
  return rest === "" || rest === "/" || rest.startsWith("?") || rest.startsWith("/?")
}

export function getSafeConnectReturnPath(next: string | null | undefined): string {
  if (!next || typeof next !== "string") {
    return "/"
  }
  let decoded: string
  try {
    decoded = decodeURIComponent(next.trim())
  } catch {
    return "/"
  }
  if (!isAllowedConnectPath(decoded)) {
    return "/"
  }
  if (decoded.startsWith("//") || decoded.includes("://")) {
    return "/"
  }
  if (!decoded.startsWith("/")) {
    return "/"
  }
  return decoded
}

export function buildLoginUrlWithConnectReturn(authorizationId: string): string {
  const connect = `${CONNECT_PREFIX}?authorization_id=${encodeURIComponent(authorizationId)}`
  return `/login?next=${encodeURIComponent(connect)}`
}
