"""Routing eval: casual RU/EN requests -> router line -> first tool / skill / guide.

Each case must match exactly one router line by intent words (4-char stems); the expected tool
must be reachable from that line (named on it, in its skill, or in its guide topic). The suite also
fails when any tool, skill or guide topic is unreachable from the router or the playbook fallback.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest

from telegram_ads_mcp import guide
from telegram_ads_mcp.router import ROUTES, instructions
from telegram_ads_mcp.server import mcp

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests/evals/routing_cases.json").read_text(encoding="utf-8"))
WORD = re.compile(r"[a-zа-яё0-9]+")
ROUTER = instructions()
SKILLS = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))


def stems(text: str) -> set[str]:
    return {w[:4] for w in WORD.findall(text.lower().replace("ё", "е")) if len(w) >= 3}


def route_for(request: str) -> str:
    words = stems(request)
    scores = {r.id: len(stems(r.intent) & words) for r in ROUTES}
    best = max(scores.values())
    winners = [rid for rid, score in scores.items() if score == best and score > 0]
    assert len(winners) == 1, (request, winners or "no route")
    return winners[0]


def skill_text(name: str) -> str:
    if not name:
        return ""
    folder = ROOT / "skills" / name
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(folder.rglob("*.md")))


def tool_names() -> set[str]:
    return {t.name for t in asyncio.run(mcp.list_tools())}


def test_case_count_and_languages():
    assert 15 <= len(CASES) <= 25
    assert any(re.search("[а-я]", c["request"]) for c in CASES)
    assert any(not re.search("[а-я]", c["request"]) for c in CASES)


@pytest.mark.parametrize("case", CASES, ids=[c["request"][:40] for c in CASES])
def test_request_routes_to_tool_skill_and_guide(case):
    rid = route_for(case["request"])
    assert rid == case["route"]
    route = next(r for r in ROUTES if r.id == rid)
    line = next(ln for ln in ROUTER.splitlines() if ln.startswith(f"- {route.intent}:"))
    for part in (route.tool, route.skill, route.topic):
        assert not part or part in line
    if route.skill:
        assert route.skill in SKILLS
    body = guide.topic(route.topic)
    assert body, route.topic
    reachable = " ".join((line, skill_text(route.skill), body))
    assert case["tool"] in reachable, (case["tool"], rid)


def test_every_tool_reachable_and_router_tools_exist():
    tools = tool_names()
    for r in ROUTES:
        assert r.tool in tools, r.tool
    playbook = guide.playbook()
    corpus = " ".join([ROUTER, playbook, *(skill_text(s) for s in SKILLS)])
    missing = sorted(t for t in tools if not re.search(rf"\b{t}\b", corpus))
    assert not missing, missing


def test_every_skill_and_topic_reachable():
    for skill in SKILLS:
        assert skill in ROUTER, skill
    routed = {r.topic for r in ROUTES}
    index = guide.index()
    for name in guide.TOPICS:
        assert guide.topic(name), name
        assert name in routed or f"ads://guide/{name}" in index
    assert "ads://playbook" in ROUTER and "ads://guide/index" in ROUTER
    assert len(ROUTER) <= 1200
