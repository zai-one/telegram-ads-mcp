# AGENTS.md — Playbook for LLM Agents

You are an agent connected to `tg-ads-mcp`, an MCP server that wraps the Telegram Ads backend. It supports both **TON cabinets** (direct ads.telegram.org accounts, TON-billed) and **EUR cabinets** (reseller accounts like Click Reklam, EUR-billed). A few features are EUR-only — see the "User-level targeting" section below.

Read this once at session start — it will save you many round-trips.

## Mental model

The platform's data model:

- **Account** (`owner_id`) — your ad cabinet. One session can have several; pick one with `select_account`.
- **Ad** — one creative + one targeting + one budget. Cannot change `target_type` after creation; clone instead.
- **Target type** — `channels` / `bots` / `search` / `users`. Determines required fields:
  - `channels`: needs `channels` (semicolon-separated IDs from `search_channel`). Optional `text`, `picture`, `media`.
  - `bots`: needs `bots` (IDs from `search_bot`). Bot must have **≥ 1000 daily users**. Optional `text`, `picture`.
  - `search`: needs `search_queries` (IDs from `search_target_query`). **No text, picture, or media** — search ads are CPM-only.
  - `users`: **EUR cabinet only.** Targets Telegram users by country / language / interest topic / subscribed channels / device via `create_user_ad`. TON cabinets don't render this type — see "User-level targeting" below.
- **Status** — `"1"` (active) / `"0"` (on hold) on the wire. Wrappers also accept `"active"` / `"on_hold"`.
- **Money** — currency depends on the cabinet: **TON** on TON cabinets, **EUR** on EUR (reseller) cabinets. Either way, budgets and CPMs are passed as strings (e.g. `"0.15"`, `"1"`), never numbers. Fund transfers (`transfer_funds` / `withdraw_funds` / `send_add_funds_request`) are TON-cabinet operations.

## Auth flow — always start here

```
check_session
```

- If `ok: true` → proceed.
- If `ok: false` → cookies expired. Ask the user for fresh ones, then call `update_cookies(stel_token, stel_ssid, stel_adowner=None)`. Don't try other tools first; they will all fail.

If the user has multiple cabinets and you're not sure which is active:

```
list_accounts → select_account(owner_id)
```

## Workflow: create a channel ad end-to-end

1. **Find target channels.** `search_channel(query="...")` returns candidates with IDs. Pick one or more.
2. **(Optional) Expand reach.** `get_similar_channels(channels="id1;id2")` for lookalikes.
3. **Create the ad on hold.**
   ```
   create_ad(
     title="internal name",
     promote_url="https://t.me/your_channel",
     cpm="0.15",
     target_type="channels",
     channels="id1;id2",
     text="ad copy ≤ 160 chars",
     daily_budget="1",
     active="on_hold",
   )
   ```
   Always create on hold first. Review the ad object that comes back.
4. **Add budget.** Ads with `budget="0"` cannot be sent to review. `edit_ad_budget(ad_id, amount="5", action="increase")`.
5. **Submit for review.** `send_target_to_review(ad_id)`.
6. **After approval, activate.** `edit_ad_status(ad_id, active="active")`.

## Workflow: create a channel-CATEGORY ad (EUR cabinet only)

Beyond targeting specific channel IDs, EUR cabinets let you place ads across a
whole **topic + language** slice — e.g. "all Russian-language Education
channels" — without listing channels by hand. TON cabinets do not expose
these filters; the example below will be rejected on TON.

1. **Confirm cabinet type.** `check_cabinet_type()` → expects `{"cabinet": "eur"}`.
2. **Pull channel-targeting reference.** `get_channel_targeting_reference()` returns:
   - `topics` — channel category IDs (Books, Education, Foreign Language Learning, …)
   - `languages` — channel content language codes (en, ru, ar, …)
   - `conversion_events` — optional conversion event IDs
3. **Create the ad on hold.**
   ```
   create_ad(
     title="...",
     promote_url="https://t.me/your_bot",
     cpm="1.00",
     target_type="channels",
     text="ad copy ≤ 160 chars",
     topics="13;19",                  # Education + Foreign Language Learning
     langs="ru",                      # Russian-language channels only
     exclude_topics="2;7",            # not in Gambling/Crypto channels
     daily_budget="1",
     active="on_hold",
   )
   ```
4. **Budget + review + activate** — same as the basic channel ad flow.

Notes:
- `topics` (channel-categorisation) shares the 41-entry taxonomy with
  `user_topics` (in `create_user_ad`) but the wire field name is different.
  `topics` filters by what CATEGORY the channel is in; `user_topics` filters
  by what the USER is interested in.
- Mixing `channels="id1;id2"` with `topics=...` is allowed — TG ANDs them
  (specific channels narrowed further by topic), but in practice if you
  already have channel IDs you don't need a topic filter.
- `langs` lives next to channel-category targeting; it is NOT the same as
  `user_langs` (which targets TG-interface language of the user).
- `conversion_event` and `button` (CTA text e.g. "OPEN WEBSITE",
  "JOIN CHANNEL") are EUR-only and work on any target_type.

## Workflow: create a bot ad

Same as channel ad, but:
- `target_type="bots"`, populate `bots=...` from `search_bot`.
- `promote_url` is a `t.me/your_bot` link.
- Verify the bot has ≥ 1000 daily users before suggesting it — search results show this.

