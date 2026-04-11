"""MCP Apps (ext-apps): Detail, Schnäppchen-Liste und Suchaufträge."""

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
    """Detailansicht für ein einzelnes Schnäppchen."""

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
        return _DETAIL_VIEW_HTML_TEMPLATE.replace("__EXT_APPS_IMPORT__", _EXT_APPS_APP_WITH_DEPS)


class RecentBargainsMcpApp:
    """Tabellarische Übersicht für ``list_recent_bargains``."""

    VIEW_URI: str = "ui://schnappster/recent-bargains.html"
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
        return _RECENT_BARGAINS_VIEW_HTML_TEMPLATE.replace(
            "__EXT_APPS_IMPORT__", _EXT_APPS_APP_WITH_DEPS
        )


class AdSearchesMcpApp:
    """Verwaltung gespeicherter Suchaufträge via ``list_ad_searches``."""

    VIEW_URI: str = "ui://schnappster/ad-searches.html"
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
        return _AD_SEARCHES_VIEW_HTML_TEMPLATE.replace(
            "__EXT_APPS_IMPORT__", _EXT_APPS_APP_WITH_DEPS
        )


def recent_bargains_tool_meta() -> dict[str, Any]:
    """Meta-Konfiguration für ``list_recent_bargains``."""
    return RecentBargainsMcpApp.tool_meta()


def ad_searches_tool_meta() -> dict[str, Any]:
    """Meta-Konfiguration für ``list_ad_searches``."""
    return AdSearchesMcpApp.tool_meta()


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

    recent_bargains = RecentBargainsMcpApp

    @mcp.resource(
        recent_bargains.VIEW_URI,
        mime_type=recent_bargains.MIME_TYPE,
        meta=recent_bargains.resource_meta(),
    )
    def recent_bargains_view() -> str:
        """Gebündelte MCP-App (HTML+JS) für list_recent_bargains."""
        return recent_bargains.embedded_view_html()

    ad_searches = AdSearchesMcpApp

    @mcp.resource(
        ad_searches.VIEW_URI,
        mime_type=ad_searches.MIME_TYPE,
        meta=ad_searches.resource_meta(),
    )
    def ad_searches_view() -> str:
        """Gebündelte MCP-App (HTML+JS) für list_ad_searches."""
        return ad_searches.embedded_view_html()


_DETAIL_VIEW_HTML_TEMPLATE = """<!DOCTYPE html>
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
    <p class="empty">Verbinde mit MCP-App…</p>
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

    function renderStatus(message) {
      root.innerHTML = "";
      root.appendChild(el("p", { className: "empty" }, [text(message)]));
    }

    function renderError(message) {
      root.innerHTML = "";
      root.appendChild(el("h1", null, [text("Fehler")]));
      root.appendChild(
        el("div", { className: "box section" }, [text(message || "Unbekannter Fehler.")])
      );
    }

    function stringifyError(err) {
      if (!err) return "Unbekannter Fehler.";
      if (typeof err === "string") return err;
      if (err.message) return String(err.message);
      try {
        return JSON.stringify(err);
      } catch (_e) {
        return String(err);
      }
    }

    const app = new App({ name: "Schnappster Schnäppchen", version: "1.0.0" });

    app.ontoolresult = ({ content }) => {
      const block = content?.find((c) => c.type === "text");
      if (!block?.text) {
        renderError("Keine Textdaten im Tool-Ergebnis.");
        return;
      }
      try {
        render(JSON.parse(block.text));
      } catch (e) {
        renderError("JSON konnte nicht gelesen werden: " + stringifyError(e));
      }
    };

    try {
      renderStatus("Lade Anzeige…");
      await app.connect();
    } catch (e) {
      renderError("Verbindung fehlgeschlagen: " + stringifyError(e));
    }
  </script>
</body>
</html>
"""

