"""Telegram Ads MCP server — MCP Python SDK v2."""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from mcp.server import MCPServer
from mcp.types import CallToolResult, ImageContent, TextContent, ToolAnnotations

from telegram_ads_mcp import __version__
from telegram_ads_mcp.client import AuthError, ConfigError, StarsCabinetError
from telegram_ads_mcp.parse import filter_ads_by_status, map_status, redact
from telegram_ads_mcp.preview import render_card
from telegram_ads_mcp.session import fail_payload, get_client, reload_from_env, switch_account

load_dotenv()

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

_PLAYBOOK_CANDIDATES = (
    Path(__file__).resolve().parent / "AGENTS.md",
    Path(__file__).resolve().parent.parent / "AGENTS.md",
)

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=True)
DEST = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True)

mcp = MCPServer(
    name="telegram-ads-mcp",
    title="Telegram Ads",
    version=__version__,
    instructions=(
        "MCP server for ads.telegram.org. TON/Gram cabinets are primary (user-geo allowed). EUR is supported. "
        "Stars cabinets are detected and refused — switch with list_accounts/select_account. "
        "Cookies live in .env only (STEL_TOKEN, STEL_SSID). Never ask the user to paste cookies "
        "into chat; tell them to update .env and call reload_session. "
        "Always create ads on_hold, add budget, then send_target_to_review. "
        "Read ads://playbook at session start."
    ),
    website_url="https://github.com/zai-one/telegram-ads-mcp",
)


