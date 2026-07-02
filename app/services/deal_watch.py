"""Deal-Watch-Service: fällige Deal-Alarme prüfen, neue MyDealz-Deals finden, benachrichtigen.

Erst-Check = stille Baseline: die bereits vorhandenen Deals werden gespeichert (im Bereich
sichtbar), aber es wird nicht benachrichtigt. Erst danach lösen **neue** Deals über der
optionalen Temperatur-Schwelle einen Alarm aus (In-App + optional Telegram).
"""

import logging
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from app.core import config as app_config
from app.models.deal_watch import Deal, DealWatch
from app.models.logs_error import ErrorLog
from app.models.notification import NOTIFICATION_DEAL_HOT
from app.scraper import mydealz
from app.services.notification import NotificationService
from app.services.settings import SettingsService
from app.services.telegram import TelegramService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DealWatchSnapshot:
    """Entkoppelte Watch-Daten, damit beim HTTP-Abruf keine DB-Verbindung gehalten wird."""

    id: int
    owner_id: str
    name: str
    query: str
    min_temperature: float | None
    last_checked_at: datetime | None
    scrape_interval_minutes: int


@dataclass
class DealCheckResult:
    """Ergebnis einer einzelnen Deal-Alarm-Prüfung."""

    status: str  # "ok" | "error" | "gone"
    new_deals: int = 0
    alarms: int = 0
    error: str | None = None


