"""scripts/check_security.py: catch fake tokens, allow .env.example, never print values."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_security.py"

sys.path.insert(0, str(ROOT / "scripts"))
import check_security  # noqa: E402


def _token(n: int = 24) -> str:
    return "A" * n


def test_env_example_allowed() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert check_security.scan_text(text, origin=".env.example", mode="repo") == []
    assert not check_security.forbidden_tracked_name(".env.example")
    assert check_security.forbidden_tracked_name(".env")
    assert check_security.forbidden_tracked_name(".env.local")
    assert check_security.forbidden_tracked_name("VERIFY.md")
    assert check_security.forbidden_tracked_name("previews/x.png")


def test_catches_filled_stel_assignment_without_printing_value() -> None:
    token = _token()
    findings = check_security.scan_text(
        f"STEL_TOKEN={token}\n",
        origin="mem",
        mode="repo",
    )
    assert findings
    assert findings[0].rule == "stel_env"
    msg = check_security.format_findings(findings)
    assert token not in msg
    assert "stel_env" in msg


def test_repo_allows_short_test_fakes() -> None:
    raw = "stel_token=supersecret stel_ssid=alsohash api_hash=deadbeef ?hash=abcdef123456"
    assert check_security.scan_text(raw, origin="mem", mode="repo") == []


def test_issue_mode_refuses_cookie_and_query_hash() -> None:
    token = _token()
    blob = "ab" * 6
    cookie = check_security.scan_text(f"stel_token={token}\n", origin="draft", mode="issue")
    assert any(f.rule == "cookie_assignment" for f in cookie)
    hashed = check_security.scan_text(f"see /api?hash={blob}\n", origin="draft", mode="issue")
    assert any(f.rule == "query_hash" for f in hashed)
    confirm = check_security.scan_text(f"confirm_hash={_token(32)}\n", origin="draft", mode="issue")
    assert any(f.rule == "confirm_hash" for f in confirm)


def test_issue_allows_redacted_placeholder() -> None:
    text = "stel_token=*** confirm_hash=redacted\n"
    assert check_security.scan_text(text, origin="draft", mode="issue") == []


def test_cli_repo_scan_passes() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "ok" in proc.stdout


def test_cli_issue_refuses_and_does_not_print_secret(tmp_path: Path) -> None:
    token = _token()
    draft = tmp_path / "draft.md"
    draft.write_text(f"# Bug\n\nstel_token={token}\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--issue", str(draft)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert token not in proc.stdout
    assert token not in proc.stderr
    assert "gh issue create" not in proc.stdout


def test_cli_issue_prints_gh_when_clean(tmp_path: Path) -> None:
    draft = tmp_path / "draft.md"
    draft.write_text("# getAd HTTP 400\n\nget_ad falls back to HTML. No cookies.\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--issue", str(draft)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "does not open" in proc.stdout.lower() or "not open" in proc.stdout.lower()
    assert "gh issue create" in proc.stdout
    assert "--body-file" in proc.stdout
    assert "issues/new/choose" in proc.stdout
