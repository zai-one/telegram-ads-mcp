"""Unit tests are not a live cabinet — do not block mutating helpers."""

import os

import pytest

os.environ.setdefault("TG_ADS_WRITE_GATE", "open")
# Never reach GitHub from tests; update-check tests opt back in with a mocked fetch.
os.environ["TG_ADS_DISABLE_UPDATE_CHECK"] = "1"


@pytest.fixture(autouse=True)
def _no_github(monkeypatch):
    """The real fetcher is swapped out, so a test that forgets ``fetch=`` fails loudly."""
    from telegram_ads_mcp import update_check

    calls: list[str] = []

    def refuse(url: str, timeout: float) -> bytes:
        calls.append(url)
        raise OSError("network is off in tests")

    monkeypatch.setattr(update_check, "_default_fetch", refuse)
    yield
    assert calls == [], f"test tried to reach GitHub: {calls}"
