"""ZAI.ONE MCP standard: L0 token budget, skills spec, guide resources, packaging."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import telegram_ads_mcp.server as server_mod
from telegram_ads_mcp import guide
from telegram_ads_mcp.descriptions import TOOLS as DESCRIPTIONS

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("token_budget", ROOT / "scripts" / "token_budget.py")
token_budget = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["token_budget"] = token_budget
_spec.loader.exec_module(token_budget)

TOOLS = server_mod.mcp._tool_manager.list_tools()


def _manifest() -> dict:
    return {
        "instructions": server_mod.mcp.instructions,
        "tools": [
            {"name": t.name, "title": t.title, "description": t.description, "inputSchema": t.parameters}
            for t in TOOLS
        ],
    }


def test_budget_report_clean() -> None:
    report = token_budget.Report()
    token_budget.check_manifest(_manifest(), report)
    for skill in token_budget.find_skills(ROOT):
        token_budget.check_skill(skill, report)
    assert not report.errors, report.errors
    assert not report.warnings, report.warnings


def test_instructions_router_shape() -> None:
    text = server_mod.mcp.instructions
    assert len(text) <= 1200
    for needle in ("check_session", "confirm=true", "ads://guide/index", "retryable", "telegram-ads-launch-campaign"):
        assert needle in text, needle


def test_every_tool_has_title_and_template_description() -> None:
    names = {t.name for t in TOOLS}
    assert names == set(DESCRIPTIONS), names ^ set(DESCRIPTIONS)
    for tool in TOOLS:
        assert tool.title, tool.name
        assert len(tool.description) <= 300, tool.name
        assert len(token_budget.first_sentence(tool.description)) <= 120, tool.name
        assert tool.annotations is not None and tool.annotations.read_only_hint is not None, tool.name


def test_destructive_tools_are_marked() -> None:
    dest = {t.name for t in TOOLS if t.annotations and t.annotations.destructive_hint}
    assert {"delete_ad", "manage_funds", "log_out", "revoke_token"} <= dest


def test_guide_topics_resolve() -> None:
    for name in guide.TOPICS:
        body = guide.topic(name)
        assert body and body.startswith("## "), name
    assert guide.topic("nope") is None
    assert "ads://guide/errors" in guide.index()


def test_runtime_resources_use_packaged_playbook(tmp_path, monkeypatch) -> None:
    expected = (ROOT / "telegram_ads_mcp" / "PLAYBOOK.md").read_text(encoding="utf-8")
    # A client may start the server inside an unrelated repository.
    (tmp_path / "AGENTS.md").write_text("development instructions only", encoding="utf-8")
    (tmp_path / "PLAYBOOK.md").write_text("unrelated playbook", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert guide.playbook() == expected
    assert server_mod.playbook_resource() == expected
    assert server_mod.guide_index_resource() == guide.index()
    for name in guide.TOPICS:
        assert server_mod.guide_resource(name) == guide.topic(name)
    assert guide.index() in server_mod.guide_resource("unknown")


def test_missing_playbook_never_serves_development_instructions(tmp_path, monkeypatch) -> None:
    package = tmp_path / "telegram_ads_mcp"
    package.mkdir()
    (tmp_path / "AGENTS.md").write_text("root development instructions", encoding="utf-8")
    (package / "AGENTS.md").write_text("legacy package instructions", encoding="utf-8")
    monkeypatch.setattr(guide, "PLAYBOOK_PATH", package / "PLAYBOOK.md")
    assert guide.playbook() == "PLAYBOOK.md is missing from the install."
    assert server_mod.playbook_resource() == "PLAYBOOK.md is missing from the install."
    assert guide.topic("auth") is None


def test_skill_references_in_sync() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_skills.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_plugin_manifests() -> None:
    claude = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    cursor = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
    for manifest in (claude, cursor):
        assert manifest["name"] == "telegram-ads"
        assert "telegram-ads" in manifest["mcpServers"]
        assert (ROOT / manifest["skills"]).is_dir()
    for skill in ("telegram-ads-launch-campaign", "telegram-ads-review-account", "telegram-ads-diagnose-ad"):
        assert (ROOT / "skills" / skill / "SKILL.md").is_file()


def test_structured_error_fields() -> None:
    from telegram_ads_mcp.client import AuthError
    from telegram_ads_mcp.session import fail_payload

    payload = fail_payload(AuthError("dead"))
    assert payload["ok"] is False and payload["code"] == "auth"
    assert payload["retryable"] is False
    assert payload["hint"] and payload["docs"] == "ads://guide/errors#auth"


def test_compact_drops_empty() -> None:
    from telegram_ads_mcp.parse import compact

    assert compact({"a": None, "b": "", "c": [], "d": {"e": None}, "f": 0, "g": "x"}) == {"f": 0, "g": "x"}


def test_env_file_override(tmp_path, monkeypatch) -> None:
    from telegram_ads_mcp import session

    env = tmp_path / "ads.env"
    env.write_text("STEL_TOKEN=t-test\nSTEL_SSID=s-test\n", encoding="utf-8")
    # setenv first so monkeypatch records the prior state and undoes what load_env sets later;
    # a bare delenv(raising=False) on an absent key records nothing and the values would leak.
    for key in ("STEL_TOKEN", "STEL_SSID"):
        monkeypatch.setenv(key, "")
        monkeypatch.delenv(key)
    monkeypatch.setenv("TG_ADS_ENV_FILE", str(env))
    session.load_env()
    assert session.env_ready()


def test_skills_self_contained() -> None:
    for skill in (ROOT / "skills").iterdir():
        body = (skill / "SKILL.md").read_text(encoding="utf-8")
        assert "](../" not in body, skill.name
        assert (skill / "templates").is_dir() and (skill / "references").is_dir(), skill.name
