# AGENTS.md — Playbook

MCP: `telegram-ads-mcp` (ads.telegram.org). Resource `ads://playbook`. No YAML frontmatter. Claude Code: `CLAUDE.md` has a bare `@AGENTS.md` line. Install/star: [INSTALL.md](INSTALL.md). Repo/CI: [CONTRIBUTING.md](CONTRIBUTING.md).

## Currency

ads.telegram.org cabinet is **TON**; billed in **Gram**. `get_account`: `cabinet: "ton"`, `currency: "GRAM"`. Say **Gram** or **TON** or **Gram (TON)** — all fine. EUR is another cabinet. Stars: `code: "stars_cabinet"` — switch, do not mutate.

## Auth

Cookies only in gitignored `.env` (`STEL_TOKEN`, `STEL_SSID`). Never paste into chat, Issues, or MCP `env`. First call: `check_session`. Dead session: human edits `.env` → `reload_session` (no cookie args). Do not `log_out` / `revoke_token` to “fix” auth — `revoke_token` is the IP-whitelist **API** token, not cookies.

Money and IDs are strings. Multi-IDs are semicolon-separated.

## Write gate (`.env`)

`TG_ADS_WRITE_GATE=strict|confirm|open` (default **confirm**). Echoed on `check_session` / `get_account` as `write_gate`.

| Gate | Without `confirm=true` | Needs `confirm=true` |
| --- | --- | --- |
| `strict` | reads + `reload_session` | every WRITE/DEST |
| `confirm` | reads + pause/CPM/create `on_hold` budget `0` + `list`/`search` on audience/event/funds | spend, review, activate, funds add/transfer/withdraw, delete, log_out, revoke, IP whitelist |
| `open` | all of the above | nothing extra (Stars still refused; cookies still `.env` only) |

Blocked call: `code: "write_gated"`. Show the operator, re-call with `confirm=true`.

Two jobs — do not mix unless they asked both: **cabinet** (`review-account`) vs **this git repo**.

## List fields

| Live | Tool |
| --- | --- |
| `trg_type: "user"` | `target_type: "users"` |
| `tme_path` | `promote_url` |
| `status: "Active"` | `active` / filter `status="active"` |
| `status: "Stopped"` | treat as `on_hold` |
| `spent` / `cpm` / `budget` | Gram on a TON cabinet |

`getAd` may HTTP 400 — `get_ad` falls back to HTML then the list. `get_ad_stats` spend is already scaled (charts ×1e6); match list `spent`. Do not divide again. `period=5min` = last 24h; `period=day` = lifetime.

## Create (always on_hold)

Prefer `launch_ad`. It does **not** activate. It **does** add budget (default `"1"` Gram) and `send_target_to_review`. Name cpm + budget + `target_type` first. If `steps.validate` fails, stop.

Search ads: no text/picture/media. IDs from `search_targets` / `get_targeting_reference` (semicolon IDs, not @names). `target_type` immutable — `clone_ad`. Pause: `edit_ad(active="on_hold")`. Go live: `edit_ad(active="active")` only if asked. Budget: `budget_action` + `budget_amount` (not `budget=`). Increasing budget on Stopped **resumes delivery** — spend class (`confirm`/`strict` need `confirm=true`).

## Danger

- Spend: `launch_ad`, `send_target_to_review`, `edit_ad(budget_action=…)` / activate.
- `manage_funds`: `list`/`search` = lookup. `add` = top-up *request*. `transfer`/`withdraw` **move money in that one call** — no platform `confirm_hash`. Never guess `account_id`.
- Platform `confirm_hash` (two HTTP steps): `delete_ad`, `clone_ad`, `manage_audience` delete|clone, `manage_event` delete. Call 1 without hash; call 2 with the returned hash after yes (`open` may do both). Do not invent or print hashes. Gate `confirm=` is a different flag.
- One-shot DEST (no hash): `manage_funds` add/transfer/withdraw, `log_out`, `revoke_token`, `save_api_settings`.
- `preview_ad` writes gitignored `previews/*.png` — do not commit.
- Access denied on audience/event: skip, do not retry. getAd 400: use fallback, do not probe JSON again.

## Autonomous (opt-in this turn)

Off unless they said to service the **cabinet** and/or **this repo**. One pass, ≤15 min. No overnight loop. **Never auto-push.**

- Cabinet default: prompt `review-account` (read-only). ≤5 problem ads, one recommendation, stop.
- Bounded write only if they asked this turn **and** the gate allows (or `confirm=true`): **one** `edit_ad` (pause xor CPM xor named budget), then verify.
- Repo: edit allowed paths if they asked; `uv run pytest -q`; leftover → chat, or one BACKLOG checkbox / one Issue (no cookies). Do not remix.

Never autonomous: funds move, delete, log_out, revoke, IP whitelist, activate, launch/create/review, Stars, cookie paste, committing `.env` / `VERIFY.md` / `previews/`.

## This repo

Tool count 12–28. After editing this file, copy to `telegram_ads_mcp/AGENTS.md`. No extra markdown/reports. No `.env` / `VERIFY.md` in git. Bilingual README + pytest/CI checklist: [CONTRIBUTING.md](CONTRIBUTING.md).
