# AGENTS.md — Playbook for LLM Agents

You are connected to `telegram-ads-mcp` (ads.telegram.org). **Read this once per session** (MCP resource `ads://playbook`). Claude Code: this file is included from `CLAUDE.md`.

## Cabinet facts (live TON / Gram)

- **TON** cabinets bill in **Gram** (💎). `get_account` returns `cabinet: "ton"`, `currency: "GRAM"`, and a Gram `balance` string. This is **not** EUR. Do not tell the user they are on EUR because ads use `trg_type=user`.
- **User-geo exists on TON.** `target_type=users` / live field `trg_type: "user"` + countries/languages/topics from `get_targeting_reference(kind="user")`. The new-ad form includes `users` **and** channels/bots/search.
- **EUR** reseller cabinets are coded (`currency-euro`). Not live-tested here.
- **Stars** (`XTR`) is heuristic-only — maintainers have no Stars cabinet. Mutations return `code: "stars_cabinet"`. Switch with `list_accounts` / `select_account`.

## Auth (never paste cookies)

Cookies live only in gitignored `.env` (`STEL_TOKEN`, `STEL_SSID`, optional `STEL_ADOWNER`). **Never ask the user to paste cookies into chat, screenshots, or tool arguments.**

1. Start with `check_session`, then `get_account` (balance + currency + cabinet).
2. Dead session (`code: "auth"`): user refreshes cookies in the browser → `.env` → `reload_session`.
3. Do not call `log_out` / `revoke_token` unless the user explicitly asked.

Money and IDs are **strings**. Multi-IDs are **semicolon-separated**. Amounts are in **Gram** on TON (not “TON coins” and not EUR).

## Live list fields vs tool fields

`get_ads` / `getAd` fallback (`source: "getAdsList"`) uses platform names. The server maps them:

| Live field | Meaning | Tool field |
| --- | --- | --- |
| `trg_type: "user"` | user-geo | `target_type: "users"` |
| `tme_path` | `t.me/...` without host | `promote_url` |
| `status: "Active"` | delivering | `active: "1"` / filter `status="active"` |
| `status: "Stopped"` | budget depleted or off | treated as `on_hold` for filters |
| `spent` / `budget` / `cpm` | Gram | strings or numbers — compare as Gram |
| `views` / `clicks` / `actions` | delivery | stats also via `get_ad_stats` |

`get_ads(status="active"|"on_hold")` matches **Active/Stopped** and wire **1/0**. `getAd` JSON method may **400** — the tool falls back to the ad HTML then the list. Prefer `get_ad` anyway; check `source`.

`get_ad_stats` spend is scaled from chart units (Gram charts are ×1e6). `summary.spend` must be the same **order of magnitude** as list `spent` (e.g. 0.27 vs 0.54), never hundreds of thousands.

## Create / launch (always on_hold)

Do **not** auto-activate. Flow:

1. `get_account` — confirm Gram/TON, note balance.
2. `check_ad_post(promote_url, text)`.
3. Resolve targeting:
   - **users (TON geo):** `get_targeting_reference(kind="user")` → `countries` / `user_langs` / `user_topics` on `create_ad` / `launch_ad`.
   - **channels:** `search_targets(kind="channel")`, optional `similar_channels`.
   - **bots:** `search_targets(kind="bot", purpose="target")` for placement; `purpose="promote"` for destination. Bot needs ≥1000 daily users. Query a **username**, not the word “telegram”.
   - **search:** `target_type="search"`, `search_queries`. No text/picture/media.
4. `launch_ad(...)` (preferred) or `create_ad(..., active="on_hold")` → `edit_ad(..., budget_action="increase", budget_amount="N")` → `send_target_to_review`.
5. `preview_ad(ad_id)` — PNG in the tool result and under `previews/`.
6. After platform approval: `edit_ad(ad_id, active="active")` **only if the user asked to go live**.

`budget="0"` cannot go to review. `target_type` is immutable — `clone_ad` then edit.

## Pause / resume / budget (efficiency)

- Pause: `edit_ad(ad_id, active="on_hold")`.
- Resume: `edit_ad(ad_id, active="active")`.
- **Stopped** with remaining `daily_budget` but `budget` ~0: increase budget; platform often resumes **without** re-review.
- CPM is **Gram per 1000 impressions**. If CTR is healthy but spend is slow, raising CPM is the lever; if CTR is dead, pause and rewrite text/`check_ad_post` before burning budget.
- Daily cap: `edit_ad(..., daily_budget="N")`. `"0"` = unlimited.

## Monitoring (no extra tools — use reads)

At the start of a performance question:

1. `get_account` — Gram balance. If it does not match the UI, say so.
2. `get_ads(status="active")` and `get_ads(status="on_hold")` — split delivering vs stopped.
3. For each problem ad: `get_ad` + `get_ad_stats(period="5min")` (last 24h buckets) then `period="day"` for lifetime.
4. Watch `summary.ctr`, `cpc`, `cpm_actual` vs the ad’s bid `cpm`. If `cpm_actual` >> bid, delivery is inefficient; if views=0 and status Active, targeting or budget is blocked.
5. `preview_ad` before recommending copy changes.

Do **not** invent a bidding bot. Recommend one change at a time (pause xor CPM xor budget xor text). Confirm before any write.

## Audiences, events, funds

- `manage_audience` / `manage_event`: on some TON Gram cabinets `action="list"` returns **Access denied**. Report that; do not retry-loop. `audience_id` on create/edit is best-effort (unverified live).
- `manage_funds`: amount string in **Gram** (or EUR on EUR). Never assume TON coins.

## Destructive

`delete_ad`, `manage_funds`, `log_out`, `revoke_token` **run when called**. Explain the blast radius. Many deletes need `confirm_hash`: call once, then again with the hash. Do not strip `confirm_hash`.

## Gotchas

- Pagination: `get_ads` 100/page, `next_offset_id`.
- `code: "auth"` → stop, user updates `.env`, `reload_session`.
- `code: "stars_cabinet"` → switch account, do not retry mutations.
- `code: "config"` → missing `.env` cookies.
- Do not put `STEL_*` in MCP client `env` blocks unless unavoidable.
- Search ads: no text, picture, or media.
- `picture=false` / `clear_media` actually detach creatives (`picture=0`, `media=""`).
