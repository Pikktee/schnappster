"""Kleinanzeigen-Scraper: URL-Bau, HTTP-Abruf (paginiert + Detailseiten) + Parsing."""

import json
import logging
import re
from urllib.parse import parse_qsl, urlencode, urlsplit

from app.platforms._base import PlatformScraper, SearchParams
from app.scraper import parser
from app.scraper.httpclient import fetch_page, fetch_page_with_status, fetch_pages
from app.scraper.parser import ScrapedAdDetail, ScrapedAdPreview

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.kleinanzeigen.de"
# Kleinanzeigen-Slugs transliterieren Umlaute (ä→ae …); Rohumlaute funktionieren zwar auch,
# aber die transliterierte Form ergibt saubere, encoding-freie URLs.
_UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
# Kategorie „Zu verschenken & Tauschen" (c272). Den Umkreis setzt localize_search_url
# beim Abruf (Pfadformat mit Orts-ID).
_GIFT_CATEGORY_PATH = "/s-zu-verschenken-tauschen/c272"


def _slugify(query: str) -> str:
    """Wandelt einen Suchbegriff in einen Kleinanzeigen-URL-Slug (lowercase, Bindestriche)."""
    text = query.strip().lower().translate(_UMLAUT_MAP)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _price_segment(min_price: float | None, max_price: float | None) -> str | None:
    """Preis-Pfadsegment 'preis:min:max' (leere Seite wenn Grenze fehlt); None ohne Preisgrenzen."""
    if min_price is None and max_price is None:
        return None
    low = "" if min_price is None else str(int(min_price))
    high = "" if max_price is None else str(int(max_price))
    return f"preis:{low}:{high}"


# Seit dem Umbau 2026 wertet Kleinanzeigen ``?locationStr=&radiusKm=`` nur noch halb aus:
# Der Ort wird gesetzt, der Umkreis aber ignoriert (Suche nur im exakten Ortsteil, oft
# 0 Treffer plus „Weitere Ergebnisse in anderen Orten"). Der Umkreis greift nur im
# Pfadformat mit interner Orts-ID, z. B. ``/s-60311/rennrad/k0l18709r30``. Die ID liefert
# der Ortsvorschlag-Endpunkt der Suchmaske. Gespeicherte Such-URLs bleiben im alten
# Format und werden erst beim Abruf umgestellt, damit bestehende Suchaufträge ohne
# Migration weiterlaufen.
_LOCATION_SUGGEST_URL = f"{_BASE_URL}/s-ort-empfehlungen.json"
_location_ids: dict[str, int] = {}


def resolve_location_id(postal_code: str) -> int | None:
    """Interne Kleinanzeigen-Orts-ID zu einer PLZ (gecacht); None, wenn nicht ermittelbar."""
    postal_code = postal_code.strip()
    if postal_code in _location_ids:
        return _location_ids[postal_code]
    suggest_url = f"{_LOCATION_SUGGEST_URL}?{urlencode({'query': postal_code})}"
    status, body = fetch_page_with_status(suggest_url)
    if status != 200:
        logger.warning(f"Ortsvorschlag für {postal_code}: HTTP {status}")
        return None
    try:
        suggestions = json.loads(body)
    except ValueError:
        logger.warning(f"Ortsvorschlag für {postal_code}: keine gültige Antwort")
        return None
    # Antwort z. B. {"_0": "Deutschland", "_18709": "60311 Altstadt", "_4296": "60311 Innenstadt"};
    # der erste Eintrag mit dieser PLZ ist der Ort, den auch die Suchmaske wählt.
    for key, label in suggestions.items():
        location_id = key.lstrip("_")
        if location_id.isdigit() and int(location_id) and str(label).startswith(postal_code):
            _location_ids[postal_code] = int(location_id)
            return int(location_id)
    return None


