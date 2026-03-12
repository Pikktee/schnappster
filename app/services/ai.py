"""AI service: analyze ads via OpenAI-compatible API, persist scores, optional Telegram."""

import base64
import json
import logging
from collections.abc import Sequence

from openai import BadRequestError, OpenAI  # pyright: ignore[reportMissingImports]
from sqlalchemy import desc
from sqlmodel import Session, select

from app.core import config as app_config
from app.models.ad import Ad
from app.models.adsearch import AdSearch
from app.models.logs_aianalysis import AIAnalysisLog
from app.models.logs_error import ErrorLog
from app.prompts import render_system_prompt, render_user_prompt
from app.scraper.httpclient import fetch_binary
from app.services.settings import SettingsService
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)

MAX_COMPARISON_ADS = 30
COMPARISON_TITLE_MAX_LEN = 80


class AIService:
    """Analyzes ads via OpenAI API; assigns bargain score, summary, reasoning; optional Telegram."""

    def __init__(self, session: Session):
        """Create AI client; raise ValueError if OPENAI_API_KEY is not set."""
        self.session = session
        if not app_config.openai_api_key:
            raise ValueError(
                "OpenAI-compatible API key not configured - set OPENAI_API_KEY in .env"
            )

        self.model = app_config.openai_model
        self.client = OpenAI(
            base_url=app_config.openai_base_url,
            api_key=app_config.openai_api_key,
        )

    def analyze_unprocessed(self, limit: int = 10) -> int:
        """Analyze up to limit unprocessed ads (oldest first); return count analyzed."""
        ads = self.session.exec(
            select(Ad)
            .where(Ad.is_analyzed.is_(False))  # pyright: ignore[reportAttributeAccessIssue]
            .order_by(desc(Ad.first_seen_at))  # pyright: ignore[reportArgumentType]
            .limit(limit)
        ).all()

        if not ads:
            logger.info("No unprocessed ads found")
            return 0

        return self._analyze_ads(ads)

    def _analyze_ads(self, ads: Sequence[Ad]) -> int:
        """Process ads one by one; on error log and continue; return count successfully analyzed."""
        analyzed = 0
        for ad in ads:
            prompt_text_for_error = self._build_prompt_text_for_log(ad)
            try:
                self._analyze_ad(ad, prompt_text_for_error)
                analyzed += 1

            except BadRequestError as e:
                self.session.rollback()
                error_msg = (
                    e.body.get("error", {}).get("message", str(e))
                    if isinstance(e.body, dict)
                    else str(e)
                )
                # Kurze, einzeilige Meldung für Konsole (vermeidet Rich-Rendering-Probleme)
                logger.error(
                    "API error for ad %s '%s': %s",
                    ad.id,
                    ad.title[:50] + "..." if len(ad.title) > 50 else ad.title,
                    error_msg[:200] + "..." if len(error_msg) > 200 else error_msg,
                )
                try:  # noqa: SIM105
                    self._log_analysis_error(
                        ad, "API error", error_msg, prompt_text=prompt_text_for_error
                    )
                except Exception:
                    pass  # best-effort error logging
                # continue with next ad

            except Exception as e:
                self.session.rollback()
                err_str = str(e)
                logger.error(
                    "Failed to analyze ad %s '%s': %s",
                    ad.id,
                    ad.title[:50] + "..." if len(ad.title) > 50 else ad.title,
                    err_str[:200] + "..." if len(err_str) > 200 else err_str,
                )
                try:  # noqa: SIM105
                    self._log_analysis_error(
                        ad, "Analysis failed", err_str, prompt_text=prompt_text_for_error
                    )
                except Exception:
                    pass  # best-effort error logging
                # continue with next ad

        return analyzed

    def _build_prompt_text_for_log(self, ad: Ad) -> str:
        """Build full prompt text (no images) for logging to ErrorLog."""
        context = self._build_user_context(ad, self.session.get(AdSearch, ad.adsearch_id))
        return render_system_prompt() + "\n\n--- Nutzerinhalt ---\n\n" + render_user_prompt(context)

    def _log_analysis_error(
        self, ad: Ad, error_type: str, message: str, prompt_text: str | None = None
    ) -> None:
        """Persist analysis error to ErrorLog so it appears in the frontend log."""
        details = message
        if prompt_text:
            details += "\n\n--- Prompt ---\n" + prompt_text
        self.session.add(
            ErrorLog(
                adsearch_id=ad.adsearch_id,
                error_type="AIAnalysisError",
                message=(
                    f"Ad {ad.id} ({ad.title[:60]}{'…' if len(ad.title) > 60 else ''}): {error_type}"
                ),
                details=details,
            )
        )
        self.session.commit()

    def _analyze_ad(self, ad: Ad, prompt_text_for_log: str) -> None:
        """Run AI analysis on one ad; update score/summary/reasoning; Telegram if score >= 8."""
        adsearch = self.session.get(AdSearch, ad.adsearch_id)
        context = self._build_user_context(ad, adsearch)
        user_content = render_user_prompt(context)
        images = self._download_images(ad)

        messages = self._build_messages(user_content, images)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # pyright: ignore[reportArgumentType]
            max_completion_tokens=1000,
            temperature=0.3,
        )

        content = response.choices[0].message.content
        result = self._parse_response(content)

        ad.bargain_score = result["score"]
        ad.ai_summary = result["summary"]
        ad.ai_reasoning = result["reasoning"]
        ad.is_analyzed = True
        self.session.commit()

        if ad.id is not None and ad.adsearch_id is not None:
            self.session.add(
                AIAnalysisLog(
                    ad_id=ad.id,
                    adsearch_id=ad.adsearch_id,
                    prompt_text=prompt_text_for_log,
                    ad_title=ad.title,
                    score=result["score"],
                    ai_summary=result["summary"],
                    ai_reasoning=result["reasoning"],
                )
            )
            self.session.commit()

        logger.info(f"Analyzed ad {ad.id} '{ad.title}': score={result['score']}")

        settings = SettingsService(self.session)
        if result["score"] >= 8 and settings.get_bool("telegram_notifications_enabled"):
            tg = TelegramService(
                bot_token=app_config.telegram_bot_token, chat_id=app_config.telegram_chat_id
            )

            tg.send_bargain_notification(ad)

    def _build_user_context(self, ad: Ad, adsearch: AdSearch | None) -> dict:
        """Build context dict for the user-message template (no string labels, only values)."""
        price_display = f"{ad.price:.0f}€" if ad.price else "VB"
        location = ""
        if ad.postal_code or ad.city:
            location = f"{ad.postal_code or ''} {ad.city or ''}".strip()

        comparison = self._build_price_context(ad)
        user_instructions = None
        if adsearch and adsearch.prompt_addition and (adsearch.prompt_addition or "").strip():
            user_instructions = (adsearch.prompt_addition or "").strip()

        return {
            "title": ad.title or "",
            "price_display": price_display,
            "description": ad.description or None,
            "condition": ad.condition or None,
            "shipping_cost": ad.shipping_cost or None,
            "location": location or None,
            "seller_name": ad.seller_name or None,
            "seller_type": ad.seller_type or None,
            "seller_rating": ad.seller_rating,
            "seller_friendly": bool(ad.seller_is_friendly),
            "seller_reliable": bool(ad.seller_is_reliable),
            "seller_active_since": ad.seller_active_since or None,
            "comparison": comparison,
            "user_instructions": user_instructions,
        }

    def _download_images(self, ad: Ad, max_images: int = 1) -> list[dict]:
        """Download up to max_images from ad; return list of image_url dicts (base64 data URLs)."""
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
        """Detect MIME type from magic bytes (PNG, JPEG, WebP, GIF); return None if unknown."""
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if data[:2] == b"\xff\xd8":
            return "image/jpeg"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if data[:4] == b"GIF8":
            return "image/gif"
        return None

    def _build_messages(self, user_content: str, images: list[dict]) -> list[dict]:
        """Build messages list for chat completion: system prompt + user content (text + images)."""
        content: list[dict] = [{"type": "text", "text": user_content}]
        content.extend(images)

        return [
            {"role": "system", "content": render_system_prompt()},
            {"role": "user", "content": content},
        ]

    @staticmethod
    def _parse_response(content: str | None) -> dict:
        """Parse JSON from model; return dict with score, summary, reasoning; raise on invalid."""
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

    def _build_price_context(self, ad: Ad) -> dict | None:
        """Return comparison data from other ads in same AdSearch (titles, condition), or None."""
        other_ads = self.session.exec(
            select(Ad)
            .where(Ad.adsearch_id == ad.adsearch_id)
            .where(Ad.id != ad.id)
            .where(Ad.price.is_not(None))  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
        ).all()

        if not other_ads:
            return None

        # Sort by price for consistent order; limit to avoid huge prompts
        sorted_ads = sorted(other_ads, key=lambda a: a.price or 0)
        limited = sorted_ads[:MAX_COMPARISON_ADS]

        entries = []
        for a in limited:
            title = (a.title or "").strip()
            if len(title) > COMPARISON_TITLE_MAX_LEN:
                title = title[: COMPARISON_TITLE_MAX_LEN - 1] + "…"
            entries.append(
                {
                    "title": title,
                    "price": a.price,
                    "condition": (a.condition or "").strip() or None,
                }
            )

        prices = [e["price"] for e in entries]
        avg_price = sum(prices) / len(prices)
        median_price = prices[len(prices) // 2]
        price_list = ", ".join(f"{p:.0f}€" for p in prices)

        return {
            "entries": entries,
            "prices": prices,
            "count": len(prices),
            "price_list": price_list,
            "average": int(round(avg_price)),
            "median": int(round(median_price)),
        }
