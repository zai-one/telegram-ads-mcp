"""Agent-facing tool titles and descriptions (L0 token budget).

Template (ZAI.ONE MCP standard):
  <Verb + object>. Use when <situation>; for <neighbour task> use `<other_tool>`.
  [Cost/Writes rule.] Returns <key fields>.
Each description stays <= 300 chars, first sentence <= 120 chars.
Developer notes stay in the function docstrings; these strings are what the host sees.
"""

from __future__ import annotations

from typing import Any

TOOLS: dict[str, tuple[str, str]] = {
    "check_session": (
        "Check session",
        "Ping the ads.telegram.org session. Use first in every chat; on ok=false code=auth offer INSTALL.md "
        "DevTools steps, then `reload_session`. Returns owner_id, cabinet, currency, balance, write_gate.",
    ),
    "check_update": (
        "Check for update",
        "Check GitHub for a newer telegram-ads-mcp release. Use when the user asks about updates. "
        "Suggest only, never install. Returns current, latest, command, run_in.",
    ),
    "reload_session": (
        "Reload session",
        "Re-read .env cookies and rebuild the HTTP session. Use after the user updated .env on disk; "
        "never pass cookie values as arguments. Returns ok and the new session card.",
    ),
    "list_accounts": (
        "List cabinets",
        "List ad cabinets for this Telegram login. Use to find owner_id before `select_account`; "
        "works on any cabinet (TON, EUR, Stars). Returns accounts.",
    ),
    "select_account": (
        "Select cabinet",
        "Switch the active ad cabinet by owner_id from `list_accounts`. Use when the wrong or a Stars "
        "cabinet is active. Writes: confirm=true under gate strict. Then call `get_account`.",
    ),
    "get_account": (
        "Get cabinet",
        "Read the current cabinet card. Use before any write to check currency and gate; for the ad list "
        "use `get_ads`. Returns owner_id, cabinet, currency (GRAM/EUR/XTR), money, balance, write_gate.",
    ),
    "get_ads": (
        "List ads",
        "List ads, 100 per page, status=any|active|on_hold. Use for account overviews; for one ad use "
        "`get_ad`. Paginate with offset_id=next_offset_id. Returns ads with status, spent, cpm, budget.",
    ),
    "get_ad": (
        "Get ad",
        "Fetch one ad by id with full fields. Use for diagnosis; for metrics use `get_ad_stats`. "
        "Falls back to HTML/list when getAd returns 400. Returns the ad card.",
    ),
    "create_ad": (
        "Create ad (full)",
        "Create an ad on_hold with the full targeting field set. Prefer `launch_ad` for the normal flow. "
        "Writes: confirm=true if budget>0 or active (gate). IDs semicolon-separated; no langs with channels.",
    ),
    "edit_ad": (
        "Edit ad",
        "Edit only the fields passed: copy, CPM, pause/activate, budget_action+budget_amount or budget_target. "
        "budget_target is read back. Targeting is immutable, use `clone_ad`. Activate/budget need confirm=true.",
    ),
    "delete_ad": (
        "Delete ad",
        "Delete an ad (destructive). Two steps: call without confirm_hash, show the user, then call with "
        "the returned hash. confirm=true is the gate flag, not the hash. To pause use `edit_ad`.",
    ),
    "clone_ad": (
        "Clone ad",
        "Duplicate an ad into a new on_hold draft with the same targeting. Use to change immutable "
        "targeting. Two-step confirm_hash; confirm=true for the gate. Returns the new ad id.",
    ),
    "check_ad_post": (
        "Validate ad post",
        "Validate promote_url and text before create or launch. Use before `launch_ad`/`create_ad`. "
        "Read-only. Returns ok or the platform error text.",
    ),
    "send_target_to_review": (
        "Send to review",
        "Submit or resubmit an ad's targeting for moderation. Use after edits; `launch_ad` already does "
        "it. Needs non-zero budget. Spend-class: confirm=true unless gate=open.",
    ),
    "launch_ad": (
        "Launch ad (on_hold)",
        "Create on_hold, add budget (default 1 Gram), send to review; never activates. Use for new ads; "
        "full targeting via `create_ad`. Spends: confirm=true unless gate=open. Returns per-step results.",
    ),
    "preview_ad": (
        "Preview ad",
        "Render a sponsored-message preview PNG and save it under ./previews (gitignored). Use to show the "
        "user the copy before launch or during diagnosis. Returns an image.",
    ),
    "upload_media": (
        "Upload media",
        "Upload a photo (16:9, <5 MB) or video (MP4 3-60s, <20 MB) by file_path or media_base64. Use before "
        "`create_ad`/`edit_ad` media=. Returns the media hash.",
    ),
    "get_ad_stats": (
        "Ad stats",
        "Get views/clicks/CTR/CPC/CPM/spend for one ad. period=5min: last 24h; day: lifetime. summary.spend "
        "is already scaled (Gram); never divide. For many ads use `get_ads`. detail=full adds charts.",
    ),
    "search_targets": (
        "Search targets",
        "Resolve channels, bots, search queries, locations or similar_* to IDs. Use before launch/create; "
        "never guess IDs. purpose=target (placement) or promote (URL lookup). Returns the platform match list.",
    ),
    "get_targeting_reference": (
        "Targeting reference",
        "List countries, languages, topics and channel taxonomies with IDs. Use for user-geo and topic "
        "targeting; for channels/bots use `search_targets`. Empty list means not embedded.",
    ),
    "manage_audience": (
        "Manage audiences",
        "Custom audiences: action=list|create|rename|delete|clone. list is read-only; delete/clone use "
        "two-step confirm_hash plus gate confirm. code=access_denied means skip, do not retry.",
    ),
    "manage_event": (
        "Manage events",
        "Conversion events and pixels: action=list|create|rename|delete|create_pixel. list is read-only; "
        "delete is destructive with two-step confirm_hash. code=access_denied means skip.",
    ),
    "manage_funds": (
        "Manage funds",
        "Funds: action=list|search (lookup), add (top-up request), transfer|withdraw (money moves now, no "
        "hash). Destructive: confirm=true and explicit user yes. Never guess account_id.",
    ),
    "revoke_token": (
        "Revoke API token",
        "Revoke and regenerate the cabinet API (IP-whitelist) token, not the ads cookies. Destructive; "
        "use only when the user asks. Never use it to fix auth.",
    ),
    "save_api_settings": (
        "Save API IP whitelist",
        "Set the newline-separated IP whitelist for the cabinet API token. Destructive; use only when the "
        "user asks. confirm=true unless gate=open.",
    ),
    "log_out": (
        "Log out",
        "Log out of ads.telegram.org; the user then needs fresh cookies in .env. Destructive; use only "
        "when explicitly asked. Never use it to fix auth.",
    ),
}


def meta(name: str) -> dict[str, Any]:
    """Keyword arguments for ``@mcp.tool``: name, title and description."""
    title, description = TOOLS[name]
    return {"title": title, "description": description}
