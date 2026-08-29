from tg_ads_mcp.parse import (
    derived_metrics,
    detect_cabinet,
    extract_json_value,
    map_status,
    parse_accounts,
    parse_chart,
    redact,
    strip_empty,
)


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
    eur = detect_cabinet("", '<input name="target_type" value="users">')
    assert eur["cabinet"] == "eur"
    assert eur["supports_user_targeting"] is True
    ton = detect_cabinet('<div>balance</div>', '<input name="target_type" value="channels">')
    assert ton["cabinet"] == "ton"


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


def test_redact_secrets() -> None:
    raw = "stel_token=supersecret stel_ssid=alsohash api_hash=deadbeef"
    out = redact(raw)
    assert "supersecret" not in out
    assert "alsohash" not in out
    assert "***" in out
