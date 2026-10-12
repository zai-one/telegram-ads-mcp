"""Suggest-only update check against public GitHub releases of zai-one/telegram-ads-mcp.

One unauthenticated HTTPS GET with a short timeout, cached for 24 hours. Every
attempt is recorded: after a failed fetch the next one waits 30 minutes, and
``force`` is honoured at most once a minute. Offline, rate-limited or malformed
answers degrade to ``status="unavailable"`` (or the last good result). Only
plain version tags (``v1.2.3``) are accepted. Nothing is ever downloaded or
installed; the result only names the command the operator may run. Set
``TG_ADS_DISABLE_UPDATE_CHECK=1`` to turn the check off.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from telegram_ads_mcp import __version__

REPO = "zai-one/telegram-ads-mcp"
DISTRIBUTION = "telegram-ads-mcp"
DISABLE_ENV = "TG_ADS_DISABLE_UPDATE_CHECK"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases"
CACHE_TTL_SECONDS = 24 * 60 * 60
FAILURE_BACKOFF_SECONDS = 30 * 60
FORCE_MIN_INTERVAL_SECONDS = 60
TIMEOUT_SECONDS = 3.0
MAX_RESPONSE_BYTES = 1_048_576
# Plain version tags only; ASCII digits (``\d`` would also accept other scripts).
_VERSION = re.compile(r"v?([0-9]{1,6}(?:\.[0-9]{1,6}){0,3})")
_PLAIN_VERSION = re.compile(r"[0-9]{1,6}(?:\.[0-9]{1,6}){0,3}")
_RELEASE_URL = re.compile(re.escape(f"{RELEASES_URL}/tag/") + r"v?[0-9]{1,6}(?:\.[0-9]{1,6}){0,3}")
RUN_IN = {
    "git": "your telegram-ads-mcp git checkout",
    "package": "the Python environment that runs telegram-ads-mcp",
}

Fetcher = Callable[[str, float], bytes]


def disabled() -> bool:
    return os.environ.get(DISABLE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def parse_version(value: Any) -> tuple[int, ...] | None:
    if not isinstance(value, str):
        return None
    match = _VERSION.fullmatch(value)
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def _is_newer(latest: str, current: str) -> bool | None:
    left, right = parse_version(latest), parse_version(current)
    if left is None or right is None:
        return None
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) > right + (0,) * (width - len(right))


def cache_path() -> Path:
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"])
    elif os.environ.get("XDG_CACHE_HOME"):
        base = Path(os.environ["XDG_CACHE_HOME"])
    else:
        base = Path.home() / ".cache"
    return base / DISTRIBUTION / "update-check.json"


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _read_cache() -> dict[str, Any]:
    """Validated cache record; anything malformed or not a plain version is dropped.

    Keys: ``attempted_at`` (last fetch attempt, success or failure), ``failed``,
    and the last good result ``checked_at`` / ``latest_version`` / ``release_url``
    (all ``None`` when there is none).
    """
    empty: dict[str, Any] = {
        "attempted_at": None,
        "failed": False,
        "checked_at": None,
        "latest_version": None,
        "release_url": None,
    }
    try:
        path = cache_path()
        if path.stat().st_size > 65_536:
            return empty
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty
    if not isinstance(data, dict):
        return empty
    record = dict(empty)
    checked_at = _number(data.get("checked_at"))
    latest = data.get("latest_version")
    if checked_at is not None and isinstance(latest, str) and _PLAIN_VERSION.fullmatch(latest):
        release_url = data.get("release_url")
        record.update(
            checked_at=checked_at,
            latest_version=latest,
            release_url=release_url
            if isinstance(release_url, str) and _RELEASE_URL.fullmatch(release_url)
            else None,
        )
    attempted_at = _number(data.get("attempted_at"))
    record["attempted_at"] = attempted_at if attempted_at is not None else checked_at
    record["failed"] = data.get("failed") is True
    return record


def _write_cache(record: dict[str, Any]) -> None:
    try:
        path = cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        pass


def _default_fetch(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": f"{DISTRIBUTION}/{__version__} update-check",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https URL
        return response.read(MAX_RESPONSE_BYTES + 1)


def _parse_release(body: bytes) -> dict[str, Any]:
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("release response too large")
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("unexpected release response")
    tag = data.get("tag_name")
    version = parse_version(tag)
    if version is None:
        raise ValueError("release tag is not a plain version")
    latest = ".".join(str(part) for part in version)
    release_url = data.get("html_url")
    if not isinstance(release_url, str) or not _RELEASE_URL.fullmatch(release_url):
        release_url = f"{RELEASES_URL}/tag/{tag}"
    return {"latest_version": latest, "release_url": release_url}


def _install_kind() -> str:
    """Return ``git`` for a source checkout, otherwise ``package``."""
    root = Path(__file__).resolve().parents[1]
    return "git" if (root / ".git").exists() and (root / "pyproject.toml").is_file() else "package"


def update_command(latest: str) -> str:
    """Executable shell command only; where to run it is ``RUN_IN[_install_kind()]``."""
    if _install_kind() == "git":
        return "git pull --ff-only && uv sync"
    return f'pip install --upgrade "{DISTRIBUTION} @ git+https://github.com/{REPO}@v{latest}"'


def _within(moment: float, since: float | None, window: float) -> bool:
    return since is not None and 0 <= moment - since < window


def _should_fetch(record: dict[str, Any], moment: float, force: bool) -> bool:
    attempted_at = record["attempted_at"]
    if _within(moment, attempted_at, FORCE_MIN_INTERVAL_SECONDS):
        return False  # at most one attempt a minute, forced or not
    if force:
        return True
    if _within(moment, record["checked_at"], CACHE_TTL_SECONDS):
        return False
    return not (record["failed"] and _within(moment, attempted_at, FAILURE_BACKOFF_SECONDS))


def check_for_update(
    *, force: bool = False, fetch: Fetcher | None = None, now: float | None = None
) -> dict[str, Any]:
    """Compare the installed version with the latest GitHub release. Never raises."""
    current = __version__
    result: dict[str, Any] = {
        "current_version": current,
        "latest_version": None,
        "update_available": None,
        "status": "unavailable",
        "source": None,
        "checked_at": None,
        "release_notes_url": RELEASES_URL,
        "update_command": None,
        "run_in": None,
        "auto_update": False,
        "disable_with": f"{DISABLE_ENV}=1",
    }
    if disabled():
        result["status"] = "disabled"
        return result
    moment = time.time() if now is None else now
    record = _read_cache()
    if _should_fetch(record, moment, force):
        try:
            fetcher = fetch if fetch is not None else _default_fetch
            fetched = _parse_release(fetcher(LATEST_RELEASE_API, TIMEOUT_SECONDS))
        except Exception:  # offline, HTTP error, rate limit, malformed JSON: degrade quietly
            fetched = None
        if fetched is not None:
            record = {"attempted_at": moment, "failed": False, "checked_at": moment, **fetched}
            result["source"] = "github"
        else:
            record = {**record, "attempted_at": moment, "failed": True}
        _write_cache(record)
    if record["latest_version"] is None:
        return result
    if result["source"] is None:
        # A failed attempt (now or within the backoff) or an expired entry makes the answer stale.
        fresh = _within(moment, record["checked_at"], CACHE_TTL_SECONDS) and not record["failed"]
        result["source"] = "cache" if fresh else "stale_cache"
    newer = _is_newer(record["latest_version"], current)
    result.update(
        latest_version=record["latest_version"],
        update_available=newer,
        status="update_available" if newer else "up_to_date",
        checked_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record["checked_at"])),
        release_notes_url=record["release_url"] or RELEASES_URL,
    )
    if newer:
        result.update(update_command=update_command(record["latest_version"]), run_in=RUN_IN[_install_kind()])
    return result


def cached_update_hint() -> str | None:
    """One-line startup hint from the cache only; never touches the network."""
    if disabled():
        return None
    latest = _read_cache()["latest_version"]
    if latest is None or not _is_newer(latest, __version__):
        return None
    return (
        f"Update available: {DISTRIBUTION} {__version__} -> {latest}. "
        f"Call check_update for release notes and the update command; "
        "nothing is installed automatically."
    )


def refresh_in_background() -> None:
    """Refresh a stale cache on a daemon thread so startup never waits on the network.

    Obeys the same rules as ``check_for_update``: 24 h cache, 30 min after a failure.
    """
    if disabled() or not _should_fetch(_read_cache(), time.time(), force=False):
        return
    threading.Thread(target=check_for_update, name="update-check", daemon=True).start()