def localize_search_url(url: str) -> str:
    """Stellt eine Such-URL mit ``?locationStr=&radiusKm=`` auf das Pfadformat mit Orts-ID um.

    ``/s-preis:300:1500/rennrad/k0?locationStr=60311&radiusKm=30`` →
    ``/s-60311/preis:300:1500/rennrad/k0l18709r30``; Kategorie-URLs wie
    ``/s-zu-verschenken-tauschen/c272`` → ``/s-zu-verschenken-tauschen/60311/c272l18709r10``.
    Ohne Ortsangabe oder ohne auflösbare Orts-ID bleibt die URL unverändert.
    """
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    postal_code = query.pop("locationStr", "").strip()
    radius = query.pop("radiusKm", "").strip()
    if not postal_code or not parts.path.startswith("/s-"):
        return url
    location_id = resolve_location_id(postal_code)
    if location_id is None:
        return url

    segments = parts.path[len("/s-") :].strip("/").split("/")
    last = f"{segments[-1]}l{location_id}" + (f"r{radius}" if radius.isdigit() else "")
    if len(segments) == 2 and re.fullmatch(r"c\d+", segments[-1]):
        # Reine Kategorie-Suche: Kategorie-Slug vorn, dann die PLZ.
        path = f"/s-{segments[0]}/{postal_code}/{last}"
    else:
        path = "/s-" + "/".join([postal_code, *segments[:-1], last])
    rest = f"?{urlencode(query)}" if query else ""
    return f"{_BASE_URL}{path}{rest}"


class KleinanzeigenScraper(PlatformScraper):
    """URL-Bau für Keyword-Suchen, paginierter Abruf + Delegation an die Parserfunktionen."""

    def build_search_url(self, params: SearchParams) -> str:
        """Baut eine Kleinanzeigen-Suchergebnis-URL aus Suchbegriff, PLZ/Radius und Preis.

        Formate empirisch bestätigt: ``/s-{slug}/k0``, Preis als Pfadsegment
        ``/s-preis:min:max/{slug}/k0``, Standort als Query ``?locationStr=&radiusKm=``
        (wird beim Abruf von :func:`localize_search_url` ins Pfadformat übersetzt).
        Im Fundgrube-Modus (``gift_only``) wird stattdessen die Verschenken-Kategorie
        im Umkreis beobachtet — ohne Suchbegriff und ohne Preisspanne.
        """
        if params.gift_only:
            return self._build_gift_url(params)

        slug = _slugify(params.query)
        if not slug:
            raise ValueError("Suchbegriff ergibt keinen gültigen URL-Slug.")

        price = _price_segment(params.min_price, params.max_price)
        path = f"/s-{price}/{slug}/k0" if price else f"/s-{slug}/k0"
        url = f"{_BASE_URL}{path}"

        query: dict[str, str | int] = {}
        if params.postal_code:
            query["locationStr"] = params.postal_code
            if params.radius_km:
                query["radiusKm"] = params.radius_km
        return f"{url}?{urlencode(query)}" if query else url

    @staticmethod
    def _build_gift_url(params: SearchParams) -> str:
        """Baut die Verschenken-Kategorie-URL im Umkreis der Nutzer-PLZ."""
        url = f"{_BASE_URL}{_GIFT_CATEGORY_PATH}"
        query: dict[str, str | int] = {}
        if params.postal_code:
            query["locationStr"] = params.postal_code
            if params.radius_km:
                query["radiusKm"] = params.radius_km
        return f"{url}?{urlencode(query)}" if query else url

    def collect_previews(self, search_url: str) -> list[ScrapedAdPreview]:
        """Lädt alle paginierten Suchergebnisseiten und sammelt Anzeigen-Vorschauen."""
        localized = localize_search_url(search_url)
        if localized != search_url:
            logger.info(f"Such-URL mit Orts-ID: {localized}")
        first_page_html = fetch_page(localized)
        previews = self.parse_search_results(first_page_html)
        next_page_urls = self.parse_next_page_urls(first_page_html)

        if next_page_urls:
            for html in fetch_pages(next_page_urls):
                if html:
                    previews.extend(self.parse_search_results(html))
        return previews

    def build_details(self, previews: list[ScrapedAdPreview]) -> list[ScrapedAdDetail]:
        """Lädt für jede Vorschau die Detailseite und parst sie zu vollständigen Anzeigendaten."""
        if not previews:
            return []

        htmls = fetch_pages([p.url for p in previews])
        details: list[ScrapedAdDetail] = []
        for preview, html in zip(previews, htmls, strict=True):
            if not html:
                logger.warning(f"Failed to fetch detail page for {preview.external_id}")
                continue
            detail = self.parse_ad_detail(html, preview.url, preview.external_id)
            if detail:
                details.append(detail)
            else:
                logger.warning(f"Failed to parse detail page for {preview.external_id}")
        return details

    def parse_search_results(self, html: str) -> list[ScrapedAdPreview]:
        return parser.parse_search_results(html)

    def parse_next_page_urls(self, html: str) -> list[str]:
        return parser.parse_next_page_urls(html)

    def parse_ad_detail(self, html: str, url: str, external_id: str) -> ScrapedAdDetail | None:
        return parser.parse_ad_detail(html, url, external_id)
