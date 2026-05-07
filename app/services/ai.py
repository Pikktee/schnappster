"""KI-Service: Anzeigen per OpenAI-kompatibler API analysieren und speichern.

Optional Telegram-Benachrichtigungen.
"""

import base64
import contextlib
import json
import logging
from collections.abc import Sequence
from io import BytesIO

from openai import BadRequestError, OpenAI  # pyright: ignore[reportMissingImports]
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core import config as app_config
from app.models.ad import Ad
from app.models.adsearch import AdSearch
from app.models.logs_aianalysis import AIAnalysisLog
from app.models.logs_error import ErrorLog
from app.prompts import render_system_prompt, render_user_prompt
from app.scraper.httpclient import fetch_binary
from app.services.deal_analysis import (
    ComparisonCandidate,
    ComparisonJudgement,
    DealAnalysisResult,
    FinalDealResult,
    MarketEstimate,
    ProductExtraction,
    build_comparison_prompt,
    build_final_prompt,
    build_market_estimate,
    build_product_prompt,
    fallback_comparison_judgements,
    fallback_final_result,
    fallback_product_extraction,
    is_gift_category_context,
    is_gift_category_search_url,
    should_use_strong_model,
    should_use_strong_model_for_gift_search,
)
from app.services.settings import SettingsService
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)

MAX_COMPARISON_ADS = 30
COMPARISON_TITLE_MAX_LEN = 80
IMAGE_MAX_EDGE_PX = 1024
IMAGE_JPEG_QUALITY = 82
REQUEST_IMAGES_TOOL_NAME = "request_product_images"
REQUEST_IMAGES_TOOL = {
    "type": "function",
    "function": {
        "name": REQUEST_IMAGES_TOOL_NAME,
        "description": (
            "Fordere die Produktbilder nur an, wenn der Text allein fuer eine faire "
            "Bewertung nicht reicht, z. B. wegen Zustand, Modellvariante, Bundle, "
            "Schaeden, Echtheit oder Vollstaendigkeit."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Kurzer Grund, warum die Bilder fuer die Bewertung noetig sind.",
                }
            },
            "required": ["reason"],
            "additionalProperties": False,
        },
    },
}


