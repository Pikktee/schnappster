"""KI-Service: Anzeigen per OpenAI-kompatibler API analysieren und speichern.

Optional Telegram-Benachrichtigungen.
"""

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
    """KI-Analyse per OpenAI-API: Score, Zusammenfassung, Begründung; optional Telegram."""

    def __init__(self, session: Session):
        """Erstellt den KI-Client; wirft ValueError, wenn OPENAI_API_KEY nicht gesetzt ist."""
        self.session = session
        if not app_config.openai_api_key:
            raise ValueError(
                "OpenAI-compatible API key not configured - set OPENAI_API_KEY in .env"
            )

        self.model = app_config.openai_model
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
        self.session.rollback()

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
                    pass  # Fehlerlog bestmöglich
                # mit nächster Anzeige weitermachen

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
                    pass  # Fehlerlog bestmöglich
                # mit nächster Anzeige weitermachen

        return analyzed

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
        user_content = render_user_prompt(context)
        self._release_session_connection()
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
        db_ad = self.session.get(Ad, ad.id)
        if not db_ad:
            raise ValueError(f"Ad {ad.id} not found while saving analysis result")
        db_ad.bargain_score = result["score"]
        db_ad.ai_summary = result["summary"]
        db_ad.ai_reasoning = result["reasoning"]
        db_ad.is_analyzed = True
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

        self._notify_if_enabled(ad, result["score"])

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
        """Lädt bis zu ``max_images`` Bilder; Liste von ``image_url``-Dicts (Base64-Data-URLs)."""
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
        if not content:
            raise ValueError("Leere Antwort von der KI")

        text = content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]

        # Einige APIs (z. B. Dashscope) liefern JSON mit echten Zeilenumbrüchen in Strings;
        # json.loads erlaubt nur escaped \n. Vor dem Parsen innerhalb von Strings escapen.
        text = AIService._sanitize_json_control_chars(text)

        result = json.loads(text)

        score = float(result["score"])
        if not 0 <= score <= 10:
            raise ValueError(f"Score {score} außerhalb des gültigen Bereichs 0–10")

        return {
            "score": score,
            "summary": str(result["summary"]),
            "reasoning": str(result["reasoning"]),
        }

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
