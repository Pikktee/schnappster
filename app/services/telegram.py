import logging

import httpx

from app.models.ad import Ad

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initializes the Telegram service.
        """
        self.bot_token = bot_token.strip() if bot_token else ""
        self.chat_id = chat_id.strip() if chat_id else ""
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    @property
    def is_configured(self) -> bool:
        """
        Checks if the service is configured.
        """

        return bool(self.bot_token and self.chat_id)

    def _format_message(self, ad: Ad) -> str:
        """
        Formats the message for Telegram.
        """
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

    def send_bargain_notification(self, ad: Ad) -> None:
        """
        Sends notification to Telegram.
        """
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
