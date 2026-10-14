"""Telegram Ads MCP server — MCP Python SDK v2."""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
from pathlib import Path
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from mcp.server import MCPServer
from mcp.types import CallToolResult, ImageContent, TextContent, ToolAnnotations

from telegram_ads_mcp import __version__, guide, lazy_loading
from telegram_ads_mcp.client import AuthError, ConfigError, StarsCabinetError, stars_enabled
from telegram_ads_mcp.descriptions import meta
from telegram_ads_mcp.gate import attach_gate, gated
from telegram_ads_mcp.router import instructions as router_instructions
from telegram_ads_mcp.parse import (
    charts_to_csv,
    check_amounts,
    compact,
    access_denied_payload,
    channel_langs_conflict,
    filter_ads_by_status,
    looks_access_denied,
    map_status,
    redact,
)
from telegram_ads_mcp.preview import render_card
from telegram_ads_mcp.session import fail_payload, get_client, load_env, reload_from_env, switch_account
from telegram_ads_mcp.update_check import cached_update_hint, check_for_update, refresh_in_background

load_env()

logging.basicConfig(
    level=os.environ.get("TG_ADS_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)
# Never let cookies / hashes leak through log formatters.
_root = logging.getLogger()
class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        return True

_root.addFilter(_RedactFilter())
log = logging.getLogger("telegram_ads_mcp")

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True)
DEST = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True)

# Cache-only update hint: startup never waits on the network.
_STARTUP_UPDATE_HINT = cached_update_hint()

mcp = MCPServer(
    name="telegram-ads-mcp",
    title="Telegram Ads",
    version=__version__,
    instructions=router_instructions(_STARTUP_UPDATE_HINT or ""),
    website_url="https://github.com/zai-one/telegram-ads-mcp",
)


