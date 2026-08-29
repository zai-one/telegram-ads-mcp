"""Docs stay in sync with the shipped server. No live cabinet data."""

from pathlib import Path

import telegram_ads_mcp.server as server_mod

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {t.name for t in server_mod.mcp._tool_manager.list_tools()}
REQUIRED = {"get_account", "get_ad_stats", "launch_ad", "reload_session", "preview_ad"}


def test_required_docs_exist() -> None:
    for name in ("README.md", "README.ru.md", "INSTALL.md", "AGENTS.md", "CLAUDE.md"):
        assert (ROOT / name).is_file(), name


def test_readme_language_switcher_and_star() -> None:
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    ru = (ROOT / "README.ru.md").read_text(encoding="utf-8")
    assert "README.ru.md" in en
    assert "README.md" in ru
    assert "🇬🇧" in en and "🇷🇺" in en
    assert "🇬🇧" in ru and "🇷🇺" in ru
    for text in (en, ru):
        assert "zai-one/telegram-ads-mcp" in text
        assert "star" in text.lower() or "звезд" in text.lower() or "★" in text
        assert "Gram" in text or "GRAM" in text
        assert "Grok" in text
        assert "zai-one.png" in text or "github.com/zai-one" in text


def test_install_md_stars_and_clone() -> None:
    text = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    assert "github.com/zai-one/telegram-ads-mcp" in text
    assert "user/starred/zai-one/telegram-ads-mcp" in text
    assert "telegram-ads-mcp" in text
    assert "stel_token" in text.lower() or "STEL_TOKEN" in text or ".env" in text


def test_readmes_list_shipped_tools() -> None:
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    ru = (ROOT / "README.ru.md").read_text(encoding="utf-8")
    missing = REQUIRED - TOOLS
    assert not missing
    for name in REQUIRED:
        assert name in en, name
        assert name in ru, name


def test_agents_hygiene_and_gram() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Gram" in text or "GRAM" in text
    assert "INSTALL.md" in text
    assert "README.ru.md" in text
    assert "star" in text.lower()
    packed = ROOT / "telegram_ads_mcp" / "AGENTS.md"
    assert packed.is_file()
