"""Telegram Ads MCP Server — all tools for ads.telegram.org."""

import os
import json

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from client import TelegramAdsClient, AuthError

load_dotenv()

mcp = FastMCP("tg-ads-mcp")

_client: TelegramAdsClient | None = None


def get_client() -> TelegramAdsClient:
    global _client
    if _client is None:
        _client = TelegramAdsClient(
            stel_token=os.environ["STEL_TOKEN"],
            stel_ssid=os.environ["STEL_SSID"],
            stel_adowner=os.environ.get("STEL_ADOWNER"),
        )
    return _client


def _owner() -> str:
    c = get_client()
    c._ensure_auth()
    return c.owner_id


# ──────────────────────────────────────────────
#  AUTH
# ──────────────────────────────────────────────


@mcp.tool()
def check_session() -> str:
    """Check if the current session is valid.
    Returns owner_id, api_hash, and account info if authenticated.
    Returns an error message if cookies are expired."""
    c = get_client()
    try:
        info = c.authenticate()
        return json.dumps({
            "ok": True,
            "owner_id": c.owner_id,
            "api_hash": c.api_hash,
        }, ensure_ascii=False)
    except AuthError as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def list_accounts() -> str:
    """List all ad accounts available for the current session.
    Returns account title, description, and owner_id for each.
    Use select_account() to switch between them."""
    c = get_client()
    try:
        accounts = c.list_accounts()
        return json.dumps({"ok": True, "accounts": accounts}, ensure_ascii=False)
    except AuthError as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def select_account(owner_id: str) -> str:
    """Switch to a different ad account.
    Use list_accounts() first to see available accounts.

    Args:
        owner_id: The owner_id of the account to switch to.
    """
    global _client
    c = get_client()
    try:
        c.select_account(owner_id)
        c.api_hash = None
        c.owner_id = None
        c._api_url = None
        # Cabinet-type detection and user-targeting reference are cabinet-specific —
        # invalidate caches so the next probe re-fetches from the new cabinet's HTML.
        c._is_eur = None
        c._user_targeting_ref = None
        info = c.authenticate()
        return json.dumps(info, ensure_ascii=False)
    except AuthError as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def update_cookies(stel_token: str, stel_ssid: str, stel_adowner: str | None = None) -> str:
    """Update session cookies without restarting the MCP server.
    Use this when cookies expire — get fresh ones from your browser.

    Args:
        stel_token: The stel_token cookie value from ads.telegram.org.
        stel_ssid: The stel_ssid cookie value from ads.telegram.org.
        stel_adowner: Optional — the stel_adowner cookie (account ID).
    """
    global _client
    _client = TelegramAdsClient(
        stel_token=stel_token,
        stel_ssid=stel_ssid,
        stel_adowner=stel_adowner,
    )
    try:
        _client.authenticate()
        return json.dumps({
            "ok": True,
            "owner_id": _client.owner_id,
            "api_hash": _client.api_hash,
        }, ensure_ascii=False)
    except AuthError as e:
        _client = None
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


# ──────────────────────────────────────────────
#  ADS — CRUD & management
# ──────────────────────────────────────────────


