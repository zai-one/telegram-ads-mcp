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


@pytest.mark.asyncio
async def test_get_ad_stats_summary_omits_charts() -> None:
    fake = _ton_gram_client()
    fake.get_ad_stats = AsyncMock(return_value={"ok": True, "period": "5min", "summary": {"spend": "1"}, "charts": {"x": [1]}})
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        lean = await server_mod.get_ad_stats("35")
        full = await server_mod.get_ad_stats("35", detail="full")
    assert "charts" not in lean and lean["charts_omitted"] is True and lean["summary"]["spend"] == "1"
    assert full["charts"] == {"x": [1]}


@pytest.mark.asyncio
async def test_get_ads_summary_compacts_items() -> None:
    fake = _ton_gram_client()
    fake.get_ads_list = AsyncMock(return_value={"items": [{"ad_id": "1", "text": "", "media": None}]})
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        lean = await server_mod.get_ads()
        full = await server_mod.get_ads(detail="full")
    assert lean["items"] == [{"ad_id": "1"}]
    assert full["items"][0]["media"] is None


def _stars_client() -> AsyncMock:
    fake = _ton_gram_client()
    cabinet = {"cabinet": "stars", "currency": "XTR", "supports_user_targeting": False, "supported": True}
    fake.detect_cabinet.return_value = cabinet
    fake.require_supported_cabinet.return_value = cabinet
    return fake


@pytest.mark.asyncio
async def test_stars_cabinet_whole_numbers_and_no_users() -> None:
    fake = _stars_client()
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)):
        bad = await server_mod.create_ad(title="s", promote_url="https://t.me/example_bot", cpm="1.5")
        users = await server_mod.create_ad(
            title="s", promote_url="https://t.me/example_bot", cpm="2", target_type="users"
        )
        good = await server_mod.create_ad(title="s", promote_url="https://t.me/example_bot", cpm="2")
    assert bad["code"] == "invalid_amount"
    assert users["code"] == "unsupported_in_cabinet"
    assert good["ok"] is True
    method, params = fake.call.await_args.args[:2]
    assert method == "createAd" and params["cpm"] == "2"


def _budget_client(start: str, *, cabinet: AsyncMock | None = None, read_delay: float = 0.0) -> AsyncMock:
    """Fake cabinet whose get_ad reports a live budget that incr/decrAdBudget really change."""
    import anyio
    from decimal import Decimal

    fake = cabinet or _ton_gram_client()
    state = {"budget": Decimal(start)}

    async def get_ad(ad_id, **_kw):
        value = state["budget"]
        await anyio.sleep(read_delay)
        return {"ok": True, "ad": {"budget": format(value.normalize(), "f")}}

    async def call(method, params=None, **_kw):
        if method in ("incrAdBudget", "decrAdBudget"):
            sign = 1 if method == "incrAdBudget" else -1
            state["budget"] += sign * Decimal(params["amount"])
        return {"ok": True, "ad_id": "99"}

    fake.get_ad.side_effect = get_ad
    fake.call.side_effect = call
    fake.state = state
    return fake


@pytest.mark.asyncio
async def test_edit_ad_budget_target_sends_difference() -> None:
    fake = _budget_client("5.5")
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
        "os.environ", {"TG_ADS_WRITE_GATE": "open"}
    ):
        up = await server_mod.edit_ad(ad_id="7", budget_target="8")
        first = fake.call.await_args_list[0].args
        fake.call.reset_mock()
        down = await server_mod.edit_ad(ad_id="7", budget_target="5")
        second = fake.call.await_args_list[0].args
        same = await server_mod.edit_ad(ad_id="7", budget_target="5")
        both = await server_mod.edit_ad(ad_id="7", budget_target="9", budget_action="increase", budget_amount="1")
    assert first[0] == "incrAdBudget" and first[1]["amount"] == "2.5" and up["ok"] is not False
    assert second[0] == "decrAdBudget" and second[1]["amount"] == "3" and down["ok"] is not False
    assert up["budget_change"] == {"current": "5.5", "target": "8", "action": "increase", "amount": "2.5",
                                   "after": "8"}
    assert down["budget_change"]["action"] == "decrease"
    assert same["code"] == "no_change" and both["code"] == "invalid_args"
    fake.get_ad.side_effect = None
    fake.get_ad.return_value = {"ok": True, "ad": {"budget": "n/a"}}
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
        "os.environ", {"TG_ADS_WRITE_GATE": "open"}
    ):
        unknown = await server_mod.edit_ad(ad_id="7", budget_target="9")
    assert unknown["code"] == "budget_unknown"


