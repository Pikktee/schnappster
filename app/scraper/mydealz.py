"""MyDealz.de: Community-Deals zu einem Suchbegriff (für den Deal-Alarm).

Kein Kaufziel — MyDealz aggregiert Deals und verlinkt zu Händlern; die **Community-Temperatur
(Grad)** ist das Schnäppchen-Signal (statt KI-Bewertung). Die Deal-Daten stecken in
``data-vue3``-Attributen (Vue-SSR-Hydration): ``{"name":"ThreadMainListItemNormalizer",
"props":{"thread":{threadId,title,temperature,price,merchant,...}}}`` — gegen die echte Seite
verifiziert. Fetch: direkt (MyDealz blockt Wohn-IPs nicht), bei Blockade Proxy-Fallback ohne
Rendering (aus dem Rechenzentrum ggf. nötig).
"""

import json
from dataclasses import dataclass
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

_BASE_URL = "https://www.mydealz.de"
_HEADERS = {"Accept-Language": "de-DE,de;q=0.9"}

# MyDealz-Bild-CDN. URL-Format live verifiziert: .../{path}/{name}/re/{größe}/qt/{q}/{name}.jpg
# liefert ein content-negotiiertes Bild (AVIF/WebP/JPEG). WICHTIG: Das CDN erlaubt nur bestimmte
# quadratische Größen-Presets (verifiziert 200 OK: 150/200/300/320/768/1024; 404 bei 256/400/600/…)
# — daher KEINE beliebige Größe raten. 768x768 = retina-scharf auf Deal-Karten (~90 KB AVIF).
_IMAGE_CDN = "https://static.mydealz.de"
_IMAGE_SIZE = "768x768"
_IMAGE_QUALITY = 60


@dataclass
class MydealzDeal:
    """Ein MyDealz-Deal aus der Suchergebnisliste."""

    external_id: str
    title: str
    url: str
    temperature: float | None
    price: float | None
    next_best_price: float | None
    merchant: str | None
    published_at: int | None
    image_url: str | None = None


def build_search_url(query: str) -> str:
    """Baut die MyDealz-Suche zu einem Suchbegriff."""
    return f"{_BASE_URL}/search?q={quote_plus(query)}"


def is_usable(status: int, html: str) -> bool:
    """True, wenn die Antwort echte Deal-Daten enthält (kein Block/keine Challenge)."""
    return status == 200 and "data-vue3" in html


def _fetch_direct(url: str, timeout: int) -> tuple[int, str]:
    """Direkter Abruf via curl-cffi; ``(0, "")`` bei Netzwerkfehler."""
    from curl_cffi import requests as cffi_requests

    from app.scraper.httpclient import IMPERSONATE

    try:
        session = cffi_requests.Session(impersonate=IMPERSONATE)
        response = session.get(url, timeout=timeout, headers=_HEADERS)
        return response.status_code, response.text
    except Exception:  # noqa: BLE001 — Netzwerkfehler als (0, "") signalisieren
        return 0, ""


def _fetch_via_proxy(url: str) -> tuple[int, str] | None:
    """Proxy-Abruf ohne Rendering (für Prod/Railway); None ohne konfigurierten Proxy."""
    from app.scraper.httpclient import PROXY_CONFIGURED, fetch_page_with_status

    if not PROXY_CONFIGURED:
        return None
    return fetch_page_with_status(url, via_proxy=True, render=False)


def fetch_deals_html(url: str, timeout: int = 30) -> tuple[int, str]:
    """Holt die MyDealz-Suchergebnisseite; direkt, bei Blockade über den Proxy."""
    status, html = _fetch_direct(url, timeout)
    if is_usable(status, html):
        return status, html
    proxied = _fetch_via_proxy(url)
    return proxied if proxied is not None else (status, html)


def _thread_url(thread: dict) -> str:
    """Kanonische Deal-URL aus titleSlug + threadId (Fallback: shareableLink)."""
    slug = thread.get("titleSlug")
    tid = thread.get("threadId")
    if slug and tid:
        return f"{_BASE_URL}/deals/{slug}-{tid}"
    return thread.get("shareableLink") or f"{_BASE_URL}/deals/{tid}"


def _as_float(value: object) -> float | None:
    """Wandelt Zahlwerte robust in float; 0/None → None (MyDealz nutzt 0 für 'kein Preis')."""
    if isinstance(value, int | float) and value:
        return float(value)
    return None


def _merchant_name(thread: dict) -> str | None:
    merchant = thread.get("merchant")
    if isinstance(merchant, dict):
        return merchant.get("merchantName") or merchant.get("name")
    return None


def _image_url(thread: dict) -> str | None:
    """Baut die CDN-Bild-URL aus ``mainImage`` (path + name); None, wenn kein Bild vorhanden."""
    image = thread.get("mainImage")
    if not isinstance(image, dict):
        return None
    path, name = image.get("path"), image.get("name")
    if not path or not name:
        return None
    return f"{_IMAGE_CDN}/{path}/{name}/re/{_IMAGE_SIZE}/qt/{_IMAGE_QUALITY}/{name}.jpg"


def _extract_threads(html: str) -> list[dict]:
    """Sammelt die ``props.thread``-Objekte aus allen data-vue3-Knoten der Deal-Liste."""
    soup = BeautifulSoup(html, "lxml")
    threads: list[dict] = []
    for node in soup.select("[data-vue3]"):
        raw = node.get("data-vue3")
        if not raw or "ThreadMainListItemNormalizer" not in raw:
            continue
        try:
            obj = json.loads(raw)
        except (ValueError, TypeError):
            continue
        thread = obj.get("props", {}).get("thread")
        if isinstance(thread, dict) and thread.get("threadId") and "temperature" in thread:
            threads.append(thread)
    return threads


def parse_deals(html: str) -> list[MydealzDeal]:
    """Parst aktive Deals aus dem MyDealz-Suchergebnis-HTML (abgelaufene/Nicht-Deals raus)."""
    deals: list[MydealzDeal] = []
    seen: set[str] = set()
    for thread in _extract_threads(html):
        if thread.get("type") != "Deal" or thread.get("isExpired"):
            continue
        external_id = str(thread["threadId"])
        if external_id in seen:
            continue
        seen.add(external_id)
        deals.append(
            MydealzDeal(
                external_id=external_id,
                title=thread.get("title") or "",
                url=_thread_url(thread),
                temperature=_as_float(thread.get("temperature")),
                price=_as_float(thread.get("price")),
                next_best_price=_as_float(thread.get("nextBestPrice")),
                merchant=_merchant_name(thread),
                published_at=thread.get("publishedAt"),
                image_url=_image_url(thread),
            )
        )
    return deals
