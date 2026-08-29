import json

import httpx
import pytest

from tg_ads_mcp.client import AuthError, TelegramAdsClient


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
async def test_stars_refused() -> None:
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
    with pytest.raises(Exception):
        await client.require_supported_cabinet()
    await client.aclose()


@pytest.mark.asyncio
async def test_missing_cookies() -> None:
    with pytest.raises(Exception):
        TelegramAdsClient("", "")
