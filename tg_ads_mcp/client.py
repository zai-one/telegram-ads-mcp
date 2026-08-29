"""Async HTTP client for the ads.telegram.org internal API."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import anyio
import httpx

from tg_ads_mcp.parse import (
    detect_cabinet,
    derived_metrics,
    extract_api_hash,
    extract_balance,
    extract_json_value,
    extract_owner_id,
    parse_accounts,
    parse_chart,
    redact,
    strip_empty,
    unescape_names,
)

log = logging.getLogger("tg_ads_mcp.client")

BASE_URL = "https://ads.telegram.org"
USER_AGENT = "tg-ads-mcp/0.2.0"


class AuthError(Exception):
    """Session cookies are invalid or expired."""


class ConfigError(Exception):
    """Required environment is missing."""


class StarsCabinetError(Exception):
    """Active cabinet is Stars — this server refuses to operate on it."""


class TelegramAdsClient:
    """Cookie-authenticated wrapper around ads.telegram.org.

    One instance is bound to one selected owner_id. Switch cabinets with
    `select_account` (invalidates api_hash and cabinet caches).
    """

    def __init__(
        self,
        stel_token: str,
        stel_ssid: str,
        stel_adowner: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not stel_token or not stel_ssid:
            raise ConfigError("STEL_TOKEN and STEL_SSID are required.")
        self.api_hash: str | None = None
        self.owner_id: str | None = None
        self._api_url: str | None = None
        self._cabinet: dict[str, Any] | None = None
        self._user_targeting_ref: dict[str, Any] | None = None
        self._channel_targeting_ref: dict[str, Any] | None = None
        self._account_html: str | None = None
        cookies: dict[str, str] = {
            "stel_token": stel_token,
            "stel_ssid": stel_ssid,
        }
        if stel_adowner:
            cookies["stel_adowner"] = stel_adowner
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            cookies=cookies,
            headers={
                "Origin": BASE_URL,
                "Referer": f"{BASE_URL}/account",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": USER_AGENT,
            },
            timeout=timeout,
            follow_redirects=False,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        retries: int = 3,
        xhr: bool = True,
        follow_redirects: bool | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}) or {})
        if not xhr:
            headers["X-Requested-With"] = ""
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                resp = await self._http.request(
                    method,
                    url,
                    headers=headers or None,
                    follow_redirects=bool(follow_redirects) if follow_redirects is not None else False,
                    **kwargs,
                )
            except httpx.TransportError as exc:
                last_exc = exc
                log.warning("transport error %s %s: %s", method, url, exc)
                await anyio.sleep(0.4 * (2**attempt))
                continue
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                log.warning("retryable HTTP %s on %s %s", resp.status_code, method, url)
                await anyio.sleep(0.4 * (2**attempt))
                continue
            return resp
        if last_exc:
            raise last_exc
        raise AuthError(f"request failed after {retries} attempts: {method} {url}")

    async def _get_html(self, path: str, follow_redirects: bool = True) -> httpx.Response:
        return await self._request(
            "GET",
            path,
            xhr=False,
            follow_redirects=follow_redirects,
        )

    def _raise_if_login(self, resp: httpx.Response, html: str) -> None:
        location = resp.headers.get("location", "")
        if resp.status_code in (301, 302, 303, 307, 308):
            if "login" in location or "auth" in location:
                raise AuthError("Session expired — cookies are no longer valid. Update .env and call reload_session.")
            raise AuthError(f"Unexpected redirect to {location}")
        if "Log in" in html and "tgme_widget" in html:
            raise AuthError("Not logged in — session cookies are invalid or expired. Update .env and call reload_session.")

    async def list_accounts(self) -> list[dict[str, str]]:
        resp = await self._get_html("/choose_account?to=account", follow_redirects=False)
        if resp.status_code in (301, 302, 303, 307, 308):
            self._raise_if_login(resp, "")
        if resp.status_code != 200:
            raise AuthError(f"Unexpected status {resp.status_code} listing accounts")
        html = resp.text
        self._raise_if_login(resp, html)
        return parse_accounts(html)

    async def select_account(self, owner_id: str) -> None:
        resp = await self._get_html(f"/choose_account/{owner_id}", follow_redirects=False)
        # Cookie is set by the platform; also force it locally.
        self._http.cookies.set("stel_adowner", owner_id, domain="ads.telegram.org")
        self.api_hash = None
        self.owner_id = None
        self._api_url = None
        self._cabinet = None
        self._user_targeting_ref = None
        self._channel_targeting_ref = None
        self._account_html = None
        log.info("selected account %s (status %s)", owner_id, resp.status_code)

    async def authenticate(self) -> dict[str, Any]:
        resp = await self._get_html("/account", follow_redirects=True)
        if resp.status_code != 200:
            raise AuthError(f"Unexpected status {resp.status_code}")
        html = resp.text
        self._raise_if_login(resp, html)

        if "choose_account" in str(resp.url) or "pr-account-button" in html:
            accounts = await self.list_accounts()
            if not accounts:
                raise AuthError("No ad accounts found for this Telegram user.")
            adowner = self._http.cookies.get("stel_adowner")
            selected = next((a for a in accounts if a["owner_id"] == adowner), None) if adowner else None
            if not selected:
                selected = next((a for a in accounts if a["owner_id"] != "new"), accounts[0])
            await self.select_account(selected["owner_id"])
            resp = await self._get_html("/account", follow_redirects=True)
            if resp.status_code != 200:
                raise AuthError(f"Failed to load account after selection: {resp.status_code}")
            html = resp.text
            self._raise_if_login(resp, html)

        api_hash = extract_api_hash(html)
        if not api_hash:
            raise AuthError("Could not extract api_hash from page HTML — layout may have changed.")
        self.api_hash = api_hash
        self._api_url = f"/api?hash={api_hash}"
        self.owner_id = extract_owner_id(html) or self._http.cookies.get("stel_adowner")
        if not self.owner_id:
            raise AuthError("Could not determine owner_id")
        self._account_html = html
        log.info("authenticated owner_id=%s", self.owner_id)
        return {"ok": True, "owner_id": self.owner_id}

    async def _ensure_auth(self) -> None:
        if self._api_url is None:
            await self.authenticate()

    async def _invalidate_auth(self) -> None:
        self._api_url = None
        self.api_hash = None

    async def detect_cabinet(self) -> dict[str, Any]:
        if self._cabinet is not None:
            return self._cabinet
        await self._ensure_auth()
        account_html = self._account_html or ""
        if not account_html:
            resp = await self._get_html("/account", follow_redirects=True)
            account_html = resp.text
            self._account_html = account_html
        new_resp = await self._get_html("/account/ad/new", follow_redirects=True)
        self._cabinet = detect_cabinet(account_html, new_resp.text)
        log.info("cabinet=%s currency=%s", self._cabinet.get("cabinet"), self._cabinet.get("currency"))
        return self._cabinet

    async def require_supported_cabinet(self) -> dict[str, Any]:
        info = await self.detect_cabinet()
        if info.get("cabinet") == "stars":
            raise StarsCabinetError(
                "Stars cabinet detected. This server only supports TON (primary) and EUR cabinets. "
                "Call list_accounts / select_account to switch away from Stars."
            )
        return info

    async def get_account(self) -> dict[str, Any]:
        await self._ensure_auth()
        cabinet = await self.detect_cabinet()
        html = self._account_html or ""
        budget_html = ""
        try:
            budget_resp = await self._get_html("/account/budget", follow_redirects=True)
            if budget_resp.status_code == 200:
                budget_html = budget_resp.text
        except Exception as exc:  # noqa: BLE001 — budget page is optional
            log.debug("budget page failed: %s", exc)
        balance = extract_balance(budget_html) or extract_balance(html)
        for key in ("balance", "accountBalance", "funds"):
            val = extract_json_value(budget_html or html, key)
            if val is not None and balance is None:
                balance = str(val)
                break
        return {
            "ok": True,
            "owner_id": self.owner_id,
            "cabinet": cabinet["cabinet"],
            "currency": cabinet["currency"],
            "supports_user_targeting": cabinet["supports_user_targeting"],
            "supported": cabinet["supported"],
            "balance": balance,
        }

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        retry_auth: bool = True,
        keep: set[str] | None = None,
    ) -> dict[str, Any]:
        await self._ensure_auth()
        data: dict[str, Any] = {"method": method}
        if params:
            data.update(strip_empty(params, keep=keep))
        resp = await self._request("POST", self._api_url or "/api", data=data)
        if resp.status_code in (301, 302, 303, 307, 308):
            if retry_auth:
                log.info("auth redirect on %s — re-authenticating", method)
                await self._invalidate_auth()
                await self.authenticate()
                return await self.call(method, params, retry_auth=False, keep=keep)
            raise AuthError("Session expired during API call. Update .env and call reload_session.")
        resp.raise_for_status()
        try:
            result = resp.json()
        except json.JSONDecodeError as exc:
            raise AuthError(f"Non-JSON response from {method}: {redact(resp.text[:200])}") from exc
        if isinstance(result, dict) and result.get("error") == "AUTH_REQUIRED":
            if retry_auth:
                log.info("AUTH_REQUIRED on %s — re-authenticating", method)
                await self._invalidate_auth()
                await self.authenticate()
                return await self.call(method, params, retry_auth=False, keep=keep)
            raise AuthError("API returned AUTH_REQUIRED — session expired. Update .env and call reload_session.")
        return result

    async def get_ads_list(self, offset_id: str | None = None) -> dict[str, Any]:
        return await self.call("getAdsList", {"owner_id": self.owner_id, "offset_id": offset_id})

    async def get_ad(self, ad_id: str) -> dict[str, Any]:
        # Prefer the JSON method; fall back to the ad page and the list.
        try:
            result = await self.call("getAd", {"owner_id": self.owner_id, "ad_id": ad_id})
            if isinstance(result, dict) and not result.get("error"):
                return {"ok": True, "ad": result, "source": "getAd"}
        except Exception as exc:  # noqa: BLE001
            log.debug("getAd method failed: %s", exc)

        resp = await self._get_html(f"/account/ad/{ad_id}", follow_redirects=True)
        if resp.status_code == 200:
            html = resp.text
            ad_state = extract_json_value(html, "ad") or extract_json_value(html, "adInfo")
            if isinstance(ad_state, dict):
                return {"ok": True, "ad": ad_state, "source": "html"}

        listing = await self.get_ads_list()
        items = listing.get("items") or listing.get("ads") or []
        for item in items:
            if str(item.get("ad_id") or item.get("id")) == str(ad_id):
                return {"ok": True, "ad": item, "source": "getAdsList"}
        return {"ok": False, "error": f"Ad {ad_id} not found", "ad_id": ad_id}

    async def get_ad_stats(self, ad_id: str, period: str = "5min") -> dict[str, Any]:
        await self._ensure_auth()
        resp = await self._get_html(f"/account/ad/{ad_id}/stats?period={period}", follow_redirects=True)
        if resp.status_code != 200:
            return {"ok": False, "error": f"HTTP {resp.status_code}", "ad_id": ad_id}
        html = resp.text
        charts: dict[str, Any] = {}
        mapping = {
            "chart_count_stats_wrap": "counts",
            "chart_budget_stats_wrap": "budget",
        }
        for html_key, result_key in mapping.items():
            parsed = parse_chart(html, html_key)
            if parsed:
                charts[result_key] = parsed
        if not charts:
            return {
                "ok": False,
                "error": "Could not parse stats charts from the page (layout may have changed).",
                "ad_id": ad_id,
                "period": period,
            }
        counts = charts.get("counts") or {}
        totals = counts.get("totals") or {}
        interval = counts.get("interval_seconds") or 0
        ts = counts.get("timestamps") or []
        if interval == 300:
            label = "24h"
        elif ts:
            try:
                span_days = (ts[-1] - ts[0]) / 1000 / 86400
                label = f"{int(span_days)}d"
            except (TypeError, ValueError):
                label = "unknown"
        else:
            label = "unknown"
        views = float(totals.get("Views") or 0)
        clicks = float(totals.get("Clicks") or 0)
        started = float(totals.get("Started bot") or 0)
        spend_totals = (charts.get("budget") or {}).get("totals") or {}
        spend = 0.0
        for key, val in spend_totals.items():
            if val is None:
                continue
            try:
                spend = max(spend, float(val))
            except (TypeError, ValueError):
                continue
        metrics = derived_metrics(views, clicks, spend)
        return {
            "ok": True,
            "ad_id": ad_id,
            "charts": charts,
            "summary": {
                "period": label,
                "interval_seconds": interval,
                "views": views,
                "clicks": clicks,
                "started_bot": started,
                "spend": spend,
                **metrics,
            },
        }

    async def get_user_targeting_reference(self) -> dict[str, Any]:
        if self._user_targeting_ref is not None:
            return self._user_targeting_ref
        await self._ensure_auth()
        resp = await self._get_html("/account/ad/new", follow_redirects=True)
        html_text = resp.text
        result: dict[str, Any] = {}
        for key in ("countryItems", "langItems", "userTopicItems"):
            items = extract_json_value(html_text, key) or []
            result[key] = unescape_names(items) if isinstance(items, list) else []
        self._user_targeting_ref = result
        return result

    async def get_channel_targeting_reference(self) -> dict[str, Any]:
        if self._channel_targeting_ref is not None:
            return self._channel_targeting_ref
        await self._ensure_auth()
        resp = await self._get_html("/account/ad/new", follow_redirects=True)
        html_text = resp.text
        result: dict[str, Any] = {}
        for key in ("topicItems", "langItems", "convEventItems"):
            items = extract_json_value(html_text, key) or []
            result[key] = unescape_names(items) if isinstance(items, list) else []
        self._channel_targeting_ref = result
        return result

    async def upload(
        self,
        target: str,
        *,
        file_path: str | None = None,
        filename: str | None = None,
        content: bytes | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        await self._ensure_auth()
        data: dict[str, Any] = {"owner_id": self.owner_id, "target": target}
        if extra:
            data.update(strip_empty(extra))
        if content is not None:
            name = filename or "upload.bin"
            files = {"file": (name, content)}
            resp = await self._request("POST", "/file/upload", data=data, files=files)
        elif file_path:
            path = Path(file_path)
            with path.open("rb") as fh:
                files = {"file": (filename or path.name, fh)}
                resp = await self._request("POST", "/file/upload", data=data, files=files)
        else:
            raise ValueError("upload requires file_path or content")
        resp.raise_for_status()
        try:
            return resp.json()
        except json.JSONDecodeError:
            return {"ok": False, "error": "Non-JSON upload response", "text": resp.text[:500]}

    async def upload_media(
        self,
        *,
        file_path: str | None = None,
        filename: str | None = None,
        content: bytes | None = None,
        ad_id: str | None = None,
    ) -> dict[str, Any]:
        """Upload a photo/video creative. Tries a few known `target` names."""
        extra = {"ad_id": ad_id} if ad_id else None
        errors: list[str] = []
        for target in ("media", "adMedia", "ad_media", "picture"):
            try:
                result = await self.upload(
                    target,
                    file_path=file_path,
                    filename=filename,
                    content=content,
                    extra=extra,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{target}: {exc}")
                continue
            if isinstance(result, dict) and not result.get("error"):
                result.setdefault("ok", True)
                result["target"] = target
                return result
            errors.append(f"{target}: {result}")
        return {"ok": False, "error": "media upload failed", "attempts": errors}

    async def preview_payload(self, ad_id: str) -> dict[str, Any]:
        """Collect fields needed to render a preview card."""
        got = await self.get_ad(ad_id)
        ad = got.get("ad") if isinstance(got, dict) else None
        if not isinstance(ad, dict):
            ad = {}
        resp = await self._get_html(f"/account/ad/{ad_id}", follow_redirects=True)
        html = resp.text if resp.status_code == 200 else ""
        preview_url = None
        for key in ("previewUrl", "preview_url", "previewImage"):
            val = extract_json_value(html, key)
            if isinstance(val, str) and val:
                preview_url = val
                break
        image_bytes: bytes | None = None
        image_url = None
        for candidate in (
            preview_url,
            ad.get("picture_url"),
            ad.get("photo"),
            ad.get("image"),
            ad.get("media_url"),
        ):
            if not isinstance(candidate, str) or not candidate:
                continue
            image_url = candidate if candidate.startswith("http") else urljoin(BASE_URL, candidate)
            try:
                img_resp = await self._request("GET", image_url, xhr=False, follow_redirects=True)
                if img_resp.status_code == 200 and img_resp.content:
                    image_bytes = img_resp.content
                    break
            except Exception as exc:  # noqa: BLE001
                log.debug("preview image fetch failed: %s", exc)
        return {
            "ok": True,
            "ad_id": ad_id,
            "title": ad.get("title") or "",
            "text": ad.get("text") or "",
            "promote_url": ad.get("promote_url") or ad.get("url") or "",
            "cpm": ad.get("cpm"),
            "status": ad.get("active") or ad.get("status"),
            "picture": bool(ad.get("picture")),
            "media": ad.get("media"),
            "image_url": image_url,
            "image_bytes": image_bytes,
            "ad": ad,
        }


async def write_temp_ids(user_ids: list[str]) -> str:
    fh = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    with fh:
        fh.write("\n".join(user_ids))
        fh.write("\n")
    return fh.name
