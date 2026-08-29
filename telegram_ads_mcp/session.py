"""Process-wide client factory. Secrets come only from the environment."""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

from telegram_ads_mcp.client import ConfigError, StarsCabinetError, TelegramAdsClient

log = logging.getLogger("telegram_ads_mcp.session")

# owner_id -> client. The empty key is the currently selected default.
_clients: dict[str, TelegramAdsClient] = {}
_active_key = ""


def env_ready() -> bool:
    return bool(os.environ.get("STEL_TOKEN") and os.environ.get("STEL_SSID"))


def missing_env_message() -> str:
    return (
        "STEL_TOKEN and STEL_SSID are not set. Copy .env.example to .env, "
        "paste cookies from ads.telegram.org, then call reload_session. "
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
    load_dotenv(override=True)
    await close_all()
    return await get_client()


async def get_client() -> TelegramAdsClient:
    global _active_key
    if not env_ready():
        load_dotenv()
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


def fail_payload(exc: BaseException) -> dict[str, Any]:
    from telegram_ads_mcp.client import AuthError

    if isinstance(exc, ConfigError):
        return {"ok": False, "error": str(exc), "code": "config"}
    if isinstance(exc, AuthError):
        return {"ok": False, "error": str(exc), "code": "auth"}
    if isinstance(exc, StarsCabinetError):
        return {"ok": False, "error": str(exc), "code": "stars_cabinet", "cabinet": "stars"}
    log.exception("unexpected error")
    return {"ok": False, "error": str(exc), "code": "error"}
