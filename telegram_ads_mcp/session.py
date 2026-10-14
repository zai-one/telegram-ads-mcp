"""Process-wide client factory. Secrets come only from the environment."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, load_dotenv

from telegram_ads_mcp.client import ConfigError, StarsCabinetError, TelegramAdsClient

log = logging.getLogger("telegram_ads_mcp.session")

# owner_id -> client. The empty key is the currently selected default.
_clients: dict[str, TelegramAdsClient] = {}
_active_key = ""


# The working directory belongs to whatever project the MCP host started the server in, so its
# .env is not ours: only the session cookies are taken from it. Transport, bind address and the
# write gate must never be switchable by an unrelated project's .env.
_CWD_ENV_PREFIX = "STEL_"


def _cwd_cookies() -> dict[str, str]:
    """STEL_* keys from ``<cwd>/.env`` only. No parent walk, nothing else is imported."""
    try:
        path = Path.cwd() / ".env"
    except OSError:
        return {}
    if not path.is_file():
        return {}
    return {
        key: value
        for key, value in dotenv_values(path).items()
        if key.startswith(_CWD_ENV_PREFIX) and value is not None
    }


def _checkout_env() -> dict[str, str]:
    """The repo checkout's .env, as on master: the nearest .env upward from this package's
    directory (not from the working directory, whatever the interpreter mode)."""
    here = Path(__file__).resolve().parent
    for folder in (here, *here.parents):
        path = folder / ".env"
        if path.is_file():
            return {key: value for key, value in dotenv_values(path).items() if value is not None}
    return {}


def load_env(override: bool = False) -> None:
    """Load settings and cookies. Values never leave the process.

    1. ``TG_ADS_ENV_FILE`` if set: that file is trusted in full and nothing else is read.
    2. Otherwise the repo checkout's .env (full trust, as before), plus ``STEL_*`` from
       ``<cwd>/.env`` (uvx / plugin installs). The cwd file wins for ``STEL_*``; any other key
       in it (MCP_HOST, MCP_TRANSPORT, TG_ADS_WRITE_GATE, ...) is ignored.
    """
    explicit = os.environ.get("TG_ADS_ENV_FILE", "").strip()
    if explicit:
        load_dotenv(explicit, override=override)
        return
    values = _checkout_env()
    values.update(_cwd_cookies())
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value


def env_ready() -> bool:
    return bool(os.environ.get("STEL_TOKEN") and os.environ.get("STEL_SSID"))


def missing_env_message() -> str:
    return (
        "STEL_TOKEN and STEL_SSID are not set. Copy .env.example to .env, "
        "use INSTALL.md DevTools steps, then call reload_session. "
        "Do not paste cookies into chat."
    )


def _build_client() -> TelegramAdsClient:
    token = os.environ.get("STEL_TOKEN", "").strip()
    ssid = os.environ.get("STEL_SSID", "").strip()
    owner = os.environ.get("STEL_ADOWNER", "").strip() or None
    if not token or not ssid:
        raise ConfigError(missing_env_message())
    return TelegramAdsClient(stel_token=token, stel_ssid=ssid, stel_adowner=owner)


async def close_all() -> None:
    global _active_key
    for client in list(_clients.values()):
        try:
            await client.aclose()
        except Exception:  # noqa: BLE001
            pass
    _clients.clear()
    _active_key = ""


async def reload_from_env() -> TelegramAdsClient:
    """Re-read .env (override) and rebuild the active client. No cookie args."""
    load_env(override=True)
    await close_all()
    return await get_client()


async def get_client() -> TelegramAdsClient:
    global _active_key
    if not env_ready():
        load_env()
    if not env_ready():
        raise ConfigError(missing_env_message())
    key = _active_key
    client = _clients.get(key)
    if client is None:
        client = _build_client()
        _clients[key] = client
    return client


async def switch_account(owner_id: str) -> TelegramAdsClient:
    """Select a cabinet and keep a per-owner client so parallel cabinets don't clash."""
    global _active_key
    client = await get_client()
    await client.select_account(owner_id)
    await client.authenticate()
    _active_key = owner_id
    _clients[owner_id] = client
    if "" in _clients and _clients[""] is not client:
        try:
            await _clients[""].aclose()
        except Exception:  # noqa: BLE001
            pass
        _clients.pop("", None)
    _clients[""] = client
    log.info("active owner_id=%s", owner_id)
    return client


_ERROR_HINTS: dict[str, tuple[bool, str]] = {
    "config": (False, "Set STEL_TOKEN/STEL_SSID in .env (INSTALL.md), then call reload_session."),
    "auth": (False, "Offer INSTALL.md DevTools steps; the user updates .env on disk, then reload_session."),
    "stars_cabinet": (False, "Stars is opt-in: set TG_ADS_STARS=on or switch via list_accounts."),
    "error": (True, "Unexpected error; retry once, then offer an Issue without secrets."),
}


def _with_hint(payload: dict[str, Any]) -> dict[str, Any]:
    retryable, hint = _ERROR_HINTS[payload["code"]]
    payload.update(retryable=retryable, hint=hint, docs=f"ads://guide/errors#{payload['code']}")
    return payload


def fail_payload(exc: BaseException) -> dict[str, Any]:
    """Structured failure: ok=false, error (text), code, retryable, hint, docs."""
    from telegram_ads_mcp.client import AuthError

    if isinstance(exc, ConfigError):
        return _with_hint({"ok": False, "error": str(exc), "code": "config"})
    if isinstance(exc, AuthError):
        return _with_hint({"ok": False, "error": str(exc), "code": "auth"})
    if isinstance(exc, StarsCabinetError):
        return _with_hint({"ok": False, "error": str(exc), "code": "stars_cabinet", "cabinet": "stars"})
    log.exception("unexpected error")
    return _with_hint({"ok": False, "error": str(exc), "code": "error"})
