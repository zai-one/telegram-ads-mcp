# AGENTS.md — Playbook for LLM Agents

You are connected to `tg-ads-mcp`, wrapping ads.telegram.org.

- **TON** cabinets (direct, TON-billed) are the primary target.
- **EUR** cabinets (reseller) work, including `target_type=users`.
- **Stars** cabinets are refused. If `check_session` / `get_account` returns `cabinet: "stars"`, call `list_accounts` and `select_account` onto a TON or EUR cabinet. Do not try to create ads on Stars.

Read this (or the `ads://playbook` resource) once per session.

## Auth

Cookies live in the user's `.env` (`STEL_TOKEN`, `STEL_SSID`). **Never ask them to paste cookies into chat.** If the session is dead:

1. Tell them to refresh cookies in the browser, put them in `.env`.
2. Call `reload_session`.

Always start with `check_session`. Then `get_account` for balance + currency.

Status on the wire is `"1"` (active) / `"0"` (on_hold). Wrappers accept `"active"` / `"on_hold"`. Money and IDs are **strings**. Multi-IDs are **semicolon-separated**.

## Create a channel ad

1. `search_targets(kind="channel", query="...")`
2. Optional `search_targets(kind="similar_channels", ids="id1;id2")`
3. `launch_ad(...)` — creates on_hold, adds budget, sends to review. Do not auto-activate.
   Or, by hand: `check_ad_post` → `create_ad(..., active="on_hold")` → `edit_ad(..., budget_action="increase", budget_amount="5")` → `send_target_to_review`.
4. `preview_ad(ad_id)` — PNG is attached; also saved under `previews/`.
5. After approval: `edit_ad(ad_id, active="active")`.

Search ads: `target_type="search"`, `search_queries="..."`. Do **not** pass text/picture/media.

Bot ads: `target_type="bots"`, IDs from `search_targets(kind="bot", purpose="target")`. Destination lookup uses `purpose="promote"`. Bot needs ≥1000 daily users.

EUR user targeting: `target_type="users"` + `get_targeting_reference(kind="user")`. TON will refuse this type.

## Stats

`get_ad_stats(ad_id, period="5min"|"day")`. Summary includes views, clicks, started_bot, spend, ctr, cpc, cpm_actual.

## Pause / resume

- Pause: `edit_ad(ad_id, active="on_hold")`
- Resume: `edit_ad(ad_id, active="active")`
- Depleted budget: `edit_ad(ad_id, budget_action="increase", budget_amount="N")` resumes without re-review.

## Audiences and events

`manage_audience(action="list"|"create"|...)`. Create with `user_ids=[...]` (preferred) or `file_path`.
`manage_event(action="list"|"create"|...)`.
Pass `audience_id` into `create_ad` / `edit_ad` when the platform accepts it.

## Funds

`manage_funds(action="add"|"transfer"|"withdraw"|"search"|"list")`. Amount is a string in the **cabinet currency** (TON or EUR), never hardcoded as TON.

## Gotchas

- Destructive tools (`delete_ad`, `manage_funds`, `log_out`, `revoke_token`) still run when called. Show the user what will happen; many deletes need `confirm_hash` (call once, then again with the hash).
- `target_type` is immutable. Clone then edit.
- `budget="0"` blocks review.
- `get_ads` paginates at 100. Use `next_offset_id`.
- If any tool returns `code: "auth"`, stop and `reload_session` after the user updates `.env`.
- If `code: "stars_cabinet"`, switch account. Do not retry the same cabinet.
