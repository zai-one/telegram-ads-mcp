"""Intent router for server instructions: each line -> first tool; skill; ads://guide/<topic>.

tests/test_routing_eval.py replays casual RU/EN requests against these lines and fails when any
tool, skill or guide topic is unreachable from the router, a skill or the playbook.
"""

from __future__ import annotations

from typing import NamedTuple


LIMIT = 1200  # instructions budget, also enforced by scripts/token_budget.py


class Route(NamedTuple):
    id: str
    intent: str
    tool: str
    skill: str
    topic: str


ROUTES: tuple[Route, ...] = (
    Route("launch", "запустить рекламу, новое, launch, new ad", "create_ad",
          "telegram-ads-launch-campaign", "create"),
    Route("review", "обзор, баланс, список, review, balance", "get_ads",
          "telegram-ads-review-account", "fields"),
    Route("diagnose", "почему не крутится, статистика, показы, stats, why", "get_ad_stats",
          "telegram-ads-diagnose-ad", "stats"),
    Route("targeting", "таргетинг, каналы, боты, аудитории, targeting", "search_targets",
          "telegram-ads-launch-campaign", "create"),
    Route("edit", "бюджет, ставка, cpm, пауза, edit, budget, pause", "edit_ad", "", "write-gate"),
    Route("cabinet", "кабинет, валюта, евро, звёзды, stars, eur, account", "get_account", "",
          "currency"),
    Route("auth", "сессия, куки, вход, session, cookies, login", "check_session", "", "auth"),
    Route("danger", "удалить, вывести деньги, delete, withdraw, token", "delete_ad", "", "danger"),
)  # fmt: skip

HEADER = (
    "telegram-ads MCP: cabinets TON (Gram), EUR, Stars (whole numbers). Start: check_session -> "
    "get_account (currency, money, write_gate). Never guess IDs."
)
FOOTER = (
    "Ads start on_hold; launch_ad spends. Spend/destructive: confirm=true only after the user says yes; "
    "never invent confirm_hash. Cookies only in .env. Retry only if retryable."
)


def router_lines() -> list[str]:
    lines = ["Intent -> first tool; skill; ads://guide/<topic>:"]
    for r in ROUTES:
        lines.append(f"- {r.intent}: " + "; ".join(p for p in (r.tool, r.skill, r.topic) if p))
    return lines


def instructions(extra: str = "") -> str:
    tail = "Unsure? ads://playbook (full text) or ads://guide/index (topics)."
    text = "\n".join([HEADER, *router_lines(), FOOTER, tail])
    if extra and len(text) + 1 + len(extra) <= LIMIT:
        text += f" {extra}"
    return text