@mcp.tool()
def get_ads_list(offset_id: str | None = None) -> str:
    """Get the list of all ads for the current account (100 per page).
    Returns items[] with ad_id, title, text, status, views, cpm, spent, target, etc.
    Use next_offset_id from response for pagination."""
    c = get_client()
    result = c.call("getAdsList", {
        "owner_id": _owner(),
        "offset_id": offset_id,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def create_ad(
    title: str,
    promote_url: str,
    cpm: str,
    target_type: str = "channels",
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
    budget: str = "0",
    daily_budget: str = "0",
    active: str = "on_hold",
    views_per_user: str = "1",
    picture: bool = False,
    media: str | None = None,
    website_name: str | None = None,
    activate_date: str | None = None,
    deactivate_date: str | None = None,
    use_schedule: bool = False,
    schedule: str | None = None,
    schedule_tz: str | None = None,
    schedule_tz_custom: str | None = None,
) -> str:
    """Create a new ad on Telegram Ads platform. Works on both TON and EUR cabinets.

    Args:
        title: Internal ad title (not shown to users).
        promote_url: URL to promote — bot link (t.me/botname) or channel link.
        cpm: Cost per 1000 views (TON for TON cabinet, EUR for EUR cabinet, e.g. "0.15" / "1.00").
        target_type: Targeting type — "channels", "bots", or "search".
            - "channels": target specific channels (use channels param). On EUR cabinets, can ALSO
              target broad categories via langs/topics without listing channels manually.
            - "bots": target specific bots (use bots param). Bot must have 1000+ daily users.
            - "search": target search keywords (use search_queries param). No text/picture/media for search ads.
        text: Ad text shown to users (max 160 chars). For channels and bots only — search ads have no text.
        channels: Semicolon-separated channel IDs (from search_channel). For target_type="channels".
        bots: Semicolon-separated bot IDs (from search_bot). For target_type="bots".
        search_queries: Semicolon-separated search query IDs (from search_target_query). For target_type="search".

        # ── EUR-cabinet-only fields (target_type="channels") ───────────────────────
        # These extend the Channels target with broad-audience filters that TON cabinets do not
        # expose. On TON cabinets, leave None; the platform will reject the ad if you pass them.
        langs: Semicolon-separated channel language codes (e.g. "en;ru"). Filters which
               channels the ad appears in by the channel's content language. EUR Channels-target only.
        topics: Semicolon-separated channel-topic numeric IDs (e.g. "13;19"). Filters by the
                topic the channel is registered under (Art, Books, Education, Foreign Language
                Learning, …). Get IDs from get_channel_targeting_reference(). EUR Channels-target only.
        exclude_topics: Semicolon-separated channel-topic IDs to EXCLUDE. EUR Channels-target only.
        exclude_channels: Semicolon-separated channel IDs to EXCLUDE. EUR Channels-target only.

        # ── EUR-cabinet-only fields (any target_type) ─────────────────────────────
        conversion_event: Conversion event ID to attribute (e.g. "page_views", "landing_views").
                          Get available IDs from get_channel_targeting_reference()['conversion_events'].
                          EUR-only — TON cabinets have no conversion tracking.
        button: Custom call-to-action button text shown on the ad
                (e.g. "OPEN WEBSITE", "JOIN CHANNEL", "VIEW MORE"). EUR-only.
        # ──────────────────────────────────────────────────────────────────────────

        budget: Total budget. "0" = no budget (ad won't go to review until budget is added).
        daily_budget: Daily budget. "0" = unlimited.
        active: Initial status after review — "active" or "on_hold" (default).
        views_per_user: Max views per unique user per day: "1", "2", "3", or "4" (default "1").
        picture: Show bot/channel avatar in the ad. For channels and bots only.
        media: Media hash for uploaded photo/video. For channels only.
        website_name: Display name for website promote URLs.
        activate_date: Auto-start date (YYYY-MM-DD HH:MM format).
        deactivate_date: Auto-stop date (YYYY-MM-DD HH:MM format).
        use_schedule: Enable hourly schedule.
        schedule: Schedule data string (7 semicolon-separated day values).
        schedule_tz: Timezone code for schedule.
        schedule_tz_custom: Custom timezone offset for schedule.
    """
    # Map human-readable status to API values
    status_map = {"active": "1", "on_hold": "0", "on hold": "0"}
    active_value = status_map.get(active.lower(), active) if active else "0"

    c = get_client()
    params = {
        "owner_id": _owner(),
        "title": title,
        "text": text,
        "promote_url": promote_url,
        "cpm": cpm,
        "budget": budget,
        "daily_budget": daily_budget,
        "active": active_value,
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
        "website_name": website_name,
        "media": media,
    }
    if picture:
        params["picture"] = "1"
    if activate_date:
        params["activate_date"] = activate_date
    if deactivate_date:
        params["deactivate_date"] = deactivate_date
    if use_schedule:
        params["schedule"] = schedule
        params["schedule_tz"] = schedule_tz
        params["schedule_tz_custom"] = schedule_tz_custom

    result = c.call("createAd", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def edit_ad(
    ad_id: str,
    title: str | None = None,
    text: str | None = None,
    promote_url: str | None = None,
    cpm: str | None = None,
    daily_budget: str | None = None,
    active: str | None = None,
    views_per_user: str | None = None,
    picture: bool = False,
    media: str | None = None,
    website_name: str | None = None,
    conversion_event: str | None = None,
    button: str | None = None,
    activate_date: str | None = None,
    deactivate_date: str | None = None,
    use_schedule: bool = False,
    schedule: str | None = None,
    schedule_tz: str | None = None,
    schedule_tz_custom: str | None = None,
) -> str:
    """Edit an existing ad. Works on both TON and EUR cabinets. Only provided fields are updated.

    Note: targeting (channels/bots/search_queries, langs/topics/exclude_*) cannot be changed
    after creation — clone the ad if you need different targeting.
    Note: promote_url cannot be changed to a different bot/channel.
    Note: use edit_ad_status for status changes, edit_ad_budget for budget changes.

    Args:
        ad_id: The ad ID.
        title: Internal ad title.
        text: Ad text (max 160 chars). Channels and bots only.
        promote_url: URL to promote.
        cpm: Cost per 1000 views (TON for TON cabinet, EUR for EUR cabinet).
        daily_budget: Daily budget. "0" = unlimited.
        active: Status — "active" or "on_hold".
        views_per_user: Max views per user per day: "1"-"4".
        picture: Show bot/channel avatar.
        media: Media hash for photo/video. Channels only.
        website_name: Display name for website promote URLs.
        conversion_event: Conversion event ID. EUR-only — leave None on TON cabinets.
        button: Custom CTA button text (e.g. "OPEN WEBSITE", "JOIN CHANNEL"). EUR-only.
        activate_date: Auto-start date (YYYY-MM-DD HH:MM).
        deactivate_date: Auto-stop date (YYYY-MM-DD HH:MM).
        use_schedule: Enable hourly schedule.
        schedule: Schedule data string.
        schedule_tz: Timezone code.
        schedule_tz_custom: Custom timezone offset.
    """
    c = get_client()
    params = {
        "owner_id": _owner(),
        "ad_id": ad_id,
        "title": title,
        "text": text,
        "promote_url": promote_url,
        "cpm": cpm,
        "daily_budget": daily_budget,
        "active": active,
        "views_per_user": views_per_user,
        "website_name": website_name,
        "media": media,
        "conversion_event": conversion_event,
        "button": button,
    }
    if picture:
        params["picture"] = "1"
    if activate_date:
        params["activate_date"] = activate_date
    if deactivate_date:
        params["deactivate_date"] = deactivate_date
    if use_schedule:
        params["schedule"] = schedule
        params["schedule_tz"] = schedule_tz
        params["schedule_tz_custom"] = schedule_tz_custom

    result = c.call("editAd", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def edit_ad_title(ad_id: str, title: str) -> str:
    """Quick-edit just the ad title without touching other fields."""
    c = get_client()
    result = c.call("editAdTitle", {
        "owner_id": _owner(),
        "ad_id": ad_id,
        "title": title,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def edit_ad_cpm(ad_id: str, cpm: str) -> str:
    """Quick-edit the ad CPM (cost per 1000 views — TON on TON cabinets, EUR on EUR cabinets).
    Example: cpm="0.10" for 0.10 per 1000 views. Passed as a string, not a number."""
    c = get_client()
    result = c.call("editAdCPM", {
        "owner_id": _owner(),
        "ad_id": ad_id,
        "cpm": cpm,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def edit_ad_budget(ad_id: str, amount: str, action: str = "increase") -> str:
    """Increase or decrease an ad's budget.

    Args:
        ad_id: The ad ID.
        amount: Amount to add or withdraw, in the cabinet's currency — TON on TON
                cabinets, EUR on EUR cabinets (e.g. "0.5", "1").
        action: "increase" to add funds, "decrease" to withdraw funds back to account balance.

    Notes:
        - Minimum budget after decrease is 1 (TON on TON cabinets, EUR on EUR cabinets).
        - Decreased funds return to your account balance and can be reused.
        - Increasing budget on a stopped (budget-depleted) ad resumes it without re-review.
    """
    c = get_client()
    method = "decrAdBudget" if action.lower() in ("decrease", "decr", "withdraw") else "incrAdBudget"
    result = c.call(method, {
        "owner_id": _owner(),
        "ad_id": ad_id,
        "amount": amount,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def edit_ad_daily_budget(ad_id: str, daily_budget: str) -> str:
    """Quick-edit the ad daily budget (TON on TON cabinets, EUR on EUR cabinets). "0" = unlimited."""
    c = get_client()
    result = c.call("editAdDailyBudget", {
        "owner_id": _owner(),
        "ad_id": ad_id,
        "daily_budget": daily_budget,
        "popup": "1",
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def edit_ad_status(
    ad_id: str,
    active: str,
    activate_date: str | None = None,
    deactivate_date: str | None = None,
    use_schedule: bool = False,
    schedule: str | None = None,
    schedule_tz: str | None = None,
    schedule_tz_custom: str | None = None,
) -> str:
    """Change ad status.

    Args:
        ad_id: The ad ID.
        active: "active" or "on_hold" (also accepts "1"/"0").
        activate_date: Optional start date (YYYY-MM-DD HH:MM).
        deactivate_date: Optional end date (YYYY-MM-DD HH:MM).
        use_schedule: Enable time-of-day schedule.
        schedule: Schedule data string.
        schedule_tz: Timezone code.
        schedule_tz_custom: Custom timezone offset.
    """
    # Platform expects "1" (active) or "0" (on_hold), not string names
    status_map = {"active": "1", "on_hold": "0", "on hold": "0"}
    active_value = status_map.get(active.lower(), active)

    c = get_client()
    params = {
        "owner_id": _owner(),
        "ad_id": ad_id,
        "active": active_value,
    }
    if activate_date:
        params["activate_date"] = activate_date
    if deactivate_date:
        params["deactivate_date"] = deactivate_date
    if use_schedule:
        params["schedule"] = schedule
        params["schedule_tz_custom"] = schedule_tz_custom
        params["schedule_tz"] = schedule_tz
    result = c.call("editAdStatus", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def delete_ad(ad_id: str, confirm_hash: str | None = None) -> str:
    """Delete an ad. First call without confirm_hash to get the confirmation hash,
    then call again with the returned confirm_hash to confirm deletion."""
    c = get_client()
    params = {
        "owner_id": _owner(),
        "ad_id": ad_id,
    }
    if confirm_hash:
        params["confirm_hash"] = confirm_hash
    result = c.call("deleteAd", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def clone_ad(ad_id: str, confirm_hash: str | None = None) -> str:
    """Clone/duplicate an existing ad into a new draft.
    May require confirm_hash for confirmation (two-step like delete)."""
    c = get_client()
    params = {
        "owner_id": _owner(),
        "ad_id": ad_id,
    }
    if confirm_hash:
        params["confirm_hash"] = confirm_hash
    result = c.call("createDraftFromAd", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def check_ad_post(promote_url: str, text: str = "") -> str:
    """Validate an ad's promote URL and text before creating.
    Returns info about the target (bot/channel/website) and any validation errors."""
    c = get_client()
    result = c.call("checkAdPost", {
        "owner_id": _owner(),
        "promote_url": promote_url,
        "text": text,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def send_target_to_review(ad_id: str) -> str:
    """Resubmit an ad's targeting for review after it was declined."""
    c = get_client()
    result = c.call("sendTargetToReview", {
        "owner_id": _owner(),
        "ad_id": ad_id,
    })
    return json.dumps(result, ensure_ascii=False)


# ──────────────────────────────────────────────
#  DRAFTS
# ──────────────────────────────────────────────


@mcp.tool()
def save_ad_draft(
    title: str = "",
    text: str = "",
    promote_url: str = "",
    cpm: str = "",
    budget: str = "",
    daily_budget: str = "",
    active: str = "on_hold",
    views_per_user: str = "1",
    target_type: str = "channels",
    channels: str | None = None,
    bots: str | None = None,
    search_queries: str | None = None,
) -> str:
    """Save current ad creation form as a draft.
    Drafts are auto-restored when visiting the new-ad page."""
    c = get_client()
    params = {
        "owner_id": _owner(),
        "title": title,
        "text": text,
        "promote_url": promote_url,
        "cpm": cpm,
        "budget": budget,
        "daily_budget": daily_budget,
        "active": active,
        "views_per_user": views_per_user,
        "target_type": target_type,
    }
    if channels:
        params["channels"] = channels
    if bots:
        params["bots"] = bots
    if search_queries:
        params["search_queries"] = search_queries
    result = c.call("saveAdDraft", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def clear_ad_draft() -> str:
    """Clear the saved ad draft."""
    c = get_client()
    result = c.call("clearAdDraft", {"owner_id": _owner()})
    return json.dumps(result, ensure_ascii=False)


# ──────────────────────────────────────────────
#  DISPLAY SETTINGS
# ──────────────────────────────────────────────


@mcp.tool()
def save_ads_columns(columns: str) -> str:
    """Save which columns are visible in the ads list table.
    columns: semicolon-separated column names (e.g. "title;status;views;cpm;spent")."""
    c = get_client()
    result = c.call("saveAdsColumns", {"columns": columns})
    return json.dumps(result, ensure_ascii=False)


# ──────────────────────────────────────────────
#  SEARCH / DISCOVERY
# ──────────────────────────────────────────────


@mcp.tool()
def search_channel(query: str) -> str:
    """Search for a Telegram channel by username or title.
    Used for targeting — returns channel ID, title, photo, subscriber count."""
    c = get_client()
    result = c.call("searchChannel", {
        "owner_id": _owner(),
        "query": query,
        "field": "channels",
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def search_bot(query: str) -> str:
    """Search for a Telegram bot by username.
    Used for promote_url — returns bot ID, title, photo, username."""
    c = get_client()
    result = c.call("searchBot", {
        "query": query,
        "field": "promote_url",
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def search_target_query(query: str) -> str:
    """Search for a keyword/query for search-based targeting.
    Returns query ID, title, and sample search results."""
    c = get_client()
    result = c.call("searchTargetQuery", {
        "query": query,
        "field": "search_queries",
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def search_location(
    query: str = "",
    country: str | None = None,
    region: str | None = None,
) -> str:
    """Search for a geographic location for geo-targeting.
    Can search by text query, or drill down by country/region."""
    c = get_client()
    params = {"owner_id": _owner()}
    if query:
        params["query"] = query
    if country:
        params["country"] = country
    if region:
        params["region"] = region
    result = c.call("searchLocation", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_similar_channels(channels: str) -> str:
    """Get channels similar to the given ones (for targeting expansion).
    channels: semicolon-separated channel IDs."""
    c = get_client()
    result = c.call("getSimilarChannels", {
        "channels": channels,
        "for": "channels",
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_similar_bots(bots: str) -> str:
    """Get bots similar to the given ones (for targeting expansion).
    bots: semicolon-separated bot IDs."""
    c = get_client()
    result = c.call("getSimilarBots", {"bots": bots})
    return json.dumps(result, ensure_ascii=False)


# ──────────────────────────────────────────────
#  AUDIENCES (custom user lists)
# ──────────────────────────────────────────────


@mcp.tool()
def create_audience(title: str, file_path: str) -> str:
    """Create a custom audience by uploading a user list file.
    The file should contain one user ID per line."""
    c = get_client()
    result = c.upload("createAudience", file_path, {
        "owner_id": _owner(),
        "title": title,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def edit_audience_title(audience_id: str, title: str) -> str:
    """Rename a custom audience."""
    c = get_client()
    result = c.call("editAudienceTitle", {
        "owner_id": _owner(),
        "audience_id": audience_id,
        "title": title,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def delete_audience(audience_id: str, confirm_hash: str | None = None) -> str:
    """Delete a custom audience. Two-step: call without confirm_hash first,
    then call with the returned confirm_hash."""
    c = get_client()
    params = {
        "owner_id": _owner(),
        "audience_id": audience_id,
    }
    if confirm_hash:
        params["confirm_hash"] = confirm_hash
    result = c.call("deleteAudience", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def clone_audience(audience_id: str, confirm_hash: str | None = None) -> str:
    """Create a new ad draft from an existing audience."""
    c = get_client()
    params = {
        "owner_id": _owner(),
        "audience_id": audience_id,
    }
    if confirm_hash:
        params["confirm_hash"] = confirm_hash
    result = c.call("createDraftFromAudience", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def update_audiences_state() -> str:
    """Refresh the processing state of all audiences.
    Call this to check if audience uploads have finished processing."""
    c = get_client()
    result = c.call("updateAudiencesState", {"owner_id": _owner()})
    return json.dumps(result, ensure_ascii=False)


# ──────────────────────────────────────────────
#  EVENTS (conversion tracking)
# ──────────────────────────────────────────────


@mcp.tool()
def create_event(title: str, event_type: str = "custom") -> str:
    """Create a conversion tracking event.

    Args:
        title: Event name (e.g. "Purchase", "Sign Up").
        event_type: Event type — "custom", "purchase", "lead", etc.
    """
    c = get_client()
    result = c.call("createEvent", {
        "owner_id": _owner(),
        "title": title,
        "type": event_type,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def edit_event_title(event_id: str, title: str) -> str:
    """Rename a conversion event."""
    c = get_client()
    result = c.call("editEventTitle", {
        "owner_id": _owner(),
        "event_id": event_id,
        "title": title,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def delete_event(event_id: str, confirm_hash: str | None = None) -> str:
    """Delete a conversion event. Two-step confirmation like delete_ad."""
    c = get_client()
    params = {
        "owner_id": _owner(),
        "event_id": event_id,
    }
    if confirm_hash:
        params["confirm_hash"] = confirm_hash
    result = c.call("deleteEvent", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def update_events_state() -> str:
    """Refresh the state of all conversion events."""
    c = get_client()
    result = c.call("updateEventsState", {"owner_id": _owner()})
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def create_pixel() -> str:
    """Create a new tracking pixel for conversion tracking.
    Returns a redirect URL or layer URL for pixel setup."""
    c = get_client()
    result = c.call("createPixel", {"owner_id": _owner()})
    return json.dumps(result, ensure_ascii=False)


# ──────────────────────────────────────────────
#  FUNDS & TRANSFERS
# ──────────────────────────────────────────────


@mcp.tool()
def send_add_funds_request(
    amount: str,
    additional_comment: str = "",
) -> str:
    """Request to add funds to the account.

    Args:
        amount: Amount in TON to add.
        additional_comment: Optional comment for the funding request.
    """
    c = get_client()
    params = {
        "owner_id": _owner(),
        "amount": amount,
    }
    if additional_comment:
        params["additional_comment"] = additional_comment
    result = c.call("sendAddFundsRequest", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def transfer_funds(account_id: str, amount: str) -> str:
    """Transfer funds to another ads account.

    Args:
        account_id: Target account ID.
        amount: Amount in TON to transfer.
    """
    c = get_client()
    result = c.call("transferFunds", {
        "owner_id": _owner(),
        "account_id": account_id,
        "amount": amount,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def withdraw_funds(account_id: str, amount: str) -> str:
    """Withdraw funds from another ads account back to yours.

    Args:
        account_id: Source account ID.
        amount: Amount in TON to withdraw.
    """
    c = get_client()
    result = c.call("transferWithdrawFunds", {
        "owner_id": _owner(),
        "account_id": account_id,
        "amount": amount,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def search_account_for_transfer(query: str) -> str:
    """Search for an ads account to transfer funds to.
    Query by account ID or owner name."""
    c = get_client()
    result = c.call("searchAccountForTransfer", {
        "owner_id": _owner(),
        "query": query,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_accounts_for_transfer() -> str:
    """Get list of linked accounts available for fund transfers."""
    c = get_client()
    result = c.call("getAccountsForTransfer", {"owner_id": _owner()})
    return json.dumps(result, ensure_ascii=False)


# ──────────────────────────────────────────────
#  ACCOUNT SETTINGS
# ──────────────────────────────────────────────


@mcp.tool()
def save_account_info(**fields: str) -> str:
    """Save account information fields.
    Pass any account fields as keyword arguments (e.g. company_name, email, etc.)."""
    c = get_client()
    params = {"owner_id": _owner()}
    params.update(fields)
    result = c.call("saveAccountInfo", params)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def save_api_settings(ip_list: str) -> str:
    """Save API access settings — set the IP whitelist for API access.

    Args:
        ip_list: Newline-separated list of allowed IP addresses.
    """
    c = get_client()
    result = c.call("saveApiSettings", {
        "owner_id": _owner(),
        "ip_list": ip_list,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_ad_stats(ad_id: str, period: str = "5min") -> str:
    """Get time-bucketed stats for an ad from the stats page.

    Returns two charts:
    - counts: Views, Clicks, 'Started bot' actions per bucket
    - budget: Spend data per bucket

    Also returns summary with totals and period info.

    Two modes:
    - period="5min": 5-minute buckets over last 24h. Use for attribution
      (match 'Started bot' timestamps with user registrations).
    - period="day": Daily buckets over full ad lifetime. Use for trend
      analysis (views/clicks/starts per day).

    summary.interval_seconds: 300 for 5min, 86400 for day.

    Args:
        ad_id: The ad ID to get stats for.
        period: "5min" (default) for 5-min buckets, "day" for daily buckets.
    """
    c = get_client()
    result = c.get_ad_stats(ad_id, period=period)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def revoke_stats_url(ad_id: str) -> str:
    """Revoke and regenerate the shared stats URL for an ad."""
    c = get_client()
    result = c.call("revokeStatsUrl", {
        "owner_id": _owner(),
        "ad_id": ad_id,
    })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def revoke_token() -> str:
    """Revoke and regenerate the API access token."""
    c = get_client()
    result = c.call("revokeToken", {"owner_id": _owner()})
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def log_out() -> str:
    """Log out of the Telegram Ads platform."""
    c = get_client()
    result = c.call("logOut", {})
    return json.dumps(result, ensure_ascii=False)


# ──────────────────────────────────────────────
#  USER-LEVEL TARGETING — EUR cabinets only
# ──────────────────────────────────────────────
#
# EUR cabinets (e.g. Click Reklam reseller) expose a fourth target_type
# alongside channels/bots/search: "users". This targets individual Telegram
# users by demographic+interest signal (country, language, interest topic,
# subscribed channels, device) rather than the channel they read.
#
# TON cabinets do NOT support this — the form on TON only renders three
# target_type radios. All tools below probe the cabinet and refuse gracefully
# when run against a TON cabinet.


@mcp.tool()
def check_cabinet_type() -> str:
    """Detect whether the active cabinet is EUR (reseller-billed) or TON
    (direct-billed). EUR cabinets unlock user-level targeting via
    `create_user_ad` and `get_user_targeting_reference`; TON cabinets do not.

    Returns: {"ok": true, "cabinet": "eur"|"ton", "supports_user_targeting": bool}
    """
    c = get_client()
    try:
        is_eur = c.is_eur_cabinet()
    except AuthError as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
    return json.dumps({
        "ok": True,
        "cabinet": "eur" if is_eur else "ton",
        "supports_user_targeting": is_eur,
    }, ensure_ascii=False)


@mcp.tool()
def get_user_targeting_reference() -> str:
    """Reference lists for user-level targeting (EUR cabinet only).

    Returns three lists you'll pass to `create_user_ad`:
      - countries: [{"val": "US", "name": "United States"}, ...] — ISO codes
      - languages: [{"val": "en", "name": "English"}, ...] — TG interface lang
      - topics:    [{"val": 13, "name": "Education"}, ...] — numeric topic IDs

    Use the `val` field as the semicolon-separated ID in `create_user_ad`'s
    `countries` / `user_langs` / `user_topics` params.

    Cached per session — call as often as you want.

    EUR-cabinet only. On TON cabinet returns `{"ok": false, "error": ...}`.
    """
    c = get_client()
    try:
        if not c.is_eur_cabinet():
            return json.dumps({
                "ok": False,
                "error": "User targeting is EUR-cabinet only. Current cabinet is TON — switch with select_account first.",
            }, ensure_ascii=False)
        ref = c.get_user_targeting_reference()
    except AuthError as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
    return json.dumps({
        "ok": True,
        "countries": ref.get("countryItems", []),
        "languages": ref.get("langItems", []),
        "topics": ref.get("userTopicItems", []),
    }, ensure_ascii=False)


@mcp.tool()
def get_channel_targeting_reference() -> str:
    """Reference lists for CHANNEL-level targeting on Channels target_type
    (EUR cabinet only).

    EUR cabinets expose extra filters on the Channels target tab that TON
    cabinets do not have: filter channels by language, by topic category,
    plus optional conversion-event attribution. This tool returns the
    numeric/string IDs you'll pass to `create_ad` when `target_type="channels"`.

    Returns:
      - topics: [{"val": 19, "name": "Foreign Language Learning"}, ...] —
                numeric channel-topic IDs. Pass as semicolon-separated string
                to `create_ad(topics=...)` or `create_ad(exclude_topics=...)`.
      - languages: [{"val": "en", "name": "English"}, ...] — channel content
                   language codes. Pass to `create_ad(langs=...)`.
      - conversion_events: [{"val": "...", "name": "Page views"}, ...] —
                           conversion event IDs. Pass to `create_ad(conversion_event=...)`.

    NOTE: `topics` here are CHANNEL categories (the channel's registered topic
    in TG's directory). They share the same 41-entry taxonomy as user `topics`
    in get_user_targeting_reference(), but the wire field name is different
    (`topics` vs `user_topics`) — do not mix them up.

    Cached per session. EUR-cabinet only — on TON returns `{"ok": false, ...}`.
    """
    c = get_client()
    try:
        if not c.is_eur_cabinet():
            return json.dumps({
                "ok": False,
                "error": "Channel-level topic/lang/conversion targeting is EUR-cabinet only. Current cabinet is TON — switch with select_account first.",
            }, ensure_ascii=False)
        ref = c.get_channel_targeting_reference()
    except AuthError as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
    return json.dumps({
        "ok": True,
        "topics": ref.get("topicItems", []),
        "languages": ref.get("langItems", []),
        "conversion_events": ref.get("convEventItems", []),
    }, ensure_ascii=False)


@mcp.tool()
def create_user_ad(
    title: str,
    promote_url: str,
    cpm: str,
    text: str = "",
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
) -> str:
    """Create an ad with user-level targeting. **EUR cabinet only.**

    User-level targeting reaches Telegram users matching demographic/interest
    criteria — independent of which channel the ad shows up in. TON cabinets
    do not support this; this tool refuses on TON.

    Args:
        title: Internal ad title (not shown to users).
        promote_url: URL to promote (t.me/bot or t.me/channel).
        cpm: Cost per 1000 views in EUR (e.g. "2.00"). EUR auction floor is €1.
        text: Ad text shown to users (max 160 chars).

        countries: Semicolon-separated ISO country codes (e.g. "US;GB;DE").
                   Use `get_user_targeting_reference` for the full list.
        locations: Semicolon-separated location IDs from `search_location`
                   (cities, regions, districts — narrower than country).
        user_langs: Semicolon-separated language codes (e.g. "en;ru;ar").
                    Telegram interface language of the user.
        user_topics: Semicolon-separated numeric topic IDs (e.g. "13;19").
                     Categories the user is interested in.
        user_channels: Semicolon-separated channel IDs (max 100) the user must
                       be subscribed to. From `search_channel`.
        intersect_topics: True = user must match ALL `user_topics` (AND).
                          False (default) = match ANY topic (OR).

        exclude_user_topics: Topic IDs whose subscribers will NOT see this ad.
        exclude_user_channels: Channel IDs whose subscribers will NOT see this.
        exclude_politic: Don't render in Politics & Incidents channels.
        exclude_crypto:  Don't render in Cryptocurrencies channels.
        only_politic: Render ONLY in Politics & Incidents channels.
        only_crypto:  Render ONLY in Cryptocurrencies channels.
        device: Device type filter (e.g. "ios", "android", "desktop").

        budget: Total budget in EUR. "0" = no budget (ad won't go to review).
        daily_budget: Daily budget in EUR. "0" = unlimited.
        active: "active" or "on_hold" (default).
        views_per_user: Max views per unique user per day ("1"-"4").
        picture: Show bot/channel avatar in the ad.
        media: Media hash for uploaded photo/video.
        website_name: Display name for website promote URLs.
    """
    c = get_client()
    try:
        if not c.is_eur_cabinet():
            return json.dumps({
                "ok": False,
                "error": "create_user_ad is EUR-cabinet only. Current cabinet is TON — switch with select_account first.",
            }, ensure_ascii=False)
    except AuthError as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    status_map = {"active": "1", "on_hold": "0", "on hold": "0"}
    active_value = status_map.get(active.lower(), active) if active else "0"

    params = {
        "owner_id": _owner(),
        "title": title,
        "text": text,
        "promote_url": promote_url,
        "cpm": cpm,
        "budget": budget,
        "daily_budget": daily_budget,
        "active": active_value,
        "views_per_user": views_per_user,
        "target_type": "users",
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
    }
    if intersect_topics:
        params["intersect_topics"] = "1"
    if exclude_politic:
        params["exclude_politic"] = "1"
    if exclude_crypto:
        params["exclude_crypto"] = "1"
    if only_politic:
        params["only_politic"] = "1"
    if only_crypto:
        params["only_crypto"] = "1"
    if picture:
        params["picture"] = "1"

    result = c.call("createAd", params)
    return json.dumps(result, ensure_ascii=False)


# ──────────────────────────────────────────────
#  ENTRYPOINT
# ──────────────────────────────────────────────


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
