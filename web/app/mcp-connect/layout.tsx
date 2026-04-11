import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "MCP & Cursor | Schnappster",
  description:
    "Hilfe zum Verbinden von Cursor oder anderen MCP-Clients mit dem Schnappster Remote-MCP.",
}

export default function McpConnectLayout({ children }: { children: React.ReactNode }) {
  return children
}