@pytest.mark.asyncio
async def test_launch_ad_checks_spend_budget_before_any_call() -> None:
    """launch_ad spends `budget` via incrAdBudget after create_ad(budget="0"), so create_ad's own check
    never sees it. A bad spend amount must stop the whole launch before the first platform call."""
    for fake, budget in ((_stars_client(), "1.5"), (_ton_gram_client(), "1,5"), (_ton_gram_client(), "2.555"),
                         (_ton_gram_client(), "1e3"), (_ton_gram_client(), "-1")):
        with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
            "os.environ", {"TG_ADS_WRITE_GATE": "open"}
        ):
            out = await server_mod.launch_ad(
                title="t", promote_url="https://t.me/example_bot", cpm="2", budget=budget
            )
        assert out["code"] == "invalid_amount", (budget, out)
        fake.call.assert_not_awaited()
    fake = _ton_gram_client()
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
        "os.environ", {"TG_ADS_WRITE_GATE": "open"}
    ):
        ok = await server_mod.launch_ad(title="t", promote_url="https://t.me/example_bot", cpm="2", budget="3.5")
    assert ok["ok"] is True
    spent = [c.args for c in fake.call.await_args_list if c.args[0] == "incrAdBudget"]
    assert spent == [("incrAdBudget", {"owner_id": "own1", "ad_id": "99", "amount": "3.5"})]


@pytest.mark.asyncio
async def test_budget_target_is_spend_gated() -> None:
    """budget_target moves money: strict and confirm must stop it without confirm=true, and touch nothing."""
    fake = _budget_client("1")
    for gate in ("strict", "confirm"):
        with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
            "os.environ", {"TG_ADS_WRITE_GATE": gate}
        ):
            out = await server_mod.edit_ad(ad_id="7", budget_target="50")
        assert out["code"] == "write_gated" and out["class"] == "spend" and out["sent"] is False, gate
        assert out["would_send"]["budget_target"] == "50"
    fake.get_ad.assert_not_awaited()
    fake.call.assert_not_awaited()
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
        "os.environ", {"TG_ADS_WRITE_GATE": "confirm"}
    ):
        done = await server_mod.edit_ad(ad_id="7", budget_target="50", confirm=True)
    assert done["budget_change"]["amount"] == "49"
    assert fake.call.await_args_list[0].args[0] == "incrAdBudget"


@pytest.mark.asyncio
async def test_budget_target_refuses_ambiguous_current_budget() -> None:
    """Reading "1,234" as 1.234 would turn target 1500 into a ~1499 increase. Refuse, send nothing."""
    for current in ("1,234", "1 234.50", "€5", "1e3", None, True, "-2"):
        fake = _ton_gram_client()
        fake.get_ad.return_value = {"ok": True, "ad": {"budget": current}}
        with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
            "os.environ", {"TG_ADS_WRITE_GATE": "open"}
        ):
            out = await server_mod.edit_ad(ad_id="7", budget_target="1500")
        assert out["code"] == "budget_unknown", (current, out)
        fake.call.assert_not_awaited()
    fake = _budget_client("4")
    reads = iter([4, 5])

    async def get_ad(ad_id, **_kw):
        return {"ok": True, "ad": {"budget": next(reads)}}  # ints, as some payloads return them

    fake.get_ad.side_effect = get_ad
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
        "os.environ", {"TG_ADS_WRITE_GATE": "open"}
    ):
        out = await server_mod.edit_ad(ad_id="7", budget_target="5")
    assert out["budget_change"] == {"current": "4", "target": "5", "action": "increase", "amount": "1",
                                    "after": "5"}


@pytest.mark.asyncio
async def test_budget_target_concurrent_calls_do_not_stack() -> None:
    """Two budget_target=10 calls from 5 must end at 10, not 15 (read-modify-write race)."""
    import anyio

    fake = _budget_client("5", read_delay=0.01)
    outs: list[dict] = []

    async def one() -> None:
        outs.append(await server_mod.edit_ad(ad_id="7", budget_target="10"))

    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
        "os.environ", {"TG_ADS_WRITE_GATE": "open"}
    ):
        async with anyio.create_task_group() as tg:
            tg.start_soon(one)
            tg.start_soon(one)
    assert str(fake.state["budget"]) == "10"
    assert sorted(o.get("code", "sent") for o in outs) == ["no_change", "sent"]
    assert [c.args[0] for c in fake.call.await_args_list] == ["incrAdBudget"]


