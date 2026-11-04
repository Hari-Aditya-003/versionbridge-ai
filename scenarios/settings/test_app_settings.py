import pytest


def test_default_settings():
    from app_settings import AppSettings

    settings = AppSettings()
    assert (settings.service_name, settings.retries) == ("versionbridge", 3)


def test_environment_override(monkeypatch: pytest.MonkeyPatch):
    from app_settings import AppSettings

    monkeypatch.setenv("RETRIES", "5")
    assert AppSettings().retries == 5
