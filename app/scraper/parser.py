"""Parse Kleinanzeigen.de HTML: search results, detail pages, titles, pagination."""

# Public
import re
from dataclasses import dataclass, field
from typing import cast

from bs4 import BeautifulSoup, Tag

__all__ = [
    "ScrapedAdPreview",
    "ScrapedAdDetail",
    "parse_search_results",
    "parse_search_title",
    "parse_next_page_urls",
    "parse_ad_detail",
]

BASE_URL = "https://www.kleinanzeigen.de"


# --------------------------
# --- Output types ---
# --------------------------
@dataclass
class ScrapedAdPreview:
    """Basic ad data from search results page."""

    external_id: str
    title: str
    url: str
    price: float | None = None
    location: str | None = None
    image_url: str | None = None


@dataclass
class ScrapedAdDetail:
    """Full ad data from detail page."""

    external_id: str
    title: str
    url: str
    description: str | None = None
    price: float | None = None
    postal_code: str | None = None
    city: str | None = None
    condition: str | None = None
    shipping_cost: str | None = None
    image_urls: list[str] = field(default_factory=list)
    seller_name: str | None = None
    seller_url: str | None = None
    seller_rating: int | None = None
    seller_is_friendly: bool = False
    seller_is_reliable: bool = False
    seller_type: str | None = None
    seller_active_since: str | None = None


