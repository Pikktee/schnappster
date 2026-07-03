"""eBay.de: aktive Angebote als Kaufquelle.

Die Trefferliste enthält bereits alle Anzeigendaten (Titel, Preis, Zustand, Verkäufertyp,
Versand, Bild) — es werden **keine Detailseiten** geholt. Das spart pro Scrape ~25 Requests,
ist schnell und minimiert Block-Risiko/Proxy-Credits. Selektoren gegen die echte Seite
verifiziert: ``li.s-card`` / ``.s-card__title`` / ``.s-card__price`` ("EUR 189,99") /
``.s-card__subtitle`` ("Gebraucht | Privat") / ``.s-card__attribute-row`` (Versandzeile).

Fetch: erst direkter Session-Abruf (Startseite→Cookies→Suche, reicht von einer Wohn-IP), bei
Blockade Proxy-Fallback ohne Rendering (aus dem Rechenzentrum blockt eBay sonst — Preise
stehen im rohen HTML, Rendering ist unnötig).
"""

import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

# Geteilte, gegen die echte Seite verifizierte Parser aus dem Sold-Modul (gleiche Kartenstruktur).
from app.scraper.ebay_sold import _parse_price, _split_subtitle
from app.scraper.parser import ScrapedAdPreview

_BASE_URL = "https://www.ebay.de"
_HEADERS = {"Accept-Language": "de-DE,de;q=0.9"}
_PLACEHOLDER_PREFIXES = ("shop on ebay",)
# eBay-Sortierung: 10 = "Neu eingestellt" → neue Treffer landen zuverlässig auf Seite 1.
_SORT_NEWLY_LISTED = "10"

_ITEM_ID_RE = re.compile(r"/itm/(?:[^/?#]+/)?(\d{6,})")
_TAB_HINT_RE = re.compile(r"\s*Wird in neuem Fenster oder Tab geöffnet\s*$", re.IGNORECASE)
_NEW_OFFER_RE = re.compile(r"^Neues Angebot\s*", re.IGNORECASE)


def build_active_search_url(
    query: str, min_price: float | None = None, max_price: float | None = None
) -> str:
    """Baut die eBay-Such-URL für aktive Angebote (Preisfilter ``_udlo``/``_udhi``, neu zuerst)."""
    parts = [f"_nkw={quote_plus(query)}", "_sacat=0", f"_sop={_SORT_NEWLY_LISTED}"]
    if min_price is not None:
        parts.append(f"_udlo={int(min_price)}")
    if max_price is not None:
        parts.append(f"_udhi={int(max_price)}")
    return f"{_BASE_URL}/sch/i.html?{'&'.join(parts)}"


def is_usable(status: int, html: str) -> bool:
    """True, wenn die Antwort echte Suchergebnisse enthält (kein Block/keine Challenge)."""
    return status == 200 and ("s-card" in html or "srp-results" in html)


def _fetch_direct(url: str, timeout: int) -> tuple[int, str]:
    """Direkter Session-Abruf (Startseite→Cookies→Suche); ``(0, "")`` bei Netzwerkfehler."""
    from curl_cffi import requests as cffi_requests

    from app.scraper.httpclient import IMPERSONATE

    try:
        session = cffi_requests.Session(impersonate=IMPERSONATE)
        session.get(f"{_BASE_URL}/", timeout=timeout, headers=_HEADERS)
        response = session.get(url, timeout=timeout, headers=_HEADERS)
        return response.status_code, response.text
    except Exception:  # noqa: BLE001 — Netzwerkfehler als (0, "") signalisieren
        return 0, ""


def _fetch_via_proxy(url: str) -> tuple[int, str] | None:
    """Proxy-Abruf ohne Rendering (für Prod/Railway); None, wenn kein Proxy konfiguriert ist."""
    from app.scraper.httpclient import PROXY_CONFIGURED, fetch_page_with_status

    if not PROXY_CONFIGURED:
        return None
    return fetch_page_with_status(url, via_proxy=True, render=False)


def fetch_active_html(url: str, timeout: int = 30) -> tuple[int, str]:
    """Holt die eBay-Aktiv-Suchergebnisseite; direkt, bei Blockade über den Proxy.

    Gibt ``(status_code, html)`` der ersten brauchbaren bzw. letzten Stufe zurück.
    """
    status, html = _fetch_direct(url, timeout)
    if is_usable(status, html):
        return status, html
    proxied = _fetch_via_proxy(url)
    return proxied if proxied is not None else (status, html)


def _text(element, selector: str) -> str | None:
    found = element.select_one(selector)
    return found.get_text(" ", strip=True) if found else None


def _clean_title(card) -> str | None:
    """Titel ohne Screenreader-Hinweis ('Wird in neuem Fenster…') und ohne 'Neues Angebot'."""
    raw = _text(card, ".s-card__title")
    if not raw:
        return None
    return _NEW_OFFER_RE.sub("", _TAB_HINT_RE.sub("", raw)).strip()


def _extract_item(card) -> tuple[str | None, str | None]:
    """(item_id, bereinigte Item-URL) aus dem ersten /itm/-Link der Karte."""
    link = card.select_one("a[href*='/itm/']")
    href = link.get("href") if link else None
    if not href:
        return None, None
    match = _ITEM_ID_RE.search(href)
    if not match:
        return None, None
    item_id = match.group(1)
    return item_id, f"{_BASE_URL}/itm/{item_id}"


# eBay bettet die Vorschau-Größe in den Dateinamen ein (s-l140/s-l500 = Mini-Thumbnails).
# eBay bedient jede Standardgröße unter derselben URL, daher auf 800px hochsetzen → scharfe Karten.
_IMG_SIZE_RE = re.compile(r"s-l\d+")
_IMG_TARGET_SIZE = "s-l800"


def _upscale_image(url: str) -> str:
    return _IMG_SIZE_RE.sub(_IMG_TARGET_SIZE, url)


def _extract_image(card) -> str | None:
    img = card.select_one("img")
    if not img:
        return None
    src = img.get("src") or img.get("data-src")
    return _upscale_image(src) if src else None


def _extract_shipping(card) -> str | None:
    """Versandzeile aus den Attribut-Zeilen ('Gratis Lieferung', '+EUR 6,90 …')."""
    for row in card.select(".s-card__attribute-row"):
        text = row.get_text(" ", strip=True)
        low = text.lower()
        if "lieferung" in low or "versand" in low:
            return text
    return None


def parse_active_listings(html: str) -> list[ScrapedAdPreview]:
    """Parst aktive Angebote aus dem Suchergebnis-HTML zu angereicherten Previews.

    Überspringt Platzhalterkarten ('Shop on eBay') und Karten ohne Item-Link.
    """
    soup = BeautifulSoup(html, "lxml")
    previews: list[ScrapedAdPreview] = []
    for card in soup.select("li.s-card"):
        title = _clean_title(card)
        if not title or title.lower().startswith(_PLACEHOLDER_PREFIXES):
            continue
        item_id, url = _extract_item(card)
        if not item_id or not url:
            continue
        price_text = _text(card, ".s-card__price")
        price, _ = _parse_price(price_text)
        condition, seller_type = _split_subtitle(_text(card, ".s-card__subtitle"))
        previews.append(
            ScrapedAdPreview(
                external_id=item_id,
                title=title,
                url=url,
                price=price,
                price_raw=price_text,
                image_url=_extract_image(card),
                condition=condition,
                seller_type=seller_type,
                shipping_cost=_extract_shipping(card),
            )
        )
    return previews