class DealWatchService:
    """Orchestriert Deal-Checks: fällige Watches, Deals holen, neue erkennen, benachrichtigen."""

    def __init__(self, session: Session):
        """Erstellt den Service mit der übergebenen Datenbank-Session."""
        self.session = session

    def check_due_watches(self) -> int:
        """Prüft alle aktiven, fälligen Deal-Alarme; Anzahl ausgelöster Alarme."""
        watches = [
            _snapshot_watch(watch)
            for watch in self.session.exec(
                select(DealWatch).where(col(DealWatch.is_active).is_(True))
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
                total_alarms += result.alarms
            except Exception as exc:
                logger.error("Deal-Check fehlgeschlagen '%s': %s", watch.name, exc)
                self._log_error(watch.id, str(exc), traceback.format_exc())
        return total_alarms

    @staticmethod
    def _is_due(watch: DealWatch | DealWatchSnapshot, now: datetime) -> bool:
        """True, wenn das Intervall abgelaufen ist oder noch nie geprüft wurde."""
        if watch.last_checked_at is None:
            return True
        next_check = watch.last_checked_at + timedelta(minutes=watch.scrape_interval_minutes)
        if next_check.tzinfo is None:
            next_check = next_check.replace(tzinfo=UTC)
        return now >= next_check

    def check_watch(self, watch: DealWatch | DealWatchSnapshot) -> DealCheckResult:
        """Prüft einen Deal-Alarm: Suche holen, Deals parsen, neue erkennen, ggf. Alarm auslösen."""
        snap = _snapshot_watch(watch)
        self._release_session_connection()

        status, html = mydealz.fetch_deals_html(mydealz.build_search_url(snap.query))
        if not mydealz.is_usable(status, html):
            return self._handle_failure(snap.id, status)

        deals = mydealz.parse_deals(html)
        return self._process_deals(snap, deals)

    def _handle_failure(self, watch_id: int, status: int) -> DealCheckResult:
        """Vermerkt einen Abruffehler am Watch (sichtbar im UI)."""
        watch = self.session.get(DealWatch, watch_id)
        if watch is None:
            return DealCheckResult(status="gone")
        watch.last_checked_at = datetime.now(UTC)
        watch.consecutive_failures += 1
        watch.last_error = (
            f"MyDealz nicht erreichbar (HTTP {status})" if status else "MyDealz nicht erreichbar"
        )
        self.session.add(watch)
        self.session.commit()
        return DealCheckResult(status="error", error=watch.last_error)

    def _process_deals(
        self, snap: DealWatchSnapshot, deals: list[mydealz.MydealzDeal]
    ) -> DealCheckResult:
        """Speichert neue Deals; benachrichtigt (außer beim Erst-Check) über der Schwelle."""
        watch = self.session.get(DealWatch, snap.id)
        if watch is None:
            return DealCheckResult(status="gone")
        watch.last_checked_at = datetime.now(UTC)
        watch.last_error = None
        watch.consecutive_failures = 0

        is_first_check = snap.last_checked_at is None
        existing = set(
            self.session.exec(select(Deal.external_id).where(Deal.deal_watch_id == snap.id)).all()
        )

        to_notify: list[mydealz.MydealzDeal] = []
        for deal in deals:
            if deal.external_id in existing:
                continue
            notify = (not is_first_check) and _meets_threshold(deal, snap.min_temperature)
            self.session.add(_to_deal_row(snap.owner_id, snap.id, deal, notified=notify))
            if notify:
                to_notify.append(deal)
        self.session.commit()

        for deal in to_notify:
            self._dispatch_alarm(snap, deal)
        return DealCheckResult(status="ok", new_deals=len(to_notify), alarms=len(to_notify))

    def _dispatch_alarm(self, snap: DealWatchSnapshot, deal: mydealz.MydealzDeal) -> None:
        """Erzeugt die In-App-Benachrichtigung und sendet optional Telegram."""
        title, body = _build_alarm_content(deal)
        NotificationService(self.session).create(
            snap.owner_id, NOTIFICATION_DEAL_HOT, title, body, f"/deal-alarms/{snap.id}"
        )

        settings = SettingsService(self.session).get_user_settings(snap.owner_id)
        if settings.notify_price_telegram and settings.telegram_chat_id:
            telegram = TelegramService(app_config.telegram_bot_token, settings.telegram_chat_id)
            telegram.send_deal_alert(
                snap.name, deal.title, deal.url, deal.temperature, deal.price, deal.merchant
            )

    def _log_error(self, watch_id: int, message: str, details: str) -> None:
        """Schreibt einen Fehlereintrag (ohne AdSearch-Bezug) in das Error-Log."""
        try:
            self.session.add(
                ErrorLog(
                    adsearch_id=None,
                    error_type="DealWatchError",
                    message=f"[DealWatch {watch_id}] {message}",
                    details=details,
                )
            )
            self.session.commit()
        except Exception:
            logger.exception("Failed to persist deal watch error")

    def _release_session_connection(self) -> None:
        """Beendet reine Read-Transaktionen vor langen externen Netzwerkaufrufen."""
        try:
            self.session.rollback()
        except SQLAlchemyError:
            self.session.invalidate()
        finally:
            self.session.close()


def _meets_threshold(deal: mydealz.MydealzDeal, min_temperature: float | None) -> bool:
    """True, wenn der Deal (ohne Schwelle immer) die Temperatur-Schwelle erreicht."""
    if min_temperature is None:
        return True
    return deal.temperature is not None and deal.temperature >= min_temperature


def _to_deal_row(
    owner_id: str, watch_id: int, deal: mydealz.MydealzDeal, *, notified: bool
) -> Deal:
    """Baut eine Deal-Zeile aus einem geparsten MyDealz-Deal."""
    return Deal(
        owner_id=owner_id,
        deal_watch_id=watch_id,
        external_id=deal.external_id,
        title=deal.title,
        url=deal.url,
        temperature=deal.temperature,
        price=deal.price,
        next_best_price=deal.next_best_price,
        merchant=deal.merchant,
        image_url=deal.image_url,
        published_at=deal.published_at,
        notified=notified,
    )


def _build_alarm_content(deal: mydealz.MydealzDeal) -> tuple[str, str]:
    """Baut Titel und Text für die In-App-Benachrichtigung eines Deals."""
    temp = f"{deal.temperature:.0f}° " if deal.temperature is not None else ""
    title = f"🔥 {temp}Neuer Deal: {deal.title}".strip()
    parts = []
    if deal.price is not None:
        parts.append(f"{deal.price:.2f} €")
    if deal.next_best_price is not None and deal.price is not None:
        parts.append(f"statt {deal.next_best_price:.2f} €")
    if deal.merchant:
        parts.append(f"@ {deal.merchant}")
    body = " ".join(parts) if parts else (deal.merchant or "")
    return title, body


def _snapshot_watch(watch: DealWatch | DealWatchSnapshot) -> DealWatchSnapshot:
    """Erzeugt einen entkoppelten Snapshot eines Deal-Alarms."""
    if isinstance(watch, DealWatchSnapshot):
        return watch
    return DealWatchSnapshot(
        id=watch.id,  # type: ignore[arg-type]
        owner_id=watch.owner_id,
        name=watch.name,
        query=watch.query,
        min_temperature=watch.min_temperature,
        last_checked_at=watch.last_checked_at,
        scrape_interval_minutes=watch.scrape_interval_minutes,
    )
