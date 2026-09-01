from pathlib import Path

from telegram_ads_mcp.parse import (
    chart_spend_scale,
    derived_metrics,
    detect_cabinet,
    extract_balance,
    extract_currency,
    extract_json_value,
    filter_ads_by_status,
    access_denied_payload,
    channel_langs_conflict,
    looks_access_denied,
    map_status,
    normalize_ad,
    parse_accounts,
    parse_chart,
    redact,
    scale_budget_chart,
    scale_chart_spend,
    strip_empty,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


NESTED = r'{"topicItems":[{"val":1,"name":"A","kids":[1,2,3]},{"val":2,"name":"B"}]}'


def test_extract_json_nested_array() -> None:
    html = f'<script>window.STATE={NESTED};</script>'
    items = extract_json_value(html, "topicItems")
    assert isinstance(items, list)
    assert items[0]["kids"] == [1, 2, 3]


def test_strip_empty_keeps_zero_and_keep_set() -> None:
    params = {"text": "", "cpm": "0.15", "media": "", "picture": "0", "skip": None}
    out = strip_empty(params)
    assert "text" not in out
    assert "skip" not in out
    assert out["cpm"] == "0.15"
    assert out["picture"] == "0"
    kept = strip_empty(params, keep={"media"})
    assert kept["media"] == ""


def test_map_status() -> None:
    assert map_status("active") == "1"
    assert map_status("on_hold") == "0"
    assert map_status("1") == "1"


def test_detect_stars_and_eur_and_ton() -> None:
    stars = detect_cabinet('"currency":"XTR"', "")
    assert stars["cabinet"] == "stars"
    assert stars["supported"] is False
    gram_account = (FIXTURES / "gram_account.html").read_text(encoding="utf-8")
    gram_new = (FIXTURES / "gram_new_ad.html").read_text(encoding="utf-8")
    gram = detect_cabinet(gram_account, gram_new)
    assert gram["cabinet"] == "ton"
    assert gram["currency"] == "GRAM"
    assert gram["supported"] is True
    assert gram["supports_user_targeting"] is True
    # value="users" alone is NOT EUR — live TON/Gram forms include users.
    users_only = detect_cabinet("", '<input name="target_type" value="users">')
    assert users_only["cabinet"] != "eur"
    eur = detect_cabinet((FIXTURES / "eur_account.html").read_text(encoding="utf-8"), "")
    assert eur["cabinet"] == "eur"
    assert eur["supports_user_targeting"] is True
    ton = detect_cabinet('<div>balance</div>', '<input name="target_type" value="channels">')
    assert ton["cabinet"] == "ton"


def test_extract_gram_balance_and_currency() -> None:
    html = (FIXTURES / "gram_account.html").read_text(encoding="utf-8")
    assert extract_currency(html) == "GRAM"
    assert extract_balance(html) == "12.00"


def test_live_status_filter_and_normalize_ad() -> None:
    items = [
        {"ad_id": 35, "status": "Active", "trg_type": "user", "tme_path": "example_bot?start=x", "spent": 0.54},
        {"ad_id": 33, "status": "Stopped", "trg_type": "user", "tme_path": "example_bot?start=y"},
        {"ad_id": 1, "active": "1", "title": "wire-active"},
        {"ad_id": 2, "active": "0", "title": "wire-hold"},
    ]
    active = filter_ads_by_status(items, "active")
    hold = filter_ads_by_status(items, "on_hold")
    assert {i["ad_id"] for i in active} == {35, 1}
    assert {i["ad_id"] for i in hold} == {33, 2}
    norm = normalize_ad(items[0])
    assert norm["target_type"] == "users"
    assert norm["promote_url"] == "https://t.me/example_bot?start=x"
    assert norm["active"] == "1"


def test_gram_chart_spend_scale() -> None:
    html = (FIXTURES / "gram_stats.html").read_text(encoding="utf-8")
    assert chart_spend_scale(html) == 1_000_000
    chart = parse_chart(html, "chart_budget_stats_wrap")
    assert chart is not None
    raw = chart["totals"]["Spent budget"]
    assert raw == 268800
    scaled = scale_chart_spend(raw, chart_spend_scale(html))
    assert scaled == 0.2688
    # Same order of magnitude as ad-list spent ~0.54, not ~1e6.
    assert 0.05 < scaled < 5
    budget = scale_budget_chart(chart, chart_spend_scale(html))
    assert budget["values_already_scaled"] is True
    assert budget["totals"]["Spent budget"] == 0.2688
    assert budget["series"]["Spent budget"] == [0.1, 0.1688]
    # Parser stays raw; get_ad_stats scales a copy.
    assert chart["totals"]["Spent budget"] == 268800


def test_parse_accounts_from_hrefs() -> None:
    html = """
    <a href="/choose_account/abc123"><div class="pr-account-button-title">Acme TON</div>
    <div class="pr-account-button-desc">TON</div></a>
    <a href="/choose_account/new">new</a>
    """
    accounts = parse_accounts(html)
    ids = {a["owner_id"] for a in accounts}
    assert "abc123" in ids
    assert "new" in ids
    acme = next(a for a in accounts if a["owner_id"] == "abc123")
    assert acme["title"] == "Acme TON"


def test_parse_accounts_prefers_json_state() -> None:
    html = """
    <script>{"accounts":[{"id":"json1","title":"From JSON","description":"TON"}]}</script>
    <a href="/choose_account/href1"><div class="pr-account-button-title">From href</div></a>
    """
    accounts = parse_accounts(html)
    assert [a["owner_id"] for a in accounts] == ["json1"]
    assert accounts[0]["title"] == "From JSON"


def test_access_denied_helper() -> None:
    assert looks_access_denied({"error": "ACCESS_DENIED"})
    assert looks_access_denied({"error": "Access denied"})
    assert looks_access_denied("Access denied")
    assert not looks_access_denied({"ok": True, "items": []})
    payload = access_denied_payload({"error": "Access denied"}, tool="manage_audience", action="list")
    assert payload == {
        "ok": False,
        "code": "access_denied",
        "hint": "skip",
        "tool": "manage_audience",
        "action": "list",
        "error": "Access denied",
    }


def test_channel_langs_conflict() -> None:
    assert channel_langs_conflict("channels", "111", "1;2") is True
    assert channel_langs_conflict("channels", None, "1;2") is False
    assert channel_langs_conflict("users", "111", "1;2") is False
    assert channel_langs_conflict("channels", "111", None) is False


def test_parse_chart_and_metrics() -> None:
    html = """
    renderGraph('chart_count_stats_wrap', {"columns":[["x",0,300000],["v",10,20],["c",1,3]],
    "names":{"v":"Views","c":"Clicks"}});
    """
    chart = parse_chart(html, "chart_count_stats_wrap")
    assert chart is not None
    assert chart["totals"]["Views"] == 30
    assert chart["interval_seconds"] == 300
    metrics = derived_metrics(1000, 25, 5)
    assert metrics["ctr"] == 0.025
    assert metrics["cpc"] == 0.2
    assert metrics["cpm_actual"] == 5.0


def test_parse_chart_malformed_does_not_raise() -> None:
    bads = [
        "renderGraph('chart_count_stats_wrap', {\"columns\": 1});",
        "renderGraph('chart_count_stats_wrap', []);",
        "renderGraph('chart_count_stats_wrap', {\"columns\":[123]});",
        "renderGraph('chart_count_stats_wrap', {\"columns\":[{\"x\":1}]});",
        "renderGraph('chart_count_stats_wrap', {",
        "not a chart at all",
    ]
    for html in bads:
        assert parse_chart(html, "chart_count_stats_wrap") is None


def test_redact_secrets() -> None:
    raw = "stel_token=supersecret stel_ssid=alsohash api_hash=deadbeef https://ads.telegram.org/api?hash=abcdef123456"
    out = redact(raw)
    assert "supersecret" not in out
    assert "alsohash" not in out
    assert "abcdef123456" not in out
    assert "***" in out
