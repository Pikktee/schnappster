"""HTTP client: fetch HTML and binary content with concurrency limits and delays (curl_cffi)."""

import asyncio
import random

from curl_cffi.requests import AsyncSession as CffiAsyncSession

# Maximum concurrent requests
MAX_CONCURRENT = 3

# Minimum and maximum delay between requests (seconds)
DELAY_MIN = 0.5
DELAY_MAX = 2.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_pages(urls: list[str]) -> list[str]:
    """Synchronous wrapper around async _fetch_pages."""
    return asyncio.run(_fetch_pages(urls))


def fetch_page(url: str) -> str:
    """Fetch a single URL; return body or empty string; ignore HTTP status."""
    results = fetch_pages([url])
    return results[0] if results else ""


def fetch_page_with_status(url: str) -> tuple[int, str]:
    """Fetch one URL; return (status_code, html); (0, '') on network/connection error."""
    return asyncio.run(_fetch_page_with_status(url))


def fetch_binary(urls: list[str]) -> list[bytes]:
    """Synchronous wrapper around async _fetch_binary."""
    return asyncio.run(_fetch_binary(urls))


# ---------------------------------------------------------------------------
# Private
# ---------------------------------------------------------------------------


async def _fetch_pages(urls: list[str]) -> list[str]:
    """Fetch multiple URLs with limited concurrency and random delay between requests."""
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
    """Fetch one URL; return (status_code, body); (0, '') on connection error."""
    async with CffiAsyncSession(impersonate="chrome") as session:
        try:
            response = await session.get(url)
            return response.status_code, response.text
        except Exception:
            return 0, ""


async def _fetch_binary(urls: list[str]) -> list[bytes]:
    """Fetch binary content (e.g. images) with limited concurrency and delays."""
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
