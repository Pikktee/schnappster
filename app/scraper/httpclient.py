import asyncio
import random

from curl_cffi.requests import AsyncSession

MAX_CONCURRENT = 3
DELAY_MIN = 0.5
DELAY_MAX = 2.0


async def _fetch_pages(urls: list[str]) -> list[str]:
    """
    Fetch multiple pages with limited concurrency and random delays.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    results: list[str] = [""] * len(urls)

    async with AsyncSession(impersonate="chrome") as session:

        async def fetch_one(index: int, url: str) -> None:
            async with semaphore:
                try:
                    response = await session.get(url)
                    results[index] = response.text
                except Exception:
                    results[index] = ""
                await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        tasks = [fetch_one(i, url) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)

    return results


def fetch_pages(urls: list[str]) -> list[str]:
    """
    Synchronous wrapper for async page fetching.
    """
    return asyncio.run(_fetch_pages(urls))


def fetch_page(url: str) -> str:
    """Fetch a single page."""
    results = fetch_pages([url])
    return results[0] if results else ""


async def _fetch_binary(urls: list[str]) -> list[bytes]:
    """
    Fetch binary content (images) with limited concurrency.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    results: list[bytes] = [b""] * len(urls)

    async with AsyncSession(impersonate="chrome") as session:

        async def fetch_one(index: int, url: str) -> None:
            async with semaphore:
                try:
                    response = await session.get(url)
                    results[index] = response.content
                except Exception:
                    results[index] = b""
                await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        tasks = [fetch_one(i, url) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)

    return results


def fetch_binary(urls: list[str]) -> list[bytes]:
    """
    Synchronous wrapper for binary content fetching.
    """
    return asyncio.run(_fetch_binary(urls))
