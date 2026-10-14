"""TG_ADS_TOOL_LOADING=lazy: small start surface, runtime toolset enabling, list_changed."""

from __future__ import annotations

import json

import anyio
import mcp.types
import pytest
from mcp.client import Client
from mcp.server import MCPServer

import telegram_ads_mcp.server as server_mod
from telegram_ads_mcp import lazy_loading
from telegram_ads_mcp.lazy_loading import ENABLE_TOOL, LAZY_CORE, TOOLSETS, estimate_tokens

ALL = {tool.name for tool in server_mod.mcp._tool_manager.list_tools()}
CORE = set(TOOLSETS["meta"]["tools"]) | set(LAZY_CORE) | {ENABLE_TOOL}
LAZY_BUDGET_TOKENS = 2_500


def build(mode: str) -> MCPServer:
    """A fresh server with the module's registered tools, so env stays per test."""
    fresh = MCPServer(name="telegram-ads-mcp", instructions=server_mod.mcp.instructions)
    for tool in server_mod.mcp._tool_manager.list_tools():
        fresh._tool_manager._tools[tool.name] = tool
    lazy_loading.install(fresh, {"TG_ADS_TOOL_LOADING": mode})
    return fresh


async def names(client: Client) -> set[str]:
    return {tool.name for tool in (await client.list_tools()).tools}


async def startup_tokens(client: Client) -> int:
    tools = (await client.list_tools()).tools
    listed = [tool.model_dump(mode="json", exclude_none=True, by_alias=True) for tool in tools]
    return estimate_tokens(listed) + estimate_tokens(client.instructions or "")


class Notices:
    def __init__(self) -> None:
        self.seen: list[str] = []

    async def __call__(self, message) -> None:
        root = getattr(message, "root", message)
        if isinstance(root, mcp.types.ToolListChangedNotification):
            self.seen.append("tools/list_changed")


def data(result) -> dict:
    payload = result.structured_content
    if payload is None:
        payload = json.loads(result.content[0].text)
    return payload.get("result", payload)


def test_toolsets_cover_every_tool_once() -> None:
    grouped = [name for spec in TOOLSETS.values() for name in spec["tools"]]
    assert len(grouped) == len(set(grouped))
    assert set(grouped) == ALL


async def test_eager_is_default_and_unchanged() -> None:
    assert ENABLE_TOOL not in ALL
    assert server_mod.LAZY_LISTED == ALL
    async with Client(build("eager")) as client:
        assert await names(client) == ALL
        assert "Lazy tools" not in (client.instructions or "")


@pytest.mark.parametrize("mode", ["legacy", "auto"])
async def test_lazy_start_surface(mode: str) -> None:
    async with Client(build("lazy"), mode=mode) as client:
        assert client.server_capabilities.tools.list_changed is True
        assert await names(client) == CORE
        assert f"{ENABLE_TOOL}()" in client.instructions and len(client.instructions) <= 1300
        rows = data(await client.call_tool(ENABLE_TOOL, {}))["toolsets"]
    assert {row["toolset"] for row in rows} == set(TOOLSETS) - {"meta"}
    assert all(row["description"] and row["token_cost"] > 0 for row in rows)


async def test_enable_registers_tools_and_notifies_legacy() -> None:
    notices = Notices()
    async with Client(build("lazy"), mode="legacy", message_handler=notices) as client:
        result = data(await client.call_tool(ENABLE_TOOL, {"toolsets": ["targeting"]}))
        listed = await names(client)
    assert set(result["added_tools"]) == {"search_targets", "get_targeting_reference"}
    assert listed == CORE | {"search_targets", "get_targeting_reference"}
    assert notices.seen == ["tools/list_changed"]
    assert "reconnect" in result["hint"]


async def test_enable_publishes_list_changed_on_listen_stream() -> None:
    async with Client(build("lazy")) as client:
        async with client.listen(tools_list_changed=True) as stream:
            await client.call_tool(ENABLE_TOOL, {"toolsets": ["ads_read"]})
            with anyio.fail_after(5):
                event = await stream.__anext__()
        assert "ToolsListChanged" in type(event).__name__
        assert {"get_ad", "preview_ad"} <= await names(client)


async def test_enable_is_idempotent() -> None:
    notices = Notices()
    async with Client(build("lazy"), mode="legacy", message_handler=notices) as client:
        await client.call_tool(ENABLE_TOOL, {"toolsets": ["ads_write"]})
        again = data(await client.call_tool(ENABLE_TOOL, {"toolsets": ["ads_write"]}))
        await client.call_tool(ENABLE_TOOL, {"toolsets": ["all"]})
        twice = data(await client.call_tool(ENABLE_TOOL, {"toolsets": ["all"]}))
        listed = await names(client)
    assert again["added_tools"] == [] and again["already_enabled"] is True
    assert twice["added_tools"] == []
    assert listed == ALL | {ENABLE_TOOL}
    assert notices.seen == ["tools/list_changed", "tools/list_changed"]


async def test_enabled_writes_keep_the_write_gate(monkeypatch) -> None:
    monkeypatch.setenv("TG_ADS_WRITE_GATE", "confirm")
    async with Client(build("lazy"), mode="legacy") as client:
        await client.call_tool(ENABLE_TOOL, {"toolsets": ["ads_write"]})
        blocked = data(await client.call_tool("delete_ad", {"ad_id": "1"}))
        unknown = data(await client.call_tool(ENABLE_TOOL, {"toolsets": ["nope"]}))
    assert blocked["code"] == "write_gated" and blocked["sent"] is False
    assert unknown["error"] == "unknown_toolset"


def test_invalid_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        build("sometimes")


async def test_lazy_startup_budget(capsys) -> None:
    costs = {}
    for mode in ("eager", "lazy"):
        async with Client(build(mode)) as client:
            costs[mode] = await startup_tokens(client)
    assert costs["lazy"] <= LAZY_BUDGET_TOKENS
    assert costs["lazy"] < costs["eager"]
    with capsys.disabled():
        print(f"\nstartup tokens {json.dumps(costs)}")