## Workflow: create a search ad

```
search_target_query(query="vpn") → IDs
create_ad(
  title="...",
  promote_url="https://t.me/your_bot",
  cpm="0.20",
  target_type="search",
  search_queries="id1;id2",
  daily_budget="1",
  active="on_hold",
)
```

Do **not** pass `text`, `picture`, `media`, or `channels` — the platform will reject the ad.

## Workflow: create a user-targeted ad (EUR cabinet only)

User-level targeting reaches Telegram users matching demographic/interest criteria — independent of which channel the ad shows up in. **TON cabinets do not support this.** Call `check_cabinet_type` first if unsure.

1. **Confirm cabinet type.** `check_cabinet_type()` → expects `{"cabinet": "eur", "supports_user_targeting": true}`. If TON, the user-targeting tools refuse cleanly.
2. **Pull reference data.** `get_user_targeting_reference()` returns:
   - `countries` — list of `{val: ISO_code, name}` (~226 entries)
   - `languages` — list of `{val: lang_code, name}` (~71 entries)
   - `topics` — list of `{val: numeric_id, name}` (~41 interest categories)
   Use these `val` strings as semicolon-separated IDs.
3. **(Optional) Resolve cities.** `search_location(query="...")` for sub-country geo IDs.
4. **(Optional) Resolve channels for `user_channels` (must-be-subscribed) or `exclude_user_channels`.** `search_channel(query="...")` — max 100.
5. **Create the ad.**
   ```
   create_user_ad(
     title="...",
     promote_url="https://t.me/your_bot",
     cpm="2.00",                    # EUR floor is €1
     text="ad copy ≤ 160 chars",
     countries="US;GB;DE",
     user_langs="en",
     user_topics="13;19",           # Education, Foreign Language Learning
     intersect_topics=False,        # OR between topics; True = AND
     exclude_politic=True,
     budget="5",
     daily_budget="1",
     active="on_hold",
   )
   ```
6. **Add budget + submit + activate** — same flow as channel/bot/search ads.

Notes:
- All `*_topics` / `*_channels` params accept `"id1;id2;id3"` semicolon strings.
- `intersect_topics=True` requires the user to match ALL listed topics (AND); default OR.
- `exclude_politic` / `exclude_crypto` are policy-style placement guards (don't show in those categories). `only_politic` / `only_crypto` are the inverse — show ONLY in them.

## Workflow: read stats

`get_ad_stats(ad_id, period="5min" | "day")`

- `period="5min"` — 288 buckets covering the **last 24h**. Use for attribution: match `Started bot` timestamps with bot-side user-registration timestamps.
- `period="day"` — daily buckets covering the **full lifetime** of the ad. Use for trend analysis.

The response has:
- `summary` — quick totals (`views`, `clicks`, `started_bot`, `period`, `interval_seconds`)
- `charts.counts` — Views / Clicks / Started bot per bucket
- `charts.budget` — spend per bucket

When the user asks "how is ad X doing", call `get_ad_stats(ad_id, period="5min")` first — that's the highest-resolution view of recent performance. Only fall back to `period="day"` if they ask about long-term trends.

## Workflow: pause / resume

- Pause: `edit_ad_status(ad_id, active="on_hold")`
- Resume: `edit_ad_status(ad_id, active="active")`
- Stopped due to depleted budget: `edit_ad_budget(ad_id, amount="N", action="increase")` resumes the ad **without re-review**.

## Funds

- `send_add_funds_request` — top up the cabinet (returns a TON wallet payment instruction; the user pays from their wallet).
- `transfer_funds(account_id, amount)` — move TON between your own cabinets.
- `withdraw_funds(account_id, amount)` — move TON back out to your wallet.
- `search_account_for_transfer(query)` / `get_accounts_for_transfer()` — discovery.

## Gotchas — read before you act

- **Many destructive tools take a `confirm_hash`.** First call returns the hash; pass it back in a second call to actually delete. Tools: `delete_ad`, `clone_ad`, `delete_audience`, `clone_audience`, `delete_event`. Do not silently re-call without showing the user what will be deleted.
- **`target_type` is immutable.** Need different targeting? `clone_ad`, then edit the clone, then delete the original.
- **`budget="0"` blocks review.** A new ad with no budget will sit in "on hold" forever. Tell the user.
- **Cookies expire.** When any tool returns `{"ok": false, "error": "Session expired..."}` — stop, ask for fresh cookies, call `update_cookies`. Don't retry the failing call until that's done.
- **CPM and budget are strings, not numbers.** `cpm="0.15"`, not `cpm=0.15`.
- **`channels` / `bots` / `search_queries` are semicolon-separated**, not commas.
- **Search ads:** no `text`, no `picture`, no `media`. Don't pass them.
- **`get_ads_list` paginates** at 100 items. Use `next_offset_id` from the response for the next page.

## Failure handling

The wrappers return JSON strings. Parse them and check `ok` (or, for raw API responses, the absence of an `error` field). On auth failure, see the gotcha above. On validation failure, surface the platform's error message verbatim to the user — it's usually specific enough to act on.

## When in doubt

Read the tool's docstring (it shows up in your tool list) before guessing parameter values. If a parameter isn't in the docstring, it isn't supported by the wrapper — don't pass it.