# ---------------
# --- Helpers ---
# ---------------
def _parse_price(text: str) -> float | None:
    """Parse price from text like '75 €', '110 € VB'; return None if not parseable."""
    cleaned = text.replace("€", "").replace("VB", "").strip()
    if not cleaned:
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _split_locality(text: str) -> tuple[str | None, str | None]:
    """Split '51105 Innenstadt - Poll' into (postal_code, city); (None, text) if no digits."""
    text = text.strip()
    if not text:
        return None, None
    parts = text.split(" ", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[0], parts[1]
    return None, text


# ------------------------------
# --- Search results parsing ---
# ------------------------------

# Matches trailing Kleinanzeigen branding at end of string (e.g. " - kleinanzeigen.de",
# " | Kleinanzeigen", " – Kleinanzeigen", " auf Kleinanzeigen"). Used to strip it from <title>.
_TITLE_SUFFIX_RE = re.compile(
    r"(?:\s*[-–|]\s*|\s+(?:auf\s+)?)kleinanzeigen(?:\.de)?\s*$",
    re.IGNORECASE,
)


def parse_search_results(html: str) -> list[ScrapedAdPreview]:
    """Parse ad previews from a search results page HTML."""
    soup = BeautifulSoup(html, "lxml")
    ads: list[ScrapedAdPreview] = []
    for item in soup.select("li.ad-listitem"):
        ad = _parse_search_item(item)
        if ad:
            ads.append(ad)
    return ads


def _parse_search_item(item: Tag) -> ScrapedAdPreview | None:
    """Parse one search result list item into ScrapedAdPreview or None if invalid."""
    link = item.select_one("a[href*='/s-anzeige/']")
    if not link:
        return None

    href = cast(str, link.get("href", ""))
    url = f"{BASE_URL}{href}" if href.startswith("/") else href

    parts = href.rstrip("/").split("/")
    if not parts:
        return None
    external_id = parts[-1].split("-")[0]
    if not external_id.isdigit():
        return None

    title_tag = item.select_one("h2")
    title = title_tag.get_text(strip=True) if title_tag else ""

    price = None
    price_tag = item.select_one("[class*='price']")
    if price_tag:
        price = _parse_price(price_tag.get_text(strip=True))

    location = None
    location_tag = item.select_one("[class*='aditem-main--top--left']")
    if location_tag:
        location = location_tag.get_text(strip=True)

    image_url = None
    img = item.select_one("img[src*='img.kleinanzeigen.de']")
    if img:
        raw = img.get("src")
        image_url = raw if isinstance(raw, str) else None

    return ScrapedAdPreview(
        external_id=external_id,
        title=title,
        url=url,
        price=price,
        location=location,
        image_url=image_url,
    )


def parse_search_title(html: str) -> str | None:
    """Extract page title from search HTML; try <title> then <h1>, strip Kleinanzeigen branding."""
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    if title_tag:
        title = _TITLE_SUFFIX_RE.sub("", title_tag.get_text(strip=True)).strip()
        if title:
            return title
    h1 = soup.find("h1")
    if h1 and isinstance(h1, Tag):
        text = h1.get_text(strip=True)
        if text:
            return text
    return None


def parse_next_page_urls(html: str) -> list[str]:
    """Extract all pagination URLs from search results."""
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    for link in soup.select("a[href*='seite:']"):
        href = cast(str, link.get("href", ""))
        full_url = f"{BASE_URL}{href}" if href.startswith("/") else href
        if full_url not in urls:
            urls.append(full_url)
    return urls


# ----------------------------
# --- Detail page parsing ---
# ----------------------------
def _parse_detail_title(soup: BeautifulSoup) -> str | None:
    """Extract title from detail page; None if missing (invalid page)."""
    title_tag = soup.select_one("#viewad-title")
    return title_tag.get_text(strip=True) if title_tag else None


def _parse_detail_price(soup: BeautifulSoup) -> float | None:
    """Extract price from meta or visible price element on detail page."""
    price_meta = soup.select_one("meta[itemprop='price']")
    if price_meta and isinstance(price_meta, Tag):
        content = price_meta.get("content", "")
        if isinstance(content, list):
            content = " ".join(content)
        if isinstance(content, str):
            return _parse_price(content)
    price_tag = soup.select_one("#viewad-price")
    if price_tag and isinstance(price_tag, Tag):
        return _parse_price(price_tag.get_text(strip=True))
    return None


def _parse_detail_location(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """Extract (postal_code, city) from locality element."""
    locality_tag = soup.select_one("#viewad-locality")
    if not locality_tag:
        return None, None
    return _split_locality(locality_tag.get_text(strip=True))


def _parse_detail_description(soup: BeautifulSoup) -> str | None:
    """Extract description text; convert <br> to newlines."""
    desc_tag = soup.select_one("#viewad-description-text")
    if not desc_tag:
        return None
    for br in desc_tag.find_all("br"):
        br.replace_with("\n")
    return desc_tag.get_text(strip=True)


def _parse_detail_condition(soup: BeautifulSoup) -> str | None:
    """Extract condition (Zustand) from details list."""
    for detail in soup.select(".addetailslist--detail"):
        label = detail.get_text(strip=True)
        value_tag = detail.select_one(".addetailslist--detail--value")
        if value_tag and "Zustand" in label:
            return value_tag.get_text(strip=True)
    return None


def _parse_detail_shipping_cost(soup: BeautifulSoup) -> str | None:
    """Extract shipping cost text from detail box."""
    shipping_tag = soup.select_one(".boxedarticle--details--shipping")
    if not shipping_tag:
        return None
    text = shipping_tag.get_text(strip=True)
    return text.replace("+ Versand ab", "").strip()


def _parse_detail_images(soup: BeautifulSoup) -> list[str]:
    """Extract image URLs from gallery (data-imgsrc)."""
    urls: list[str] = []
    for img in soup.select(".galleryimage-element img[data-imgsrc]"):
        raw = img.get("data-imgsrc", "")
        src = raw if isinstance(raw, str) else None
        if src and src not in urls:
            urls.append(src)
    return urls


def _parse_detail_seller(
    soup: BeautifulSoup,
) -> tuple[
    str | None,
    str | None,
    int | None,
    bool,
    bool,
    str | None,
    str | None,
]:
    """Extract seller fields from profile box (name, url, rating, badges, type, active_since)."""
    seller_name = None
    seller_url = None
    seller_rating = None
    seller_is_friendly = False
    seller_is_reliable = False
    seller_type = None
    seller_active_since = None

    profile_box = soup.select_one("#viewad-profile-box")
    if not profile_box:
        return (
            seller_name,
            seller_url,
            seller_rating,
            seller_is_friendly,
            seller_is_reliable,
            seller_type,
            seller_active_since,
        )

    name_link = profile_box.select_one(".userprofile-vip a")
    if name_link:
        seller_name = name_link.get_text(strip=True)
        raw_href = name_link.get("href", "")
        href = raw_href if isinstance(raw_href, str) else ""
        seller_url = f"{BASE_URL}{href}" if href.startswith("/") else href

    rating_tag = profile_box.select_one(".userbadges-profile-rating")
    if rating_tag:
        icon = rating_tag.select_one("i")
        if icon:
            classes = icon.get("class") or []
            if "icon-rating-tag-2" in classes:
                seller_rating = 2
            elif "icon-rating-tag-1" in classes:
                seller_rating = 1
            elif "icon-rating-tag-0" in classes:
                seller_rating = 0

    seller_is_friendly = profile_box.select_one(".userbadges-profile-friendliness") is not None
    seller_is_reliable = profile_box.select_one(".userbadges-profile-reliability") is not None

    for detail in profile_box.select(".userprofile-vip-details-text"):
        text = detail.get_text(strip=True)
        if "Nutzer" in text:
            seller_type = text.replace("Nutzer", "").replace("er", "").strip()
        elif "Aktiv seit" in text:
            seller_active_since = text.replace("Aktiv seit", "").strip()

    return (
        seller_name,
        seller_url,
        seller_rating,
        seller_is_friendly,
        seller_is_reliable,
        seller_type,
        seller_active_since,
    )


def parse_ad_detail(html: str, url: str, external_id: str) -> ScrapedAdDetail | None:
    """Parse full ad details from a detail page; return None if title missing (invalid page)."""
    soup = BeautifulSoup(html, "lxml")

    title = _parse_detail_title(soup)
    if not title:
        return None

    price = _parse_detail_price(soup)
    postal_code, city = _parse_detail_location(soup)
    description = _parse_detail_description(soup)
    condition = _parse_detail_condition(soup)
    shipping_cost = _parse_detail_shipping_cost(soup)
    image_urls = _parse_detail_images(soup)
    (
        seller_name,
        seller_url,
        seller_rating,
        seller_is_friendly,
        seller_is_reliable,
        seller_type,
        seller_active_since,
    ) = _parse_detail_seller(soup)

    return ScrapedAdDetail(
        external_id=external_id,
        title=title,
        url=url,
        description=description,
        price=price,
        postal_code=postal_code,
        city=city,
        condition=condition,
        shipping_cost=shipping_cost,
        image_urls=image_urls,
        seller_name=seller_name,
        seller_url=seller_url,
        seller_rating=seller_rating,
        seller_is_friendly=seller_is_friendly,
        seller_is_reliable=seller_is_reliable,
        seller_type=seller_type,
        seller_active_since=seller_active_since,
    )
