"""HTTP-Client: HTML und Binärdaten mit Begrenzung der Parallelität und Verzögerungen.

Nutzt curl_cffi.
"""

import asyncio
import logging
import os
import random

from curl_cffi.requests import AsyncSession as CffiAsyncSession

from app.core.config import config

logger = logging.getLogger(__name__)


def _int_env(name: str, default: int) -> int:
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    val = os.environ.get(name)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _str_env(name: str, default: str) -> str:
    val = os.environ.get(name)
    return val if val else default


# Browser-Fingerprint für curl_cffi (env: SCRAPE_IMPERSONATE).
# "chrome131" passt empirisch viele Anti-Bot-Schutzmaßnahmen (Cloudflare, Amazon),
# die der curl_cffi-Default "chrome" auslöst (403 bzw. preisbereinigte Seiten).
IMPERSONATE = _str_env("SCRAPE_IMPERSONATE", "chrome131")


def _resolve_proxy(render: bool) -> tuple[str, bool]:
    """Ermittelt (Proxy-URL, verify) für die gewünschte Rendering-Stufe.

    Vorrang: expliziter ``scrape_proxy_url`` (kennt keine Rendering-Umschaltung, daher für
    beide Stufen identisch); sonst aus ``scrapingant_api_key`` eine ScrapingAnt-URL bauen,
    deren ``browser=``-Flag das (langsame, credit-teure) JS-Rendering steuert. Leer = kein
    Proxy → direkter Abruf.
    """
    if config.scrape_proxy_url:
        return config.scrape_proxy_url, config.scrape_proxy_verify
    if config.scrapingant_api_key:
        flag = "true" if render else "false"
        parts = ["scrapingant", f"browser={flag}", "proxy_type=residential"]
        if config.scrapingant_country:
            parts.append(f"proxy_country={config.scrapingant_country}")
        user = "&".join(parts)
        url = f"http://{user}:{config.scrapingant_api_key}@proxy.scrapingant.com:8080"
        return url, False  # ScrapingAnt nutzt ein eigenes TLS-Zertifikat → verify aus
    return "", True


# Zwei Proxy-Stufen: ohne Rendering (schnell + billig) und mit Rendering (Notnagel für reine
# JS-Seiten). Der gestufte Abruf probiert erst ohne, dann mit Rendering.
_PROXY_NORENDER_URL, PROXY_VERIFY = _resolve_proxy(render=False)
_PROXY_RENDER_URL, _ = _resolve_proxy(render=True)
# Ob überhaupt ein Proxy konfiguriert ist (für den gestuften Abruf: erst direkt, dann Proxy).
PROXY_CONFIGURED = bool(_PROXY_NORENDER_URL)
# Rendering-Stufe nur, wenn sie sich vom reinen HTTP-Proxy unterscheidet (ScrapingAnt) und
# erlaubt ist. Ein expliziter scrape_proxy_url kennt keine Umschaltung → keine dritte Stufe.
_RENDER_TIER_ENABLED = (
    bool(_PROXY_RENDER_URL)
    and config.scrapingant_render
    and _PROXY_RENDER_URL != _PROXY_NORENDER_URL
)
if PROXY_CONFIGURED:
    logger.info(
        "Preis-Alarm-Abrufe nutzen Proxy/Unlocker (verify=%s, Rendering-Fallback=%s)",
        PROXY_VERIFY,
        _RENDER_TIER_ENABLED,
    )


def _proxy_extra(render: bool) -> dict:
    """Proxy-Argumente (proxy + verify) für die gewünschte Stufe; leer ohne Proxy.

    NUR für Preis-Alarm-Abrufe — der hochvolumige Kleinanzeigen-Scraper bleibt proxyfrei,
    sonst würden seine vielen Seitenabrufe das Credit-Kontingent aufbrauchen.
    """
    url = _PROXY_RENDER_URL if render else _PROXY_NORENDER_URL
    if not url:
        return {}
    return {"proxy": url, "verify": PROXY_VERIFY}


# Maximale gleichzeitige Anfragen (env: SCRAPE_MAX_CONCURRENT)
MAX_CONCURRENT = _int_env("SCRAPE_MAX_CONCURRENT", 6)

# Min./max. Pause zwischen Anfragen in Sekunden (env: SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX)
DELAY_MIN = _float_env("SCRAPE_DELAY_MIN", 0.25)
DELAY_MAX = _float_env("SCRAPE_DELAY_MAX", 1.0)
REQUEST_TIMEOUT = config.scrape_request_timeout
# Sprach-/Länder-Header für Preis-Abrufe: ohne ihn liefert Amazon die englische Seite mit
# abweichenden Preisen/Formaten statt der deutschen EUR-Variante.
_PRICEWATCH_HEADERS = (
    {"Accept-Language": config.scrape_accept_language} if config.scrape_accept_language else {}
)
# Kurzes Timeout für die erste (direkte) Preis-Alarm-Stufe: fällt sie ohnehin auf den Proxy
# zurück, darf sie nicht erst ~20 s hängen (env: PRICEWATCH_DIRECT_TIMEOUT).
_PRICEWATCH_DIRECT_TIMEOUT = _float_env("PRICEWATCH_DIRECT_TIMEOUT", 8.0)
# Proxy mit Rendering ist deutlich langsamer als ein direkter Abruf → großzügigeres Timeout.
_PROXY_TIMEOUT = max(REQUEST_TIMEOUT, 70.0)


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------


