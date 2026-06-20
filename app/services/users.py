"""Benutzerbezogene Schreiboperationen (Konto-Loeschung inkl. aller App-Daten)."""

from sqlalchemy import delete, func
from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.ad import Ad
from app.models.adsearch import AdSearch
from app.models.logs_aianalysis import AIAnalysisLog
from app.models.logs_error import ErrorLog
from app.models.logs_scraperun import ScrapeRun
from app.models.settings_user import UserSettings
from app.models.user import User


def ensure_admin_from_env(session: Session, email: str, password: str) -> bool:
    """Legt beim Start einen Admin aus ADMIN_EMAIL/ADMIN_PASSWORD an, falls noch nicht vorhanden.

    Gibt ``True`` zurueck, wenn ein Konto angelegt wurde.
    """
    normalized = (email or "").strip().lower()
    if not normalized or not password:
        return False
    existing = session.exec(select(User).where(User.email == normalized)).first()
    if existing is not None:
        return False
    session.add(
        User(
            email=normalized,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
    )
    session.commit()
    return True


def count_active_admins(session: Session) -> int:
    """Zaehlt freigeschaltete Admin-Konten (Schutz vor dem Loeschen des letzten Admins)."""
    stmt = (
        select(func.count())
        .select_from(User)
        .where(User.role == "admin", User.is_active == True)  # noqa: E712
    )
    return int(session.exec(stmt).one())


def delete_user_and_data(session: Session, user_id: str) -> None:
    """Entfernt alle App-Daten eines Users, dessen Settings und das Konto selbst.

    Loeschreihenfolge folgt den Fremdschluesseln (Kinder vor Eltern), damit SQLite mit
    aktivem ``foreign_keys=ON`` nicht blockiert.
    """
    user_search_ids = select(AdSearch.id).where(AdSearch.owner_id == user_id)
    user_ad_ids = select(Ad.id).where(Ad.owner_id == user_id)

    session.execute(delete(AIAnalysisLog).where(AIAnalysisLog.adsearch_id.in_(user_search_ids)))
    session.execute(delete(AIAnalysisLog).where(AIAnalysisLog.ad_id.in_(user_ad_ids)))
    session.execute(delete(ErrorLog).where(ErrorLog.adsearch_id.in_(user_search_ids)))
    session.execute(delete(ScrapeRun).where(ScrapeRun.adsearch_id.in_(user_search_ids)))
    session.execute(delete(Ad).where(Ad.owner_id == user_id))
    session.execute(delete(AdSearch).where(AdSearch.owner_id == user_id))
    session.execute(delete(UserSettings).where(UserSettings.user_id == user_id))
    session.execute(delete(User).where(User.id == user_id))
    session.commit()
