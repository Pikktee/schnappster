"""eBay.de: verkaufte/beendete Angebote als Marktwert-Referenz (Sold Comps).

Direkte Requests blockt eBay (403). Mit einer Session (erst Startseite → Cookies →
dann Suche) liefert eBay die Ergebnisse. Selektoren gegen die echte Seite verifiziert:
``li.s-card`` / ``.s-card__title`` / ``.s-card__price`` ("EUR 609,00") /
``.s-card__caption`` ("Verkauft 1. Jul 2026") / ``.s-card__subtitle`` ("Gebraucht | Privat").

Hinweis: Aus einem Rechenzentrum (Railway) blockt eBay vermutlich trotzdem — dann wäre ein
Proxy/Unblocker nötig (Folge-Scheibe). Von einer Wohn-IP funktioniert der Session-Ansatz.
"""

import os
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

_BASE_URL = "https://www.ebay.de"
_IMPERSONATE = os.environ.get("SCRAPE_IMPERSONATE", "chrome131")
_HEADERS = {"Accept-Language": "de-DE,de;q=0.9"}
_PLACEHOLDER_PREFIXES = ("shop on ebay",)

_PRICE_RE = re.compile(r"(\d[\d.\s]*,\d{2})")
_SOLD_DATE_RE = re.compile(r"(?:Verkauft|Beendet)\s+(.+)", re.IGNORECASE)
_NEW_OFFER_RE = re.compile(r"^Neues Angebot\s*", re.IGNORECASE)


@dataclass
class SoldListing:
    """Ein einzelnes verkauftes eBay-Angebot."""

    title: str
    price: float | None
    currency: str | None
    sold_date: str | None
    condition: str | None
    seller_type: str | None


def build_sold_search_url(query: str) -> str:
    """Baut die eBay-Such-URL für verkaufte/beendete Angebote."""
    return f"{_BASE_URL}/sch/i.html?_nkw={quote_plus(query)}&LH_Sold=1&LH_Complete=1&_sacat=0"


def fetch_sold_html(query: str, timeout: int = 30) -> tuple[int, str]:
    """Holt die Sold-Suchergebnisseite (erst Startseite für Cookies, dann Suche).

    Gibt ``(status_code, html)`` zurück; ``(0, "")`` bei Netzwerkfehler.
    """
    try:
        session = cffi_requests.Session(impersonate=_IMPERSONATE)
        session.get(f"{_BASE_URL}/", timeout=timeout, headers=_HEADERS)
        response = session.get(build_sold_search_url(query), timeout=timeout, headers=_HEADERS)
        return response.status_code, response.text
    except Exception:  # noqa: BLE001 — Netzwerkfehler als (0, "") signalisieren
        return 0, ""


def _text(element, selector: str) -> str | None:
    found = element.select_one(selector)
    return found.get_text(" ", strip=True) if found else None


def _parse_price(text: str | None) -> tuple[float | None, str | None]:
    """Parst 'EUR 609,00' / '609,00 €' → (609.0, 'EUR'); (None, currency) wenn nicht parsebar."""
    if not text:
        return None, None
    currency = "EUR" if ("EUR" in text or "€" in text) else None
    match = _PRICE_RE.search(text)
    if not match:
        return None, currency
    raw = match.group(1).replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(raw), currency
    except ValueError:
        return None, currency


def _split_subtitle(subtitle: str | None) -> tuple[str | None, str | None]:
    """'Gebraucht | Privat' → ('Gebraucht', 'Privat')."""
    if not subtitle:
        return None, None
    parts = [p.strip() for p in subtitle.split("|")]
    return (parts[0] or None), (parts[1] if len(parts) > 1 else None)


def _extract_sold_date(caption: str | None) -> str | None:
    if not caption:
        return None
    match = _SOLD_DATE_RE.search(caption)
    return match.group(1).strip() if match else None


def parse_sold_listings(html: str) -> list[SoldListing]:
    """Parst verkaufte Angebote aus dem Sold-Suchergebnis-HTML (ohne Platzhalter-Item)."""
    soup = BeautifulSoup(html, "lxml")
    listings: list[SoldListing] = []
    for card in soup.select("li.s-card"):
        raw_title = _text(card, ".s-card__title")
        if not raw_title:
            continue
        title = _NEW_OFFER_RE.sub("", raw_title).strip()
        if title.lower().startswith(_PLACEHOLDER_PREFIXES):
            continue
        price, currency = _parse_price(_text(card, ".s-card__price"))
        condition, seller_type = _split_subtitle(_text(card, ".s-card__subtitle"))
        listings.append(
            SoldListing(
                title=title,
                price=price,
                currency=currency,
                sold_date=_extract_sold_date(_text(card, ".s-card__caption")),
                condition=condition,
                seller_type=seller_type,
            )
        )
    return listings
