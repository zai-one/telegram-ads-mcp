"""Progressive disclosure: split PLAYBOOK.md into topic guides.

One source of truth: packaged PLAYBOOK.md. ``ads://guide/{topic}`` serves one section;
``skills/*/references/*.md`` are generated copies (``scripts/sync_skills.py``),
kept in sync by ``tests/test_token_budget.py``.
"""

from __future__ import annotations

from pathlib import Path

PLAYBOOK_PATH = Path(__file__).resolve().parent / "PLAYBOOK.md"

# topic -> heading prefix in PLAYBOOK.md
TOPICS: dict[str, str] = {
    "currency": "Currency",
    "auth": "Auth",
    "write-gate": "Write gate",
    "errors": "Errors",
    "updates": "Updates",
    "issues": "Found a bug",
    "fields": "List fields",
    "stats": "Reports / stats",
    "create": "Create",
    "danger": "Danger",
    "autonomous": "Autonomous",
    "contracts": "Future service",
}


def playbook() -> str:
    if PLAYBOOK_PATH.is_file():
        return PLAYBOOK_PATH.read_text(encoding="utf-8")
    return "PLAYBOOK.md is missing from the install."


def sections(text: str | None = None) -> dict[str, str]:
    text = playbook() if text is None else text
    out: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                out[current] = "\n".join(lines).strip() + "\n"
            current, lines = line[3:].strip(), [line]
        elif current:
            lines.append(line)
    if current:
        out[current] = "\n".join(lines).strip() + "\n"
    return out


def topic(name: str) -> str | None:
    prefix = TOPICS.get(name)
    if prefix is None:
        return None
    for heading, body in sections().items():
        if heading.startswith(prefix):
            return body
    return None


def index() -> str:
    rows = [f"- `ads://guide/{name}` — {prefix}" for name, prefix in TOPICS.items()]
    return "# Telegram Ads guides\n\nRead only the topic you need.\n\n" + "\n".join(rows) + "\n"
