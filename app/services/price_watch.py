"""Preis-Watch-Service: fällige Watches prüfen, Preise extrahieren, Alarme auslösen."""

import logging
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from app.core import config as app_config
from app.models.logs_error import ErrorLog
from app.models.notification import (
    NOTIFICATION_PRICE_BELOW_THRESHOLD,
    NOTIFICATION_PRICE_DROP,
)
from app.models.price_watch import PricePoint, PriceWatch
from app.scraper.httpclient import fetch_with_proxy_fallback
from app.services.notification import NotificationService
from app.services.price_extractor import extract_price
from app.services.settings import SettingsService
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PriceWatchSnapshot:
    """Entkoppelte Watch-Daten, damit beim HTTP-Abruf keine DB-Verbindung gehalten wird."""

    id: int
    owner_id: str
    name: str
    url: str
    locator: dict
    currency: str | None
    notify_threshold: float | None
    last_price: float | None
    last_checked_at: datetime | None
    scrape_interval_minutes: int


@dataclass
class PriceCheckResult:
    """Ergebnis einer einzelnen Watch-Prüfung."""

    status: str  # "ok" | "error" | "gone"
    new_price: float | None = None
    old_price: float | None = None
    alarm_triggered: bool = False
    error: str | None = None


class PriceWatchService:
    """Orchestriert Preis-Checks: fällige Watches, Preis holen, vergleichen, benachrichtigen."""

    def __init__(self, session: Session):
        """Erstellt den Service mit der übergebenen Datenbank-Session."""
        self.session = session

    def check_due_watches(self) -> int:
        """Prüft alle aktiven, fälligen Watches; Anzahl ausgelöster Alarme."""
        watches = [
            _snapshot_watch(watch)
            for watch in self.session.exec(
                select(PriceWatch).where(col(PriceWatch.is_active).is_(True))
            ).all()
            if watch.id is not None
        ]
        self._release_session_connection()

        total_alarms = 0
        now = datetime.now(UTC)
        for watch in watches:
            if not self._is_due(watch, now):
                continue
            try:
                result = self.check_watch(watch)
                if result.alarm_triggered:
                    total_alarms += 1
            except Exception as exc:
                logger.error("Preis-Check fehlgeschlagen '%s': %s", watch.name, exc)
                self._log_error(watch.id, str(exc), traceback.format_exc())
        return total_alarms

    @staticmethod
    def _is_due(watch: PriceWatch | PriceWatchSnapshot, now: datetime) -> bool:
        """True, wenn das Intervall abgelaufen ist oder noch nie geprüft wurde."""
        if watch.last_checked_at is None:
            return True
        next_check = watch.last_checked_at + timedelta(minutes=watch.scrape_interval_minutes)
        if next_check.tzinfo is None:
            next_check = next_check.replace(tzinfo=UTC)
        return now >= next_check

    def check_watch(self, watch: PriceWatch | PriceWatchSnapshot) -> PriceCheckResult:
        """Prüft einen Watch: Seite holen, Preis extrahieren, vergleichen, ggf. Alarm auslösen."""
        snap = _snapshot_watch(watch)
        self._release_session_connection()

        def has_price(status: int, html: str) -> bool:
            return status == 200 and extract_price(html, snap.locator)[0] is not None

        status, html = fetch_with_proxy_fallback(snap.url, has_price)
        new_price, detected_currency = (None, None)
        if status == 200 and html:
            new_price, detected_currency = extract_price(html, snap.locator)

        db_watch = self.session.get(PriceWatch, snap.id)
        if db_watch is None:
            return PriceCheckResult(status="gone")

        db_watch.last_checked_at = datetime.now(UTC)
        if new_price is None:
            return self._handle_failure(db_watch, status)
        return self._handle_price(db_watch, snap, new_price, detected_currency)

    def _handle_failure(self, watch: PriceWatch, status: int) -> PriceCheckResult:
        """Vermerkt einen Extraktionsfehler am Watch (sichtbar im UI)."""
        watch.consecutive_failures += 1
        watch.last_error = (
            f"Preis nicht gefunden (HTTP {status})" if status else "Seite nicht erreichbar"
        )
        self.session.add(watch)
        self.session.commit()
        return PriceCheckResult(status="error", error=watch.last_error)

    def _handle_price(
        self,
        watch: PriceWatch,
        snap: PriceWatchSnapshot,
        new_price: float,
        detected_currency: str | None,
    ) -> PriceCheckResult:
        """Verarbeitet einen gelesenen Preis: speichern, vergleichen, benachrichtigen."""
        watch.last_error = None
        watch.consecutive_failures = 0
        currency = detected_currency or watch.currency
        if currency:
            watch.currency = currency

        old_price = watch.last_price
        first_check = old_price is None
        if first_check:
            watch.initial_price = new_price
        if first_check or new_price != old_price:
            watch.last_price = new_price
            self._add_point(watch, new_price, currency)

        alarm_type = _evaluate_alarm(snap.notify_threshold, old_price, new_price, first_check)
        self.session.add(watch)
        self.session.commit()

        if alarm_type:
            self._dispatch_alarm(watch, old_price, new_price, currency, alarm_type)
        return PriceCheckResult(
            status="ok",
            new_price=new_price,
            old_price=old_price,
            alarm_triggered=bool(alarm_type),
        )

    def _add_point(self, watch: PriceWatch, price: float, currency: str | None) -> None:
        """Speichert einen Preis-Datenpunkt (nur bei Änderung aufgerufen)."""
        self.session.add(
            PricePoint(
                owner_id=watch.owner_id,
                pricewatch_id=watch.id,  # type: ignore[arg-type]
                price=price,
                currency=currency,
            )
        )

    def _dispatch_alarm(
        self,
        watch: PriceWatch,
        old_price: float | None,
        new_price: float,
        currency: str | None,
        alarm_type: str,
    ) -> None:
        """Erzeugt die In-App-Benachrichtigung und sendet optional Telegram."""
        title, body, link = _build_alarm_content(watch, old_price, new_price, currency, alarm_type)
        NotificationService(self.session).create(watch.owner_id, alarm_type, title, body, link)

        settings = SettingsService(self.session).get_user_settings(watch.owner_id)
        if settings.notify_price_telegram and settings.telegram_chat_id:
            TelegramService(
                app_config.telegram_bot_token, settings.telegram_chat_id
            ).send_price_alert(
                watch.name, watch.url, old_price, new_price, currency, watch.notify_threshold
            )

    def _log_error(self, watch_id: int, message: str, details: str) -> None:
        """Schreibt einen Fehlereintrag (ohne AdSearch-Bezug) in das Error-Log."""
        try:
            self.session.add(
                ErrorLog(
                    adsearch_id=None,
                    error_type="PriceWatchError",
                    message=f"[Watch {watch_id}] {message}",
                    details=details,
                )
            )
            self.session.commit()
        except Exception:
            logger.exception("Failed to persist price watch error")

    def _release_session_connection(self) -> None:
        """Beendet reine Read-Transaktionen vor langen externen Netzwerkaufrufen."""
        try:
            self.session.rollback()
        except SQLAlchemyError:
            self.session.invalidate()
        finally:
            self.session.close()


