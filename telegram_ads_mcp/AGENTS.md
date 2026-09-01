# AGENTS.md — Playbook

MCP: `telegram-ads-mcp` (ads.telegram.org). Resource `ads://playbook`. No YAML frontmatter. Claude Code: `CLAUDE.md` has a bare `@AGENTS.md` line. Install/star: [INSTALL.md](INSTALL.md). Repo/CI: [CONTRIBUTING.md](CONTRIBUTING.md).

## Currency

ads.telegram.org cabinet is **TON**; billed in **Gram**. `get_account`: `cabinet: "ton"`, `currency: "GRAM"`. Say **Gram** or **TON** or **Gram (TON)** — all fine. EUR is another cabinet. Stars: `code: "stars_cabinet"` — switch, do not mutate.

## Auth

Cookies only in gitignored `.env` (`STEL_TOKEN`, `STEL_SSID`). Never paste into chat, Issues, MCP `env`, or tool args. First call: `check_session`. Dead session: **offer** the INSTALL.md DevTools steps (do not ask them to paste values into chat). Chrome/Edge Windows: stay logged in at https://ads.telegram.org → **F12** or **Ctrl+Shift+I** → **Application** (Edge: **Storage**) → Cookies → `https://ads.telegram.org` → copy `stel_token` / `stel_ssid` **into `.env` only**. Not Network headers, not telegram.org / web.telegram.org. Last resort is not a browser/CDP cookie dump into the transcript: the operator (or an agent that can write the gitignored file **without echoing contents**) updates `.env`, then `reload_session` → `check_session` (no cookie args). Never `log_out` / `revoke_token` to “fix” auth — `revoke_token` is the IP-whitelist **API** token, not cookies. Do not file an Issue to “fix” a dead session. DevTools dumps still forbidden in Issues.

Money and IDs are strings. Multi-IDs are semicolon-separated.

## Write gate (`.env`)

`TG_ADS_WRITE_GATE=strict|confirm|open` (default **confirm**). Echoed on `check_session` / `get_account` as `write_gate`.

| Gate | Without `confirm=true` | Needs `confirm=true` |
| --- | --- | --- |
| `strict` | reads + `reload_session` | every WRITE/DEST |
| `confirm` | reads + pause/CPM/create `on_hold` budget `0` + `list`/`search` on audience/event/funds | spend, review, activate, funds add/transfer/withdraw, delete, log_out, revoke, IP whitelist |
| `open` | all of the above | nothing extra (Stars still refused; cookies still `.env` only) |

Blocked call: `code: "write_gated"` with `tool`, `class`, `would_send` (intended args, no secrets), `sent: false`. Not a platform dry-run. Show the operator, re-call with `confirm=true`.

Two jobs — do not mix unless they asked both: **cabinet** (`review-account`) vs **this git repo**.

## Found a bug → Issue

Issues are for **MCP clients** (this playbook), not only people hacking the git repo.

- **Cabinet** (dead session, targeting, spend): stay on tools. Human edits `.env` → `reload_session`. Never an Issue to “fix” auth.
- **MCP / playbook / durable platform quirk** (tool error, playbook lie, unexpected API): **offer** an Issue. Do not open one unasked.

If they say yes — one problem. Include: tool name, ads.telegram.org method, expected vs actual, pytest notes if any. Numeric ad ids OK. Forbidden: cookies, `.env`, `STEL_TOKEN` / `STEL_SSID`, `confirm_hash`, API `hash=`, DevTools, cookie-shaped account IDs. Redact hashes `***`. Do not invent or print hashes.

How: form https://github.com/zai-one/telegram-ads-mcp/issues/new/choose — or a markdown draft + `uv run python scripts/check_security.py --issue draft.md` (prints `gh issue create`; does not open). Show that command. Run `gh` only after they confirmed. A tool/playbook ticket is the repo job; still no cookies. Do not mix with a cabinet pass unless they asked both.

## List fields

| Live | Tool |
| --- | --- |
| `trg_type: "user"` | `target_type: "users"` |
| `tme_path` | `promote_url` |
| `status: "Active"` | `active` / filter `status="active"` |
| `status: "Stopped"` | treat as `on_hold` |
| `spent` / `cpm` / `budget` | Gram on a TON cabinet |

`getAd` may HTTP 400 — `get_ad` falls back to HTML then the list. `get_ad_stats` spend and `charts.budget` are already scaled; match list `spent`. Do not divide again. `period=5min` = last 24h; `period=day` = lifetime.

## Reports / stats

No CSV / export tool (`get_ad_stats_csv` does not exist). A dump is tool JSON: `get_account` + `get_ads`/`get_ad` + `get_ad_stats`. Cabinet job — interpret in chat; do not mix with this git repo.

