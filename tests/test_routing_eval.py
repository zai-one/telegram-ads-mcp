"""Routing eval: casual RU/EN requests -> router line -> first tool / skill / guide.

Each case must match exactly one router line by intent words (suffix-stripped RU/EN stems, stopwords dropped; ties fail, no match = out of scope); the expected tool
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
ALL_CASES = json.loads((ROOT / "tests/evals/routing_cases.json").read_text(encoding="utf-8"))
CASES = [c for c in ALL_CASES if c["route"]]
NEGATIVE = [c for c in ALL_CASES if not c["route"]]
WORD = re.compile(r"[a-zа-яё0-9]+")
ROUTER = instructions()
INTENTS = [(r.id, r.intent) for r in ROUTES]
SKILLS = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))


_RU_ENDINGS = (
    "ировать ировал ование ения ение ости ость ться ются ется ишь ить ать ять еть уть ывать ивать "
    "ами ями ого его ому ему ыми ими ией иям иях ях ах ов ев ей ой ий ый ая яя ое ее ые ие ую юю "
    "ом ем ам ям а я о е ы и у ю ь"
)
_EN_ENDINGS = "ization ations ation ings ing ies ied ers er ed es s ly"
_STOPWORDS = (
    "the and for with from into this that what how can you please my our me all any get show give "
    "make let need want just some about over then also are was its use using "
    "и в во на по с со к ко из за для от до как что это мне мой моя мои наш все всё ли не "
    "же бы или а но у о об при так ещё еще есть был была было надо нужно можно пожалуйста дай покажи "
    "сделай хочу"
)
RU_SUFFIXES = sorted(_RU_ENDINGS.split(), key=len, reverse=True)
EN_SUFFIXES = sorted(_EN_ENDINGS.split(), key=len, reverse=True)
STOP = set(_STOPWORDS.split())


def stem(word: str) -> str:
    word = word.replace("ё", "е")
    suffixes = RU_SUFFIXES if re.search("[а-я]", word) else EN_SUFFIXES
    for suffix in suffixes:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def stems(text: str) -> set[str]:
    return {stem(w) for w in WORD.findall(text.lower()) if len(w) >= 3 and w not in STOP}


def scores_for(request: str) -> dict[str, int]:
    words = stems(request)
    return {rid: len(stems(intent) & words) for rid, intent in INTENTS}


def route_id(request: str) -> str | None:
    scores = scores_for(request)
    ranked = sorted(scores.values(), reverse=True)
    if ranked[0] == 0:
        return None
    winners = [rid for rid, score in scores.items() if score == ranked[0]]
    assert len(winners) == 1, (request, winners)
    return winners[0]


def route_for(request: str):
    rid = route_id(request)
    assert rid, (request, "no route")
    return rid


def skill_text(name: str) -> str:
    if not name:
        return ""
    folder = ROOT / "skills" / name
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(folder.rglob("*.md")))


def tool_names() -> set[str]:
    return {t.name for t in asyncio.run(mcp.list_tools())}


def test_case_count_and_languages():
    routes = {rid for rid, _ in INTENTS}
    assert {c["route"] for c in CASES} == routes
    for rid in routes:  # every route needs at least two independent paraphrases
        assert sum(c["route"] == rid for c in CASES) >= 2, rid
    assert len(NEGATIVE) >= 3 and len(ALL_CASES) <= 60
    assert any(re.search("[а-я]", c["request"]) for c in CASES)
    assert any(not re.search("[а-я]", c["request"]) for c in CASES)


def test_paraphrases_are_not_router_copies():
    intents = dict(INTENTS)
    for case in CASES:
        assert stems(case["request"]) - stems(intents[case["route"]]), case["request"]


def test_every_route_has_a_distinctive_stem():
    for rid, intent in INTENTS:
        others = set().union(*(stems(i) for r, i in INTENTS if r != rid))
        assert stems(intent) - others, f"route {rid} has no stem of its own"


@pytest.mark.parametrize("case", NEGATIVE, ids=[c["request"][:40] for c in NEGATIVE])
def test_out_of_scope_requests_match_no_route(case):
    assert route_id(case["request"]) is None, (case["request"], scores_for(case["request"]))


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
