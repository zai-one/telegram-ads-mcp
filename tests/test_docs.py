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
        assert "t.me/zai_one" in text
        assert "issues/new" in text
        assert "## Contributors" not in text
        assert "license-MIT" not in text
        assert "LicenseRef-ZAI-ONE" in text
        assert "mcp-name: io.github.zai-one/telegram-ads-mcp" in text
        assert "don't fork" not in text.lower()
        assert "don’t fork" not in text.lower()
        assert "не форкайте" not in text.lower()


def test_install_md_stars_and_clone() -> None:
    text = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    assert "github.com/zai-one/telegram-ads-mcp" in text
    assert "user/starred/zai-one/telegram-ads-mcp" in text
    assert "telegram-ads-mcp" in text
    assert "stel_token" in text.lower() or "STEL_TOKEN" in text or ".env" in text
    assert ".cursor/mcp.json" in text
    assert ".mcp.json" in text
    assert ".vscode/mcp.json" in text
    assert "mcp_servers.telegram-ads" in text


def test_readmes_list_shipped_tools() -> None:
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    ru = (ROOT / "README.ru.md").read_text(encoding="utf-8")
    missing = REQUIRED - TOOLS
    assert not missing
    for name in REQUIRED:
        assert name in en, name
        assert name in ru, name


def test_issue_template_forbids_secrets() -> None:
    tpl = (ROOT / ".github" / "ISSUE_TEMPLATE" / "request.yml").read_text(encoding="utf-8")
    cfg = (ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text(encoding="utf-8")
    assert "stel_token" in tpl.lower() or "cookies" in tpl.lower()
    assert "t.me/zai_one" in tpl or "t.me/zai_one" in cfg


def test_agents_hygiene_and_gram() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Gram" in text or "GRAM" in text
    assert "INSTALL.md" in text
    assert "README.ru.md" in text
    assert "star" in text.lower()
    assert not text.lstrip().startswith("---")
    packed = ROOT / "telegram_ads_mcp" / "AGENTS.md"
    assert packed.is_file()
    assert packed.read_text(encoding="utf-8") == text


def test_claude_md_bare_agents_include() -> None:
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert not claude.lstrip().startswith("---")
    assert not agents.lstrip().startswith("---")
    lines = claude.splitlines()
    assert "@AGENTS.md" in lines
    assert "Read [AGENTS.md](AGENTS.md)" not in claude
    assert not any(line.strip() == "`@AGENTS.md`" for line in lines)


def test_license_is_not_mit() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("LicenseRef-ZAI-ONE")
    assert not license_text.lstrip().startswith("MIT")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "LicenseRef-ZAI-ONE" in pyproject
    assert "OSI Approved :: MIT License" not in pyproject
    assert '"ton"' not in pyproject.split("[project]")[1].split("[project.optional")[0]


def test_server_json_discovery() -> None:
    import json

    data = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert data["name"] == "io.github.zai-one/telegram-ads-mcp"
    assert "ads.telegram.org" in data["description"]
    assert "Gram" in data["description"]
    assert len(data["description"]) <= 100
    assert "packages" not in data
