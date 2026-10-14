"""Which .env files load_env trusts, and for which keys.

The working directory is the user's project (uvx / plugin hosts start the server there), so
its .env may only supply STEL_* cookies. MCP_TRANSPORT / MCP_HOST / MCP_PORT and
TG_ADS_WRITE_GATE from it, or from any parent folder, must not reach the process.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from telegram_ads_mcp import gate, session

ROOT = Path(__file__).resolve().parents[1]

_KEYS = (
    "STEL_TOKEN",
    "STEL_SSID",
    "STEL_ADOWNER",
    "MCP_TRANSPORT",
    "MCP_HOST",
    "MCP_PORT",
    "TG_ADS_WRITE_GATE",
    "TG_ADS_ENV_FILE",
    "TG_ADS_LOG_LEVEL",
    "TG_ADS_STARS",
)

_HOSTILE = (
    "MCP_TRANSPORT=sse\n"
    "MCP_HOST=0.0.0.0\n"
    "MCP_PORT=6666\n"
    "TG_ADS_WRITE_GATE=open\n"
    "TG_ADS_LOG_LEVEL=DEBUG\n"
    "TG_ADS_STARS=on\n"
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    """Clean env for _KEYS (restored afterwards, even for keys load_env sets) and a fake
    package dir with no .env above it, so a developer's checkout .env cannot interfere."""
    for key in _KEYS:
        monkeypatch.setenv(key, "")
        monkeypatch.delenv(key)
    pkg = tmp_path / "site" / "telegram_ads_mcp"
    pkg.mkdir(parents=True)
    monkeypatch.setattr(session, "__file__", str(pkg / "session.py"))
    return tmp_path


def _project(root: Path, *, parent_env: str = "", cwd_env: str = "") -> Path:
    parent = root / "work"
    project = parent / "project"
    project.mkdir(parents=True)
    if parent_env:
        (parent / ".env").write_text(parent_env, encoding="utf-8")
    if cwd_env:
        (project / ".env").write_text(cwd_env, encoding="utf-8")
    return project


def test_cwd_env_supplies_cookies_only(isolated, monkeypatch) -> None:
    project = _project(isolated, cwd_env="STEL_TOKEN=t-cwd\nSTEL_SSID=s-cwd\nSTEL_ADOWNER=42\n" + _HOSTILE)
    monkeypatch.chdir(project)
    session.load_env()
    assert session.env_ready()
    assert os.environ["STEL_TOKEN"] == "t-cwd" and os.environ["STEL_ADOWNER"] == "42"
    for key in ("MCP_TRANSPORT", "MCP_HOST", "MCP_PORT", "TG_ADS_WRITE_GATE", "TG_ADS_LOG_LEVEL", "TG_ADS_STARS"):
        assert key not in os.environ, key
    assert gate.write_gate() == gate.DEFAULT != "open"
    from telegram_ads_mcp.client import stars_enabled

    assert not stars_enabled()  # a project .env cannot opt a cabinet into Stars spending


def test_parent_env_is_not_read(isolated, monkeypatch) -> None:
    project = _project(isolated, parent_env="STEL_TOKEN=t-parent\nSTEL_SSID=s-parent\n" + _HOSTILE)
    monkeypatch.chdir(project)
    session.load_env()
    for key in _KEYS:
        assert key not in os.environ, key
    assert not session.env_ready()


def test_reload_override_keeps_settings_out(isolated, monkeypatch) -> None:
    project = _project(isolated, cwd_env="STEL_TOKEN=t-new\nSTEL_SSID=s-new\n" + _HOSTILE)
    monkeypatch.chdir(project)
    monkeypatch.setenv("STEL_TOKEN", "t-old")
    monkeypatch.setenv("MCP_HOST", "127.0.0.1")
    monkeypatch.setenv("TG_ADS_WRITE_GATE", "strict")
    session.load_env(override=True)
    assert os.environ["STEL_TOKEN"] == "t-new"
    assert os.environ["MCP_HOST"] == "127.0.0.1"
    assert os.environ["TG_ADS_WRITE_GATE"] == "strict"


def test_explicit_env_file_is_trusted_in_full(isolated, monkeypatch) -> None:
    env = isolated / "ads.env"
    env.write_text("STEL_TOKEN=t-x\nSTEL_SSID=s-x\nTG_ADS_WRITE_GATE=strict\n", encoding="utf-8")
    project = _project(isolated, cwd_env="STEL_TOKEN=t-cwd\n" + _HOSTILE)
    monkeypatch.chdir(project)
    monkeypatch.setenv("TG_ADS_ENV_FILE", str(env))
    session.load_env()
    assert os.environ["STEL_TOKEN"] == "t-x"
    assert os.environ["TG_ADS_WRITE_GATE"] == "strict"
    assert "MCP_HOST" not in os.environ


def test_checkout_env_still_trusted(isolated, monkeypatch) -> None:
    checkout = Path(session.__file__).parent.parent
    (checkout / ".env").write_text("STEL_TOKEN=t-co\nSTEL_SSID=s-co\nTG_ADS_WRITE_GATE=strict\n", encoding="utf-8")
    project = _project(isolated, cwd_env="STEL_TOKEN=t-cwd\nSTEL_SSID=s-cwd\n" + _HOSTILE)
    monkeypatch.chdir(project)
    session.load_env()
    assert os.environ["STEL_TOKEN"] == "t-cwd"  # cwd wins for cookies
    assert os.environ["TG_ADS_WRITE_GATE"] == "strict"  # checkout settings still apply
    assert "MCP_HOST" not in os.environ


def test_server_import_ignores_hostile_project_env(tmp_path) -> None:
    """End to end: importing the server (load_env at import time) in a project with a hostile
    .env, and a hostile parent .env, leaves transport, bind address and gate untouched."""
    project = _project(tmp_path, parent_env=_HOSTILE, cwd_env="STEL_TOKEN=t-cwd\nSTEL_SSID=s-cwd\n" + _HOSTILE)
    env = {k: v for k, v in os.environ.items() if k not in _KEYS}
    env["TG_ADS_DISABLE_UPDATE_CHECK"] = "1"
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    code = (
        "import json, os\n"
        "import telegram_ads_mcp.server\n"
        "from telegram_ads_mcp.gate import write_gate\n"
        "keys = ('STEL_TOKEN', 'MCP_TRANSPORT', 'MCP_HOST', 'MCP_PORT', 'TG_ADS_WRITE_GATE')\n"
        "print(json.dumps({**{k: os.environ.get(k) for k in keys}, 'gate': write_gate()}))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=project, env=env, capture_output=True, text=True, timeout=60, check=True
    )
    seen = json.loads(out.stdout.strip().splitlines()[-1])
    assert seen["STEL_TOKEN"] == "t-cwd"
    assert seen["MCP_TRANSPORT"] != "sse"
    assert seen["MCP_HOST"] != "0.0.0.0"
    assert seen["MCP_PORT"] != "6666"
    assert seen["TG_ADS_WRITE_GATE"] != "open" and seen["gate"] != "open"
