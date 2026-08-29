"""HTML / JSON extraction helpers for ads.telegram.org pages.

Telegram's advertiser UI embeds state as JS object literals. Regex-to-first-`]`
breaks on nested arrays, so everything here uses a balanced scanner.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
from typing import Any

log = logging.getLogger("tg_ads_mcp.parse")

_CURRENCY_RE = re.compile(
    r'"(?:currency|balanceCurrency|fundsCurrency)"\s*:\s*"([^"]+)"',
    re.I,
)
_BALANCE_RE = re.compile(
    r'"(?:balance|accountBalance|funds)"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?',
    re.I,
)


class ParseError(ValueError):
    """Page HTML did not contain the expected structure."""


def _scan_balanced(text: str, start: int) -> str:
    """Return the substring of a JSON value starting at `start` (`{` or `[`)."""
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ParseError(f"unbalanced {opener} starting at {start}")


def extract_json_value(html: str, key: str) -> Any | None:
    """Extract a JSON object/array/scalar assigned to `"key":` in HTML/JS."""
    pattern = re.compile(rf'"{re.escape(key)}"\s*:')
    match = pattern.search(html)
    if not match:
        return None
    i = match.end()
    while i < len(html) and html[i].isspace():
        i += 1
    if i >= len(html):
        return None
    ch = html[i]
    if ch in "{[":
        raw = _scan_balanced(html, i)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            log.debug("failed to decode JSON for key %s", key)
            return None
    if ch == '"':
        m = re.match(r'"((?:\\.|[^"\\])*)"', html[i:])
        if not m:
            return None
        return json.loads(m.group(0))
    m = re.match(r"true|false|null|-?\d+(?:\.\d+)?", html[i:])
    if not m:
        return None
    return json.loads(m.group(0))


def unescape_names(items: list[Any]) -> list[Any]:
    for item in items:
        if isinstance(item, dict) and "name" in item and isinstance(item["name"], str):
            item["name"] = html_lib.unescape(item["name"])
    return items


def parse_accounts(html: str) -> list[dict[str, str]]:
    """Parse the account chooser page. JSON state first, CSS markup as fallback."""
    for key in ("accounts", "accountItems", "ownerItems"):
        raw = extract_json_value(html, key)
        if isinstance(raw, list) and raw:
            out = []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                owner_id = str(item.get("id") or item.get("owner_id") or item.get("val") or "")
                if not owner_id:
                    continue
                out.append(
                    {
                        "title": html_lib.unescape(str(item.get("title") or item.get("name") or owner_id)),
                        "description": html_lib.unescape(str(item.get("description") or item.get("desc") or "")),
                        "owner_id": owner_id,
                        "url": f"/choose_account/{owner_id}",
                    }
                )
            if out:
                return out

    accounts: list[dict[str, str]] = []
    seen: set[str] = set()
    # Broad match on choose_account links; title/desc are best-effort.
    for match in re.finditer(
        r'href="(/choose_account/([^"/?]+))"',
        html,
    ):
        url, owner_id = match.group(1), match.group(2)
        if owner_id in seen:
            continue
        seen.add(owner_id)
        window = html[match.end() : match.end() + 800]
        title_m = re.search(
            r'pr-account-button-title[^>]*>(.*?)</(?:div|span|h\d)>',
            window,
            re.DOTALL | re.I,
        )
        desc_m = re.search(
            r'pr-account-button-desc[^>]*>(.*?)</(?:div|span)>',
            window,
            re.DOTALL | re.I,
        )
        title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else owner_id
        desc = re.sub(r"<[^>]+>", "", desc_m.group(1)).strip() if desc_m else ""
        accounts.append(
            {
                "title": html_lib.unescape(title),
                "description": html_lib.unescape(desc),
                "owner_id": owner_id,
                "url": url,
            }
        )
    return accounts


def extract_api_hash(html: str) -> str | None:
    m = re.search(r'"apiUrl"\s*:\s*"[^"]*hash=([a-f0-9]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'hash=([a-f0-9]{8,})', html)
    return m.group(1) if m else None


def extract_owner_id(html: str) -> str | None:
    m = re.search(r'"ownerId"\s*:\s*"([^"]+)"', html)
    return m.group(1) if m else None


def extract_currency(html: str) -> str | None:
    m = _CURRENCY_RE.search(html)
    if m:
        return m.group(1).upper()
    if re.search(r"\bXTR\b", html):
        return "XTR"
    if re.search(r"€|EUR", html) and re.search(r"balance|budget|cpm", html, re.I):
        # weak signal; caller combines with target_type=users
        return None
    return None


def extract_balance(html: str) -> str | None:
    m = _BALANCE_RE.search(html)
    if m:
        return m.group(1)
    m = re.search(
        r'pr-(?:account-)?balance[^>]*>\s*([0-9]+(?:[.,][0-9]+)?)',
        html,
        re.I,
    )
    if m:
        return m.group(1).replace(",", ".")
    return None


def detect_cabinet(account_html: str, new_ad_html: str = "") -> dict[str, Any]:
    """Classify TON / EUR / Stars. Stars is unsupported by this server."""
    blob = f"{account_html}\n{new_ad_html}"
    currency = extract_currency(blob)
    has_users = 'name="target_type" value="users"' in new_ad_html or 'value="users"' in new_ad_html
    looks_stars = False
    if currency in {"XTR", "STARS", "STAR"}:
        looks_stars = True
    elif re.search(r'data-currency=["\']stars["\']', blob, re.I):
        looks_stars = True
    elif re.search(r'"cabinet(?:Type)?"\s*:\s*"stars"', blob, re.I):
        looks_stars = True
    elif re.search(r"Telegram Stars", blob) and re.search(r"CPM|budget|balance", blob, re.I):
        looks_stars = True

    if looks_stars:
        kind = "stars"
        cur = currency or "STARS"
    elif has_users or currency == "EUR":
        kind = "eur"
        cur = currency or "EUR"
    else:
        kind = "ton"
        cur = currency or "TON"

    return {
        "cabinet": kind,
        "currency": cur,
        "supports_user_targeting": kind == "eur",
        "supported": kind != "stars",
    }


def parse_chart(html: str, wrap_id: str) -> dict[str, Any] | None:
    needle = f"renderGraph('{wrap_id}',"
    idx = html.find(needle)
    if idx == -1:
        needle = f'renderGraph("{wrap_id}",'
        idx = html.find(needle)
    if idx == -1:
        return None
    brace = html.find("{", idx)
    if brace == -1:
        return None
    try:
        raw = _scan_balanced(html, brace)
        chart_data = json.loads(raw)
    except (ParseError, json.JSONDecodeError):
        log.debug("failed to parse chart %s", wrap_id)
        return None

    columns = chart_data.get("columns") or []
    names = chart_data.get("names") or {}
    if not columns:
        return None
    timestamps = columns[0][1:]
    series: dict[str, list[Any]] = {}
    for col in columns[1:]:
        col_id = col[0]
        col_name = names.get(col_id, col_id)
        series[col_name] = col[1:]
    interval = 0
    if len(timestamps) > 1:
        try:
            interval = int((timestamps[1] - timestamps[0]) // 1000)
        except (TypeError, ValueError):
            interval = 0
    totals = {}
    for col_name, values in series.items():
        try:
            totals[col_name] = sum(v or 0 for v in values)
        except TypeError:
            totals[col_name] = None
    return {
        "interval_seconds": interval,
        "names": names,
        "timestamps": timestamps,
        "series": series,
        "totals": totals,
    }


def derived_metrics(views: float, clicks: float, spend: float) -> dict[str, float | None]:
    def ratio(num: float, den: float) -> float | None:
        if not den:
            return None
        return round(num / den, 6)

    return {
        "ctr": ratio(clicks, views),
        "cpc": ratio(spend, clicks),
        "cpm_actual": ratio(spend * 1000, views) if views else None,
    }


def strip_empty(params: dict[str, Any], keep: set[str] | None = None) -> dict[str, Any]:
    """Drop None and empty-string values so search ads are not rejected.

    `keep` is the set of keys that must be sent even when empty (e.g. media=""
    to detach a creative).
    """
    keep = keep or set()
    out = {}
    for k, v in params.items():
        if k in keep:
            out[k] = v
            continue
        if v is None:
            continue
        if v == "":
            continue
        out[k] = v
    return out


def map_status(active: str | None) -> str | None:
    if active is None:
        return None
    status_map = {
        "active": "1",
        "on_hold": "0",
        "on hold": "0",
        "1": "1",
        "0": "0",
    }
    return status_map.get(active.lower(), active)


_SECRET_KEYS = ("stel_token", "stel_ssid", "api_hash", "confirm_hash", "cookie")


def redact(value: str) -> str:
    redacted = value
    for key in _SECRET_KEYS:
        redacted = re.sub(
            rf"({key}['\"=\s:]+)([^\s&\"']+)",
            r"\1***",
            redacted,
            flags=re.I,
        )
    return redacted
