"""HTTP-Client: HTML und Binärdaten mit Begrenzung der Parallelität und Verzögerungen (curl_cffi)."""

import asyncio
import random

from curl_cffi.requests import AsyncSession as CffiAsyncSession

# Maximale gleichzeitige Anfragen
MAX_CONCURRENT = 3

# Minimale und maximale Pause zwischen Anfragen (Sekunden)
DELAY_MIN = 0.5
DELAY_MAX = 2.0


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------


def fetch_pages(urls: list[str]) -> list[str]:
    """Synchrone Hülle um asynchrone _fetch_pages."""
    return asyncio.run(_fetch_pages(urls))


def fetch_page(url: str) -> str:
    """Lädt eine URL; gibt den Response-Body oder leeren String zurück; HTTP-Status wird ignoriert."""
    results = fetch_pages([url])
    return results[0] if results else ""


def fetch_page_with_status(url: str) -> tuple[int, str]:
    """Lädt eine URL; gibt (status_code, html) zurück; (0, '') bei Netz-/Verbindungsfehler."""
    return asyncio.run(_fetch_page_with_status(url))


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

    async with CffiAsyncSession(impersonate="chrome") as session:

        async def fetch_one(index: int, url: str) -> None:
            async with semaphore:
                try:
                    response = await session.get(url)
                    results[index] = response.text
                except Exception:
                    results[index] = ""
                await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        tasks = []
        for i, url in enumerate(urls):
            tasks.append(fetch_one(i, url))

        await asyncio.gather(*tasks)

    return results


async def _fetch_page_with_status(url: str) -> tuple[int, str]:
    """Lädt eine URL; gibt (status_code, body) zurück; (0, '') bei Verbindungsfehler."""
    async with CffiAsyncSession(impersonate="chrome") as session:
        try:
            response = await session.get(url)
            return response.status_code, response.text
        except Exception:
            return 0, ""


async def _fetch_binary(urls: list[str]) -> list[bytes]:
    """Lädt Binärdaten (z. B. Bilder) mit begrenzter Parallelität und Verzögerungen."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    results: list[bytes] = [b""] * len(urls)

    async with CffiAsyncSession(impersonate="chrome") as session:

        async def fetch_one(index: int, url: str) -> None:
            async with semaphore:
                try:
                    response = await session.get(url)
                    results[index] = response.content
                except Exception:
                    results[index] = b""
                await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        tasks = []
        for i, url in enumerate(urls):
            tasks.append(fetch_one(i, url))

        await asyncio.gather(*tasks)

    return results