def _ok(data: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": True}
    if data:
        out.update(data)
    out.update(extra)
    return out


async def _client_or_fail(require_supported: bool = True):
    try:
        client = await get_client()
        if require_supported:
            await client.require_supported_cabinet()
        return client, None
    except (ConfigError, AuthError, StarsCabinetError) as exc:
        return None, fail_payload(exc)


# ── resources / prompts ──────────────────────────────────────────────


@mcp.resource("ads://playbook", mime_type="text/markdown")
def playbook_resource() -> str:
    """Agent playbook: auth, create-on-hold, budget, review, TON Gram user-geo."""
    for path in _PLAYBOOK_CANDIDATES:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return "AGENTS.md is missing from the install."


@mcp.resource("ads://account", mime_type="application/json")
async def account_resource() -> str:
    """Current cabinet: owner_id, currency, balance, type."""
    client, err = await _client_or_fail(require_supported=False)
    if err:
        return json.dumps(err, ensure_ascii=False)
    info = await client.get_account()
    info.pop("api_hash", None)
    return json.dumps(info, ensure_ascii=False)


@mcp.prompt(name="launch-campaign", description="End-to-end flow to create and submit a Telegram ad.")
def launch_campaign_prompt(
    target_type: str = "channels",
    promote_url: str = "https://t.me/your_channel",
) -> str:
    return (
        f"Launch a {target_type} ad promoting {promote_url}.\n"
        "1. check_session — if ok=false, tell the user to refresh .env cookies and reload_session.\n"
        "2. get_account — confirm TON/Gram (or EUR), read balance and currency. Abort on Stars.\n"
        "3. search_targets to resolve IDs.\n"
        "4. check_ad_post on the promote_url + text.\n"
        "5. launch_ad (creates on_hold, adds budget, sends to review). Do not auto-activate.\n"
        "6. preview_ad and show the PNG to the user.\n"
    )


@mcp.prompt(name="review-account", description="Read-only morning pass: balance, live vs stopped ads, stats on a few problems.")
def review_account_prompt() -> str:
    return (
        "Read-only review of the Telegram Ads cabinet. Do not create, edit, or spend.\n"
        "1. get_account — expect cabinet=ton, currency=GRAM, a Gram balance. Abort if eur/stars misdetect.\n"
        "2. get_ads(status=active) and get_ads(status=on_hold). Use list spent/views/ctr; do not fetch stats for every ad.\n"
        "3. Pick at most 5 problem ads (Active with 0 views, or Stopped with leftover daily_budget, or CTR crash).\n"
        "4. For each: get_ad_stats(period=5min) then period=day if needed. Compare summary.spend to list spent (same order of magnitude).\n"
        "5. preview_ad only if copy might be the issue.\n"
        "6. Recommend at most one change (pause xor CPM xor budget xor text). Wait for the user before any write.\n"
    )


@mcp.prompt(name="diagnose-ad", description="Inspect one ad: card, stats, preview.")
def diagnose_ad_prompt(ad_id: str = "") -> str:
    return (
        f"Diagnose ad {ad_id or '(ask the user for ad_id)'}.\n"
        "Call get_ad, get_ad_stats(period=5min), preview_ad. "
        "Summarise views/clicks/CTR/spend and whether budget or status is blocking delivery."
    )


# ── auth ─────────────────────────────────────────────────────────────


@mcp.tool(annotations=READ)
async def check_session() -> dict[str, Any]:
    """Ping the current ads.telegram.org session.

    Returns owner_id, cabinet (ton/eur/stars), currency, balance.
    Does not return api_hash or cookies. Stars cabinets are reported but not used.
    If ok=false with code=auth, tell the user to refresh cookies in .env and call reload_session.
    """
    client, err = await _client_or_fail(require_supported=False)
    if err:
        return err
    try:
        await client.authenticate()
        info = await client.get_account()
        return info
    except (AuthError, ConfigError, StarsCabinetError) as exc:
        return fail_payload(exc)


@mcp.tool(annotations=WRITE)
async def reload_session() -> dict[str, Any]:
    """Re-read .env (STEL_TOKEN / STEL_SSID / STEL_ADOWNER) and rebuild the HTTP session.

    Use this after the user updates cookies on disk. Never pass cookie values as arguments.
    """
    try:
        client = await reload_from_env()
        await client.authenticate()
        info = await client.get_account()
        return info
    except (AuthError, ConfigError) as exc:
        return fail_payload(exc)


@mcp.tool(annotations=READ)
async def list_accounts() -> dict[str, Any]:
    """List ad cabinets for this Telegram login. Works even on a Stars cabinet so you can switch away."""
    client, err = await _client_or_fail(require_supported=False)
    if err:
        return err
    try:
        accounts = await client.list_accounts()
        return _ok(accounts=accounts)
    except (AuthError, ConfigError) as exc:
        return fail_payload(exc)


@mcp.tool(annotations=WRITE)
async def select_account(owner_id: str) -> dict[str, Any]:
    """Switch the active ad cabinet. Then check_session / get_account.

    Args:
        owner_id: From list_accounts.
    """
    try:
        client = await switch_account(owner_id)
        info = await client.get_account()
        if info.get("cabinet") == "stars":
            return {
                "ok": False,
                "code": "stars_cabinet",
                "cabinet": "stars",
                "owner_id": owner_id,
                "error": "Stars cabinet selected. This server refuses to run ads on Stars. Pick a TON or EUR cabinet.",
                "accounts_hint": "Call list_accounts and select_account with a TON/EUR owner_id.",
            }
        return info
    except (AuthError, ConfigError, StarsCabinetError) as exc:
        return fail_payload(exc)


@mcp.tool(annotations=READ)
async def get_account() -> dict[str, Any]:
    """Current cabinet card: owner_id, ton/eur/stars, currency, balance."""
    client, err = await _client_or_fail(require_supported=False)
    if err:
        return err
    try:
        return await client.get_account()
    except (AuthError, ConfigError, StarsCabinetError) as exc:
        return fail_payload(exc)


# ── ads ──────────────────────────────────────────────────────────────


@mcp.tool(annotations=READ)
async def get_ads(
    offset_id: str | None = None,
    status: Literal["any", "active", "on_hold"] = "any",
) -> dict[str, Any]:
    """List ads (100 per page). Filter by status client-side.

    Args:
        offset_id: Pagination cursor from next_offset_id.
        status: any | active | on_hold.
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
    return result


@mcp.tool(annotations=READ)
async def get_ad(ad_id: str) -> dict[str, Any]:
    """Fetch a single ad by id (API method, HTML state, or list fallback)."""
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.get_ad(ad_id)


@mcp.tool(annotations=WRITE)
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
) -> dict[str, Any]:
    """Create an ad. TON/Gram allows channels, bots, search, and users (geo). EUR too.

    Always create on_hold. Budget "0" cannot go to review. IDs are semicolon-separated.
    Search ads: do not pass text/picture/media.
    Empty strings are stripped and not sent.
    """
    client, err = await _client_or_fail()
    if err:
        return err
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
        "langs": langs,
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
    return result


@mcp.tool(annotations=WRITE)
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
    activate_date: str | None = None,
    deactivate_date: str | None = None,
    schedule: str | None = None,
    schedule_tz: str | None = None,
    schedule_tz_custom: str | None = None,
) -> dict[str, Any]:
    """Edit an ad. Only provided fields are sent.

    picture=True shows the avatar, picture=False turns it off (sends picture=0).
    clear_media=True removes attached photo/video.
    budget_action + budget_amount changes total budget (increase resumes a depleted ad).
    Targeting cannot be changed after creation — clone_ad instead.
    """
    client, err = await _client_or_fail()
    if err:
        return err
    results: dict[str, Any] = {}
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


@mcp.tool(annotations=DEST)
async def delete_ad(ad_id: str, confirm_hash: str | None = None) -> dict[str, Any]:
    """Delete an ad. First call without confirm_hash; pass the returned hash to confirm."""
    client, err = await _client_or_fail()
    if err:
        return err
    params: dict[str, Any] = {"owner_id": client.owner_id, "ad_id": ad_id}
    if confirm_hash:
        params["confirm_hash"] = confirm_hash
    return await client.call("deleteAd", params)


@mcp.tool(annotations=WRITE)
async def clone_ad(ad_id: str, confirm_hash: str | None = None) -> dict[str, Any]:
    """Duplicate an ad into a new draft. Targeting is copied; edit the clone if you need changes."""
    client, err = await _client_or_fail()
    if err:
        return err
    params: dict[str, Any] = {"owner_id": client.owner_id, "ad_id": ad_id}
    if confirm_hash:
        params["confirm_hash"] = confirm_hash
    return await client.call("createDraftFromAd", params)


@mcp.tool(annotations=READ)
async def check_ad_post(promote_url: str, text: str = "") -> dict[str, Any]:
    """Validate promote URL + text before create/launch. Surfaces platform errors."""
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.call("checkAdPost", {"owner_id": client.owner_id, "promote_url": promote_url, "text": text})


@mcp.tool(annotations=WRITE)
async def send_target_to_review(ad_id: str) -> dict[str, Any]:
    """Submit (or resubmit) targeting for review. Requires a non-zero budget."""
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.call("sendTargetToReview", {"owner_id": client.owner_id, "ad_id": ad_id})


@mcp.tool(annotations=WRITE)
async def launch_ad(
    title: str,
    promote_url: str,
    cpm: str,
    target_type: Literal["channels", "bots", "search", "users"] = "channels",
    text: str = "",
    channels: str | None = None,
    bots: str | None = None,
    search_queries: str | None = None,
    budget: str = "1",
    daily_budget: str = "0",
    media: str | None = None,
    audience_id: str | None = None,
    countries: str | None = None,
    user_langs: str | None = None,
    user_topics: str | None = None,
    skip_review: bool = False,
) -> dict[str, Any]:
    """Create on_hold, add budget, submit for review. Does not activate.

    Returns each step so you can see which one failed. Prefer this over calling
    create_ad + edit_ad + send_target_to_review by hand.
    """
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
        budget="0",
        daily_budget=daily_budget,
        active="on_hold",
        media=media,
        audience_id=audience_id,
        countries=countries,
        user_langs=user_langs,
        user_topics=user_topics,
    )
    steps["create"] = created
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


@mcp.tool(annotations=READ, structured_output=False)
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


@mcp.tool(annotations=WRITE)
async def upload_media(
    file_path: str | None = None,
    filename: str | None = None,
    media_base64: str | None = None,
    ad_id: str | None = None,
) -> dict[str, Any]:
    """Upload a photo (JPEG/PNG 16:9, <5 MB) or video (MP4 3–60s, <20 MB).

    Pass a local file_path OR media_base64 (+ filename). Returns a media hash
    to feed into create_ad(media=...) / edit_ad(media=...).
    """
    client, err = await _client_or_fail()
    if err:
        return err
    content = base64.b64decode(media_base64) if media_base64 else None
    if not file_path and content is None:
        return {"ok": False, "error": "Provide file_path or media_base64."}
    return await client.upload_media(file_path=file_path, filename=filename, content=content, ad_id=ad_id)


@mcp.tool(annotations=READ)
async def get_ad_stats(ad_id: str, period: Literal["5min", "day"] = "5min") -> dict[str, Any]:
    """Time-bucketed stats plus CTR / CPC / actual CPM.

    period=5min → last 24h in 5-minute buckets. period=day → full lifetime daily.
    """
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.get_ad_stats(ad_id, period=period)


# ── targeting ────────────────────────────────────────────────────────


@mcp.tool(annotations=READ)
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


@mcp.tool(annotations=READ)
async def get_targeting_reference(
    kind: Literal["user", "channel", "both"] = "both",
) -> dict[str, Any]:
    """Countries / languages / topics for user-geo (TON Gram cabinets have this too) plus channel taxonomies.

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


@mcp.tool(annotations=WRITE)
async def manage_audience(
    action: Literal["list", "create", "rename", "delete", "clone"],
    audience_id: str | None = None,
    title: str | None = None,
    file_path: str | None = None,
    user_ids: list[str] | None = None,
    confirm_hash: str | None = None,
) -> dict[str, Any]:
    """Custom audiences. action=list|create|rename|delete|clone.

    create: pass file_path (one user id per line) or user_ids=[...].
    delete/clone: two-step confirm_hash.
    """
    client, err = await _client_or_fail()
    if err:
        return err
    if action == "list":
        result = await client.call("updateAudiencesState", {"owner_id": client.owner_id})
        if isinstance(result, dict):
            result.setdefault("ok", True)
        return result
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
        return result
    if action == "rename":
        return await client.call(
            "editAudienceTitle",
            {"owner_id": client.owner_id, "audience_id": audience_id, "title": title},
        )
    if action == "delete":
        params: dict[str, Any] = {"owner_id": client.owner_id, "audience_id": audience_id}
        if confirm_hash:
            params["confirm_hash"] = confirm_hash
        return await client.call("deleteAudience", params)
    if action == "clone":
        params = {"owner_id": client.owner_id, "audience_id": audience_id}
        if confirm_hash:
            params["confirm_hash"] = confirm_hash
        return await client.call("createDraftFromAudience", params)
    return {"ok": False, "error": f"unknown action {action}"}


@mcp.tool(annotations=WRITE)
async def manage_event(
    action: Literal["list", "create", "rename", "delete", "create_pixel"],
    event_id: str | None = None,
    title: str | None = None,
    event_type: str = "custom",
    confirm_hash: str | None = None,
) -> dict[str, Any]:
    """Conversion events and pixels. action=list|create|rename|delete|create_pixel."""
    client, err = await _client_or_fail()
    if err:
        return err
    if action == "list":
        return await client.call("updateEventsState", {"owner_id": client.owner_id})
    if action == "create":
        return await client.call("createEvent", {"owner_id": client.owner_id, "title": title, "type": event_type})
    if action == "rename":
        return await client.call("editEventTitle", {"owner_id": client.owner_id, "event_id": event_id, "title": title})
    if action == "delete":
        params: dict[str, Any] = {"owner_id": client.owner_id, "event_id": event_id}
        if confirm_hash:
            params["confirm_hash"] = confirm_hash
        return await client.call("deleteEvent", params)
    if action == "create_pixel":
        return await client.call("createPixel", {"owner_id": client.owner_id})
    return {"ok": False, "error": f"unknown action {action}"}


@mcp.tool(annotations=DEST)
async def manage_funds(
    action: Literal["add", "transfer", "withdraw", "search", "list"],
    amount: str | None = None,
    account_id: str | None = None,
    query: str | None = None,
    additional_comment: str = "",
) -> dict[str, Any]:
    """Funds. Currency follows the cabinet (Gram on TON, EUR on EUR) — amount is a string.

    action=add (top-up request), transfer, withdraw, search (find a cabinet), list (linked cabinets).
    """
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


@mcp.tool(annotations=DEST)
async def revoke_token() -> dict[str, Any]:
    """Revoke and regenerate the cabinet API token (IP-whitelist token on ads.telegram.org)."""
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.call("revokeToken", {"owner_id": client.owner_id})


@mcp.tool(annotations=WRITE)
async def save_api_settings(ip_list: str) -> dict[str, Any]:
    """Set the IP whitelist for the cabinet API token. Newline-separated IPs."""
    client, err = await _client_or_fail()
    if err:
        return err
    return await client.call("saveApiSettings", {"owner_id": client.owner_id, "ip_list": ip_list})


@mcp.tool(annotations=DEST)
async def log_out() -> dict[str, Any]:
    """Log out of ads.telegram.org for this session. You will need fresh cookies in .env afterwards."""
    client, err = await _client_or_fail(require_supported=False)
    if err:
        return err
    return await client.call("logOut", {})


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
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