- Currency: `get_account` → `cabinet: "ton"`, `currency: "GRAM"`. List `spent`/`cpm`/`budget` and `summary.spend` are Gram. IDs and money stay strings.
- Request `period=5min` (default) = last 24h, 5-minute buckets (`interval_seconds` 300). `period=day` = lifetime daily. Success JSON echoes `period` (`5min`/`day`). `summary.period` is a span label (`24h` / `Nd`), not the request arg. Write `period` next to every dump. Do not mix 24h with lifetime.
- `summary.spend` is already scaled (`spend_already_scaled: true`; `spend_scale` usually `1000000` on Gram). Same order of magnitude as list `spent`. **Do not divide again.** `charts.budget` series/totals are scaled the same way (`values_already_scaled: true`) — prefer `summary.spend`; do not treat chart totals as a second unscaled Gram figure. Views/clicks/CTR/CPC/`cpm_actual` live on `summary`.
- `status: "Stopped"` = `on_hold`, not deleted. Leftover `daily_budget` can still resume delivery if budget is increased (spend class).
- Save vs chat: chat JSON is enough. If you write a file, gitignored `reports/` (same rule as `previews/`; optional `reports/<ad_id>-<period>.json`). Allowlist: `ad_id`, request `period`, `summary` (spend, spend_already_scaled, spend_scale, views, clicks, ctr, cpc, cpm_actual), list `spent`/`cpm`/`budget`/`active`. No cookies, `.env`, hashes, DevTools, full `charts`. Schema: `telegram_ads_mcp/schemas/stats-dump.schema.json`.
- Read-only pass: prompt `review-account` — ≤5 problem ads, one recommendation, stop. `diagnose-ad` = one ad (`get_ad` + `get_ad_stats(period=5min)` + `preview_ad`; `period=day` for lifetime). If the dump contradicts this playbook (scale, period, getAd 400), **offer** an Issue (Found a bug → Issue).

## Create (always on_hold)

Prefer `launch_ad`. It does **not** activate. It **does** add budget (default `"1"` Gram) and `send_target_to_review`. Name cpm + budget + `target_type` first. If `steps.validate` fails, stop. Optional targeting on `launch_ad`: `topics`, `exclude_topics` / `exclude_channels`, `locations`, user excludes. Do **not** send `langs` together with specific `channels` (platform Target invalid) — the tool drops `langs` in that case. Full field set remains on `create_ad`.

Search ads: no text/picture/media. IDs from `search_targets` / `get_targeting_reference` (semicolon IDs, not @names). `target_type` immutable — `clone_ad`. Pause: `edit_ad(active="on_hold")`. Go live: `edit_ad(active="active")` only if asked. Budget: `budget_action` + `budget_amount` (not `budget=`). Increasing budget on Stopped **resumes delivery** — spend class (`confirm`/`strict` need `confirm=true`).

## Danger

- Spend: `launch_ad`, `send_target_to_review`, `edit_ad(budget_action=…)` / activate.
- `manage_funds`: `list`/`search` = lookup. `add` = top-up *request*. `transfer`/`withdraw` **move money in that one call** — no platform `confirm_hash`. Never guess `account_id`.
- Platform `confirm_hash` (two HTTP steps): `delete_ad`, `clone_ad`, `manage_audience` delete|clone, `manage_event` delete. Call 1 without hash; call 2 with the returned hash after yes (`open` may do both). Do not invent or print hashes. Gate `confirm=` is a different flag.
- One-shot DEST (no hash): `manage_funds` add/transfer/withdraw, `log_out`, `revoke_token`, `save_api_settings`.
- `preview_ad` writes gitignored `previews/*.png` — do not commit.
- Access denied on audience/event: tool returns `code: "access_denied"`, `hint: "skip"`. Do not retry. getAd 400: use fallback, do not probe JSON again.

## Autonomous (opt-in this turn)

Off unless they said to service the **cabinet** and/or **this repo**. One pass, ≤15 min. No overnight loop. **Never auto-push.**

- Cabinet default: prompt `review-account` (read-only). ≤5 problem ads, one recommendation, stop.
- Bounded write only if they asked this turn **and** the gate allows (or `confirm=true`): **one** `edit_ad` (pause xor CPM xor named budget), then verify.
- Repo: edit allowed paths if they asked; `uv run pytest -q`; leftover → chat, or **offer** an Issue (Found a bug → Issue). Do not remix.

Never autonomous: funds move, delete, log_out, revoke, IP whitelist, activate, launch/create/review, Stars, cookie paste, committing `.env` / `VERIFY.md` / `previews/` / `reports/`.

## Future service / contracts

This MCP is not a campaign SaaS. Wheel JSON Schema (`telegram_ads_mcp/schemas/`) is the durable names a later HTTP/job service can ingest — no extra export tool:

| Artifact | Schema | Produced by |
| --- | --- | --- |
| Campaign brief | `campaign-brief.schema.json` | maps 1:1 to `launch_ad` (short targeting subset) or `create_ad` (full targeting). Always `on_hold`. Do not send `langs` with specific `channels`. |
| Review artifact | `review-artifact.schema.json` | prompt `review-account`: cabinet, currency, write_gate, ≤5 problems, one recommendation. |
| Stats dump | `stats-dump.schema.json` | `get_ad_stats` allowlist (echoed `period`, already-scaled spend). |

Call chain a service would replay: `check_session` → `search_targets` → `launch_ad` → `get_ad_stats`. Stay human: `confirm=true` spend, activate, funds. Do not absorb Telethon, Playwright login, or `raw_api`. Stars refuse. IDs and money stay strings in briefs/reviews.

## This repo

Tool count 12–28. After editing this file, copy to `telegram_ads_mcp/AGENTS.md`. No extra markdown/reports. No `.env` / `VERIFY.md` in git. Bilingual README + pytest/CI checklist: [CONTRIBUTING.md](CONTRIBUTING.md).
