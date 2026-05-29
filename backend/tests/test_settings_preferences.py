"""Settings preferences validation tests."""

import pytest
from fastapi import HTTPException

from app.users.routes_settings import VALID_THEMES, update_preferences, PreferencesSettings


class _User:
    username = "tester"


@pytest.mark.parametrize("theme", sorted(VALID_THEMES))
def test_valid_theme_values(theme):
    prefs = PreferencesSettings(theme=theme)
    assert prefs.theme == theme


def test_invalid_theme_rejected_by_route():
    prefs = PreferencesSettings(theme="neon")
    with pytest.raises(HTTPException) as exc:
        import asyncio
        asyncio.run(update_preferences(preferences=prefs, current_user=_User()))
    assert exc.value.status_code == 400
    assert "Invalid theme" in exc.value.detail