def _ok(data: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": True}
    if data:
        out.update(data)
    out.update(extra)
    return out


async def _money_error(client: Any, target_type: str | None = None, **amounts: str | None) -> dict | None:
    """Cabinet-aware amount check: Stars take whole numbers and no user targeting; EUR/Gram 2 decimals."""
    cabinet = await client.require_supported_cabinet()
    if not isinstance(cabinet, dict):
        return None
    if cabinet.get("cabinet") == "stars" and target_type == "users":
        return attach_gate({"ok": False, "code": "unsupported_in_cabinet", "cabinet": "stars",
                            "error": "Stars cabinets cannot target users; use channels or bots.",
                            "retryable": False})
    problem = check_amounts(cabinet, **amounts)
    if problem:
        return attach_gate({"ok": False, "code": "invalid_amount", "cabinet": cabinet.get("cabinet"),
                            "currency": cabinet.get("currency"), "error": problem, "retryable": False})
    return None


async def _budget_delta(client: Any, ad_id: str, target: str) -> tuple[str | None, str | None]:
    """(action, amount) that moves the ad's total budget to `target`; (None, reason) when unknown."""
    card = await client.get_ad(ad_id)
    ad = card.get("ad") if isinstance(card, dict) and isinstance(card.get("ad"), dict) else {}
    raw = ad.get("budget")
    try:
        current = Decimal(str(raw).replace(",", ".").strip())
        wanted = Decimal(str(target).replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        return None, f"Current budget of ad {ad_id} is not readable ({raw!r}); use budget_action."
    delta = wanted - current
    if delta == 0:
        return "none", f"Budget already equals {target}; nothing sent."
    return ("increase" if delta > 0 else "decrease"), format(abs(delta).normalize(), "f")


async def _client_or_fail(require_supported: bool = True):
    try:
        client = await get_client()
        if require_supported:
            await client.require_supported_cabinet()
        return client, None
    except (ConfigError, AuthError, StarsCabinetError) as exc:
        return None, attach_gate(fail_payload(exc))


def _gate(
    cls: str,
    confirm: bool,
    tool: str,
    would_send: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    blocked = gated(cls=cls, confirm=confirm, tool=tool, would_send=would_send)
    return attach_gate(blocked) if blocked else None


def _maybe_access_denied(result: Any, *, tool: str, action: str) -> Any:
    if looks_access_denied(result):
        return access_denied_payload(result, tool=tool, action=action)
    return result


# ── resources / prompts ──────────────────────────────────────────────


@mcp.resource("ads://playbook", mime_type="text/markdown")
def playbook_resource() -> str:
    """Full agent playbook (AGENTS.md). Prefer ads://guide/{topic} for one section."""
    return guide.playbook()


@mcp.resource("ads://guide/index", mime_type="text/markdown")
def guide_index_resource() -> str:
    """List of guide topics: auth, write-gate, errors, stats, create, danger, ..."""
    return guide.index()


@mcp.resource("ads://guide/{topic}", mime_type="text/markdown")
def guide_resource(topic: str) -> str:
    """One playbook section by topic (see ads://guide/index)."""
    body = guide.topic(topic)
    if body is None:
        return f"Unknown topic {topic!r}.\n\n" + guide.index()
    return body


@mcp.resource("ads://account", mime_type="application/json")
async def account_resource() -> str:
    """Current cabinet: owner_id, currency, balance, type."""
    client, err = await _client_or_fail(require_supported=False)
    if err:
        return json.dumps(err, ensure_ascii=False)
    info = attach_gate(await client.get_account())
    info.pop("api_hash", None)
    return json.dumps(info, ensure_ascii=False)


@mcp.prompt(name="launch-campaign", description="End-to-end flow to create and submit a Telegram ad.")
def launch_campaign_prompt(
    target_type: str = "channels",
    promote_url: str = "https://t.me/your_channel",
) -> str:
    return (
        f"Launch a {target_type} ad promoting {promote_url}.\n"
        "1. check_session — if ok=false, offer INSTALL.md DevTools steps; they write .env (never paste into chat); then reload_session.\n"
        "2. get_account — cabinet (TON/EUR/Stars), currency and money rules. Note write_gate.\n"
        "3. search_targets to resolve IDs.\n"
        "4. check_ad_post on the promote_url + text.\n"
        "5. launch_ad (on_hold + budget + review, does not activate). Pass confirm=true if write_gated.\n"
        "6. preview_ad and show the PNG to the user.\n"
        "get_ad_stats spend is already scaled (do not divide). If you save a dump, gitignored reports/.\n"
    )


@mcp.prompt(name="review-account", description="Read-only morning pass: balance, live vs stopped ads, stats on a few problems.")
def review_account_prompt() -> str:
    return (
        "Read-only review of the Telegram Ads cabinet. Do not create, edit, or spend.\n"
        "1. get_account — cabinet and currency (GRAM/EUR/XTR). Note write_gate.\n"
        "2. get_ads(status=active) and get_ads(status=on_hold). Use list spent/views/ctr; do not fetch stats for every ad.\n"
        "3. Pick at most 5 problem ads (Active with 0 views, or Stopped with leftover daily_budget, or CTR crash).\n"
        "4. For each: get_ad_stats(period=5min) then period=day if needed. Compare summary.spend to list spent (same order of magnitude). Spend is already scaled — do not divide.\n"
        "5. preview_ad only if copy might be the issue.\n"
        "6. At most 5 problem ads and one recommendation, then stop. Wait for the user before any write.\n"
        "If you save a dump, gitignored reports/<ad_id>-<period>.json (playbook allowlist).\n"
    )


@mcp.prompt(name="diagnose-ad", description="Inspect one ad: card, stats, preview.")
def diagnose_ad_prompt(ad_id: str = "") -> str:
    return (
        f"Diagnose ad {ad_id or '(ask the user for ad_id)'}.\n"
        "Call get_ad, get_ad_stats(period=5min), preview_ad. "
        "Use period=day when they need lifetime. Write the request period next to any dump. "
        "Do not divide summary.spend (spend_already_scaled). Prefer summary.spend; "
        "charts.budget is already scaled — not a second Gram figure to re-divide. "
        "Summarise views/clicks/CTR/spend and whether budget or status is blocking delivery."
    )


# ── auth ─────────────────────────────────────────────────────────────


@mcp.tool(annotations=READ, **meta("check_session"))
async def check_session() -> dict[str, Any]:
    """Ping the current ads.telegram.org session.

    Returns owner_id, cabinet (ton/eur/stars), currency, balance.
    Does not return api_hash or cookies. TON and EUR cabinets are supported; Stars only with TG_ADS_STARS=on.
    If ok=false with code=auth, offer INSTALL.md DevTools steps; they write .env (never paste into chat); then reload_session.
    """
    client, err = await _client_or_fail(require_supported=False)
    if err:
        return err
    try:
        await client.authenticate()
        info = attach_gate(await client.get_account())
    except (AuthError, ConfigError, StarsCabinetError) as exc:
        return attach_gate(fail_payload(exc))
    hint = cached_update_hint()
    if hint:
        info["update_hint"] = hint
    return info


@mcp.tool(annotations=READ, **meta("check_update"))
def check_update(force: bool = False) -> dict[str, Any]:
    """Check GitHub for a newer telegram-ads-mcp release; suggest only, never install.

    Returns current/latest version, release notes link, the update command and run_in
    (where to run it). One anonymous GitHub API call (3 s timeout), cached 24h; force=true
    re-checks at most once a minute. After a failed call it waits 30 min.
    Offline -> status=unavailable. Disable with TG_ADS_DISABLE_UPDATE_CHECK=1.
    Tell the user the command; do not run it yourself unless they ask.
    """
    return check_for_update(force=bool(force))


@mcp.tool(annotations=WRITE, **meta("reload_session"))
async def reload_session() -> dict[str, Any]:
    """Re-read .env (STEL_TOKEN / STEL_SSID / STEL_ADOWNER) and rebuild the HTTP session.

    Use this after the user updates cookies on disk. Never pass cookie values as arguments.
    """
    try:
        client = await reload_from_env()
        await client.authenticate()
        return attach_gate(await client.get_account())
    except (AuthError, ConfigError) as exc:
        return attach_gate(fail_payload(exc))


@mcp.tool(annotations=READ, **meta("list_accounts"))
async def list_accounts() -> dict[str, Any]:
    """List ad cabinets for this Telegram login. Works on any cabinet (TON, EUR, Stars)."""
    client, err = await _client_or_fail(require_supported=False)
    if err:
        return err
    try:
        accounts = await client.list_accounts()
        return attach_gate(_ok(accounts=accounts))
    except (AuthError, ConfigError) as exc:
        return attach_gate(fail_payload(exc))


@mcp.tool(annotations=WRITE, **meta("select_account"))
async def select_account(owner_id: str, confirm: bool = False) -> dict[str, Any]:
    """Switch the active ad cabinet. Then check_session / get_account.

    Args:
        owner_id: From list_accounts.
        confirm: Required when TG_ADS_WRITE_GATE=strict.
    """
    blocked = _gate("write", confirm, "select_account", {"owner_id": owner_id})
    if blocked:
        return blocked
    try:
        client = await switch_account(owner_id)
        info = attach_gate(await client.get_account())
        if info.get("cabinet") == "stars" and not stars_enabled():
            return attach_gate({
                "ok": False,
                "code": "stars_cabinet",
                "cabinet": "stars",
                "owner_id": owner_id,
                "error": "Stars cabinet selected; Stars support is opt-in. Set TG_ADS_STARS=on or pick a Gram/EUR cabinet.",
                "accounts_hint": "Call list_accounts and select_account with a Gram/TON or EUR owner_id.",
            })
        return info
    except (AuthError, ConfigError, StarsCabinetError) as exc:
        return attach_gate(fail_payload(exc))


@mcp.tool(annotations=READ, **meta("get_account"))
async def get_account() -> dict[str, Any]:
    """Current cabinet card: owner_id, cabinet (ton/eur/stars), currency (GRAM/EUR/XTR), money, balance, write_gate."""
    client, err = await _client_or_fail(require_supported=False)
    if err:
        return err
    try:
        return attach_gate(await client.get_account())
    except (AuthError, ConfigError, StarsCabinetError) as exc:
        return attach_gate(fail_payload(exc))


# ── ads ──────────────────────────────────────────────────────────────


@mcp.tool(annotations=READ, **meta("get_ads"))
async def get_ads(
    offset_id: str | None = None,
    status: Literal["any", "active", "on_hold"] = "any",
    detail: Literal["summary", "full"] = "summary",
) -> dict[str, Any]:
    """List ads (100 per page). Filter by status client-side.

    Args:
        offset_id: Pagination cursor from next_offset_id.
        status: any | active | on_hold.
        detail: summary drops null/empty fields from items; full returns them as-is.
    """
    client, err = await _client_or_fail()
    if err:
        return err
    result = await client.get_ads_list(offset_id)
    items = list(result.get("items") or result.get("ads") or [])
    if status != "any":
        items = filter_ads_by_status(items, status)
        result = dict(result)
        result["items"] = items
        result["filtered_status"] = status
    if isinstance(result, dict):
        result.setdefault("ok", True)
        if detail == "summary":
            result = dict(result)
            for key in ("items", "ads"):
                if isinstance(result.get(key), list):
                    result[key] = [compact(item) for item in result[key]]
    return result


@mcp.tool(annotations=READ, **meta("get_ad"))
async def get_ad(ad_id: str) -> dict[str, Any]:
    """Fetch a single ad by id (API method, HTML state, or list fallback)."""
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.get_ad(ad_id)


@mcp.tool(annotations=WRITE, **meta("create_ad"))
async def create_ad(
    title: str,
    promote_url: str,
    cpm: str,
    target_type: Literal["channels", "bots", "search", "users"] = "channels",
    text: str = "",
    channels: str | None = None,
    bots: str | None = None,
    search_queries: str | None = None,
    langs: str | None = None,
    topics: str | None = None,
    exclude_topics: str | None = None,
    exclude_channels: str | None = None,
    conversion_event: str | None = None,
    button: str | None = None,
    audience_id: str | None = None,
    countries: str | None = None,
    locations: str | None = None,
    user_langs: str | None = None,
    user_topics: str | None = None,
    user_channels: str | None = None,
    intersect_topics: bool = False,
    exclude_user_topics: str | None = None,
    exclude_user_channels: str | None = None,
    exclude_politic: bool = False,
    exclude_crypto: bool = False,
    only_politic: bool = False,
    only_crypto: bool = False,
    device: str | None = None,
    budget: str = "0",
    daily_budget: str = "0",
    active: str = "on_hold",
    views_per_user: str = "1",
    picture: bool = False,
    media: str | None = None,
    website_name: str | None = None,
    activate_date: str | None = None,
    deactivate_date: str | None = None,
    schedule: str | None = None,
    schedule_tz: str | None = None,
    schedule_tz_custom: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Create an ad. TON/Gram cabinets allow channels, bots, search, and users (geo). EUR too.

    Always create on_hold. Budget "0" cannot go to review. IDs are semicolon-separated.
    Search ads: do not pass text/picture/media.
    Empty strings are stripped and not sent.
    Do not send langs together with specific channel IDs (platform Target invalid) —
    langs is dropped in that case.
    confirm: required for spend (budget>0 or active) when TG_ADS_WRITE_GATE is not open.
    """
    spend = (budget and budget != "0") or map_status(active) == "1"
    langs_omitted = None
    langs_sent = langs
    if channel_langs_conflict(target_type, channels, langs):
        langs_sent = None
        langs_omitted = "langs omitted: channels×langs is Target invalid"
    blocked = _gate(
        "spend" if spend else "write",
        confirm,
        "create_ad",
        {
            "title": title,
            "promote_url": promote_url,
            "cpm": cpm,
            "target_type": target_type,
            "budget": budget,
            "daily_budget": daily_budget,
            "active": active,
            "channels": channels,
            "bots": bots,
            "search_queries": search_queries,
            "langs": langs_sent,
            "topics": topics,
            "exclude_topics": exclude_topics,
            "exclude_channels": exclude_channels,
            "countries": countries,
            "locations": locations,
            "audience_id": audience_id,
        },
    )
    if blocked:
        return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    money_err = await _money_error(client, target_type=target_type, cpm=cpm, budget=budget,
                                   daily_budget=daily_budget)
    if money_err:
        return money_err
    params: dict[str, Any] = {
        "owner_id": client.owner_id,
        "title": title,
        "text": text,
        "promote_url": promote_url,
        "cpm": cpm,
        "budget": budget,
        "daily_budget": daily_budget,
        "active": map_status(active),
        "views_per_user": views_per_user,
        "target_type": target_type,
        "channels": channels,
        "bots": bots,
        "search_queries": search_queries,
        "langs": langs_sent,
        "topics": topics,
        "exclude_topics": exclude_topics,
        "exclude_channels": exclude_channels,
        "conversion_event": conversion_event,
        "button": button,
        "audience_id": audience_id,
        "countries": countries,
        "locations": locations,
        "user_langs": user_langs,
        "user_topics": user_topics,
        "user_channels": user_channels,
        "exclude_user_topics": exclude_user_topics,
        "exclude_user_channels": exclude_user_channels,
        "device": device,
        "website_name": website_name,
        "media": media,
        "activate_date": activate_date,
        "deactivate_date": deactivate_date,
        "schedule": schedule,
        "schedule_tz": schedule_tz,
        "schedule_tz_custom": schedule_tz_custom,
    }
    flags = {
        "picture": picture,
        "intersect_topics": intersect_topics,
        "exclude_politic": exclude_politic,
        "exclude_crypto": exclude_crypto,
        "only_politic": only_politic,
        "only_crypto": only_crypto,
    }
    for key, enabled in flags.items():
        if enabled:
            params[key] = "1"
    result = await client.call("createAd", params)
    if isinstance(result, dict):
        result.setdefault("ok", "error" not in result)
        if langs_omitted:
            result["langs_omitted"] = langs_omitted
    return result


@mcp.tool(annotations=WRITE, **meta("edit_ad"))
async def edit_ad(
    ad_id: str,
    title: str | None = None,
    text: str | None = None,
    promote_url: str | None = None,
    cpm: str | None = None,
    daily_budget: str | None = None,
    active: str | None = None,
    views_per_user: str | None = None,
    picture: bool | None = None,
    clear_media: bool = False,
    media: str | None = None,
    website_name: str | None = None,
    conversion_event: str | None = None,
    button: str | None = None,
    audience_id: str | None = None,
    budget_action: Literal["increase", "decrease"] | None = None,
    budget_amount: str | None = None,
    budget_target: str | None = None,
    activate_date: str | None = None,
    deactivate_date: str | None = None,
    schedule: str | None = None,
    schedule_tz: str | None = None,
    schedule_tz_custom: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Edit an ad. Only provided fields are sent.

    picture=True shows the avatar, picture=False turns it off (sends picture=0).
    clear_media=True removes attached photo/video.
    budget_action + budget_amount changes total budget (increase resumes a depleted Stopped ad).
    budget_target sets the total budget to an absolute value (the server reads the current budget and
    sends the increase/decrease difference); do not combine with budget_action.
    Targeting cannot be changed after creation — clone_ad instead.
    confirm: required to activate or change budget unless TG_ADS_WRITE_GATE=open.
    """
    going_live = active is not None and map_status(active) == "1"
    spend = going_live or bool(budget_action) or budget_target is not None
    blocked = _gate(
        "spend" if spend else "write",
        confirm,
        "edit_ad",
        {
            "ad_id": ad_id,
            "title": title,
            "cpm": cpm,
            "daily_budget": daily_budget,
            "active": active,
            "budget_action": budget_action,
            "budget_amount": budget_amount,
            "budget_target": budget_target,
        },
    )
    if blocked:
        return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    money_err = await _money_error(
        client, cpm=cpm, daily_budget=daily_budget, budget_amount=budget_amount, budget_target=budget_target
    )
    if money_err:
        return money_err
    if budget_target is not None:
        if budget_action or budget_amount:
            return attach_gate({"ok": False, "code": "invalid_args", "retryable": False,
                                "error": "Pass budget_target or budget_action+budget_amount, not both."})
        budget_action, budget_amount = await _budget_delta(client, ad_id, budget_target)
        if budget_action == "none":
            return attach_gate({"ok": True, "code": "no_change", "budget_change": None, "note": budget_amount})
        if budget_action is None:
            return attach_gate({"ok": False, "code": "budget_unknown", "retryable": False,
                                "error": budget_amount or "Current budget unknown; use budget_action."})
    results: dict[str, Any] = {}
    if budget_target is not None:
        # Report the computed difference so the spend is visible, not only the absolute target.
        results["budget_change"] = {"target": budget_target, "action": budget_action, "amount": budget_amount}
    if budget_action and budget_amount:
        method = "decrAdBudget" if budget_action == "decrease" else "incrAdBudget"
        results["budget"] = await client.call(
            method,
            {"owner_id": client.owner_id, "ad_id": ad_id, "amount": budget_amount},
        )
    params: dict[str, Any] = {
        "owner_id": client.owner_id,
        "ad_id": ad_id,
        "title": title,
        "text": text,
        "promote_url": promote_url,
        "cpm": cpm,
        "daily_budget": daily_budget,
        "active": map_status(active) if active is not None else None,
        "views_per_user": views_per_user,
        "website_name": website_name,
        "conversion_event": conversion_event,
        "button": button,
        "audience_id": audience_id,
        "activate_date": activate_date,
        "deactivate_date": deactivate_date,
        "schedule": schedule,
        "schedule_tz": schedule_tz,
        "schedule_tz_custom": schedule_tz_custom,
    }
    if picture is True:
        params["picture"] = "1"
    elif picture is False:
        params["picture"] = "0"
    if clear_media:
        params["media"] = ""
    elif media:
        params["media"] = media
    keep: set[str] = set()
    if picture is False:
        keep.add("picture")
    if clear_media:
        keep.add("media")
    editable = {k: v for k, v in params.items() if k not in {"owner_id", "ad_id"}}
    from telegram_ads_mcp.parse import strip_empty

    if strip_empty(editable, keep=keep) or keep:
        results["edit"] = await client.call("editAd", params, keep=keep or None)
    if not results:
        return {"ok": False, "error": "No fields to update."}
    results["ok"] = True
    return results


@mcp.tool(annotations=DEST, **meta("delete_ad"))
async def delete_ad(ad_id: str, confirm_hash: str | None = None, confirm: bool = False) -> dict[str, Any]:
    """Delete an ad. Two-step: first call without confirm_hash; pass the returned hash to confirm.

    confirm: TG_ADS_WRITE_GATE (danger). confirm_hash is the platform hash, not the gate.
    """
    blocked = _gate("danger", confirm, "delete_ad", {"ad_id": ad_id})
    if blocked:
        return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    params: dict[str, Any] = {"owner_id": client.owner_id, "ad_id": ad_id}
    if confirm_hash:
        params["confirm_hash"] = confirm_hash
    return await client.call("deleteAd", params)


@mcp.tool(annotations=WRITE, **meta("clone_ad"))
async def clone_ad(ad_id: str, confirm_hash: str | None = None, confirm: bool = False) -> dict[str, Any]:
    """Duplicate an ad into a new draft. Targeting is copied; edit the clone if you need changes.

    Two-step confirm_hash (platform). confirm is TG_ADS_WRITE_GATE (write).
    """
    blocked = _gate("write", confirm, "clone_ad", {"ad_id": ad_id})
    if blocked:
        return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    params: dict[str, Any] = {"owner_id": client.owner_id, "ad_id": ad_id}
    if confirm_hash:
        params["confirm_hash"] = confirm_hash
    return await client.call("createDraftFromAd", params)


@mcp.tool(annotations=READ, **meta("check_ad_post"))
async def check_ad_post(promote_url: str, text: str = "") -> dict[str, Any]:
    """Validate promote URL + text before create/launch. Surfaces platform errors."""
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.call("checkAdPost", {"owner_id": client.owner_id, "promote_url": promote_url, "text": text})


@mcp.tool(annotations=WRITE, **meta("send_target_to_review"))
async def send_target_to_review(ad_id: str, confirm: bool = False) -> dict[str, Any]:
    """Submit (or resubmit) targeting for review. Requires a non-zero budget. Spend-class gate."""
    blocked = _gate("spend", confirm, "send_target_to_review", {"ad_id": ad_id})
    if blocked:
        return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.call("sendTargetToReview", {"owner_id": client.owner_id, "ad_id": ad_id})


@mcp.tool(annotations=WRITE, **meta("launch_ad"))
async def launch_ad(
    title: str,
    promote_url: str,
    cpm: str,
    target_type: Literal["channels", "bots", "search", "users"] = "channels",
    text: str = "",
    channels: str | None = None,
    bots: str | None = None,
    search_queries: str | None = None,
    langs: str | None = None,
    topics: str | None = None,
    exclude_topics: str | None = None,
    exclude_channels: str | None = None,
    locations: str | None = None,
    exclude_user_topics: str | None = None,
    exclude_user_channels: str | None = None,
    exclude_politic: bool = False,
    exclude_crypto: bool = False,
    budget: str = "1",
    daily_budget: str = "0",
    media: str | None = None,
    audience_id: str | None = None,
    countries: str | None = None,
    user_langs: str | None = None,
    user_topics: str | None = None,
    skip_review: bool = False,
    confirm: bool = False,
) -> dict[str, Any]:
    """Create on_hold, add budget, submit for review. Does not activate.

    Spends `budget` (default 1 Gram) and sends targeting to review. Not go-live.
    Returns each step so you can see which one failed. Prefer this over calling
    create_ad + edit_ad + send_target_to_review by hand.
    Safe targeting subset vs create_ad: topics, exclude_*, locations, user_langs/user_topics.
    Do not send langs together with specific channel IDs (platform Target invalid);
    langs is dropped in that case. Full field set remains on create_ad.
    confirm: required unless TG_ADS_WRITE_GATE=open.
    """
    would = {
            "title": title,
            "promote_url": promote_url,
            "cpm": cpm,
            "target_type": target_type,
            "channels": channels,
            "bots": bots,
            "search_queries": search_queries,
            "langs": langs,
            "topics": topics,
            "exclude_topics": exclude_topics,
            "exclude_channels": exclude_channels,
            "locations": locations,
            "countries": countries,
            "budget": budget,
            "daily_budget": daily_budget,
            "skip_review": skip_review,
        }
    if channel_langs_conflict(target_type, channels, langs):
        would["langs_omitted"] = "channels×langs is Target invalid"
    blocked = _gate(
        "spend",
        confirm,
        "launch_ad",
        would,
    )
    if blocked:
        return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    steps: dict[str, Any] = {}
    steps["validate"] = await client.call(
        "checkAdPost",
        {"owner_id": client.owner_id, "promote_url": promote_url, "text": text},
    )
    created = await create_ad(
        title=title,
        promote_url=promote_url,
        cpm=cpm,
        target_type=target_type,
        text=text,
        channels=channels,
        bots=bots,
        search_queries=search_queries,
        langs=langs,
        topics=topics,
        exclude_topics=exclude_topics,
        exclude_channels=exclude_channels,
        locations=locations,
        exclude_user_topics=exclude_user_topics,
        exclude_user_channels=exclude_user_channels,
        exclude_politic=exclude_politic,
        exclude_crypto=exclude_crypto,
        budget="0",
        daily_budget=daily_budget,
        active="on_hold",
        media=media,
        audience_id=audience_id,
        countries=countries,
        user_langs=user_langs,
        user_topics=user_topics,
        confirm=confirm,
    )
    steps["create"] = created
    if isinstance(created, dict) and created.get("langs_omitted"):
        steps["langs_omitted"] = created["langs_omitted"]
    ad_id = None
    if isinstance(created, dict):
        ad_id = created.get("ad_id") or (created.get("ad") or {}).get("ad_id") or created.get("id")
    if not ad_id:
        return {"ok": False, "error": "create_ad did not return ad_id", "steps": steps}
    if budget and budget != "0":
        steps["budget"] = await client.call(
            "incrAdBudget",
            {"owner_id": client.owner_id, "ad_id": str(ad_id), "amount": budget},
        )
    if not skip_review:
        steps["review"] = await client.call(
            "sendTargetToReview",
            {"owner_id": client.owner_id, "ad_id": str(ad_id)},
        )
    return {"ok": True, "ad_id": str(ad_id), "steps": steps}


@mcp.tool(annotations=READ, structured_output=False, **meta("preview_ad"))
async def preview_ad(ad_id: str) -> CallToolResult:
    """Render a sponsored-message preview PNG for chat, and save it under TG_ADS_PREVIEW_DIR (default ./previews)."""
    client, err = await _client_or_fail()
    if err:
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(err, ensure_ascii=False))], is_error=True)
    payload = await client.preview_payload(ad_id)
    try:
        png, path = render_card(
            ad_id=ad_id,
            title=str(payload.get("title") or ""),
            text=str(payload.get("text") or ""),
            promote_url=str(payload.get("promote_url") or ""),
            image_bytes=payload.get("image_bytes") if isinstance(payload.get("image_bytes"), bytes) else None,
            cpm=str(payload.get("cpm") or ""),
            status=str(payload.get("status") or ""),
        )
    except Exception as exc:  # noqa: BLE001
        meta = {k: v for k, v in payload.items() if k != "image_bytes"}
        meta["ok"] = False
        meta["error"] = f"PNG render failed: {exc}. Fields are in this JSON; save them yourself."
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(meta, ensure_ascii=False))], is_error=True)

    meta = {
        "ok": True,
        "ad_id": ad_id,
        "path": str(path),
        "title": payload.get("title"),
        "text": payload.get("text"),
        "promote_url": payload.get("promote_url"),
        "note": "PNG is attached. If your client cannot show images, open the path.",
    }
    b64 = base64.b64encode(png).decode()
    return CallToolResult(
        content=[
            TextContent(type="text", text=json.dumps(meta, ensure_ascii=False)),
            ImageContent(type="image", data=b64, mimeType="image/png"),
        ]
    )


