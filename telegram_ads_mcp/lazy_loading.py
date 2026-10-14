"""Optional lazy tool loading: start with a small core, enable toolsets at runtime.

TG_ADS_TOOL_LOADING=eager (default) keeps every tool in tools/list. With
TG_ADS_TOOL_LOADING=lazy only the core (session/cabinet tools, get_ads, get_ad_stats
and tg_ads_enable_toolsets) is listed at start; enabling a toolset registers its tools
and announces the change: notifications/tools/list_changed on handshake-era sessions and
a ToolsListChanged event on subscriptions/listen (2026-07-28+). Enabled tools keep
their TG_ADS_WRITE_GATE confirm/confirm_hash gates; Stars stays opt-in (TG_ADS_STARS).
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations

ENV = "TG_ADS"
MODES = ("eager", "lazy")
ENABLE_TOOL = "tg_ads_enable_toolsets"

TOOLSETS: dict[str, dict[str, Any]] = {
    "meta": {
        "description": "Session, update check, cabinets and account (always listed).",
        "tools": ("check_session", "check_update", "reload_session", "list_accounts", "select_account",
                  "get_account"),
    },
    "ads_read": {
        "description": "Read ads: list, one ad, post check, card preview, statistics.",
        "tools": ("get_ads", "get_ad", "check_ad_post", "preview_ad", "get_ad_stats"),
    },
    "targeting": {
        "description": "Find channels/bots/audiences and the targeting reference (countries, topics...).",
        "tools": ("search_targets", "get_targeting_reference"),
    },
    "ads_write": {
        "description": "Create, edit, clone, review, launch (spends), upload media, delete ads; gated writes.",
        "tools": ("create_ad", "edit_ad", "clone_ad", "send_target_to_review", "launch_ad", "upload_media",
                  "delete_ad"),
    },
    "audiences_events": {
        "description": "Manage custom audiences and conversion events (gated writes).",
        "tools": ("manage_audience", "manage_event"),
    },
    "account_admin": {
        "description": "Funds, API token and settings, log out (destructive; confirm=true).",
        "tools": ("manage_funds", "revoke_token", "save_api_settings", "log_out"),
    },
}  # fmt: skip
LAZY_CORE = ("get_ads", "get_ad_stats")
HINT = (
    "If the new tools do not appear, this client ignores tools/list_changed: re-list tools or reconnect "
    f"the MCP server, or set {ENV}_TOOL_LOADING=eager."
)
ROUTER_LINE = f"Lazy tools: {ENABLE_TOOL}() lists toolsets; {ENABLE_TOOL}(toolsets=[...]) adds them."


def loading_mode(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    value = (env.get(f"{ENV}_TOOL_LOADING") or "eager").strip().lower()
    if value not in MODES:
        raise ValueError(f"{ENV}_TOOL_LOADING must be eager or lazy")
    return value


def estimate_tokens(payload: Any) -> int:
    """Rough token estimate (~4 characters per token) of a JSON-serialised MCP object."""
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return (len(text) + 3) // 4


def tool_tokens(tool: Any) -> int:
    listed = {
        "name": tool.name,
        "title": tool.title,
        "description": tool.description,
        "inputSchema": tool.parameters,
        "outputSchema": tool.output_schema,
        "annotations": tool.annotations.model_dump(mode="json", exclude_none=True, by_alias=True)
        if tool.annotations
        else None,
    }
    return estimate_tokens({key: value for key, value in listed.items() if value is not None})


def install(server: Any, environ: Mapping[str, str] | None = None) -> set[str]:
    """Defer non-core tools in lazy mode. Returns the names listed at start."""
    manager = server._tool_manager  # SDK has no public accessor for the registered Tool objects
    names = {tool.name for tool in manager.list_tools()}
    if loading_mode(environ) != "lazy":
        return names
    grouped = {name for spec in TOOLSETS.values() for name in spec["tools"]}
    core = (set(TOOLSETS["meta"]["tools"]) | set(LAZY_CORE) | (names - grouped)) & names
    deferred = {name: manager._tools.pop(name) for name in sorted(names - core)}
    groups = {
        toolset: [name for name in spec["tools"] if name in deferred]
        for toolset, spec in TOOLSETS.items()
        if any(name in deferred for name in spec["tools"])
    }
    enabled: set[str] = set()

    def catalog() -> list[dict[str, Any]]:
        return [
            {
                "toolset": toolset,
                "description": TOOLSETS[toolset]["description"],
                "tools": members,
                "token_cost": sum(tool_tokens(deferred[name]) for name in members),
                "enabled": all(name in enabled for name in members),
            }
            for toolset, members in groups.items()
        ]

    async def tg_ads_enable_toolsets(toolsets: list[str] | None = None, ctx: Context | None = None) -> dict:
        """List toolsets that are not loaded yet (description, tools, token cost), or enable them by name ('all' enables every one). Enabled tools appear via tools/list_changed."""  # noqa: E501
        requested = [item.strip() for item in (toolsets or []) if item and item.strip()]
        if not requested:
            return {"mode": "lazy", "toolsets": catalog(), "hint": f"Call {ENABLE_TOOL}(toolsets=[...])."}
        if "all" in requested:
            requested = list(groups)
        unknown = sorted(set(requested) - set(groups))
        if unknown:
            return {"error": "unknown_toolset", "unknown": unknown, "available": sorted(groups)}
        added: list[str] = []
        for toolset in requested:
            for name in groups[toolset]:
                if name not in enabled:
                    manager._tools[name] = deferred[name]
                    enabled.add(name)
                    added.append(name)
        if added and ctx is not None:
            await _announce(ctx)
        return {"mode": "lazy", "enabled": requested, "added_tools": added, "already_enabled": not added,
                "hint": HINT}  # fmt: skip

    server.add_tool(
        tg_ads_enable_toolsets,
        name=ENABLE_TOOL,
        title="Telegram Ads: enable toolsets",
        annotations=ToolAnnotations(
            read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
        ),
    )
    low = server._lowlevel_server
    low.instructions = f"{low.instructions}\n{ROUTER_LINE}" if low.instructions else ROUTER_LINE
    original = low.create_initialization_options

    def initialization_options(notification_options: Any = None, *args: Any, **kwargs: Any) -> Any:
        # Declare tools.listChanged for handshake-era clients (modern ones derive it from listen).
        options = notification_options or NotificationOptions(tools_changed=True)
        return original(options, *args, **kwargs)

    low.create_initialization_options = initialization_options
    return core | {ENABLE_TOOL}


async def _announce(ctx: Context) -> None:
    try:
        await ctx.notify_tools_changed()  # subscriptions/listen streams (2026-07-28+)
    except Exception:  # noqa: BLE001 - no subscription bus: the legacy path below still runs
        pass
    try:
        await ctx.request_context.session.send_tool_list_changed()  # handshake-era sessions
    except Exception:  # noqa: BLE001 - modern per-request path has no legacy session stream
        pass
