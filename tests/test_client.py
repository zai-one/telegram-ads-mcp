import json

import httpx
import pytest

from pathlib import Path

from telegram_ads_mcp.client import AuthError, TelegramAdsClient
from telegram_ads_mcp.parse import extract_balance, normalize_ad

FIXTURES = Path(__file__).resolve().parent / "fixtures"


ACCOUNT_HTML = """
<html><script>
window.__STATE__ = {"apiUrl":"/api?hash=abcdef123456","ownerId":"own1","currency":"TON","balance":"12.5"};
</script></html>
"""

EUR_NEW_AD = '<form><input name="target_type" value="users"><input name="target_type" value="channels"></form>'
TON_NEW_AD = '<form><input name="target_type" value="channels"><input name="target_type" value="bots"></form>'
STARS_ACCOUNT = """
<html><script>{"apiUrl":"/api?hash=abcdef123456","ownerId":"s1","currency":"XTR","balance":"1000"}</script></html>
"""


def _router(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if request.url.path == "/account":
        html = ACCOUNT_HTML
        if request.headers.get("x-test-cabinet") == "stars":
            html = STARS_ACCOUNT
        return httpx.Response(200, text=html)
    if request.url.path == "/account/ad/new":
        return httpx.Response(200, text=TON_NEW_AD)
    if request.url.path == "/account/budget":
        return httpx.Response(200, text='{"balance":"12.5","currency":"TON"}')
    if request.url.path.startswith("/api"):
        body = dict(request.content and {})  # unused
        return httpx.Response(200, json={"ok": True, "method": "echo", "items": [{"ad_id": "1", "active": "1"}]})
    if request.url.path == "/choose_account":
        return httpx.Response(
            200,
            text='<a href="/choose_account/own1"><div class="pr-account-button-title">Main</div></a>',
        )
    return httpx.Response(404, text="no")


@pytest.mark.asyncio
async def test_authenticate_and_get_account() -> None:
    transport = httpx.MockTransport(_router)
    client = TelegramAdsClient("tok", "ssid")
    await client._http.aclose()
    client._http = httpx.AsyncClient(
        base_url="https://ads.telegram.org",
        transport=transport,
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    info = await client.authenticate()
    assert info["ok"] is True
    assert client.owner_id == "own1"
    assert "abcdef" in (client.api_hash or "")
    acc = await client.get_account()
    assert acc["cabinet"] == "ton"
    assert acc["currency"] == "TON"
    assert acc["balance"] == "12.5"
    await client.aclose()


@pytest.mark.asyncio
async def test_stars_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("TG_ADS_STARS", raising=False)
    def stars_router(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/account":
            return httpx.Response(200, text=STARS_ACCOUNT)
        if request.url.path == "/account/ad/new":
            return httpx.Response(200, text=TON_NEW_AD)
        if request.url.path == "/account/budget":
            return httpx.Response(200, text='{"currency":"XTR"}')
        return httpx.Response(404)

    client = TelegramAdsClient("tok", "ssid")
    await client._http.aclose()
    client._http = httpx.AsyncClient(
        base_url="https://ads.telegram.org",
        transport=httpx.MockTransport(stars_router),
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    await client.authenticate()
    cabinet = await client.detect_cabinet()
    assert cabinet["cabinet"] == "stars"
    with pytest.raises(Exception):  # default: refused (paid path only fixture-tested)
        await client.require_supported_cabinet()
    assert (await client.get_account())["supported"] is False  # the card must not claim otherwise
    monkeypatch.setenv("TG_ADS_STARS", "on")
    assert (await client.require_supported_cabinet())["money"]["unit"].startswith("Telegram Stars")
    assert (await client.get_account())["supported"] is True
    await client.aclose()


@pytest.mark.asyncio
async def test_missing_cookies() -> None:
    with pytest.raises(Exception):
        TelegramAdsClient("", "")


GRAM_ACCOUNT = (FIXTURES / "gram_account.html").read_text(encoding="utf-8")
GRAM_STATS = (FIXTURES / "gram_stats.html").read_text(encoding="utf-8")
GRAM_NEW = (FIXTURES / "gram_new_ad.html").read_text(encoding="utf-8")


def _gram_router(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/account":
        return httpx.Response(
            200,
            text='<html><script>window.__STATE__ = {"apiUrl":"/api?hash=abcdef123456","ownerId":"own1"};</script>'
            + GRAM_ACCOUNT
            + "</html>",
        )
    if path == "/account/ad/new":
        return httpx.Response(200, text=GRAM_NEW)
    if path == "/account/budget":
        return httpx.Response(200, text="<html>no json balance</html>")
    if path == "/account/ad/35/stats":
        return httpx.Response(200, text=GRAM_STATS)
    if path.startswith("/api"):
        body = request.content.decode("utf-8", "replace") if request.content else ""
        if "getAdsList" in body:
            pass
        elif "method=getAd" in body or body.endswith("getAd") or "getAd&" in body:
            return httpx.Response(400, text="Bad request")
        return httpx.Response(
            200,
            json={
                "ok": True,
                "items": [
                    {
                        "ad_id": 35,
                        "status": "Active",
                        "trg_type": "user",
                        "tme_path": "example_bot?start=x",
                        "spent": 0.54,
                        "title": "geo",
                    }
                ],
            },
        )
    if path == "/account/ad/35":
        return httpx.Response(200, text="<html>no ad json</html>")
    return httpx.Response(404, text="no")


@pytest.mark.asyncio
async def test_gram_account_not_eur_and_balance() -> None:
    client = TelegramAdsClient("tok", "ssid")
    await client._http.aclose()
    client._http = httpx.AsyncClient(
        base_url="https://ads.telegram.org",
        transport=httpx.MockTransport(_gram_router),
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    await client.authenticate()
    acc = await client.get_account()
    assert acc["cabinet"] == "ton"
    assert acc["cabinet"] != "eur"
    assert acc["currency"] == "GRAM"
    assert acc["balance"] == "12.00"
    assert extract_balance(GRAM_ACCOUNT) == "12.00"
    await client.aclose()


@pytest.mark.asyncio
async def test_get_ad_stats_scales_gram_spend() -> None:
    client = TelegramAdsClient("tok", "ssid")
    await client._http.aclose()
    client._http = httpx.AsyncClient(
        base_url="https://ads.telegram.org",
        transport=httpx.MockTransport(_gram_router),
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    await client.authenticate()
    stats = await client.get_ad_stats("35", period="5min")
    assert stats["ok"] is True
    assert stats["period"] == "5min"
    spend = stats["summary"]["spend"]
    assert stats["summary"]["spend_scale"] == 1_000_000
    assert stats["summary"]["spend_already_scaled"] is True
    assert spend == 0.2688
    assert 0.05 < spend < 5
    budget = stats["charts"]["budget"]
    assert budget["values_already_scaled"] is True
    assert budget["totals"]["Spent budget"] == 0.2688
    assert 268800 not in (budget["totals"].get("Spent budget"),)
    day = await client.get_ad_stats("35", period="day")
    assert day["ok"] is True
    assert day["period"] == "day"
    assert day["summary"]["spend_already_scaled"] is True
    listing = await client.get_ads_list()
    item = listing["items"][0]
    assert item["target_type"] == "users"
    assert item["promote_url"].startswith("https://t.me/")
    assert item["active"] == "1"
    got = await client.get_ad("35")
    assert got["ad"]["promote_url"].startswith("https://t.me/")
    await client.aclose()


@pytest.mark.asyncio
async def test_ads_list_cache_and_getad_skip() -> None:
    hits = {"api": 0}

    def router(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/account":
            return httpx.Response(
                200,
                text='<html><script>window.__STATE__ = {"apiUrl":"/api?hash=abcdef123456","ownerId":"own1"};</script>'
                + GRAM_ACCOUNT
                + "</html>",
            )
        if path.startswith("/api"):
            hits["api"] += 1
            body = request.content.decode("utf-8", "replace") if request.content else ""
            if "getAdsList" in body:
                return httpx.Response(200, json={"ok": True, "items": [{"ad_id": 1, "status": "Active"}]})
            return httpx.Response(400, text="Bad request")
        if path.startswith("/account/ad/"):
            return httpx.Response(200, text="<html>no ad json</html>")
        return httpx.Response(404)

    client = TelegramAdsClient("tok", "ssid")
    await client._http.aclose()
    client._http = httpx.AsyncClient(
        base_url="https://ads.telegram.org",
        transport=httpx.MockTransport(router),
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    await client.authenticate()
    await client.get_ads_list()
    await client.get_ads_list()
    list_hits = hits["api"]
    assert list_hits == 1
    await client.get_ad("1")
    after_first = hits["api"]
    await client.get_ad("1")
    assert hits["api"] == after_first
    await client.aclose()


def test_normalize_ad_shipped() -> None:
    out = normalize_ad({"status": "Stopped", "trg_type": "user", "tme_path": "bot/start"})
    assert out["active"] == "0"
    assert out["target_type"] == "users"
    assert "t.me/bot/start" in out["promote_url"]


def _money_client(handler) -> TelegramAdsClient:
    """Authenticated-looking client whose /api posts go to `handler(method, request)`."""
    from urllib.parse import parse_qs

    def router(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/api"):
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            return handler(form.get("method"), request)
        return _router(request)

    client = TelegramAdsClient("tok", "ssid")
    client._http = httpx.AsyncClient(
        base_url="https://ads.telegram.org",
        transport=httpx.MockTransport(router),
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["read_timeout", "http_502"])
async def test_money_call_is_never_resent_after_it_may_have_landed(failure: str) -> None:
    """A lost reply / 5xx on incrAdBudget must not be retried: the retry would add the money twice."""
    sent: list[str] = []

    def handler(method, request):
        sent.append(method)
        if failure == "read_timeout":
            raise httpx.ReadTimeout("lost reply", request=request)
        return httpx.Response(502, text="bad gateway")

    client = _money_client(handler)
    await client.authenticate()
    out = await client.call("incrAdBudget", {"owner_id": "own1", "ad_id": "7", "amount": "5"})
    assert sent == ["incrAdBudget"]
    assert out["ok"] is False and out["code"] == "outcome_unknown" and out["retryable"] is False
    sent.clear()
    out = await client.call("transferFunds", {"owner_id": "own1", "account_id": "a", "amount": "5"})
    assert sent == ["transferFunds"] and out["code"] == "outcome_unknown"
    await client.aclose()


@pytest.mark.asyncio
async def test_money_call_retries_only_when_request_was_not_sent() -> None:
    """ConnectError means the request never left: retrying a money call is safe there. Reads still retry 5xx."""
    seen: list[str] = []

    def handler(method, request):
        seen.append(method)
        if len(seen) == 1:
            raise httpx.ConnectError("refused", request=request)
        if method == "getAdsList" and seen.count("getAdsList") == 1:
            return httpx.Response(502, text="bad gateway")
        return httpx.Response(200, json={"ok": True, "items": []})

    client = _money_client(handler)
    await client.authenticate()
    out = await client.call("incrAdBudget", {"owner_id": "own1", "ad_id": "7", "amount": "5"})
    assert out["ok"] is True and seen == ["incrAdBudget", "incrAdBudget"]
    listing = await client.call("getAdsList", {"owner_id": "own1"})
    assert listing["ok"] is True and seen.count("getAdsList") == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_get_ad_fresh_bypasses_cached_list() -> None:
    """budget_target reads with fresh=True: a 30 s cached list budget must not be used for money."""
    budget = {"value": "5"}

    def handler(method, request):
        if method == "getAd":
            return httpx.Response(400, text="bad")
        return httpx.Response(200, json={"items": [{"ad_id": "7", "budget": budget["value"]}]})

    client = _money_client(handler)
    await client.authenticate()
    assert (await client.get_ad("7"))["ad"]["budget"] == "5"
    budget["value"] = "8"  # changed in the cabinet UI meanwhile
    assert (await client.get_ad("7"))["ad"]["budget"] == "5"  # cached view (fine for reads)
    assert (await client.get_ad("7", fresh=True))["ad"]["budget"] == "8"
    await client.aclose()
