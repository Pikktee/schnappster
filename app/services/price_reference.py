"""Marktwert-Referenz aus echten eBay-Verkäufen: Median + Spanne (Sold Comps)."""

import logging
import statistics
import time
from dataclasses import dataclass

from app.scraper.ebay_sold import SoldListing, fetch_sold_html, parse_sold_listings

logger = logging.getLogger(__name__)

# Weniger belastbare Vergleiche ergeben keinen aussagekräftigen Median.
MIN_COMPARISONS = 3
MAX_COMPARISONS = 60

# Cache pro Produkt-Schlüssel (viele Anzeigen = dasselbe Produkt → ein Abruf).
# Prozessweit: der Analyse-Job läuft im langlebigen API-Prozess, ein Neustart leert ihn.
_CACHE_TTL_SECONDS = 7 * 24 * 3600
# Nach einem Block/Fehler eine Weile gar nicht abfragen (kein 403-Storm in Prod ohne Proxy).
_BLOCK_COOLDOWN_SECONDS = 3600

_cache: dict[str, tuple[float, "SoldReference | None"]] = {}
_blocked_until: float = 0.0


class EbayBlockedError(RuntimeError):
    """eBay hat den Abruf blockiert (z. B. 403) oder war nicht erreichbar."""


@dataclass
class SoldReference:
    """Aggregierter Marktwert aus verkauften eBay-Angeboten."""

    query: str
    currency: str
    median: float
    low: float
    high: float
    count: int
    listings: list[SoldListing]


def get_ebay_sold_reference(query: str) -> SoldReference | None:
    """Holt verkaufte eBay-Angebote und berechnet Median + Spanne (nur EUR).

    Wirft ``EbayBlockedError`` bei Block/Netzwerkfehler. Gibt ``None`` zurück, wenn zu
    wenige belastbare Vergleiche gefunden wurden.
    """
    status, html = fetch_sold_html(query)
    if status in (0, 403, 429, 503) or not html:
        raise EbayBlockedError(f"eBay-Abruf fehlgeschlagen (Status {status}).")

    priced = [
        listing
        for listing in parse_sold_listings(html)
        if listing.price and listing.price > 0 and listing.currency == "EUR"
    ][:MAX_COMPARISONS]

    prices = sorted(listing.price for listing in priced)  # type: ignore[misc]
    if len(prices) < MIN_COMPARISONS:
        return None

    trimmed = _trim_outliers(prices)
    return SoldReference(
        query=query,
        currency="EUR",
        median=round(statistics.median(trimmed), 2),
        low=min(trimmed),
        high=max(trimmed),
        count=len(trimmed),
        listings=priced,
    )


def _trim_outliers(sorted_prices: list[float]) -> list[float]:
    """Entfernt grobe Ausreißer über den 1,5·IQR-Zaun; behält mindestens die Hälfte."""
    n = len(sorted_prices)
    if n < 4:
        return sorted_prices
    q1 = sorted_prices[n // 4]
    q3 = sorted_prices[(3 * n) // 4]
    iqr = q3 - q1
    low_fence = q1 - 1.5 * iqr
    high_fence = q3 + 1.5 * iqr
    trimmed = [p for p in sorted_prices if low_fence <= p <= high_fence]
    return trimmed if len(trimmed) >= max(MIN_COMPARISONS, n // 2) else sorted_prices


def get_market_reference_cached(query: str) -> SoldReference | None:
    """Wie ``get_ebay_sold_reference``, aber mit Cache + Block-Cooldown und ohne Exceptions.

    Für den Einsatz in der Analyse-Pipeline: liefert ``None`` (statt zu werfen), wenn eBay
    gerade blockt oder zu wenige Vergleiche vorliegen — dann greift der bisherige
    Suchvergleich als Marktwert.
    """
    global _blocked_until
    key = query.strip().lower()
    if not key:
        return None

    now = time.time()
    cached = _cache.get(key)
    if cached is not None and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    if now < _blocked_until:
        return None  # Cooldown: eBay wird gerade nicht abgefragt

    try:
        reference = get_ebay_sold_reference(query)
    except EbayBlockedError as exc:
        _blocked_until = now + _BLOCK_COOLDOWN_SECONDS
        logger.info("eBay-Sold blockiert (%s) — Cooldown %ss", exc, _BLOCK_COOLDOWN_SECONDS)
        return None

    _cache[key] = (now, reference)
    return reference


def reset_cache() -> None:
    """Leert Cache und Cooldown (v. a. für Tests)."""
    global _blocked_until
    _cache.clear()
    _blocked_until = 0.0