def fetch_pages(urls: list[str]) -> list[str]:
    """Synchrone Hülle um asynchrone _fetch_pages."""
    return asyncio.run(_fetch_pages(urls))


def fetch_page(url: str) -> str:
    """Lädt eine URL; Body oder leerer String; HTTP-Status wird ignoriert."""
    results = fetch_pages([url])
    return results[0] if results else ""


def fetch_page_with_status(
    url: str, via_proxy: bool = False, render: bool = False, timeout: float | None = None
) -> tuple[int, str]:
    """Lädt eine URL; gibt (status_code, html) zurück; (0, '') bei Netz-/Verbindungsfehler.

    ``via_proxy=True`` routet über den konfigurierten Proxy/Unlocker — nur für Preis-Alarme
    auf geschützten Shop-Seiten, nicht für den Kleinanzeigen-Scraper (Credit-Schonung).
    ``render=True`` aktiviert zusätzlich das (langsame) JS-Rendering des Proxys; ``timeout``
    überschreibt das Standard-Timeout der jeweiligen Stufe.
    """
    return asyncio.run(_fetch_page_with_status(url, via_proxy, render, timeout))


def fetch_with_proxy_fallback(url: str, is_success) -> tuple[int, str]:
    """Gestufter Abruf: direkt → Proxy ohne Rendering → Proxy mit Rendering.

    ``is_success(status, html) -> bool`` bewertet jede Stufe (z. B. „Preis gefunden?"). Die
    erste brauchbare Stufe gewinnt, sonst geht es eine Stufe weiter. So bleiben ungeschützte
    Seiten sofort/gratis, geschützte nutzen den schnellen HTTP-Proxy und nur reine JS-Seiten
    das teure Rendering. Rückgabe: (status_code, html) der genutzten bzw. letzten Stufe.
    """
    status, html = fetch_page_with_status(url, via_proxy=False, timeout=_PRICEWATCH_DIRECT_TIMEOUT)
    if not PROXY_CONFIGURED or is_success(status, html):
        return status, html
    status, html = fetch_page_with_status(url, via_proxy=True, render=False)
    if is_success(status, html) or not _RENDER_TIER_ENABLED:
        return status, html
    return fetch_page_with_status(url, via_proxy=True, render=True)


def fetch_binary(urls: list[str]) -> list[bytes]:
    """Synchrone Hülle um asynchrone _fetch_binary."""
    return asyncio.run(_fetch_binary(urls))


# ---------------------------------------------------------------------------
# Intern
# ---------------------------------------------------------------------------


async def _fetch_pages(urls: list[str]) -> list[str]:
    """Lädt mehrere URLs mit begrenzter Parallelität und zufälliger Pause zwischen den Anfragen."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    results: list[str] = [""] * len(urls)

    async with CffiAsyncSession(impersonate=IMPERSONATE) as session:

        async def fetch_one(index: int, url: str) -> None:
            async with semaphore:
                try:
                    response = await session.get(url, timeout=REQUEST_TIMEOUT)
                    results[index] = response.text
                except Exception:
                    results[index] = ""
                await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        tasks = []
        for i, url in enumerate(urls):
            tasks.append(fetch_one(i, url))

        await asyncio.gather(*tasks)

    return results


async def _fetch_page_with_status(
    url: str, via_proxy: bool = False, render: bool = False, request_timeout: float | None = None
) -> tuple[int, str]:
    """Lädt eine URL; gibt (status_code, body) zurück; (0, '') bei Verbindungsfehler."""
    extra = _proxy_extra(render) if via_proxy else {}
    if request_timeout is None:
        request_timeout = _PROXY_TIMEOUT if (extra and render) else REQUEST_TIMEOUT
    async with CffiAsyncSession(impersonate=IMPERSONATE) as session:
        try:
            response = await session.get(
                url, timeout=request_timeout, headers=_PRICEWATCH_HEADERS, **extra
            )
            return response.status_code, response.text
        except Exception:
            return 0, ""


async def _fetch_binary(urls: list[str]) -> list[bytes]:
    """Lädt Binärdaten (z. B. Bilder) mit begrenzter Parallelität und Verzögerungen."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    results: list[bytes] = [b""] * len(urls)

    async with CffiAsyncSession(impersonate=IMPERSONATE) as session:

        async def fetch_one(index: int, url: str) -> None:
            async with semaphore:
                try:
                    response = await session.get(url, timeout=REQUEST_TIMEOUT)
                    results[index] = response.content
                except Exception:
                    results[index] = b""
                await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        tasks = []
        for i, url in enumerate(urls):
            tasks.append(fetch_one(i, url))

        await asyncio.gather(*tasks)

    return results
