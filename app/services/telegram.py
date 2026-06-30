"""Telegram-Benachrichtigungen für hoch bewertete Schnäppchen."""

import logging

import httpx

from app.models.ad import Ad

logger = logging.getLogger(__name__)


class TelegramService:
    """Sendet Nachrichten in einen Telegram-Chat über die Bot-API."""

    def __init__(self, bot_token: str, chat_id: str):
        """Speichert Bot-Token und Chat-ID; baut die sendMessage-API-URL."""
        self.bot_token = bot_token.strip() if bot_token else ""
        self.chat_id = chat_id.strip() if chat_id else ""
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_bargain_notification(self, ad: Ad) -> None:
        """Sendet die formatierte Anzeige an den Telegram-Chat; no-op wenn nicht konfiguriert."""
        if not self.is_configured:
            logger.debug("Telegram is not configured, skipping notification")
            return

        text = self._format_message(ad)
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            # Wir nutzen einen Context-Manager für den Client
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(self.api_url, json=payload)
                if not resp.is_success:
                    logger.warning("Telegram API error: %s %s", resp.status_code, resp.text)
                else:
                    logger.info("Telegram notification sent for ad %s", ad.id)
        except Exception as e:
            logger.warning("Failed to send Telegram notification: %s", e)

    def send_price_alert(
        self,
        name: str,
        url: str,
        old_price: float | None,
        new_price: float,
        currency: str | None = None,
        threshold: float | None = None,
    ) -> None:
        """Sendet eine Preisänderungs-Benachrichtigung; no-op wenn nicht konfiguriert."""
        if not self.is_configured:
            logger.debug("Telegram is not configured, skipping price alert")
            return

        text = self._format_price_message(name, url, old_price, new_price, currency, threshold)
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(self.api_url, json=payload)
                if not resp.is_success:
                    logger.warning("Telegram API error: %s %s", resp.status_code, resp.text)
                else:
                    logger.info("Telegram price alert sent for %s", name)
        except Exception as e:
            logger.warning("Failed to send Telegram price alert: %s", e)

    @property
    def is_configured(self) -> bool:
        """True, wenn Bot-Token und Chat-ID gesetzt sind."""
        return bool(self.bot_token and self.chat_id)

    @staticmethod
    def _format_price_message(
        name: str,
        url: str,
        old_price: float | None,
        new_price: float,
        currency: str | None,
        threshold: float | None,
    ) -> str:
        """Markdown für Telegram: Name, URL, alter→neuer Preis, optional Schwelle."""
        unit = f" {currency}" if currency else ""
        new_str = f"{new_price:.2f}{unit}"
        if old_price is not None:
            arrow = "📉" if new_price < old_price else "📈"
            change = f"{arrow} {old_price:.2f}{unit} → *{new_str}*"
        else:
            change = f"Aktueller Preis: *{new_str}*"
        threshold_line = (
            f"\n🎯 Zielpreis {threshold:.2f}{unit} erreicht!" if threshold is not None else ""
        )
        return f"💰 *Preisänderung: {name}*\n\n{change}{threshold_line}\n\n🔗 {url}"

    def _format_message(self, ad: Ad) -> str:
        """Markdown für Telegram: Titel, URL, Preis, Score, Zusammenfassung, Begründung."""
        price_str = f"{ad.price:.0f} €" if ad.price is not None else "VB"
        score_str = f"{ad.bargain_score:.1f}" if ad.bargain_score is not None else "–"

        summary = ad.ai_summary or ""
        reasoning = ad.ai_reasoning or ""
        ki_text = f"{summary}\n\n{reasoning}".strip() if reasoning else summary

        return (
            f"**{ad.title}**\n\n"
            f"🔗 {ad.url}\n\n"
            f"Preis: {price_str}\n"
            f"Bargain-Score: {score_str}/10\n\n"
            f"{ki_text}"
        )
