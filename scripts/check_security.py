"""Local leak scan: cookies, .env, confirm hashes. Stdlib only. Never prints secret values.

  uv run python scripts/check_security.py
  uv run python scripts/check_security.py --issue draft.md
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "zai-one/telegram-ads-mcp"
FORM_URL = f"https://github.com/{REPO}/issues/new/choose"

_SECRET_ENV_KEYS = ("STEL_TOKEN", "STEL_SSID", "STEL_ADOWNER", "STEL_TON_TOKEN")
_MIN_INLINE = 16
_MIN_ENV_LEAK = 8

_IDENT_VALUES = {
    "stel_token",
    "stel_ssid",
    "stel_adowner",
    "confirm_hash",
    "api_hash",
    "token",
    "ssid",
}
_ISSUE_PLACEHOLDERS = {"", "...", "***", "redacted", "placeholder", "<token>"}
_PLACEHOLDERS = _ISSUE_PLACEHOLDERS | {
    "changeme",
    "your_token_here",
    "xxx",
    "dummy",
    "none",
    "null",
    "supersecret",
    "alsohash",
    "deadbeef",
}

_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pyc", ".zip", ".woff", ".woff2"}
_SKIP_DIR_PARTS = {
    ".git",
    ".venv",
    "previews",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".claude",
}

# Line-start env assignments (export KEY=value).
_ENV_ASSIGN_RE = re.compile(
    r"^(?:export\s+)?(" + "|".join(_SECRET_ENV_KEYS) + r")\s*=\s*(.*)$",
)
# Cookie / hash key=value or key: value. Value group must stay unnamed in messages.
_COOKIE_RE = re.compile(
    r"(?i)\b(stel_token|stel_ssid)\s*[=:]\s*([^\s&\"']+)",
)
_CONFIRM_RE = re.compile(
    r"(?i)\b(confirm_hash|api_hash)\s*[=:]\s*([^\s&\"']+)",
)
_QUERY_HASH_RE = re.compile(r"(?i)[?&]hash=([a-f0-9]+)")
_TOKEN_SHAPE_RE = re.compile(r"^[A-Za-z0-9_\-+/=.]{16,}$")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str


def _posix(rel: str) -> str:
    return rel.replace("\\", "/")


def _strip_value(raw: str) -> str:
    v = raw.strip().strip('"').strip("'").strip("`")
    if " #" in v:
        v = v.split(" #", 1)[0].strip()
    if v.endswith(",") or v.endswith(";"):
        v = v[:-1].rstrip()
    return v


def _is_placeholder(value: str) -> bool:
    v = value.strip()
    if len(v) >= 2 and v[0] == "{" and v[-1] == "}":
        return True
    return v.startswith("$")


def looks_like_secret(value: str) -> bool:
    v = _strip_value(value)
    if not v or v.lower() in _PLACEHOLDERS or _is_placeholder(v) or len(v) < _MIN_INLINE:
        return False
    return bool(_TOKEN_SHAPE_RE.match(v))


def _skip_rel(rel: str) -> bool:
    parts = _posix(rel).split("/")
    return any(p in _SKIP_DIR_PARTS for p in parts)


def forbidden_tracked_name(rel: str) -> bool:
    name = _posix(rel)
    base = name.split("/")[-1]
    if name == "VERIFY.md" or name.endswith("/VERIFY.md"):
        return True
    if name == ".env" or name.endswith("/.env"):
        return True
    if base.startswith(".env") and base != ".env.example":
        return True
    if name == "previews" or name.startswith("previews/"):
        return True
    return False


def _git_z(root: Path, extra: list[str]) -> list[str]:
    cmd = ["git", *extra, "-z"]
    try:
        out = subprocess.check_output(cmd, cwd=root, text=True, stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"git {' '.join(extra)} failed: {exc}") from exc
    return [p for p in out.split("\0") if p]


def parse_env_file(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return parsed
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        val = _strip_value(val)
        if key:
            parsed[key] = val
    return parsed


def _value_forbidden(value: str, *, issue: bool) -> bool:
    v = _strip_value(value)
    if not v:
        return False
    allowed = _ISSUE_PLACEHOLDERS if issue else _PLACEHOLDERS
    if v.lower() in allowed or v.lower() in _IDENT_VALUES or _is_placeholder(v):
        return False
    if issue:
        return True
    return looks_like_secret(v)


def scan_text(text: str, *, origin: str, mode: str) -> list[Finding]:
    """Return findings without secret values. mode is 'repo' or 'issue'."""
    found: list[Finding] = []
    issue = mode == "issue"
    for n, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        env_src = stripped.lstrip("#").strip() if issue else stripped
        env_m = _ENV_ASSIGN_RE.match(env_src)
        if env_m:
            val = _strip_value(env_m.group(2))
            allowed = _ISSUE_PLACEHOLDERS if issue else _PLACEHOLDERS
            skip_val = (
                not val
                or val.lower() in allowed
                or val.lower() in _IDENT_VALUES
                or _is_placeholder(val)
            )
            if not skip_val:
                found.append(Finding(origin, n, "stel_env"))
        for m in _COOKIE_RE.finditer(raw):
            if _value_forbidden(m.group(2), issue=issue):
                found.append(Finding(origin, n, "cookie_assignment"))
        for m in _CONFIRM_RE.finditer(raw):
            if _value_forbidden(m.group(2), issue=issue):
                rule = "confirm_hash" if m.group(1).lower() == "confirm_hash" else "api_hash"
                found.append(Finding(origin, n, rule))
        for m in _QUERY_HASH_RE.finditer(raw):
            hex_val = m.group(1)
            min_len = 8 if issue else _MIN_INLINE
            allowed = _ISSUE_PLACEHOLDERS if issue else _PLACEHOLDERS
            if len(hex_val) >= min_len and hex_val.lower() not in allowed:
                found.append(Finding(origin, n, "query_hash"))
    return found


def _read_text(path: Path) -> str | None:
    if path.suffix.lower() in _SKIP_SUFFIXES:
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) > 2_000_000 or b"\0" in data[:1024]:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def scan_repo(root: Path | None = None) -> list[Finding]:
    root = root or ROOT
    found: list[Finding] = []
    try:
        tracked = _git_z(root, ["ls-files"])
        others = _git_z(root, ["ls-files", "--others", "--exclude-standard"])
    except RuntimeError:
        found.append(Finding(".", 0, "git_failed"))
        return found

    for rel in tracked:
        if forbidden_tracked_name(rel):
            found.append(Finding(_posix(rel), 0, "tracked_forbidden"))

    seen: set[str] = set()
    texts: list[tuple[str, str]] = []
    for rel in [*tracked, *others]:
        if rel in seen or _skip_rel(rel):
            continue
        seen.add(rel)
        path = root / rel
        if not path.is_file():
            continue
        text = _read_text(path)
        if text is None:
            continue
        texts.append((_posix(rel), text))
        found.extend(scan_text(text, origin=_posix(rel), mode="repo"))

    env_path = root / ".env"
    if env_path.is_file():
        secrets = parse_env_file(env_path)
        for key in _SECRET_ENV_KEYS:
            val = secrets.get(key, "").strip()
            if len(val) < _MIN_ENV_LEAK:
                continue
            for rel, text in texts:
                if rel in {".env", ".env.example"}:
                    continue
                if val in text:
                    found.append(Finding(rel, 0, f"leaked_env:{key}"))
    return found


def scan_issue_path(path: Path) -> list[Finding]:
    name = path.name
    if name == ".env" or (name.startswith(".env") and name != ".env.example"):
        return [Finding(str(path), 0, "issue_env_file")]
    if name == "VERIFY.md":
        return [Finding(str(path), 0, "issue_verify_file")]
    text = _read_text(path)
    if text is None:
        return [Finding(str(path), 0, "unreadable")]
    return scan_text(text, origin=str(path), mode="issue")


def format_findings(findings: list[Finding]) -> str:
    lines = [f"check_security: {len(findings)} finding(s)"]
    for item in findings:
        loc = f"{item.path}:{item.line}" if item.line else item.path
        lines.append(f"  {loc}: {item.rule}")
    return "\n".join(lines)


def _cmd_quote(value: str) -> str:
    return '"' + value.replace('"', "'") + '"'


def issue_create_command(draft: Path, title: str) -> str:
    return (
        f"gh issue create --repo {REPO} --title {_cmd_quote(title)} "
        f"--body-file {_cmd_quote(str(draft))}"
    )


def _title_from_draft(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan for cookie / hash leaks. Never prints secret values.")
    parser.add_argument(
        "--issue",
        metavar="PATH",
        help="Scan a markdown draft; print gh issue create if clean (does not open).",
    )
    parser.add_argument("--title", help="Title for gh issue create (else first markdown heading).")
    args = parser.parse_args(argv)

    if args.issue:
        draft = Path(args.issue)
        if not draft.is_file():
            print(f"check_security: not a file: {draft}", file=sys.stderr)
            return 2
        findings = scan_issue_path(draft)
        if findings:
            print(format_findings(findings), file=sys.stderr)
            print("Refusing gh issue create. Redact cookies, .env, hashes, then retry.", file=sys.stderr)
            return 1
        title = (args.title or _title_from_draft(draft)).strip()
        if not title:
            title = "…"
        print("Draft looks clean. This does not open an Issue.")
        print(f"Prefer the form (secrets checklist): {FORM_URL}")
        print(issue_create_command(draft, title))
        return 0

    findings = scan_repo(ROOT)
    if findings:
        print(format_findings(findings), file=sys.stderr)
        return 1
    print("check_security: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
