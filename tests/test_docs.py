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
        assert "check_security.py" in text
        assert "INSTALL.md" in text
        assert "DevTools" in text
        assert "mcp.json.example" in text
        assert "write_gated" in text
        assert "don't fork" not in text.lower()
        assert "don’t fork" not in text.lower()
        assert "не форкайте" not in text.lower()


def test_install_md_stars_and_clone() -> None:
    text = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    assert "github.com/zai-one/telegram-ads-mcp" in text
    assert "user/starred/zai-one/telegram-ads-mcp" in text
    assert "telegram-ads-mcp" in text
    assert "stel_token" in text.lower() or "STEL_TOKEN" in text or ".env" in text
    assert "F12" in text
    assert "Ctrl+Shift+I" in text
    assert "Application" in text
    assert "reload_session" in text
    assert "do not ask" in text.lower() or "не проси" in text.lower()
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
    assert "confirm_hash" in tpl.lower()
    assert "check_security.py" in tpl
    assert "t.me/zai_one" in tpl or "t.me/zai_one" in cfg
    contrib = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "scripts/check_security.py" in contrib
    assert "gh issue create" in contrib
    assert "Found a bug → Issue" in contrib
    assert "AGENTS.local.md" in contrib
    assert "INSTALL.md" in cfg


def test_gitignore_local_notes_not_client_playbook() -> None:
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gi
    assert "VERIFY.md" in gi
    assert "previews/" in gi
    assert "reports/" in gi
    assert "AGENTS.local.md" in gi
    assert "CLAUDE.local.md" in gi
    assert "draft.md" in gi
    assert "*.issue.md" in gi
    for raw in gi.splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith("!"):
            continue
        assert s not in {"AGENTS.md", "/AGENTS.md", "**/AGENTS.md"}
        assert "telegram_ads_mcp/AGENTS.md" not in s
        assert "check_security.py" not in s
        assert not s.startswith("tests/")
    example = ROOT / "AGENTS.local.md.example"
    assert example.is_file()
    stub = example.read_text(encoding="utf-8")
    assert "AGENTS.md" in stub
    assert "STEL_TOKEN=" not in stub
    assert len(stub.splitlines()) <= 8


def test_agents_hygiene_and_gram() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Gram" in text or "GRAM" in text
    assert "INSTALL.md" in text
    assert "CONTRIBUTING.md" in text
    assert "TG_ADS_WRITE_GATE" in text
    assert "write_gated" in text
    assert "would_send" in text
    assert "access_denied" in text
    assert "Target invalid" in text
    assert "channels×langs" in text or "langs" in text
    assert "review-account" in text
    assert "## Reports / stats" in text
    assert "spend_scale" in text
    assert "spend_already_scaled" in text
    assert "values_already_scaled" in text
    assert "get_ad_stats_csv" in text
    assert "reports/" in text
    assert "## Future service / contracts" in text
    assert "telegram_ads_mcp/schemas/" in text
    assert "does **not** echo" not in text
    assert "confirm_hash" in text
    assert "manage_funds" in text
    assert "check_security.py" in text
    assert "Found a bug → Issue" in text
    assert "issues/new/choose" in text
    assert "offer" in text.lower()
    assert "F12" in text
    assert "Ctrl+Shift+I" in text
    assert "DevTools" in text
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
    assert '"gram"' in pyproject.split("[project]")[1].split("[project.optional")[0]


def test_server_json_discovery() -> None:
    import json

    data = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert data["name"] == "io.github.zai-one/telegram-ads-mcp"
    assert "ads.telegram.org" in data["description"]
    assert "Gram" in data["description"]
    assert len(data["description"]) <= 100
    assert "packages" not in data
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    import re
    from telegram_ads_mcp import __version__

    m = re.search(r'^version = "([^"]+)"', pyproject, re.M)
    assert m and m.group(1) == data["version"] == __version__


def test_mcp_json_example_has_no_secrets() -> None:
    example = ROOT / "mcp.json.example"
    assert example.is_file()
    text = example.read_text(encoding="utf-8")
    assert "telegram-ads-mcp" in text
    assert "STEL_" not in text
    assert "stel_token" not in text.lower()
    assert "mcpServers" in text
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    assert "mcp.json.example" in install


def test_contracts_ship_in_wheel() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "schemas/*.json" in pyproject
    schemas = ROOT / "telegram_ads_mcp" / "schemas"
    for name in (
        "campaign-brief.schema.json",
        "review-artifact.schema.json",
        "stats-dump.schema.json",
    ):
        assert (schemas / name).is_file(), name
    contrib = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "out of this repository" in contrib
    assert "telegram_ads_mcp/schemas/" in contrib
    backlog = (ROOT / "BACKLOG.md").read_text(encoding="utf-8")
    assert "Campaign-setup SaaS" in backlog

