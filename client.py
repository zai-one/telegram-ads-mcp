"""HTTP client for Telegram Ads API."""

import re
import json

import httpx

BASE_URL = "https://ads.telegram.org"


class AuthError(Exception):
    """Session cookies are invalid or expired."""


class TelegramAdsClient:
    """HTTP client wrapping the ads.telegram.org internal API.

    Auth flow:
    1. Provide stel_token + stel_ssid cookies (from browser)
    2. Optionally provide stel_adowner (account ID) — skips account selection
    3. On first API call, authenticate() runs automatically:
       - Fetches /choose_account to list available ad accounts
       - Selects account (auto if one, or uses stel_adowner)
       - Extracts api_hash and owner_id from the session
    """

    def __init__(self, stel_token: str, stel_ssid: str, stel_adowner: str | None = None):
        self.api_hash: str | None = None
        self.owner_id: str | None = None
        self._api_url: str | None = None
        cookies = {
            "stel_token": stel_token,
            "stel_ssid": stel_ssid,
        }
        if stel_adowner:
            cookies["stel_adowner"] = stel_adowner
        self._http = httpx.Client(
            base_url=BASE_URL,
            cookies=cookies,
            headers={
                "Origin": BASE_URL,
                "Referer": f"{BASE_URL}/account",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=30.0,
            follow_redirects=False,
        )

    def list_accounts(self) -> list[dict]:
        """Fetch the account chooser page and return available accounts.
        Each account has: title, description, owner_id, url."""
        resp = self._http.get("/choose_account?to=account", headers={"X-Requested-With": ""})

        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("location", "")
            if "login" in location or "auth" in location:
                raise AuthError("Session expired — cookies are no longer valid.")
            raise AuthError(f"Unexpected redirect to {location}")

        if resp.status_code != 200:
            raise AuthError(f"Unexpected status {resp.status_code}")

        html = resp.text

        if "Log in" in html and "tgme_widget" in html:
            raise AuthError("Not logged in — session cookies are invalid or expired.")

        # Parse account entries: each is an <a> with href="/choose_account/OWNER_ID"
        accounts = []
        # Find all account link blocks
        pattern = r'href="(/choose_account/([^"]+))"[^>]*>.*?pr-account-button-title[^>]*>(.*?)</div>.*?pr-account-button-desc[^>]*>(.*?)</div>'
        for match in re.finditer(pattern, html, re.DOTALL):
            url, owner_id, title_html, desc = match.groups()
            # Strip HTML tags from title
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            accounts.append({
                "title": title,
                "description": desc.strip(),
                "owner_id": owner_id,
                "url": url,
            })

        return accounts

    def select_account(self, owner_id: str) -> None:
        """Select an ad account by visiting its choose_account URL.
        This sets the stel_adowner cookie for subsequent requests."""
        resp = self._http.get(
            f"/choose_account/{owner_id}",
            headers={"X-Requested-With": ""},
            follow_redirects=False,
        )
        # Should redirect to /account — the cookie gets set
        self._http.cookies.set("stel_adowner", owner_id, domain="ads.telegram.org")

    def authenticate(self) -> dict:
        """Full auth flow: list accounts, select one, extract api_hash + owner_id.
        If stel_adowner cookie is already set, skips account selection.
        Returns session info dict. Raises AuthError on failure."""

        # Try fetching /account directly (works if stel_adowner is set)
        resp = self._http.get("/account", headers={"X-Requested-With": ""}, follow_redirects=True)

        if resp.status_code != 200:
            raise AuthError(f"Unexpected status {resp.status_code}")

        html = resp.text

        # Check if we landed on the choose_account page
        if "choose_account" in str(resp.url) or "pr-account-button" in html:
            # Need to select an account first
            accounts = self.list_accounts()
            if not accounts:
                raise AuthError("No ad accounts found for this Telegram user.")

            # Check if we have a stored adowner preference
            adowner = self._http.cookies.get("stel_adowner")
            selected = None
            if adowner:
                selected = next((a for a in accounts if a["owner_id"] == adowner), None)

            if not selected:
                if len(accounts) == 1:
                    selected = accounts[0]
                else:
                    # Auto-select first non-"new" account
                    selected = next(
                        (a for a in accounts if a["owner_id"] != "new"),
                        accounts[0]
                    )

            self.select_account(selected["owner_id"])

            # Now fetch /account again
            resp = self._http.get("/account", headers={"X-Requested-With": ""}, follow_redirects=True)
            if resp.status_code != 200:
                raise AuthError(f"Failed to load account after selection: {resp.status_code}")
            html = resp.text

        # Extract apiUrl
        hash_match = re.search(r'"apiUrl"\s*:\s*"[^"]*hash=([a-f0-9]+)"', html)
        if not hash_match:
            if "Log in" in html:
                raise AuthError("Not logged in — session cookies are invalid or expired.")
            raise AuthError("Could not extract api_hash from page HTML")

        self.api_hash = hash_match.group(1)
        self._api_url = f"/api?hash={self.api_hash}"

        # Extract ownerId
        owner_match = re.search(r'"ownerId"\s*:\s*"([^"]+)"', html)
        if owner_match:
            self.owner_id = owner_match.group(1)
        else:
            # Use adowner cookie as fallback
            self.owner_id = self._http.cookies.get("stel_adowner")
            if not self.owner_id:
                raise AuthError("Could not determine owner_id")

        return {
            "ok": True,
            "api_hash": self.api_hash,
            "owner_id": self.owner_id,
        }

    def _ensure_auth(self) -> None:
        """Auto-authenticate on first API call."""
        if self._api_url is None:
            self.authenticate()

    def is_eur_cabinet(self) -> bool:
        """Detect EUR (reseller) vs TON cabinet by probing /account/ad/new.

        EUR cabinets expose target_type='users' for user-level demographic
        targeting; TON cabinets only support channels/bots/search. Cached for
        the lifetime of this client instance.
        """
        if getattr(self, "_is_eur", None) is None:
            self._ensure_auth()
            resp = self._http.get(
                "/account/ad/new",
                headers={"X-Requested-With": ""},
                follow_redirects=False,
            )
            self._is_eur = 'name="target_type" value="users"' in resp.text
        return self._is_eur

    def get_user_targeting_reference(self) -> dict:
        """Pull static reference lists (countries, languages, topics) for
        user-level targeting from /account/ad/new HTML state.

        Returns dict with keys: countryItems, langItems, userTopicItems.
        Cached for the lifetime of this client instance.
        EUR-cabinet only — TON cabinets don't render these arrays.
        """
        if getattr(self, "_user_targeting_ref", None) is None:
            self._ensure_auth()
            resp = self._http.get(
                "/account/ad/new",
                headers={"X-Requested-With": ""},
                follow_redirects=False,
            )
            html_text = resp.text
            import html as _html
            result = {}
            for key in ("countryItems", "langItems", "userTopicItems"):
                m = re.search(rf'"{key}":(\[[^\]]*\])', html_text)
                if not m:
                    result[key] = []
                    continue
                try:
                    items = json.loads(m.group(1))
                except json.JSONDecodeError:
                    items = []
                for item in items:
                    if isinstance(item, dict) and "name" in item:
                        item["name"] = _html.unescape(item["name"])
                result[key] = items
            self._user_targeting_ref = result
        return self._user_targeting_ref

    def get_channel_targeting_reference(self) -> dict:
        """Pull static reference lists for channel-level targeting
        (Channels target type) from /account/ad/new HTML state.

        Returns dict with keys:
          - topicItems: channel topic categories (e.g. Education, Books, Crypto)
          - langItems:  channel content languages (shared with user_langs taxonomy)
          - convEventItems: conversion events for attribution

        These are siblings to userTopicItems / countryItems on the page state;
        the same JSON state object on /account/ad/new powers both Channels and
        Users target tabs. Cached for the lifetime of this client instance.
        EUR-cabinet only — TON cabinets only render the channel filter on the
        Channels tab and do not expose topicItems / convEventItems.
        """
        if getattr(self, "_channel_targeting_ref", None) is None:
            self._ensure_auth()
            resp = self._http.get(
                "/account/ad/new",
                headers={"X-Requested-With": ""},
                follow_redirects=False,
            )
            html_text = resp.text
            import html as _html
            result = {}
            for key in ("topicItems", "langItems", "convEventItems"):
                m = re.search(rf'"{key}":(\[[^\]]*\])', html_text)
                if not m:
                    result[key] = []
                    continue
                try:
                    items = json.loads(m.group(1))
                except json.JSONDecodeError:
                    items = []
                for item in items:
                    if isinstance(item, dict) and "name" in item:
                        item["name"] = _html.unescape(item["name"])
                result[key] = items
            self._channel_targeting_ref = result
        return self._channel_targeting_ref

    def call(self, method: str, params: dict | None = None) -> dict:
        """Call an API method. Auto-authenticates on first call."""
        self._ensure_auth()
        data = {"method": method}
        if params:
            data.update({k: v for k, v in params.items() if v is not None})
        resp = self._http.post(self._api_url, data=data)

        if resp.status_code in (301, 302, 303, 307, 308):
            raise AuthError("Session expired during API call")

        resp.raise_for_status()
        result = resp.json()

        if isinstance(result, dict) and result.get("error") == "AUTH_REQUIRED":
            raise AuthError("API returned AUTH_REQUIRED — session expired")

        return result

    def upload(self, target: str, file_path: str, params: dict | None = None) -> dict:
        """Upload a file (e.g. audience list)."""
        self._ensure_auth()
        data = {"owner_id": self.owner_id, "target": target}
        if params:
            data.update({k: v for k, v in params.items() if v is not None})
        with open(file_path, "rb") as f:
            files = {"file": (file_path.split("/")[-1], f)}
            resp = self._http.post("/file/upload", data=data, files=files)
        resp.raise_for_status()
        return resp.json()

    def get_ad_stats(self, ad_id: str, period: str = "5min") -> dict:
        """Fetch time-bucketed stats from the ad stats page.

        Args:
            ad_id: The ad ID.
            period: "5min" for 5-minute buckets (last 24h, active ads only)
                    or "day" for daily buckets (full ad lifetime).
        """
        self._ensure_auth()
        resp = self._http.get(
            f"/account/ad/{ad_id}/stats",
            params={"period": period},
            headers={"X-Requested-With": ""},
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return {"ok": False, "error": f"HTTP {resp.status_code}"}

        html = resp.text
        result = {"ok": True, "ad_id": ad_id, "charts": {}}

        chart_names = {
            "chart_count_stats_wrap": "counts",
            "chart_budget_stats_wrap": "budget",
        }

        for html_key, result_key in chart_names.items():
            idx = html.find(f"renderGraph('{html_key}',")
            if idx == -1:
                continue

            json_start = html.index("{", idx)
            depth = 0
            end = json_start
            for i in range(json_start, min(len(html), json_start + 100_000)):
                if html[i] == "{":
                    depth += 1
                elif html[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break

            try:
                chart_data = json.loads(html[json_start:end])
            except json.JSONDecodeError:
                continue

            columns = chart_data.get("columns", [])
            names = chart_data.get("names", {})

            # Build structured output: list of {timestamp, col1, col2, ...}
            if not columns:
                continue

            timestamps = columns[0][1:]  # first column is "x" with timestamps
            series = {}
            for col in columns[1:]:
                col_id = col[0]
                col_name = names.get(col_id, col_id)
                series[col_name] = col[1:]

            interval = (timestamps[1] - timestamps[0]) // 1000 if len(timestamps) > 1 else 0

            chart_entry = {
                "interval_seconds": interval,
                "names": names,
                "timestamps": timestamps,
                "series": series,
            }

            # Add 24h totals for quick filtering
            chart_entry["totals"] = {
                col_name: sum(values) for col_name, values in series.items()
            }

            result["charts"][result_key] = chart_entry

        # Top-level summary — period depends on interval
        counts = result["charts"].get("counts", {})
        totals = counts.get("totals", {})
        interval = counts.get("interval_seconds", 0)
        ts = counts.get("timestamps", [])

        if interval == 300:
            period = "24h"
        elif ts:
            span_days = (ts[-1] - ts[0]) / 1000 / 86400
            period = f"{int(span_days)}d"
        else:
            period = "unknown"

        result["summary"] = {
            "period": period,
            "interval_seconds": interval,
            "views": totals.get("Views", 0),
            "clicks": totals.get("Clicks", 0),
            "started_bot": totals.get("Started bot", 0),
        }

        return result

    def close(self):
        self._http.close()
