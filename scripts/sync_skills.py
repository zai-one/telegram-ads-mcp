"""Regenerate skills/*/references/*.md from AGENTS.md sections (single source).

Usage: python scripts/sync_skills.py [--check]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from telegram_ads_mcp import guide  # noqa: E402

REFERENCES: dict[str, list[str]] = {
    "telegram-ads-launch-campaign": ["auth", "create", "write-gate", "danger"],
    "telegram-ads-review-account": ["stats", "fields"],
    "telegram-ads-diagnose-ad": ["stats", "danger", "errors"],
}

HEADER = "<!-- generated from AGENTS.md by scripts/sync_skills.py; do not edit -->\n\n"


def expected() -> dict[Path, str]:
    out: dict[Path, str] = {}
    for skill, topics in REFERENCES.items():
        for name in topics:
            body = guide.topic(name)
            if body is None:
                raise SystemExit(f"missing AGENTS.md section for topic {name}")
            out[ROOT / "skills" / skill / "references" / f"{name}.md"] = HEADER + body
    return out


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for path, text in expected().items():
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current != text:
            stale.append(path.relative_to(ROOT).as_posix())
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8", newline="\n")
    if check and stale:
        print("stale references:", ", ".join(stale))
        return 1
    print("ok" if not stale else "updated: " + ", ".join(stale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
