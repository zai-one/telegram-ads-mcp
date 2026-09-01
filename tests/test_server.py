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


@pytest.mark.asyncio
async def test_launch_ad_passes_exclude_and_locations() -> None:
    fake = _ton_gram_client()
    fake.call.side_effect = [
        {"ok": True},
        {"ok": True, "ad_id": "42"},
        {"ok": True},
        {"ok": True},
    ]
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        out = await server_mod.launch_ad(
            title="geo",
            promote_url="https://t.me/example_bot",
            cpm="0.15",
            target_type="users",
            countries="BY",
            locations="123",
            exclude_user_topics="9",
            exclude_topics="1",
            topics="2",
            budget="1",
            confirm=True,
        )
    assert out.get("ok") is True
    create_params = next(c.args[1] for c in fake.call.await_args_list if c.args[0] == "createAd")
    assert create_params["locations"] == "123"
    assert create_params["exclude_user_topics"] == "9"
    assert create_params["exclude_topics"] == "1"
    assert create_params["topics"] == "2"
    assert "langs" not in create_params or create_params.get("langs") in (None, "")


@pytest.mark.asyncio
async def test_launch_ad_drops_langs_when_channels_set() -> None:
    fake = _ton_gram_client()
    fake.call.side_effect = [
        {"ok": True},
        {"ok": True, "ad_id": "7"},
        {"ok": True},
        {"ok": True},
    ]
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        out = await server_mod.launch_ad(
            title="ch",
            promote_url="https://t.me/example",
            cpm="0.2",
            target_type="channels",
            channels="111;222",
            langs="1;2",
            topics="3",
            exclude_channels="999",
            budget="1",
            confirm=True,
        )
    assert out.get("ok") is True
    assert "langs_omitted" in out["steps"]
    create_params = next(c.args[1] for c in fake.call.await_args_list if c.args[0] == "createAd")
    assert not create_params.get("langs")
    assert create_params["channels"] == "111;222"
    assert create_params["topics"] == "3"
    assert create_params["exclude_channels"] == "999"


@pytest.mark.asyncio
async def test_launch_ad_sends_langs_without_channel_ids() -> None:
    fake = _ton_gram_client()
    fake.call.side_effect = [
        {"ok": True},
        {"ok": True, "ad_id": "8"},
        {"ok": True},
        {"ok": True},
    ]
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        out = await server_mod.launch_ad(
            title="lang-wide",
            promote_url="https://t.me/example",
            cpm="0.2",
            target_type="channels",
            langs="1;2",
            budget="1",
            confirm=True,
        )
    assert out.get("ok") is True
    create_params = next(c.args[1] for c in fake.call.await_args_list if c.args[0] == "createAd")
    assert create_params["langs"] == "1;2"


@pytest.mark.asyncio
async def test_audience_list_access_denied_is_structured() -> None:
    fake = _ton_gram_client()
    fake.call.return_value = {"error": "Access denied"}
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        out = await server_mod.manage_audience(action="list")
    assert out["ok"] is False
    assert out["code"] == "access_denied"
    assert out["hint"] == "skip"
    assert out["tool"] == "manage_audience"
    assert out["action"] == "list"
    fake.call.assert_awaited_once()


@pytest.mark.asyncio
async def test_event_list_access_denied_is_structured() -> None:
    fake = _ton_gram_client()
    fake.call.return_value = {"error": "ACCESS_DENIED"}
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        out = await server_mod.manage_event(action="list")
    assert out["ok"] is False
    assert out["code"] == "access_denied"
    assert out["hint"] == "skip"
    assert out["tool"] == "manage_event"
    fake.call.assert_awaited_once()


def test_prompts_match_stats_contract() -> None:
    diag = server_mod.diagnose_ad_prompt("35")
    assert "35" in diag
    assert "period=day" in diag
    assert "do not divide" in diag.lower() or "already scaled" in diag.lower()
    assert "spend_already_scaled" in diag
    review = server_mod.review_account_prompt()
    assert "already scaled" in review.lower()
    assert "reports/" in review
    assert "5 problem" in review
    assert "one recommendation" in review.lower()
    launch = server_mod.launch_campaign_prompt()
    assert "already scaled" in launch.lower()
    assert "reports/" in launch