def _evaluate_alarm(
    threshold: float | None,
    old_price: float | None,
    new_price: float,
    first_check: bool,
) -> str | None:
    """Entscheidet, ob (und welcher Typ) Alarm ausgelöst wird.

    Mit Schwelle: Alarm beim Unterschreiten (gefallen oder initial schon darunter).
    Ohne Schwelle: Alarm bei jeder Preissenkung.
    """
    dropped = old_price is not None and new_price < old_price
    if threshold is not None:
        below = new_price <= threshold
        if below and (dropped or first_check):
            return NOTIFICATION_PRICE_BELOW_THRESHOLD
        return None
    if dropped:
        return NOTIFICATION_PRICE_DROP
    return None


def _build_alarm_content(
    watch: PriceWatch,
    old_price: float | None,
    new_price: float,
    currency: str | None,
    alarm_type: str,
) -> tuple[str, str, str]:
    """Baut Titel, Text und In-App-Link für die Benachrichtigung."""
    unit = f" {currency}" if currency else ""
    if alarm_type == NOTIFICATION_PRICE_BELOW_THRESHOLD:
        title = f"Zielpreis erreicht: {watch.name}"
    else:
        title = f"Preis gefallen: {watch.name}"
    if old_price is not None:
        body = f"{old_price:.2f}{unit} → {new_price:.2f}{unit}"
    else:
        body = f"Aktueller Preis: {new_price:.2f}{unit}"
    return title, body, f"/price-alerts/{watch.id}"


def _snapshot_watch(watch: PriceWatch | PriceWatchSnapshot) -> PriceWatchSnapshot:
    """Erzeugt einen entkoppelten Snapshot eines Watches."""
    if isinstance(watch, PriceWatchSnapshot):
        return watch
    return PriceWatchSnapshot(
        id=watch.id,  # type: ignore[arg-type]
        owner_id=watch.owner_id,
        name=watch.name,
        url=watch.url,
        locator=dict(watch.locator or {}),
        currency=watch.currency,
        notify_threshold=watch.notify_threshold,
        last_price=watch.last_price,
        last_checked_at=watch.last_checked_at,
        scrape_interval_minutes=watch.scrape_interval_minutes,
    )
