"""TG_ADS_WRITE_GATE: strict / confirm / open."""

from unittest.mock import AsyncMock, patch

import pytest

from telegram_ads_mcp.gate import DEFAULT, gated, write_gate
import telegram_ads_mcp.server as server_mod


def test_default_gate_is_confirm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TG_ADS_WRITE_GATE", raising=False)
    assert write_gate() == DEFAULT == "confirm"


def test_unknown_gate_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TG_ADS_WRITE_GATE", "yolo")
    assert write_gate() == "confirm"


def test_gated_matrix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TG_ADS_WRITE_GATE", "confirm")
    assert gated(cls="write", tool="edit_ad") is None
    spend = gated(cls="spend", tool="launch_ad")
    assert spend is not None and spend["code"] == "write_gated"
    assert gated(cls="spend", tool="launch_ad", confirm=True) is None

    monkeypatch.setenv("TG_ADS_WRITE_GATE", "strict")
    assert gated(cls="write", tool="edit_ad") is not None
    assert gated(cls="write", tool="edit_ad", confirm=True) is None

    monkeypatch.setenv("TG_ADS_WRITE_GATE", "open")
    assert gated(cls="danger", tool="manage_funds") is None


@pytest.mark.asyncio
async def test_launch_ad_confirm_gate_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TG_ADS_WRITE_GATE", "confirm")
    out = await server_mod.launch_ad(
        title="geo",
        promote_url="https://t.me/example_bot",
        cpm="0.15",
    )
    assert out["ok"] is False
    assert out["code"] == "write_gated"
    assert out["class"] == "spend"


@pytest.mark.asyncio
async def test_create_on_hold_free_under_confirm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TG_ADS_WRITE_GATE", "confirm")
    fake = AsyncMock()
    fake.owner_id = "own1"
    fake.require_supported_cabinet.return_value = {"cabinet": "ton", "currency": "GRAM", "supported": True}
    fake.call.return_value = {"ok": True, "ad_id": "1"}
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        out = await server_mod.create_ad(
            title="geo",
            promote_url="https://t.me/example_bot",
            cpm="0.15",
            active="on_hold",
            budget="0",
        )
    assert out.get("ok") is True
    fake.call.assert_awaited()


@pytest.mark.asyncio
async def test_edit_budget_is_spend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TG_ADS_WRITE_GATE", "confirm")
    out = await server_mod.edit_ad(ad_id="1", budget_action="increase", budget_amount="2")
    assert out["code"] == "write_gated"
    assert out["class"] == "spend"
    fake = AsyncMock()
    fake.owner_id = "own1"
    fake.require_supported_cabinet.return_value = {"cabinet": "ton", "currency": "GRAM"}
    fake.call.return_value = {"ok": True}
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        pause = await server_mod.edit_ad(ad_id="1", active="on_hold")
    assert pause.get("code") != "write_gated"
    fake.call.assert_awaited()


@pytest.mark.asyncio
async def test_funds_list_free_withdraw_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TG_ADS_WRITE_GATE", "confirm")
    fake = AsyncMock()
    fake.owner_id = "own1"
    fake.require_supported_cabinet.return_value = {"cabinet": "ton", "currency": "GRAM"}
    fake.detect_cabinet.return_value = {"cabinet": "ton", "currency": "GRAM"}
    fake.call.return_value = {"ok": True, "accounts": []}
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        listed = await server_mod.manage_funds(action="list")
    assert listed.get("code") != "write_gated"
    blocked = await server_mod.manage_funds(action="withdraw", amount="1", account_id="x")
    assert blocked["code"] == "write_gated"
    assert blocked["class"] == "danger"


@pytest.mark.asyncio
async def test_delete_strict_needs_confirm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TG_ADS_WRITE_GATE", "strict")
    out = await server_mod.delete_ad(ad_id="1")
    assert out["code"] == "write_gated"
    assert out["class"] == "danger"
