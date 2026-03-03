import asyncio

from curl_cffi.requests import AsyncSession


async def _fetch_pages(urls: list[str]) -> list[str]:
    """Fetch multiple pages concurrently using browser-like TLS fingerprint."""
    results: list[str] = []
    async with AsyncSession(impersonate="chrome") as session:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for response in responses:
            if isinstance(response, Exception):
                results.append("")
            else:
                results.append(response.text)
    return results


def fetch_pages(urls: list[str]) -> list[str]:
    """Synchronous wrapper for async page fetching."""
    return asyncio.run(_fetch_pages(urls))


def fetch_page(url: str) -> str:
    """Fetch a single page."""
    results = fetch_pages([url])
    return results[0] if results else ""
