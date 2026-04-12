"""Validierung der Nutzer-Profil-/Settings-Pydantic-Modelle."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.settings_user import UserProfileUpdate, UserSettingsUpdate


def test_user_profile_update_strips_and_accepts_unicode_name() -> None:
    m = UserProfileUpdate(display_name="  José  ")
    assert m.display_name == "José"


def test_user_profile_update_rejects_digits_only() -> None:
    with pytest.raises(ValidationError):
        UserProfileUpdate(display_name="12345")


def test_user_profile_update_rejects_whitespace_only() -> None:
    with pytest.raises(ValidationError):
        UserProfileUpdate(display_name="   \t")


def test_user_profile_update_requires_field() -> None:
    with pytest.raises(ValidationError):
        UserProfileUpdate.model_validate({})


def test_user_settings_update_omits_display_name() -> None:
    m = UserSettingsUpdate(notify_telegram=True)
    assert m.display_name is None


def test_user_settings_update_valid_display_name() -> None:
    m = UserSettingsUpdate(display_name="  Anna  ")
    assert m.display_name == "Anna"


def test_user_settings_update_rejects_no_letter_when_set() -> None:
    with pytest.raises(ValidationError):
        UserSettingsUpdate(display_name="___")