class AIService:
    """KI-Analyse per OpenAI-API: Score, Zusammenfassung, Begründung; optional Telegram."""

    def __init__(self, session: Session):
        """Erstellt den KI-Client; wirft ValueError, wenn OPENAI_API_KEY nicht gesetzt ist."""
        self.session = session
        if not app_config.openai_api_key:
            raise ValueError(
                "OpenAI-compatible API key not configured - set OPENAI_API_KEY in .env"
            )

        self.model = app_config.openai_model
        self.cheap_model = app_config.openai_cheap_model or app_config.openai_model
        self.client = OpenAI(
            base_url=app_config.openai_base_url,
            api_key=app_config.openai_api_key,
            timeout=app_config.ai_request_timeout,
        )

    def analyze_unprocessed(self, limit: int = 10) -> int:
        """Analysiert bis zu ``limit`` unbearbeitete Anzeigen (älteste zuerst); Anzahl zurück."""
        ads = self.session.exec(
            select(Ad)
            .where(Ad.is_analyzed.is_(False))  # pyright: ignore[reportAttributeAccessIssue]
            .order_by(desc(Ad.first_seen_at))  # pyright: ignore[reportArgumentType]
            .limit(limit)
        ).all()

        if not ads:
            logger.info("No unprocessed ads found")
            return 0

        for ad in ads:
            self.session.expunge(ad)
        self._release_session_connection()
        return self._analyze_ads(ads)

    def _release_session_connection(self) -> None:
        """Beendet Read-Transaktionen vor Bilddownload, OpenAI oder Telegram."""
        try:
            self.session.rollback()
        except SQLAlchemyError:
            self.session.invalidate()
        finally:
            self.session.close()

    def _analyze_ads(self, ads: Sequence[Ad]) -> int:
        """Anzeigen nacheinander; Fehler loggen und weitermachen; Zahl der Erfolge."""
        analyzed = 0
        for ad in ads:
            prompt_text_for_error = self._build_prompt_text_for_log(ad)
            self._release_session_connection()
            try:
                self._analyze_ad(ad, prompt_text_for_error)
                analyzed += 1

            except BadRequestError as e:
                error_msg = (
                    e.body.get("error", {}).get("message", str(e))
                    if isinstance(e.body, dict)
                    else str(e)
                )
                self._handle_analysis_error(ad, "API error", error_msg, prompt_text_for_error)

            except Exception as e:
                err_str = str(e)
                self._handle_analysis_error(ad, "Analysis failed", err_str, prompt_text_for_error)

        return analyzed

    def _handle_analysis_error(
        self, ad: Ad, error_type: str, message: str, prompt_text: str
    ) -> None:
        """Loggt Analysefehler, ohne dass kaputte DB-Verbindungen den Batch stoppen."""
        self._release_session_connection()
        logger.error(
            "Failed to analyze ad %s '%s': %s",
            ad.id,
            self._short_log_title(ad.title),
            self._short_log_message(message),
        )
        with contextlib.suppress(Exception):
            self._log_analysis_error(ad, error_type, message, prompt_text=prompt_text)

    @staticmethod
    def _short_log_title(title: str) -> str:
        """Kuerzt Titel fuer einzeilige Logs."""
        return title[:50] + "..." if len(title) > 50 else title

    @staticmethod
    def _short_log_message(message: str) -> str:
        """Kuerzt Fehlermeldungen fuer einzeilige Logs."""
        return message[:200] + "..." if len(message) > 200 else message

    def _build_prompt_text_for_log(self, ad: Ad) -> str:
        """Erstellt den vollen Prompt-Text (ohne Bilder) für das ErrorLog."""
        context = self._build_user_context(ad, self.session.get(AdSearch, ad.adsearch_id))
        return render_system_prompt() + "\n\n--- Nutzerinhalt ---\n\n" + render_user_prompt(context)

    def _log_analysis_error(
        self, ad: Ad, error_type: str, message: str, prompt_text: str | None = None
    ) -> None:
        """Schreibt Analysefehler ins ErrorLog, damit er im Frontend-Log erscheint."""
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
        """KI-Analyse für eine Anzeige; Score/Zusammenfassung/Begründung; Telegram ab Score 8."""
        adsearch = self.session.get(AdSearch, ad.adsearch_id)
        context = self._build_user_context(ad, adsearch)
        result = self._run_deal_pipeline(ad, context)

        final = result.final
        ad.bargain_score = final.score
        ad.ai_summary = final.summary
        ad.ai_reasoning = final.reasoning
        ad.is_analyzed = True
        db_ad = self.session.get(Ad, ad.id)
        if not db_ad:
            raise ValueError(f"Ad {ad.id} not found while saving analysis result")
        self._apply_result_to_ad(db_ad, result)
        self.session.commit()

        if ad.id is not None and ad.adsearch_id is not None:
            self.session.add(
                AIAnalysisLog(
                    ad_id=ad.id,
                    adsearch_id=ad.adsearch_id,
                    prompt_text=prompt_text_for_log,
                    ad_title=ad.title,
                    score=final.score,
                    ai_summary=final.summary,
                    ai_reasoning=final.reasoning,
                    estimated_market_price=final.estimated_market_price,
                    market_price_confidence=final.market_price_confidence,
                    price_delta_percent=final.price_delta_percent,
                    comparison_count=result.market.comparison_count,
                    comparison_summary=final.comparison_summary,
                    deal_evidence=result.evidence_json(),
                )
            )
            self.session.commit()

        logger.info("Analyzed ad %s '%s': score=%s", ad.id, ad.title, final.score)

        self._notify_if_enabled(ad, final.score)

    def _run_deal_pipeline(self, ad: Ad, context: dict) -> DealAnalysisResult:
        """Runs cheap extraction, comparison judging and final scoring."""
        self._release_session_connection()
        product = self._extract_product(ad, context)
        candidates = self._build_comparison_candidates(ad)
        self._release_session_connection()
        judgements = self._judge_comparisons(context, product, candidates)
        market = build_market_estimate(ad.price, product, candidates, judgements)
        is_gift_category = is_gift_category_context(context)
        use_strong = should_use_strong_model(
            market,
            app_config.ai_strong_model_min_delta_percent,
            app_config.ai_strong_model_min_savings_eur,
            ad.price,
        ) or should_use_strong_model_for_gift_search(product, is_gift_category)
        model = self.model if use_strong else self.cheap_model
        final = self._score_deal(ad, context, product, market, judgements, model)
        return DealAnalysisResult(
            final=final,
            product=product,
            comparisons=candidates,
            judgements=judgements,
            market=market,
            model_used=model,
            used_strong_model=use_strong,
        )

    def _extract_product(self, ad: Ad, context: dict) -> ProductExtraction:
        """Low-cost product extraction with deterministic fallback."""
        try:
            prompt = build_product_prompt(context)
            content = self._complete_json(prompt, self.cheap_model, max_tokens=500)
            return ProductExtraction.model_validate(self._parse_json_content(content))
        except Exception as exc:  # noqa: BLE001 — fallback keeps the queue moving.
            logger.warning("Product extraction fallback for ad %s: %s", ad.id, exc)
            return fallback_product_extraction(ad.title)

    def _judge_comparisons(
        self,
        context: dict,
        product: ProductExtraction,
        candidates: list[ComparisonCandidate],
    ) -> list[ComparisonJudgement]:
        """Cheap comparison relevance judgement, bounded by candidate count."""
        if not candidates:
            return []
        try:
            prompt = build_comparison_prompt(context, product, candidates)
            content = self._complete_json(prompt, self.cheap_model, max_tokens=1200)
            payload = self._parse_json_content(content)
            if not isinstance(payload, list):
                raise TypeError("Comparison judgement response must be a JSON array")
            return [ComparisonJudgement.model_validate(item) for item in payload]
        except Exception as exc:  # noqa: BLE001 — weak same-search evidence is still useful.
            logger.warning("Comparison judgement fallback: %s", exc)
            return fallback_comparison_judgements(candidates)

    def _score_deal(
        self,
        ad: Ad,
        context: dict,
        product: ProductExtraction,
        market: MarketEstimate,
        judgements: list[ComparisonJudgement],
        model: str,
    ) -> FinalDealResult:
        """Final JSON score, with model-requested images only when useful.

        Falls back to a deterministic score from the market estimate if every model call
        (cheap, then main via `_complete_json`) fails. The error is recorded in
        `ErrorLog` so the user sees it without the queue stalling.
        """
        prompt = build_final_prompt(context, product, market, judgements)
        try:
            content = self._complete_final_json(prompt, model, ad, max_tokens=1000)
            final = FinalDealResult.model_validate(self._parse_json_content(content))
            return self._fill_final_defaults(final, market)
        except Exception as exc:  # noqa: BLE001 — keep queue moving on API failure
            logger.error("Final scoring failed for ad %s: %s", ad.id, exc)
            with contextlib.suppress(Exception):
                self._log_analysis_error(ad, "Final scoring fallback", str(exc))
            return fallback_final_result(market, is_gift_category_context(context))

    def _fill_final_defaults(
        self, final: FinalDealResult, market: MarketEstimate
    ) -> FinalDealResult:
        """Ensure DB columns are filled even if a model omits optional evidence fields."""
        return final.model_copy(
            update={
                "estimated_market_price": final.estimated_market_price
                if final.estimated_market_price is not None
                else market.estimated_market_price,
                "market_price_confidence": final.market_price_confidence
                if final.market_price_confidence
                else market.market_price_confidence,
                "price_delta_percent": final.price_delta_percent
                if final.price_delta_percent is not None
                else market.price_delta_percent,
                "comparison_summary": final.comparison_summary or market.comparison_summary,
            }
        )

    def _apply_result_to_ad(self, ad: Ad, result: DealAnalysisResult) -> None:
        """Persist final score and explainable evidence on the ad row."""
        final = result.final
        ad.bargain_score = final.score
        ad.ai_summary = final.summary
        ad.ai_reasoning = final.reasoning
        ad.estimated_market_price = final.estimated_market_price
        ad.market_price_confidence = final.market_price_confidence
        ad.price_delta_percent = final.price_delta_percent
        ad.comparison_count = result.market.comparison_count
        ad.comparison_summary = final.comparison_summary
        ad.deal_evidence = result.evidence_json()
        ad.is_analyzed = True

    def _notify_if_enabled(self, ad: Ad, score: float) -> None:
        """Versendet Telegram-Benachrichtigungen gemaess UserSettings."""
        settings_service = SettingsService(self.session)
        user_settings = settings_service.get_user_settings(ad.owner_id)
        notify_min_score = user_settings.notify_min_score
        notify_telegram = user_settings.notify_telegram
        telegram_chat_id = user_settings.telegram_chat_id
        self._release_session_connection()
        if score < notify_min_score:
            return
        if notify_telegram and telegram_chat_id:
            tg = TelegramService(
                bot_token=app_config.telegram_bot_token,
                chat_id=telegram_chat_id,
            )
            tg.send_bargain_notification(ad)

    def _build_user_context(self, ad: Ad, adsearch: AdSearch | None) -> dict:
        """Erstellt das Kontext-Dict für die Nutzer-Nachricht (nur Werte, keine String-Labels)."""
        is_gift_search = is_gift_category_search_url(adsearch.url if adsearch else None)
        if ad.price is not None:
            price_display = f"{ad.price:.0f}€"
        elif is_gift_search:
            price_display = "Zu verschenken"
        else:
            price_display = "VB"
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
            "search_url": adsearch.url if adsearch else None,
            "analysis_mode": "gift_category" if is_gift_search else "priced_market",
            "is_gift_category_search": is_gift_search,
        }

    def _complete_final_json(
        self,
        prompt: str,
        model: str,
        ad: Ad,
        max_tokens: int,
    ) -> str | None:
        """Final scoring call; lets the model request images only when needed."""
        image_urls = self._image_urls(ad)
        if not image_urls:
            return self._complete_json(prompt, model, max_tokens=max_tokens)

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Antworte ausschliesslich mit validem JSON."},
                    {
                        "role": "user",
                        "content": self._final_prompt_with_image_tool_hint(prompt, len(image_urls)),
                    },
                ],  # pyright: ignore[reportArgumentType]
                tools=[REQUEST_IMAGES_TOOL],  # pyright: ignore[reportArgumentType]
                tool_choice="auto",
                max_completion_tokens=max_tokens,
                temperature=0.1,
            )
        except Exception as exc:
            logger.warning("Image-decision tool call failed; falling back to text-only: %s", exc)
            return self._complete_json(prompt, model, max_tokens=max_tokens)

        message = response.choices[0].message
        if not self._message_requests_images(message):
            return message.content

        logger.info("Model requested product images for ad %s", ad.id)
        images = self._download_images(ad)
        if not images:
            return self._complete_json(prompt, model, max_tokens=max_tokens)

        image_prompt = (
            f"{prompt}\n\n"
            f"Du hast die Produktbilder angefordert. Es sind {len(images)} optimierte "
            "Produktbilder beigefuegt. Nutze sie nur fuer sichtbare Evidenz und antworte "
            "weiterhin ausschliesslich mit validem JSON."
        )
        return self._complete_json(image_prompt, model, images=images, max_tokens=max_tokens)

    @staticmethod
    def _final_prompt_with_image_tool_hint(prompt: str, image_count: int) -> str:
        """Add a short decision hint without sending images yet."""
        return (
            f"{prompt}\n\n"
            f"Zu dieser Anzeige sind {image_count} Produktbilder vorhanden. "
            f"Wenn der Text allein fuer score/summary/reasoning genuegt, antworte direkt "
            f"mit JSON. Wenn sichtbare Details fuer die Bewertung relevant sein koennten, "
            f"rufe das Tool {REQUEST_IMAGES_TOOL_NAME} auf."
        )

    @staticmethod
    def _message_requests_images(message: object) -> bool:
        """Detect whether the model chose the product-image tool."""
        tool_calls = getattr(message, "tool_calls", None) or []
        return any(
            getattr(getattr(tool_call, "function", None), "name", None) == REQUEST_IMAGES_TOOL_NAME
            for tool_call in tool_calls
        )

    @staticmethod
    def _image_urls(ad: Ad) -> list[str]:
        """Return all non-empty image URLs once, preserving scraper order."""
        if not ad.image_urls:
            return []
        urls = [url.strip() for url in ad.image_urls.split(",") if url.strip()]
        return list(dict.fromkeys(urls))

    def _download_images(self, ad: Ad) -> list[dict]:
        """Lädt alle Bilder; Liste von ``image_url``-Dicts mit optimierten Base64-Data-URLs."""
        if not ad.image_urls:
            return []

        urls = self._image_urls(ad)
        image_data = fetch_binary(urls)

        images = []
        for _, data in zip(urls, image_data, strict=True):
            if data:
                optimized = self._optimize_image(data)
                media_type = self._detect_image_type(optimized)
                if not media_type:
                    continue

                encoded = base64.b64encode(optimized).decode("utf-8")
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
    def _optimize_image(data: bytes) -> bytes:
        """Downscale and compress images before sending them to the model."""
        try:
            with Image.open(BytesIO(data)) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((IMAGE_MAX_EDGE_PX, IMAGE_MAX_EDGE_PX), Image.Resampling.LANCZOS)
                if image.mode in {"RGBA", "LA"}:
                    background = Image.new("RGB", image.size, "white")
                    alpha = image.getchannel("A")
                    background.paste(image.convert("RGBA"), mask=alpha)
                    image = background
                elif image.mode != "RGB":
                    image = image.convert("RGB")

                output = BytesIO()
                image.save(
                    output,
                    format="JPEG",
                    quality=IMAGE_JPEG_QUALITY,
                    optimize=True,
                    progressive=True,
                )
                return output.getvalue()
        except (OSError, UnidentifiedImageError):
            return data

    @staticmethod
    def _detect_image_type(data: bytes) -> str | None:
        """Erkennt MIME-Typ anhand der Magic-Bytes (PNG, JPEG, WebP, GIF); None bei unbekannt."""
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
        """Nachrichtenliste für Chat-Completion: System-Prompt + Nutzerinhalt (Text + Bilder)."""
        content: list[dict] = [{"type": "text", "text": user_content}]
        content.extend(images)

        return [
            {"role": "system", "content": render_system_prompt()},
            {"role": "user", "content": content},
        ]

    def _complete_json(
        self,
        prompt: str,
        model: str,
        images: list[dict] | None = None,
        max_tokens: int = 1000,
    ) -> str | None:
        """Calls an OpenAI-compatible model and expects JSON-only text.

        If the chosen model fails (e.g. misconfigured cheap model), retries once with the
        configured main model so a broken cheap-model env var cannot stall the queue.
        """
        try:
            return self._chat_json(prompt, model, images, max_tokens)
        except Exception as exc:
            if model == self.model:
                raise
            logger.warning(
                "Model %s failed (%s); falling back to main model %s", model, exc, self.model
            )
            return self._chat_json(prompt, self.model, images, max_tokens)

    def _chat_json(
        self,
        prompt: str,
        model: str,
        images: list[dict] | None,
        max_tokens: int,
    ) -> str | None:
        """Single chat completion call, no fallback."""
        content: str | list[dict]
        if images:
            multimodal_content: list[dict] = [{"type": "text", "text": prompt}]
            multimodal_content.extend(images)
            content = multimodal_content
        else:
            content = prompt

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Antworte ausschliesslich mit validem JSON."},
                {"role": "user", "content": content},
            ],  # pyright: ignore[reportArgumentType]
            max_completion_tokens=max_tokens,
            temperature=0.1,
        )
        return response.choices[0].message.content

    @staticmethod
    def _sanitize_json_control_chars(s: str) -> str:
        """Ersetzt rohe Steuerzeichen (z. B. Zeilenumbruch) in JSON-Strings durch \\n/\\r/\\t,
        damit json.loads() nicht mit „Invalid control character“ abbricht."""
        result: list[str] = []
        in_string = False
        escape = False
        i = 0
        while i < len(s):
            c = s[i]
            if escape:
                result.append(c)
                escape = False
                i += 1
                continue
            if c == "\\" and in_string:
                result.append(c)
                escape = True
                i += 1
                continue
            if c == '"':
                in_string = not in_string
                result.append(c)
                i += 1
                continue
            if in_string and ord(c) < 32 and c != " ":
                if c == "\n":
                    result.append("\\n")
                elif c == "\r":
                    result.append("\\r")
                elif c == "\t":
                    result.append("\\t")
                else:
                    result.append(" ")
                i += 1
                continue
            result.append(c)
            i += 1
        return "".join(result)

    @staticmethod
    def _parse_response(content: str | None) -> dict:
        """JSON aus der Modellantwort → score, summary, reasoning; wirft bei Ungültigkeit."""
        result = AIService._parse_json_content(content)
        if not isinstance(result, dict):
            raise TypeError("KI-Antwort muss ein JSON-Objekt sein")

        score = float(result["score"])
        if not 0 <= score <= 10:
            raise ValueError(f"Score {score} außerhalb des gültigen Bereichs 0–10")

        return {
            "score": score,
            "summary": str(result["summary"]),
            "reasoning": str(result["reasoning"]),
        }

    @staticmethod
    def _parse_json_content(content: str | None) -> object:
        """Parse JSON content from plain text or Markdown fenced model output."""
        if not content:
            raise ValueError("Leere Antwort von der KI")

        text = content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]

        text = AIService._sanitize_json_control_chars(text)
        return json.loads(text)

    def _build_price_context(self, ad: Ad) -> dict | None:
        """Vergleichsdaten aus anderen Anzeigen derselben Suche (Titel, Zustand) oder None."""
        other_ads = self.session.exec(
            select(Ad)
            .where(Ad.adsearch_id == ad.adsearch_id)
            .where(Ad.id != ad.id)
            .where(Ad.price.is_not(None))  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
            .order_by(Ad.price)
            .limit(MAX_COMPARISON_ADS)
        ).all()

        if not other_ads:
            return None

        entries = []
        for a in other_ads:
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

    def _build_comparison_candidates(self, ad: Ad) -> list[ComparisonCandidate]:
        """Build bounded same-search comparison candidates for the evidence pipeline."""
        other_ads = self.session.exec(
            select(Ad)
            .where(Ad.adsearch_id == ad.adsearch_id)
            .where(Ad.id != ad.id)
            .where(Ad.price.is_not(None))  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
            .order_by(Ad.price)
            .limit(app_config.ai_max_comparison_candidates)
        ).all()

        return [
            ComparisonCandidate(
                id=other_ad.id,
                title=self._short_title(other_ad.title),
                price=float(other_ad.price or 0),
                condition=(other_ad.condition or "").strip() or None,
            )
            for other_ad in other_ads
            if other_ad.price and other_ad.price > 0
        ]

    @staticmethod
    def _short_title(title: str) -> str:
        """Shortens comparison titles for prompts and evidence."""
        text = (title or "").strip()
        if len(text) <= COMPARISON_TITLE_MAX_LEN:
            return text
        return text[: COMPARISON_TITLE_MAX_LEN - 1] + "…"