_RECENT_BARGAINS_VIEW_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Schnappster Schnäppchen</title>
  <style>
    :root {
      color-scheme: light dark;
      font-family: system-ui, sans-serif;
      line-height: 1.45;
    }
    body { margin: 0; padding: 12px; background: transparent; }
    #root { max-width: 64rem; margin: 0 auto; }
    .muted { opacity: 0.72; font-size: 0.9rem; }
    .toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
      flex-wrap: wrap;
    }
    .toolbar .controls {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    select {
      border-radius: 8px;
      border: 1px solid color-mix(in oklab, CanvasText 20%, Canvas);
      background: color-mix(in oklab, CanvasText 4%, Canvas);
      color: inherit;
      padding: 5px 7px;
      font: inherit;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: color-mix(in oklab, CanvasText 3%, Canvas);
      border-radius: 10px;
      overflow: hidden;
    }
    th, td {
      text-align: left;
      padding: 9px 10px;
      border-bottom: 1px solid color-mix(in oklab, CanvasText 8%, Canvas);
      vertical-align: top;
    }
    tr:last-child td { border-bottom: 0; }
    tr:hover { background: color-mix(in oklab, CanvasText 7%, Canvas); }
    button {
      border: 1px solid color-mix(in oklab, CanvasText 20%, Canvas);
      background: color-mix(in oklab, CanvasText 5%, Canvas);
      color: inherit;
      border-radius: 8px;
      padding: 4px 8px;
      cursor: pointer;
      font: inherit;
    }
    button:hover { background: color-mix(in oklab, CanvasText 10%, Canvas); }
    .score {
      display: inline-block;
      min-width: 2.2rem;
      text-align: center;
      padding: 2px 8px;
      border-radius: 999px;
      font-weight: 600;
      font-size: 0.84rem;
      background: color-mix(in oklab, CanvasText 12%, Canvas);
    }
    .score-high {
      background: color-mix(in oklab, #24a148 28%, Canvas);
      color: color-mix(in oklab, #24a148 80%, CanvasText);
    }
    .score-medium {
      background: color-mix(in oklab, #f1c21b 30%, Canvas);
      color: color-mix(in oklab, #8b6a00 65%, CanvasText);
    }
    .score-low {
      background: color-mix(in oklab, #da1e28 24%, Canvas);
      color: color-mix(in oklab, #a2191f 70%, CanvasText);
    }
    .status {
      margin: 0 0 8px;
      font-size: 0.9rem;
      opacity: 0.8;
    }
    .error-box {
      margin-top: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid color-mix(in oklab, #da1e28 30%, Canvas);
      background: color-mix(in oklab, #da1e28 10%, Canvas);
      color: inherit;
    }
    a.link {
      color: inherit;
      text-decoration: none;
      border-bottom: 1px dashed color-mix(in oklab, CanvasText 32%, Canvas);
    }
    .empty { opacity: 0.72; }
  </style>
</head>
<body>
  <div id="root">
    <p class="status">Verbinde mit MCP-App…</p>
  </div>
  <script type="module">
    import { App } from "__EXT_APPS_IMPORT__";

    const root = document.getElementById("root");
    const state = {
      items: [],
      total: 0,
      sortBy: "score",
      notice: "",
      error: "",
    };

    function text(t) {
      return document.createTextNode(t == null ? "" : String(t));
    }

    function el(tag, props, children) {
      const n = document.createElement(tag);
      if (props) Object.assign(n, props);
      (children || []).forEach((c) => {
        if (c != null) n.appendChild(c);
      });
      return n;
    }

    function fmtPrice(p) {
      if (p == null || p === "") return "—";
      return new Intl.NumberFormat("de-DE", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 0,
      }).format(Number(p));
    }

    function fmtDate(value) {
      if (!value) return "—";
      try {
        return new Intl.DateTimeFormat("de-DE", {
          dateStyle: "short",
          timeStyle: "short",
        }).format(new Date(value));
      } catch (_e) {
        return String(value);
      }
    }

    function scoreClass(score) {
      if (score == null || Number.isNaN(Number(score))) return "";
      if (score >= 7) return "score-high";
      if (score >= 4) return "score-medium";
      return "score-low";
    }

    function sortedItems() {
      const items = [...state.items];
      if (state.sortBy === "price") {
        return items.sort(
          (a, b) => (a.price ?? Number.MAX_SAFE_INTEGER) - (b.price ?? Number.MAX_SAFE_INTEGER)
        );
      }
      if (state.sortBy === "date") {
        return items.sort(
          (a, b) =>
            new Date(b.first_seen_at || 0).getTime() - new Date(a.first_seen_at || 0).getTime()
        );
      }
      return items.sort((a, b) => (b.bargain_score ?? -1) - (a.bargain_score ?? -1));
    }

    function stringifyError(err) {
      if (!err) return "Unbekannter Fehler.";
      if (typeof err === "string") return err;
      if (err.message) return String(err.message);
      try {
        return JSON.stringify(err);
      } catch (_e) {
        return String(err);
      }
    }

    function parseToolTextContent(content) {
      const block = content?.find((c) => c.type === "text");
      if (!block?.text) throw new Error("Keine Textdaten im Tool-Ergebnis.");
      return JSON.parse(block.text);
    }

    async function callServerToolOrThrow(name, args) {
      if (typeof app.callServerTool !== "function") {
        throw new Error("Direkte Server-Tool-Calls werden vom Host nicht unterstützt.");
      }
      return app.callServerTool({ name, arguments: args });
    }

    function render() {
      root.innerHTML = "";

      const title = el("h1", null, [text("Schnäppchen-Liste")]);
      const subtitle = el(
        "p",
        { className: "muted" },
        [text("Interaktive Ansicht für list_recent_bargains mit Direktaufruf der Detailansicht.")]
      );
      root.appendChild(title);
      root.appendChild(subtitle);

      const sortSelect = el("select", null, [
        el("option", { value: "score" }, [text("Sortierung: Score")]),
        el("option", { value: "price" }, [text("Sortierung: Preis")]),
        el("option", { value: "date" }, [text("Sortierung: Datum")]),
      ]);
      sortSelect.value = state.sortBy;
      sortSelect.addEventListener("change", () => {
        state.sortBy = sortSelect.value;
        render();
      });

      const controls = el("div", { className: "controls" }, [sortSelect]);
      const top = el("div", { className: "toolbar" }, [
        el("strong", null, [text("Treffer: " + state.items.length + " von " + state.total)]),
        controls,
      ]);
      root.appendChild(top);

      if (state.notice) {
        root.appendChild(el("p", { className: "status" }, [text(state.notice)]));
      }
      if (state.error) {
        root.appendChild(el("div", { className: "error-box" }, [text(state.error)]));
      }

      if (!state.items.length) {
        root.appendChild(
          el("p", { className: "empty" }, [text("Keine Schnäppchen in diesem Ergebnis.")])
        );
        return;
      }

      const table = el("table", null, [
        el("thead", null, [
          el("tr", null, [
            el("th", null, [text("Score")]),
            el("th", null, [text("Titel")]),
            el("th", null, [text("Preis")]),
            el("th", null, [text("Datum")]),
            el("th", null, [text("Aktion")]),
          ]),
        ]),
        el("tbody", null, []),
      ]);
      const body = table.querySelector("tbody");

      for (const item of sortedItems()) {
        const score = item.bargain_score == null ? "—" : String(item.bargain_score);
        const detailButton = el("button", { type: "button" }, [text("Details")]);
        detailButton.addEventListener("click", async () => {
          state.notice = "Lade Detailansicht…";
          state.error = "";
          render();
          try {
            await callServerToolOrThrow("show_bargain_detail", { ad_id: item.id });
            state.notice = "Detailansicht wurde angefordert.";
            state.error = "";
          } catch (err) {
            state.notice = "";
            state.error = "Detailansicht fehlgeschlagen: " + stringifyError(err);
          }
          render();
        });

        const row = el("tr", null, [
          el("td", null, [
            el("span", { className: "score " + scoreClass(item.bargain_score) }, [text(score)]),
          ]),
          el("td", null, [
            item.url
              ? el(
                  "a",
                  {
                    href: item.url,
                    target: "_blank",
                    rel: "noopener noreferrer",
                    className: "link",
                  },
                  [text(item.title || "Anzeige")]
                )
              : text(item.title || "Anzeige"),
          ]),
          el("td", null, [text(fmtPrice(item.price))]),
          el("td", null, [text(fmtDate(item.first_seen_at))]),
          el("td", null, [detailButton]),
        ]);
        body.appendChild(row);
      }

      root.appendChild(table);
    }

    const app = new App({ name: "Schnappster Bargains", version: "1.0.0" });

    app.ontoolresult = ({ content }) => {
      try {
        const payload = parseToolTextContent(content);
        const items = Array.isArray(payload?.items) ? payload.items : [];
        state.items = items;
        state.total = Number(payload?.total ?? items.length);
        state.notice = "";
        state.error = "";
        render();
      } catch (err) {
        state.notice = "";
        state.error = "Antwort konnte nicht gelesen werden: " + stringifyError(err);
        render();
      }
    };

    try {
      await app.connect();
      state.notice = "Warte auf Tool-Daten…";
      state.error = "";
      render();
    } catch (err) {
      state.notice = "";
      state.error = "Verbindung fehlgeschlagen: " + stringifyError(err);
      render();
    }
  </script>
</body>
</html>
"""

_AD_SEARCHES_VIEW_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Schnappster Suchaufträge</title>
  <style>
    :root {
      color-scheme: light dark;
      font-family: system-ui, sans-serif;
      line-height: 1.45;
    }
    body { margin: 0; padding: 12px; background: transparent; }
    #root { max-width: 68rem; margin: 0 auto; }
    .toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }
    .muted { opacity: 0.74; font-size: 0.9rem; }
    .status {
      margin: 0 0 8px;
      font-size: 0.9rem;
      opacity: 0.82;
    }
    .error-box {
      margin-bottom: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid color-mix(in oklab, #da1e28 30%, Canvas);
      background: color-mix(in oklab, #da1e28 10%, Canvas);
      color: inherit;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: color-mix(in oklab, CanvasText 3%, Canvas);
      border-radius: 10px;
      overflow: hidden;
    }
    th, td {
      text-align: left;
      padding: 9px 10px;
      border-bottom: 1px solid color-mix(in oklab, CanvasText 8%, Canvas);
      vertical-align: top;
    }
    tr:last-child td { border-bottom: 0; }
    tr:hover { background: color-mix(in oklab, CanvasText 6%, Canvas); }
    .url {
      word-break: break-all;
      opacity: 0.95;
    }
    button {
      border: 1px solid color-mix(in oklab, CanvasText 20%, Canvas);
      background: color-mix(in oklab, CanvasText 5%, Canvas);
      color: inherit;
      border-radius: 8px;
      padding: 4px 8px;
      cursor: pointer;
      font: inherit;
    }
    button:hover { background: color-mix(in oklab, CanvasText 10%, Canvas); }
    .toggle {
      display: inline-flex;
      gap: 6px;
      align-items: center;
      cursor: pointer;
      user-select: none;
    }
    .toggle input {
      width: 1.05rem;
      height: 1.05rem;
      margin: 0;
    }
    .pill {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 600;
      background: color-mix(in oklab, CanvasText 12%, Canvas);
    }
    .pill.active {
      background: color-mix(in oklab, #24a148 28%, Canvas);
      color: color-mix(in oklab, #24a148 80%, CanvasText);
    }
    .pill.inactive {
      background: color-mix(in oklab, #8d8d8d 25%, Canvas);
    }
  </style>
</head>
<body>
  <div id="root">
    <p class="status">Verbinde mit MCP-App…</p>
  </div>
  <script type="module">
    import { App } from "__EXT_APPS_IMPORT__";

    const root = document.getElementById("root");
    const state = {
      searches: [],
      notice: "",
      error: "",
      busyIds: new Set(),
    };

    function text(t) {
      return document.createTextNode(t == null ? "" : String(t));
    }

    function el(tag, props, children) {
      const n = document.createElement(tag);
      if (props) Object.assign(n, props);
      (children || []).forEach((c) => {
        if (c != null) n.appendChild(c);
      });
      return n;
    }

    function fmtDate(value) {
      if (!value) return "—";
      try {
        return new Intl.DateTimeFormat("de-DE", {
          dateStyle: "short",
          timeStyle: "short",
        }).format(new Date(value));
      } catch (_e) {
        return String(value);
      }
    }

    function stringifyError(err) {
      if (!err) return "Unbekannter Fehler.";
      if (typeof err === "string") return err;
      if (err.message) return String(err.message);
      try {
        return JSON.stringify(err);
      } catch (_e) {
        return String(err);
      }
    }

    function parseToolResult(toolResult) {
      const content = Array.isArray(toolResult?.content) ? toolResult.content : [];
      const block = content.find((c) => c.type === "text");
      if (!block?.text) {
        throw new Error("Keine Textdaten im Tool-Ergebnis.");
      }
      return JSON.parse(block.text);
    }

    async function callServerToolOrThrow(name, args) {
      if (typeof app.callServerTool !== "function") {
        throw new Error("Direkte Server-Tool-Calls werden vom Host nicht unterstützt.");
      }
      return app.callServerTool({ name, arguments: args });
    }

    async function refreshSearches() {
      state.notice = "Aktualisiere Suchaufträge…";
      state.error = "";
      render();
      try {
        const result = await callServerToolOrThrow("list_ad_searches", {});
        const payload = parseToolResult(result);
        state.searches = Array.isArray(payload) ? payload : [];
        state.notice = "Aktualisiert.";
        state.error = "";
      } catch (err) {
        state.notice = "";
        state.error = "Aktualisierung fehlgeschlagen: " + stringifyError(err);
      }
      render();
    }

    async function toggleSearch(item, nextValue) {
      state.busyIds.add(item.id);
      state.notice = "Speichere Status…";
      state.error = "";
      render();
      try {
        await callServerToolOrThrow("update_ad_search", {
          adsearch_id: item.id,
          is_active: nextValue,
        });
        item.is_active = nextValue;
        state.notice = "Status gespeichert.";
        state.error = "";
      } catch (err) {
        state.notice = "";
        state.error = "Toggle fehlgeschlagen: " + stringifyError(err);
      } finally {
        state.busyIds.delete(item.id);
        render();
      }
    }

    function render() {
      root.innerHTML = "";
      root.appendChild(el("h1", null, [text("Suchauftrags-Manager")]));
      root.appendChild(
        el("p", { className: "muted" }, [
          text("Verwaltung der gespeicherten Suchaufträge inklusive Aktiv/Inaktiv-Toggle."),
        ])
      );

      const refreshBtn = el("button", { type: "button" }, [text("Neu laden")]);
      refreshBtn.addEventListener("click", refreshSearches);

      root.appendChild(
        el("div", { className: "toolbar" }, [
          el("strong", null, [text("Suchaufträge: " + state.searches.length)]),
          refreshBtn,
        ])
      );

      if (state.notice) {
        root.appendChild(el("p", { className: "status" }, [text(state.notice)]));
      }
      if (state.error) {
        root.appendChild(el("div", { className: "error-box" }, [text(state.error)]));
      }

      if (!state.searches.length) {
        root.appendChild(el("p", { className: "muted" }, [text("Keine Suchaufträge vorhanden.")]));
        return;
      }

      const table = el("table", null, [
        el("thead", null, [
          el("tr", null, [
            el("th", null, [text("Name")]),
            el("th", null, [text("URL")]),
            el("th", null, [text("Status")]),
            el("th", null, [text("Zuletzt gescraped")]),
            el("th", null, [text("Aktivieren/Deaktivieren")]),
          ]),
        ]),
        el("tbody", null, []),
      ]);
      const body = table.querySelector("tbody");

      for (const item of state.searches) {
        const busy = state.busyIds.has(item.id);
        const checkbox = el("input", {
          type: "checkbox",
          checked: !!item.is_active,
          disabled: busy,
        });
        checkbox.addEventListener("change", () => {
          toggleSearch(item, !!checkbox.checked);
        });
        const toggleLabel = el("label", { className: "toggle" }, [
          checkbox,
          text(busy ? "Speichert…" : item.is_active ? "Aktiv" : "Inaktiv"),
        ]);

        const row = el("tr", null, [
          el("td", null, [text(item.name || "Unbenannter Suchauftrag")]),
          el("td", { className: "url" }, [text(item.url || "—")]),
          el("td", null, [
            el("span", { className: "pill " + (item.is_active ? "active" : "inactive") }, [
              text(item.is_active ? "Aktiv" : "Inaktiv"),
            ]),
          ]),
          el("td", null, [text(fmtDate(item.last_scraped_at))]),
          el("td", null, [toggleLabel]),
        ]);
        body.appendChild(row);
      }

      root.appendChild(table);
    }

    const app = new App({ name: "Schnappster AdSearches", version: "1.0.0" });

    app.ontoolresult = ({ content }) => {
      try {
        const block = content?.find((c) => c.type === "text");
        if (!block?.text) throw new Error("Keine Textdaten im Tool-Ergebnis.");
        const payload = JSON.parse(block.text);
        state.searches = Array.isArray(payload) ? payload : [];
        state.notice = "";
        state.error = "";
      } catch (err) {
        state.notice = "";
        state.error = "Antwort konnte nicht gelesen werden: " + stringifyError(err);
      }
      render();
    };

    try {
      await app.connect();
      state.notice = "Warte auf Tool-Daten…";
      state.error = "";
      render();
    } catch (err) {
      state.notice = "";
      state.error = "Verbindung fehlgeschlagen: " + stringifyError(err);
      render();
    }
  </script>
</body>
</html>
"""
