"""API-Schemas für den Ergebnis-Stream (Start-Feed): Anzeigen, Deals und Preis-Ereignisse."""

from datetime import datetime

from sqlmodel import SQLModel

from app.models.ad import AdRead
from app.models.deal_watch import DealRead

FEED_TYPE_AD = "ad"
FEED_TYPE_DEAL = "deal"
FEED_TYPE_PRICE = "price"


class FeedPriceEvent(SQLModel):
    """Eine Preisänderung eines Preis-Alarms als Stream-Ereignis."""

    watch_id: int
    watch_name: str
    url: str
    price: float
    previous_price: float | None = None
    currency: str | None = None
    recorded_at: datetime


class FeedItem(SQLModel):
    """Ein Element des Streams; genau eines der Nutzdaten-Felder ist gesetzt (je nach type)."""

    type: str  # "ad" | "deal" | "price"
    occurred_at: datetime
    ad: AdRead | None = None
    deal: DealRead | None = None
    price_event: FeedPriceEvent | None = None


class FeedPage(SQLModel):
    """Eine Seite des Streams mit Gesamtzahl (für Pagination/Mehr-laden)."""

    items: list[FeedItem]
    total: int
