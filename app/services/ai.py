import base64
import json
import logging

from openai import BadRequestError, OpenAI  # pyright: ignore[reportMissingImports]
from sqlalchemy import desc
from sqlmodel import Session, select

from app.core import config as app_config
from app.models.ad import Ad
from app.models.adsearch import AdSearch
from app.prompts import ADANALYZER_PROMPT
from app.scraper.httpclient import fetch_binary
from app.services.settings import SettingsService
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, session: Session):
        self.session = session
        if not app_config.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured - set OPENROUTER_API_KEY in .env")

        self.model = app_config.openrouter_ai_model
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=app_config.openrouter_api_key,
        )

    def analyze_unprocessed(self, limit: int = 10) -> int:
        """
        Analyze unprocessed ads. Returns number of ads analyzed.
        """
        ads = self.session.exec(
            select(Ad)
            .where(Ad.is_analyzed.is_(False))  # pyright: ignore[reportAttributeAccessIssue]
            .order_by(desc(Ad.first_seen_at))  # pyright: ignore[reportArgumentType]
            .limit(limit)
        ).all()

        if not ads:
            logger.info("No unprocessed ads found")
            return 0

        analyzed = 0
        for ad in ads:
            try:
                self._analyze_ad(ad)
                analyzed += 1
            except BadRequestError as e:
                error_msg = (
                    e.body.get("error", {}).get("message", str(e))
                    if isinstance(e.body, dict)
                    else str(e)
                )
                logger.error(f"API error: {error_msg}")
                return analyzed
            except Exception as e:
                logger.error(f"Failed to analyze ad {ad.id} '{ad.title}': {e}")
                ad.is_analyzed = True
                self.session.commit()

        return analyzed

    def _analyze_ad(self, ad: Ad) -> None:
        """
        Analyze a single ad with the AI model.
        """
        adsearch = self.session.get(AdSearch, ad.adsearch_id)
        ad_text = self._build_ad_text(ad, adsearch)
        images = self._download_images(ad)

        messages = self._build_messages(ad_text, images, adsearch)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # pyright: ignore[reportArgumentType]
            max_tokens=1000,
            temperature=0.3,
        )

        content = response.choices[0].message.content
        result = self._parse_response(content)

        ad.bargain_score = result["score"]
        ad.ai_summary = result["summary"]
        ad.ai_reasoning = result["reasoning"]
        ad.is_analyzed = True
        self.session.commit()

        logger.info(f"Analyzed ad {ad.id} '{ad.title}': score={result['score']}")

        settings = SettingsService(self.session)
        if result["score"] >= 8 and settings.get_bool("telegram_notifications_enabled"):
            tg = TelegramService(
                bot_token=app_config.telegram_bot_token, chat_id=app_config.telegram_chat_id
            )

            tg.send_bargain_notification(ad)

    def _build_ad_text(self, ad: Ad, adsearch: AdSearch | None) -> str:
        """Build a text representation of the ad for the AI."""
        parts = [
            f"Titel: {ad.title}",
            f"Preis: {ad.price:.0f}€" if ad.price else "Preis: VB",
        ]

        if ad.description:
            parts.append(f"Beschreibung: {ad.description}")
        if ad.condition:
            parts.append(f"Zustand: {ad.condition}")
        if ad.shipping_cost:
            parts.append(f"Versand: {ad.shipping_cost}")
        if ad.postal_code or ad.city:
            parts.append(f"Standort: {ad.postal_code or ''} {ad.city or ''}".strip())

        seller_parts = []
        if ad.seller_name:
            seller_parts.append(f"Name: {ad.seller_name}")
        if ad.seller_type:
            seller_parts.append(f"Typ: {ad.seller_type}")
        if ad.seller_rating is not None:
            rating_labels = {2: "TOP", 1: "OK", 0: "Na ja"}
            seller_parts.append(f"Bewertung: {rating_labels.get(ad.seller_rating, 'Unbekannt')}")
        if ad.seller_is_friendly:
            seller_parts.append("Freundlich")
        if ad.seller_is_reliable:
            seller_parts.append("Zuverlässig")
        if ad.seller_active_since:
            seller_parts.append(f"Aktiv seit: {ad.seller_active_since}")

        if seller_parts:
            parts.append(f"Verkäufer: {', '.join(seller_parts)}")

        # Vergleichspreise hinzufügen
        price_context = self._build_price_context(ad)
        if price_context:
            parts.append(price_context)

        if adsearch and adsearch.prompt_addition:
            parts.append(f"Zusätzlicher Kontext: {adsearch.prompt_addition}")

        return "\n".join(parts)

    def _download_images(self, ad: Ad, max_images: int = 3) -> list[dict]:
        """Download ad images and return as base64-encoded dicts."""
        if not ad.image_urls:
            return []

        urls = ad.image_urls.split(",")[:max_images]
        image_data = fetch_binary(urls)

        images = []
        for _, data in zip(urls, image_data, strict=True):
            if data:
                media_type = self._detect_image_type(data)
                if not media_type:
                    continue

                encoded = base64.b64encode(data).decode("utf-8")
                images.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{encoded}",
                        },
                    }
                )

        return images

    @staticmethod
    def _detect_image_type(data: bytes) -> str | None:
        """Detect image MIME type from binary data."""
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if data[:2] == b"\xff\xd8":
            return "image/jpeg"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if data[:4] == b"GIF8":
            return "image/gif"
        return None

    def _build_messages(
        self, ad_text: str, images: list[dict], adsearch: AdSearch | None
    ) -> list[dict]:
        """Build the messages array for the API call."""
        content: list[dict] = [{"type": "text", "text": ad_text}]
        content.extend(images)

        return [
            {"role": "system", "content": ADANALYZER_PROMPT},
            {"role": "user", "content": content},
        ]

    @staticmethod
    def _parse_response(content: str | None) -> dict:
        """Parse the JSON response from the AI model."""
        if not content:
            raise ValueError("Empty response from AI")

        text = content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]

        result = json.loads(text)

        score = float(result["score"])
        if not 0 <= score <= 10:
            raise ValueError(f"Score {score} out of range 0-10")

        return {
            "score": score,
            "summary": str(result["summary"]),
            "reasoning": str(result["reasoning"]),
        }

    def _build_price_context(self, ad: Ad) -> str:
        """Build price comparison context from other ads in the same search."""
        other_ads = self.session.exec(
            select(Ad)
            .where(Ad.adsearch_id == ad.adsearch_id)
            .where(Ad.id != ad.id)
            .where(Ad.price.is_not(None))  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
        ).all()

        if not other_ads:
            return ""

        prices = sorted([a.price for a in other_ads])  # pyright: ignore[reportArgumentType]
        avg_price = sum(prices) / len(prices)
        median_price = prices[len(prices) // 2]

        price_list = ", ".join(f"{p:.0f}€" for p in prices)

        return (
            f"\nVergleichspreise aus derselben Suche ({len(prices)} Angebote):\n"
            f"{price_list}\n"
            f"Durchschnitt: {avg_price:.0f}€, Median: {median_price:.0f}€"
        )
