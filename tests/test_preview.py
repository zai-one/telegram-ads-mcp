from telegram_ads_mcp.preview import render_card


def test_render_card_writes_png(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TG_ADS_PREVIEW_DIR", str(tmp_path))
    from telegram_ads_mcp import preview as preview_mod

    monkeypatch.setattr(preview_mod, "DEFAULT_DIR", tmp_path)
    png, path = render_card(
        ad_id="42",
        title="Test ad",
        text="Hello world from Telegram Ads preview",
        promote_url="https://t.me/example",
        cpm="0.15",
        status="1",
    )
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert path.exists()
    assert path.stat().st_size > 100
