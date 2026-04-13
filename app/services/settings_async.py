"""Async-Zugriff auf UserSettings fuer FastAPI-async-Routen (kein Sync-Session-Pool)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings_user import UserSettings


class SettingsAsyncService:
    """Entspricht den UserSettings-Teilen von SettingsService, aber mit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_settings(self, user_id: str, default_display_name: str = "") -> UserSettings:
        user_settings = await self.session.get(UserSettings, user_id)
        if user_settings:
            return user_settings
        user_settings = UserSettings(
            user_id=user_id,
            display_name=(default_display_name or "").strip(),
            display_name_user_set=False,
        )
        self.session.add(user_settings)
        await self.session.commit()
        await self.session.refresh(user_settings)
        return user_settings

    async def hydrate_display_name_from_identity(
        self,
        user_id: str,
        identity_display_name: str,
    ) -> UserSettings:
        identity_display_name = (identity_display_name or "").strip()
        settings = await self.get_user_settings(user_id, default_display_name=identity_display_name)
        if settings.display_name_user_set:
            return settings
        if identity_display_name and not (settings.display_name or "").strip():
            settings.display_name = identity_display_name
            self.session.add(settings)
            await self.session.commit()
            await self.session.refresh(settings)
        return settings
