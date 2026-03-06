import logging

from app.core import settings
from app.models.ad import Ad

logger = logging.getLogger(__name__)


def is_telegram_configured() -> bool:
    """
    Return True if Telegram bot token and chat ID are set in .env.
    """
    return bool(settings.telegram_bot_token.strip() and settings.telegram_chat_id.strip())


def send_bargain_notification(ad: Ad) -> None:
    """
    Send a Telegram message for an identified bargain.
    Logs errors and does not raise, so the analysis flow continues.
    """
    if not is_telegram_configured():
        logger.debug("Telegram not configured, skipping notification")
        return

    price_str = f"{ad.price:.0f} €" if ad.price is not None else "VB"
    score_str = f"{ad.bargain_score:.1f}" if ad.bargain_score is not None else "–"
    summary = ad.ai_summary or ""
    reasoning = ad.ai_reasoning or ""
    ki_text = f"{summary}\n\n{reasoning}".strip() if reasoning else summary

    text = (
        f"**{ad.title}**\n\n"
        f"🔗 {ad.url}\n\n"
        f"Preis: {price_str}\n"
        f"Bargain-Score: {score_str}/10\n\n"
        f"{ki_text}"
    )

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        import httpx

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            if not resp.is_success:
                logger.warning(
                    "Telegram API error: %s %s",
                    resp.status_code,
                    resp.text,
                )
            else:
                logger.info("Telegram notification sent for ad %s", ad.id)
    except Exception as e:
        logger.warning("Failed to send Telegram notification: %s", e)
