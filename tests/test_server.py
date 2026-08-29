import inspect
from unittest.mock import AsyncMock, patch

import pytest

import telegram_ads_mcp.server as server_mod
from telegram_ads_mcp.parse import filter_ads_by_status


def _tools():
    return server_mod.mcp._tool_manager.list_tools()


def test_ci_import_entrypoint() -> None:
    """Same imports GitHub Actions runs after pytest. Catch rename drift locally."""
    from telegram_ads_mcp.server import mcp

    assert mcp.name == "telegram-ads-mcp"
    import tg_ads_mcp

    assert tg_ads_mcp.__version__ == __import__("telegram_ads_mcp").__version__


def test_tool_count_collapsed() -> None:
    names = sorted(t.name for t in _tools())
    assert "update_cookies" not in names
    assert "edit_ad_title" not in names
    assert "save_ads_columns" not in names
    assert "create_user_ad" not in names
    assert "reload_session" in names
    assert "launch_ad" in names
    assert "preview_ad" in names
    assert "get_account" in names
    assert "upload_media" in names
    assert 12 <= len(names) <= 28


def test_reload_session_has_no_cookie_args() -> None:
    assert list(inspect.signature(server_mod.reload_session).parameters) == []
    assert list(inspect.signature(server_mod.check_session).parameters) == []


def test_check_session_annotations_readonly() -> None:
    tools = {t.name: t for t in _tools()}
    anns = tools["check_session"].annotations
    assert anns is not None
    assert anns.read_only_hint is True
    dest = tools["delete_ad"].annotations
    assert dest is not None
    assert dest.destructive_hint is True


def test_get_ads_uses_shipped_status_filter() -> None:
    # server.get_ads must call filter_ads_by_status (imported), not a private copy.
    assert server_mod.filter_ads_by_status is filter_ads_by_status
    items = [{"ad_id": 1, "status": "Active"}, {"ad_id": 2, "status": "Stopped"}]
    assert [i["ad_id"] for i in filter_ads_by_status(items, "active")] == [1]
    src = inspect.getsource(server_mod.get_ads)
    assert "filter_ads_by_status" in src


def _ton_gram_client() -> AsyncMock:
    fake = AsyncMock()
    fake.owner_id = "own1"
    cabinet = {
        "cabinet": "ton",
        "currency": "GRAM",
        "supports_user_targeting": True,
        "supported": True,
    }
    fake.detect_cabinet.return_value = cabinet
    fake.require_supported_cabinet.return_value = cabinet
    fake.call.return_value = {"ok": True, "ad_id": "99"}
    return fake


@pytest.mark.asyncio
async def test_create_ad_users_allowed_on_ton_gram() -> None:
    """Live Gram cabinets use trg_type=user. create_ad must not EUR-only refuse."""
    src = inspect.getsource(server_mod.create_ad)
    assert "EUR-cabinet only" not in src
    fake = _ton_gram_client()
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        out = await server_mod.create_ad(
            title="geo",
            promote_url="https://t.me/example_bot",
            cpm="0.15",
            target_type="users",
            countries="BY;KZ",
        )
    assert out.get("error") != "target_type=users is EUR-cabinet only."
    assert out.get("ok") is True
    fake.call.assert_awaited()
    method, params = fake.call.await_args.args[:2]
    assert method == "createAd"
    assert params["target_type"] == "users"
    assert params["countries"] == "BY;KZ"


@pytest.mark.asyncio
async def test_launch_ad_users_on_ton_gram_calls_createAd() -> None:
    fake = _ton_gram_client()
    fake.call.side_effect = [
        {"ok": True},  # checkAdPost
        {"ok": True, "ad_id": "99"},  # createAd via create_ad -> call
        {"ok": True},  # incrAdBudget
        {"ok": True},  # sendTargetToReview
    ]
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        out = await server_mod.launch_ad(
            title="geo",
            promote_url="https://t.me/example_bot",
            cpm="0.15",
            target_type="users",
            countries="BY;KZ",
            budget="1",
        )
    assert out.get("error") != "target_type=users is EUR-cabinet only."
    assert out.get("ok") is True
    assert out.get("ad_id") == "99"
    methods = [c.args[0] for c in fake.call.await_args_list]
    assert "createAd" in methods
    create_params = next(c.args[1] for c in fake.call.await_args_list if c.args[0] == "createAd")
    assert create_params["target_type"] == "users"
