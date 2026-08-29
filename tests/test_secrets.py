"""Fail the suite if session cookies or .env values land in git-tracked files.

Never interpolates secret values into assertion messages.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]

_SECRET_ENV_KEYS = ("STEL_TOKEN", "STEL_SSID", "STEL_ADOWNER", "STEL_TON_TOKEN")
_MIN_SECRET_LEN = 8


def _tracked_paths() -> list[Path]:
    out = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        text=True,
    )
    return [ROOT / p for p in out.split("\0") if p]


def test_env_file_is_not_tracked() -> None:
    tracked = {p.relative_to(ROOT).as_posix() for p in _tracked_paths()}
    assert ".env" not in tracked
    assert "VERIFY.md" not in tracked


def test_dotenv_example_has_no_cookie_values() -> None:
    example = ROOT / ".env.example"
    parsed = dotenv_values(example)
    for key in _SECRET_ENV_KEYS:
        val = (parsed.get(key) or "").strip()
        assert val == "", f".env.example must leave {key} empty"


def test_live_cookie_values_absent_from_tracked_files() -> None:
    """If a local .env exists, none of its cookie values appear in git files."""
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    secrets: list[tuple[str, str]] = []
    parsed = dotenv_values(env_path)
    for key in _SECRET_ENV_KEYS:
        val = (parsed.get(key) or "").strip().strip('"').strip("'")
        if len(val) >= _MIN_SECRET_LEN:
            secrets.append((key, val))
    if not secrets:
        return

    leaked: list[str] = []
    for path in _tracked_paths():
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for key, val in secrets:
            if val in text:
                leaked.append(f"{path.relative_to(ROOT).as_posix()} contains {key}")
    assert leaked == [], "tracked files must not contain .env cookie values: " + "; ".join(leaked)


def test_no_filled_stel_assignments_in_tracked_files() -> None:
    """Catch STEL_TOKEN=actualvalue in tracked files (empty assignment in .env.example is ok)."""
    bad: list[str] = []
    for path in _tracked_paths():
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            for key in _SECRET_ENV_KEYS:
                prefix = f"{key}="
                if stripped.startswith(prefix) or stripped.startswith(f"export {prefix}"):
                    raw = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                    if raw and raw not in {"...", "changeme", "your_token_here"}:
                        bad.append(f"{rel} has a non-empty {key} assignment")
    assert bad == [], "; ".join(bad)
