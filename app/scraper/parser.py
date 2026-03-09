from dataclasses import dataclass, field
from typing import cast

from bs4 import BeautifulSoup, Tag

BASE_URL = "https://www.kleinanzeigen.de"


@dataclass
class ScrapedAdPreview:
    """
    Basic ad data from search results page.
    """

    external_id: str
    title: str
    url: str
    price: float | None = None
    location: str | None = None
    image_url: str | None = None


@dataclass
class ScrapedAdDetail:
    """
    Full ad data from detail page.
    """

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


# ------------------------------
# --- Search results parsing ---
# ------------------------------
def parse_search_results(html: str) -> list[ScrapedAdPreview]:
    """Parse ad previews from a search results page."""
    soup = BeautifulSoup(html, "lxml")
    ads: list[ScrapedAdPreview] = []

    for item in soup.select("li.ad-listitem"):
        ad = _parse_search_item(item)
        if ad:
            ads.append(ad)

    return ads


def _parse_search_item(item: Tag) -> ScrapedAdPreview | None:
    """
    Parse a single search result item.
    """
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
def parse_ad_detail(html: str, url: str, external_id: str) -> ScrapedAdDetail | None:
    """
    Parse full ad details from a detail page.
    """
    soup = BeautifulSoup(html, "lxml")

    # Title
    title_tag = soup.select_one("#viewad-title")
    if not title_tag:
        return None
    title = title_tag.get_text(strip=True)

    # Price from meta tag (more reliable) or visible price
    price = None
    price_meta = soup.select_one("meta[itemprop='price']")
    if price_meta and isinstance(price_meta, Tag):
        content = price_meta.get("content", "")

        if isinstance(content, list):
            content = " ".join(content)
        if isinstance(content, str):
            price = _parse_price(content)
    else:
        price_tag = soup.select_one("#viewad-price")

        if price_tag and isinstance(price_tag, Tag):
            price = _parse_price(price_tag.get_text(strip=True))

    # Location: split "51105 Innenstadt - Poll" into postal_code and city
    postal_code = None
    city = None
    locality_tag = soup.select_one("#viewad-locality")
    if locality_tag:
        locality_text = locality_tag.get_text(strip=True)
        postal_code, city = _split_locality(locality_text)

    # Description
    description = None
    desc_tag = soup.select_one("#viewad-description-text")
    if desc_tag:
        for br in desc_tag.find_all("br"):
            br.replace_with("\n")
        description = desc_tag.get_text(strip=True)

    # Condition and other details
    condition = None
    details = soup.select(".addetailslist--detail")
    for detail in details:
        label = detail.get_text(strip=True)
        value_tag = detail.select_one(".addetailslist--detail--value")
        if value_tag and "Zustand" in label:
            condition = value_tag.get_text(strip=True)

    # Shipping cost
    shipping_cost = None
    shipping_tag = soup.select_one(".boxedarticle--details--shipping")
    if shipping_tag:
        shipping_text = shipping_tag.get_text(strip=True)
        shipping_cost = shipping_text.replace("+ Versand ab", "").strip()

    # Images
    image_urls: list[str] = []
    for img in soup.select(".galleryimage-element img[data-imgsrc]"):
        raw = img.get("data-imgsrc", "")
        src = raw if isinstance(raw, str) else None
        if src and src not in image_urls:
            image_urls.append(src)

    # Seller info
    seller_name = None
    seller_url = None
    seller_rating = None
    seller_is_friendly = False
    seller_is_reliable = False
    seller_type = None
    seller_active_since = None

    profile_box = soup.select_one("#viewad-profile-box")
    if profile_box:
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

        friendly_tag = profile_box.select_one(".userbadges-profile-friendliness")
        seller_is_friendly = friendly_tag is not None

        reliable_tag = profile_box.select_one(".userbadges-profile-reliability")
        seller_is_reliable = reliable_tag is not None

        for detail in profile_box.select(".userprofile-vip-details-text"):
            text = detail.get_text(strip=True)
            if "Nutzer" in text:
                seller_type = text.replace("Nutzer", "").replace("er", "").strip()
            elif "Aktiv seit" in text:
                seller_active_since = text.replace("Aktiv seit", "").strip()

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


# ---------------
# --- Helpers ---
# ---------------
def _parse_price(text: str) -> float | None:
    """
    Parse price from text like '75 €', '110 € VB', '110.00', 'VB'.
    """
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
    """
    Split '51105 Innenstadt - Poll' into ('51105', 'Innenstadt - Poll').
    """
    text = text.strip()
    if not text:
        return None, None

    parts = text.split(" ", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[0], parts[1]

    return None, text