@mcp.tool(annotations=WRITE, **meta("upload_media"))
async def upload_media(
    file_path: str | None = None,
    filename: str | None = None,
    media_base64: str | None = None,
    ad_id: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Upload a photo (JPEG/PNG 16:9, <5 MB) or video (MP4 3–60s, <20 MB).

    Pass a local file_path OR media_base64 (+ filename). Returns a media hash
    to feed into create_ad(media=...) / edit_ad(media=...).
    """
    blocked = _gate(
        "write",
        confirm,
        "upload_media",
        {
            "filename": filename,
            "ad_id": ad_id,
            "has_file_path": bool(file_path),
            "media_base64": media_base64,
        },
    )
    if blocked:
        return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    content = base64.b64decode(media_base64) if media_base64 else None
    if not file_path and content is None:
        return {"ok": False, "error": "Provide file_path or media_base64."}
    return await client.upload_media(file_path=file_path, filename=filename, content=content, ad_id=ad_id)


@mcp.tool(annotations=READ, **meta("get_ad_stats"))
async def get_ad_stats(
    ad_id: str,
    period: Literal["5min", "day"] = "5min",
    detail: Literal["summary", "full", "csv"] = "summary",
) -> dict[str, Any]:
    """Time-bucketed stats plus CTR / CPC / actual CPM.

    period=5min → last 24h in 5-minute buckets. period=day → full lifetime daily.
    Success JSON echoes the request `period` (`5min`/`day`). `summary.period` is a
    span label (`24h`/`Nd`), not the request arg.
    `summary.spend` is already scaled (Gram on a TON cabinet); `spend_already_scaled`
    is true; `spend_scale` stays for compatibility. Do not divide again.
    `charts.budget` series/totals are scaled the same way (`values_already_scaled`).
    Prefer `summary.spend`. detail=csv returns `csv` (time + every chart series) instead of
    `charts`; if you save it, use gitignored `reports/`.
    detail=summary (default) omits the per-bucket `charts`; detail=full returns them.
    """
    client, err = await _client_or_fail()
    if err:
        return err
    stats = await client.get_ad_stats(ad_id, period=period)
    if detail == "csv" and isinstance(stats, dict) and isinstance(stats.get("charts"), dict):
        csv_text = charts_to_csv(stats["charts"])
        stats = {k: v for k, v in stats.items() if k != "charts"}
        stats["csv"] = csv_text
        return stats
    if detail == "summary" and isinstance(stats, dict) and "charts" in stats:
        stats = {k: v for k, v in stats.items() if k != "charts"}
        stats["charts_omitted"] = True
        stats["hint"] = "Pass detail='full' for per-bucket charts."
    return stats


# ── targeting ────────────────────────────────────────────────────────


@mcp.tool(annotations=READ, **meta("search_targets"))
async def search_targets(
    kind: Literal["channel", "bot", "query", "location", "similar_channels", "similar_bots"],
    query: str = "",
    ids: str | None = None,
    purpose: Literal["target", "promote"] = "target",
    country: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Search targeting entities.

    kind=channel|bot|query|location, or similar_channels/similar_bots (pass ids as semicolon-separated).
    purpose=target (placement) vs promote (destination URL lookup). Bots use field=bots vs promote_url.
    """
    client, err = await _client_or_fail()
    if err:
        return err
    if kind == "channel":
        return await client.call("searchChannel", {"owner_id": client.owner_id, "query": query, "field": "channels"})
    if kind == "bot":
        field = "promote_url" if purpose == "promote" else "bots"
        return await client.call("searchBot", {"query": query, "field": field})
    if kind == "query":
        return await client.call("searchTargetQuery", {"query": query, "field": "search_queries"})
    if kind == "location":
        params: dict[str, Any] = {"owner_id": client.owner_id}
        if query:
            params["query"] = query
        if country:
            params["country"] = country
        if region:
            params["region"] = region
        return await client.call("searchLocation", params)
    if kind == "similar_channels":
        return await client.call("getSimilarChannels", {"channels": ids or query, "for": "channels"})
    if kind == "similar_bots":
        return await client.call("getSimilarBots", {"bots": ids or query})
    return {"ok": False, "error": f"unknown kind {kind}"}


@mcp.tool(annotations=READ, **meta("get_targeting_reference"))
async def get_targeting_reference(
    kind: Literal["user", "channel", "both"] = "both",
) -> dict[str, Any]:
    """Countries / languages / topics for user-geo (Gram cabinets have this too) plus channel taxonomies.

    Stars cabinets never reach this tool. Empty lists mean the form did not embed that taxonomy.
    """
    client, err = await _client_or_fail()
    if err:
        return err
    cabinet = await client.detect_cabinet()
    out: dict[str, Any] = {"ok": True, "cabinet": cabinet["cabinet"], "currency": cabinet.get("currency")}
    if kind in ("user", "both"):
        ref = await client.get_user_targeting_reference()
        out["user"] = {
            "countries": ref.get("countryItems") or [],
            "languages": ref.get("langItems") or [],
            "topics": ref.get("userTopicItems") or [],
        }
    if kind in ("channel", "both"):
        ref = await client.get_channel_targeting_reference()
        out["channel"] = {
            "topics": ref.get("topicItems") or [],
            "languages": ref.get("langItems") or [],
            "conversion_events": ref.get("convEventItems") or [],
        }
    return out


# ── audiences / events / funds ───────────────────────────────────────


@mcp.tool(annotations=WRITE, **meta("manage_audience"))
async def manage_audience(
    action: Literal["list", "create", "rename", "delete", "clone"],
    audience_id: str | None = None,
    title: str | None = None,
    file_path: str | None = None,
    user_ids: list[str] | None = None,
    confirm_hash: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Custom audiences. action=list|create|rename|delete|clone.

    create: pass file_path (one user id per line) or user_ids=[...].
    delete/clone: two-step confirm_hash (platform). confirm is TG_ADS_WRITE_GATE.
    list is not gated. Access denied → code:access_denied, hint:skip (do not retry).
    """
    if action != "list":
        cls = "danger" if action == "delete" else "write"
        blocked = _gate(
            cls,
            confirm,
            "manage_audience",
            {
                "action": action,
                "audience_id": audience_id,
                "title": title,
                "has_file_path": bool(file_path),
                "has_user_ids": bool(user_ids),
            },
        )
        if blocked:
            return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    if action == "list":
        result = await client.call("updateAudiencesState", {"owner_id": client.owner_id})
        return _maybe_access_denied(result, tool="manage_audience", action="list")
    if action == "create":
        path = file_path
        tmp = None
        if user_ids and not path:
            from telegram_ads_mcp.client import write_temp_ids

            tmp = await write_temp_ids(user_ids)
            path = tmp
        if not path:
            return {"ok": False, "error": "create requires file_path or user_ids."}
        try:
            result = await client.upload("createAudience", file_path=path, extra={"title": title or "audience"})
        finally:
            if tmp:
                try:
                    Path(tmp).unlink(missing_ok=True)
                except OSError:
                    pass
        return _maybe_access_denied(result, tool="manage_audience", action="create")
    if action == "rename":
        return _maybe_access_denied(
            await client.call(
                "editAudienceTitle",
                {"owner_id": client.owner_id, "audience_id": audience_id, "title": title},
            ),
            tool="manage_audience",
            action="rename",
        )
    if action == "delete":
        params: dict[str, Any] = {"owner_id": client.owner_id, "audience_id": audience_id}
        if confirm_hash:
            params["confirm_hash"] = confirm_hash
        return _maybe_access_denied(
            await client.call("deleteAudience", params),
            tool="manage_audience",
            action="delete",
        )
    if action == "clone":
        params = {"owner_id": client.owner_id, "audience_id": audience_id}
        if confirm_hash:
            params["confirm_hash"] = confirm_hash
        return _maybe_access_denied(
            await client.call("createDraftFromAudience", params),
            tool="manage_audience",
            action="clone",
        )
    return {"ok": False, "error": f"unknown action {action}"}


@mcp.tool(annotations=WRITE, **meta("manage_event"))
async def manage_event(
    action: Literal["list", "create", "rename", "delete", "create_pixel"],
    event_id: str | None = None,
    title: str | None = None,
    event_type: str = "custom",
    confirm_hash: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Conversion events and pixels. action=list|create|rename|delete|create_pixel.

    list is not gated. delete is danger + two-step confirm_hash.
    Access denied → code:access_denied, hint:skip (do not retry).
    """
    if action != "list":
        cls = "danger" if action == "delete" else "write"
        blocked = _gate(
            cls,
            confirm,
            "manage_event",
            {"action": action, "event_id": event_id, "title": title, "event_type": event_type},
        )
        if blocked:
            return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    if action == "list":
        return _maybe_access_denied(
            await client.call("updateEventsState", {"owner_id": client.owner_id}),
            tool="manage_event",
            action="list",
        )
    if action == "create":
        return _maybe_access_denied(
            await client.call("createEvent", {"owner_id": client.owner_id, "title": title, "type": event_type}),
            tool="manage_event",
            action="create",
        )
    if action == "rename":
        return _maybe_access_denied(
            await client.call(
                "editEventTitle",
                {"owner_id": client.owner_id, "event_id": event_id, "title": title},
            ),
            tool="manage_event",
            action="rename",
        )
    if action == "delete":
        params: dict[str, Any] = {"owner_id": client.owner_id, "event_id": event_id}
        if confirm_hash:
            params["confirm_hash"] = confirm_hash
        return _maybe_access_denied(
            await client.call("deleteEvent", params),
            tool="manage_event",
            action="delete",
        )
    if action == "create_pixel":
        return _maybe_access_denied(
            await client.call("createPixel", {"owner_id": client.owner_id}),
            tool="manage_event",
            action="create_pixel",
        )
    return {"ok": False, "error": f"unknown action {action}"}


@mcp.tool(annotations=DEST, **meta("manage_funds"))
async def manage_funds(
    action: Literal["add", "transfer", "withdraw", "search", "list"],
    amount: str | None = None,
    account_id: str | None = None,
    query: str | None = None,
    additional_comment: str = "",
    confirm: bool = False,
) -> dict[str, Any]:
    """Funds. Amount is a Gram (or EUR) string.

    list/search = lookup, not gated.
    add = top-up *request* (not instant credit).
    transfer/withdraw = money moves in this one call — no confirm_hash. Danger gate.
    """
    if action in {"add", "transfer", "withdraw"}:
        blocked = _gate(
            "danger",
            confirm,
            "manage_funds",
            {"action": action, "amount": amount, "account_id": account_id},
        )
        if blocked:
            return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    cabinet = await client.detect_cabinet()
    currency = cabinet.get("currency")
    if action == "add":
        params: dict[str, Any] = {"owner_id": client.owner_id, "amount": amount}
        if additional_comment:
            params["additional_comment"] = additional_comment
        result = await client.call("sendAddFundsRequest", params)
        if isinstance(result, dict):
            result["currency"] = currency
        return result
    if action == "transfer":
        result = await client.call(
            "transferFunds",
            {"owner_id": client.owner_id, "account_id": account_id, "amount": amount},
        )
        if isinstance(result, dict):
            result["currency"] = currency
        return result
    if action == "withdraw":
        result = await client.call(
            "transferWithdrawFunds",
            {"owner_id": client.owner_id, "account_id": account_id, "amount": amount},
        )
        if isinstance(result, dict):
            result["currency"] = currency
        return result
    if action == "search":
        return await client.call("searchAccountForTransfer", {"owner_id": client.owner_id, "query": query})
    if action == "list":
        return await client.call("getAccountsForTransfer", {"owner_id": client.owner_id})
    return {"ok": False, "error": f"unknown action {action}"}


@mcp.tool(annotations=DEST, **meta("revoke_token"))
async def revoke_token(confirm: bool = False) -> dict[str, Any]:
    """Revoke and regenerate the cabinet API token (IP-whitelist token, not ads cookies)."""
    blocked = _gate("danger", confirm, "revoke_token", {"action": "revoke_token"})
    if blocked:
        return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.call("revokeToken", {"owner_id": client.owner_id})


@mcp.tool(annotations=WRITE, **meta("save_api_settings"))
async def save_api_settings(ip_list: str, confirm: bool = False) -> dict[str, Any]:
    """Set the IP whitelist for the cabinet API token. Newline-separated IPs."""
    blocked = _gate("danger", confirm, "save_api_settings", {"ip_list": ip_list})
    if blocked:
        return blocked
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.call("saveApiSettings", {"owner_id": client.owner_id, "ip_list": ip_list})


@mcp.tool(annotations=DEST, **meta("log_out"))
async def log_out(confirm: bool = False) -> dict[str, Any]:
    """Log out of ads.telegram.org for this session. You will need fresh cookies in .env afterwards."""
    blocked = _gate("danger", confirm, "log_out", {"action": "log_out"})
    if blocked:
        return blocked
    client, err = await _client_or_fail(require_supported=False)
    if err:
        return err
    return await client.call("logOut", {})


# Optional lazy tool loading (TG_ADS_TOOL_LOADING=lazy): defer non-core tools until enabled.
LAZY_LISTED = lazy_loading.install(mcp)


# ── entry ────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(prog="telegram-ads-mcp")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "sse"),
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
    )
    parser.add_argument("--host", default=os.environ.get("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_PORT", "8000")))
    args = parser.parse_args()
    log.info("starting telegram-ads-mcp %s transport=%s", __version__, args.transport)
    refresh_in_background()
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
