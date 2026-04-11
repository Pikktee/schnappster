"""MCP App (ext-apps): interaktive Detailansicht für ein Schnäppchen / eine Anzeige."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import Icon, TextContent

from schnappster_mcp.api_client import SchnappsterApiClient

# Gleiche CDN-Zeile wie im offiziellen ext-apps qr-server-Beispiel (stabile 0.4.x).
_EXT_APPS_APP_WITH_DEPS = (
    "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps"
)


class BargainDetailMcpApp:
    """Registrierung der UI-Ressource und des zugehörigen Tools für die Schnappster-MCP-App."""

    VIEW_URI: str = "ui://schnappster/bargain-detail.html"
    MIME_TYPE: str = "text/html;profile=mcp-app"

    @classmethod
    def tool_meta(cls) -> dict[str, Any]:
        uri = cls.VIEW_URI
        return {"ui": {"resourceUri": uri}, "ui/resourceUri": uri}

    @classmethod
    def resource_meta(cls) -> dict[str, Any]:
        return {"ui": {"csp": {"resourceDomains": ["https://unpkg.com"]}}}

    @classmethod
    def embedded_view_html(cls) -> str:
        return _VIEW_HTML_TEMPLATE.replace("__EXT_APPS_IMPORT__", _EXT_APPS_APP_WITH_DEPS)


def register_bargain_detail_mcp_app(
    mcp: FastMCP,
    *,
    get_api_client: Callable[[], SchnappsterApiClient],
    run_api: Callable[[Awaitable[Any]], Awaitable[Any]],
    tool_icons: list[Icon],
) -> None:
    """Registriert Tool + HTML-Ressource auf dem bestehenden FastMCP-Server."""

    app = BargainDetailMcpApp

    @mcp.tool(
        icons=tool_icons,
        meta=app.tool_meta(),
        title="Schnäppchen-Details",
    )
    async def show_bargain_detail(ad_id: int) -> list[TextContent]:
        """Zeigt Details zu einer analysierten Anzeige in der MCP-App-Ansicht an.

        Parameter ``ad_id`` ist die interne Schnappster-Anzeigen-ID (z. B. aus
        ``list_recent_bargains``).
        """
        client = get_api_client()
        payload = await run_api(client.request("GET", f"/ads/{ad_id}"))
        text = json.dumps(payload, ensure_ascii=False, default=str)
        return [TextContent(type="text", text=text)]

    @mcp.resource(
        app.VIEW_URI,
        mime_type=app.MIME_TYPE,
        meta=app.resource_meta(),
    )
    def bargain_detail_view() -> str:
        """Gebündelte MCP-App (HTML+JS) für die Detailansicht."""
        return app.embedded_view_html()


_VIEW_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Schnäppchen</title>
  <style>
    :root {
      color-scheme: light dark;
      font-family: system-ui, sans-serif;
      line-height: 1.45;
    }
    body {
      margin: 0;
      padding: 12px;
      background: transparent;
    }
    #root { max-width: 42rem; margin: 0 auto; }
    h1 { font-size: 1.15rem; margin: 0 0 8px; font-weight: 650; }
    .muted { opacity: 0.75; font-size: 0.85rem; }
    .score {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-weight: 600;
      font-size: 0.85rem;
      background: color-mix(in oklab, CanvasText 12%, Canvas);
    }
    .section { margin-top: 14px; }
    .section h2 {
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin: 0 0 6px;
      opacity: 0.7;
    }
    .box {
      padding: 10px 12px;
      border-radius: 10px;
      background: color-mix(in oklab, CanvasText 6%, Canvas);
    }
    a.link { color: inherit; word-break: break-all; }
    .empty { opacity: 0.7; font-size: 0.9rem; }
  </style>
</head>
<body>
  <div id="root">
    <p class="empty">Lade Anzeige…</p>
  </div>
  <script type="module">
    import { App } from "__EXT_APPS_IMPORT__";

    const root = document.getElementById("root");

    function el(tag, props, children) {
      const n = document.createElement(tag);
      if (props) Object.assign(n, props);
      (children || []).forEach((c) => {
        if (c != null) n.appendChild(c);
      });
      return n;
    }

    function text(t) {
      return document.createTextNode(t == null ? "" : String(t));
    }

    function fmtPrice(p) {
      if (p == null || p === "") return "—";
      return new Intl.NumberFormat("de-DE", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 0,
      }).format(Number(p));
    }

    function render(data) {
      root.innerHTML = "";
      if (!data || typeof data !== "object") {
        root.appendChild(el("p", { className: "empty" }, [text("Keine Daten.")]));
        return;
      }

      const title = data.title || "Anzeige";
      const score =
        data.bargain_score != null ? String(data.bargain_score) : "—";

      const head = el("div", null, [
        el("h1", null, [text(title)]),
        el("p", { className: "muted" }, [
          text("Score: "),
          el("span", { className: "score" }, [text(score)]),
          text(
            data.city || data.postal_code
              ? " · " + [data.postal_code, data.city].filter(Boolean).join(" ")
              : ""
          ),
        ]),
      ]);
      root.appendChild(head);

      if (data.url) {
        root.appendChild(
          el("p", { className: "section" }, [
            el("a", {
              className: "link",
              href: data.url,
              target: "_blank",
              rel: "noopener noreferrer",
            }, [text("Auf Kleinanzeigen öffnen")]),
          ])
        );
      }

      const addSection = (label, bodyText) => {
        if (!bodyText) return;
        root.appendChild(
          el("div", { className: "section" }, [
            el("h2", null, [text(label)]),
            el("div", { className: "box" }, [text(bodyText)]),
          ])
        );
      };

      addSection("Kurzfassung", data.ai_summary);
      addSection("Begründung", data.ai_reasoning);

      const sellerBits = [
        data.seller_name && "Verkäufer: " + data.seller_name,
        data.seller_type && "Typ: " + data.seller_type,
        data.price != null && "Preis: " + fmtPrice(data.price),
      ].filter(Boolean);
      if (sellerBits.length) {
        root.appendChild(
          el("div", { className: "section" }, [
            el("h2", null, [text("Angebot")]),
            el("div", { className: "box" }, [
              text(sellerBits.join(" · ")),
            ]),
          ])
        );
      }

      if (data.description) {
        addSection("Beschreibung", data.description);
      }
    }

    const app = new App({ name: "Schnappster Schnäppchen", version: "1.0.0" });

    app.ontoolresult = ({ content }) => {
      const block = content?.find((c) => c.type === "text");
      if (!block?.text) {
        root.innerHTML = "";
        root.appendChild(
          el("p", { className: "empty" }, [text("Keine Textdaten im Tool-Ergebnis.")])
        );
        return;
      }
      try {
        render(JSON.parse(block.text));
      } catch (e) {
        root.innerHTML = "";
        root.appendChild(
          el("p", { className: "empty" }, [text("JSON konnte nicht gelesen werden.")])
        );
      }
    };

    await app.connect();
  </script>
</body>
</html>
"""