@pytest.mark.asyncio
async def test_budget_target_reads_fresh_and_flags_wrong_result() -> None:
    """The current budget is read uncached; if the read-back is not the target, say so (no false success)."""
    fake = _budget_client("5")
    real_call = fake.call.side_effect

    async def other_writer_too(method, params=None, **kw):
        out = await real_call(method, params, **kw)
        if method == "incrAdBudget":
            fake.state["budget"] += 3  # someone else (cabinet UI, another process) added 3 meanwhile
        return out

    fake.call.side_effect = other_writer_too
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
        "os.environ", {"TG_ADS_WRITE_GATE": "open"}
    ):
        out = await server_mod.edit_ad(ad_id="7", budget_target="10", title="t")
    assert all(c.kwargs.get("fresh") is True for c in fake.get_ad.await_args_list)
    assert out["ok"] is False and out["code"] == "budget_mismatch" and out["retryable"] is False
    assert out["budget_change"]["after"] == "13" and out["edit_skipped"] is True
    assert "editAd" not in [c.args[0] for c in fake.call.await_args_list]


@pytest.mark.asyncio
async def test_budget_target_lost_reply_is_not_success() -> None:
    """outcome_unknown from the money call: read-back decides; budget unchanged -> not ok, nothing re-sent."""
    fake = _budget_client("5")
    lost = {"ok": False, "code": "outcome_unknown", "retryable": False}

    async def call(method, params=None, **_kw):
        return lost

    fake.call.side_effect = call
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
        "os.environ", {"TG_ADS_WRITE_GATE": "open"}
    ):
        out = await server_mod.edit_ad(ad_id="7", budget_target="10")
        plain = await server_mod.edit_ad(ad_id="7", budget_action="increase", budget_amount="1", active="active")
    assert out["ok"] is False and out["code"] == "budget_mismatch" and out["budget"] == lost
    assert plain["ok"] is False and plain["code"] == "outcome_unknown" and plain["edit_skipped"] is True
    assert [c.args[0] for c in fake.call.await_args_list] == ["incrAdBudget", "incrAdBudget"]


@pytest.mark.asyncio
async def test_budget_target_equal_still_sends_other_fields() -> None:
    """budget already at target must skip only the budget, not the pause sent in the same call."""
    fake = _budget_client("5")
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
        "os.environ", {"TG_ADS_WRITE_GATE": "open"}
    ):
        out = await server_mod.edit_ad(ad_id="7", budget_target="5", active="on_hold", confirm=True)
    calls = [c.args for c in fake.call.await_args_list]
    assert [c[0] for c in calls] == ["editAd"]
    assert calls[0][1]["active"] == "0"
    assert out["ok"] is True and out["budget_change"] is None and "edit" in out


@pytest.mark.asyncio
async def test_budget_target_difference_must_fit_cabinet() -> None:
    """current 0.123456 -> target 1 would send 0.876544: refuse before any money call."""
    fake = _budget_client("0.123456")
    stars = _budget_client("1.5", cabinet=_stars_client())
    for client, target in ((fake, "1"), (stars, "3")):
        with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=client)), patch.dict(
            "os.environ", {"TG_ADS_WRITE_GATE": "open", "TG_ADS_STARS": "on"}
        ):
            out = await server_mod.edit_ad(ad_id="7", budget_target=target)
        assert out["code"] == "invalid_amount", out
        client.call.assert_not_awaited()


@pytest.mark.asyncio
async def test_manage_funds_checks_cabinet_amount_rules() -> None:
    """transfer/withdraw/add move money: "1.5" Stars, "1e3", "1,5" or a missing amount never reach the API."""
    cases = [(_stars_client(), "1.5"), (_ton_gram_client(), "1e3"), (_ton_gram_client(), "1,5"),
             (_ton_gram_client(), "2.555"), (_ton_gram_client(), None)]
    for fake, amount in cases:
        for action in ("transfer", "withdraw", "add"):
            with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
                "os.environ", {"TG_ADS_WRITE_GATE": "open", "TG_ADS_STARS": "on"}
            ):
                out = await server_mod.manage_funds(action=action, amount=amount, account_id="acc")
            assert out["code"] == "invalid_amount", (action, amount, out)
        fake.call.assert_not_awaited()
    fake = _stars_client()
    with patch("telegram_ads_mcp.server.get_client", AsyncMock(return_value=fake)), patch.dict(
        "os.environ", {"TG_ADS_WRITE_GATE": "open", "TG_ADS_STARS": "on"}
    ):
        ok = await server_mod.manage_funds(action="transfer", amount="15", account_id="acc")
    assert ok["ok"] is True
    assert fake.call.await_args.args == ("transferFunds", {"owner_id": "own1", "account_id": "acc", "amount": "15"})
