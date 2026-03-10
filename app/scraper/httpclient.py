import asyncio
import random

from curl_cffi.requests import AsyncSession

# Maximum concurrent requests
MAX_CONCURRENT = 3

# Minimum and maximum delay between requests (seconds)
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
    """
    Fetch a single page (ignores HTTP status).
    """
    results = fetch_pages([url])
    return results[0] if results else ""


async def _fetch_page_checked(url: str) -> tuple[int, str]:
    """
    Fetch a single page and return (status_code, html).
    """
    async with AsyncSession(impersonate="chrome") as session:
        try:
            response = await session.get(url)
            return response.status_code, response.text
        except Exception:
            return 0, ""


def fetch_page_checked(url: str) -> tuple[int, str]:
    """
    Fetch a single page and return (http_status_code, html).

    Returns (0, "") on network / connection error.
    """
    return asyncio.run(_fetch_page_checked(url))


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
