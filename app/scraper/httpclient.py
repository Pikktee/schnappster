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


def _resolve_proxy() -> tuple[str, bool]:
    """Ermittelt (Proxy-URL, verify) aus der Konfiguration (.env oder echte Env-Variablen).

    Vorrang: expliziter ``scrape_proxy_url``; sonst aus ``scrapingant_api_key`` eine
    ScrapingAnt-Proxy-URL bauen (Residential, optional JS-Rendering). Leer = direkter Abruf.
    """
    if config.scrape_proxy_url:
        return config.scrape_proxy_url, config.scrape_proxy_verify
    if config.scrapingant_api_key:
        render = "true" if config.scrapingant_render else "false"
        user = f"scrapingant&browser={render}&proxy_type=residential"
        url = f"http://{user}:{config.scrapingant_api_key}@proxy.scrapingant.com:8080"
        return url, False  # ScrapingAnt nutzt ein eigenes TLS-Zertifikat → verify aus
    return "", True


PROXY_URL, PROXY_VERIFY = _resolve_proxy()

# Proxy-Args NUR für Preis-Alarm-Abrufe (fetch_page_with_status), NICHT für den
# hochvolumigen Kleinanzeigen-Scraper — sonst würden dessen viele Seitenabrufe das
# Proxy-/Credit-Kontingent aufbrauchen. Ohne Proxy bleibt das Dict leer (Verhalten wie bisher).
_PROXY_EXTRA: dict = {}
if PROXY_URL:
    _PROXY_EXTRA["proxy"] = PROXY_URL
    _PROXY_EXTRA["verify"] = PROXY_VERIFY
    logger.info("Preis-Alarm-Abrufe nutzen Proxy/Unlocker (verify=%s)", PROXY_VERIFY)

# Maximale gleichzeitige Anfragen (env: SCRAPE_MAX_CONCURRENT)
MAX_CONCURRENT = _int_env("SCRAPE_MAX_CONCURRENT", 6)

# Min./max. Pause zwischen Anfragen in Sekunden (env: SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX)
DELAY_MIN = _float_env("SCRAPE_DELAY_MIN", 0.25)
DELAY_MAX = _float_env("SCRAPE_DELAY_MAX", 1.0)
REQUEST_TIMEOUT = config.scrape_request_timeout
# Proxy/Rendering ist deutlich langsamer als ein direkter Abruf → großzügigeres Timeout.
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


def fetch_page_with_status(url: str, via_proxy: bool = False) -> tuple[int, str]:
    """Lädt eine URL; gibt (status_code, html) zurück; (0, '') bei Netz-/Verbindungsfehler.

    ``via_proxy=True`` routet über den konfigurierten Proxy/Unlocker — nur für Preis-Alarme
    auf geschützten Shop-Seiten, nicht für den Kleinanzeigen-Scraper (Credit-Schonung).
    """
    return asyncio.run(_fetch_page_with_status(url, via_proxy))


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


async def _fetch_page_with_status(url: str, via_proxy: bool = False) -> tuple[int, str]:
    """Lädt eine URL; gibt (status_code, body) zurück; (0, '') bei Verbindungsfehler."""
    extra = _PROXY_EXTRA if via_proxy else {}
    timeout = _PROXY_TIMEOUT if extra else REQUEST_TIMEOUT
    async with CffiAsyncSession(impersonate=IMPERSONATE) as session:
        try:
            response = await session.get(url, timeout=timeout, **extra)
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
