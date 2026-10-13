<!-- generated from AGENTS.md by scripts/sync_skills.py; do not edit -->

## Reports / stats

No CSV / export tool (`get_ad_stats_csv` does not exist). A dump is tool JSON: `get_account` + `get_ads`/`get_ad` + `get_ad_stats`. Cabinet job — interpret in chat; do not mix with this git repo.

- Currency: `get_account` → `cabinet: "ton"`, `currency: "GRAM"`. List `spent`/`cpm`/`budget` and `summary.spend` are Gram. IDs and money stay strings.
- Request `period=5min` (default) = last 24h, 5-minute buckets (`interval_seconds` 300). `period=day` = lifetime daily. Success JSON echoes `period` (`5min`/`day`). `summary.period` is a span label (`24h` / `Nd`), not the request arg. Write `period` next to every dump. Do not mix 24h with lifetime.
- `summary.spend` is already scaled (`spend_already_scaled: true`; `spend_scale` usually `1000000` on Gram). Same order of magnitude as list `spent`. **Do not divide again.** `charts.budget` series/totals are scaled the same way (`values_already_scaled: true`) — prefer `summary.spend`; do not treat chart totals as a second unscaled Gram figure. Views/clicks/CTR/CPC/`cpm_actual` live on `summary`.
- `status: "Stopped"` = `on_hold`, not deleted. Leftover `daily_budget` can still resume delivery if budget is increased (spend class).
- Save vs chat: chat JSON is enough. If you write a file, gitignored `reports/` (same rule as `previews/`; optional `reports/<ad_id>-<period>.json`). Allowlist: `ad_id`, request `period`, `summary` (spend, spend_already_scaled, spend_scale, views, clicks, ctr, cpc, cpm_actual), list `spent`/`cpm`/`budget`/`active`. No cookies, `.env`, hashes, DevTools, full `charts`. Schema: `telegram_ads_mcp/schemas/stats-dump.schema.json`.
- Read-only pass: prompt `review-account` — ≤5 problem ads, one recommendation, stop. `diagnose-ad` = one ad (`get_ad` + `get_ad_stats(period=5min)` + `preview_ad`; `period=day` for lifetime). If the dump contradicts this playbook (scale, period, getAd 400), **offer** an Issue (Found a bug → Issue).

`get_ad_stats(detail="csv")` returns a `csv` string (time + every chart series) for export.
