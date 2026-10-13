---
name: telegram-ads-review-account
description: Read-only Telegram Ads cabinet review - balance, active vs stopped ads, up to 5 problem ads with stats, one recommendation. Use for "check my Telegram ads", "утренний обзор кабинета Telegram Ads".
license: LicenseRef-ZAI-ONE
compatibility: Needs the telegram-ads MCP server (zai-one/telegram-ads-mcp).
metadata:
  mcp-server: telegram-ads
  prompt: review-account
---

# Review a Telegram Ads cabinet (read-only)

Do not create, edit, or spend in this skill.

## Steps
1. `check_session`, then `get_account` (TON, `GRAM`, `write_gate`). Abort on Stars.
2. `get_ads(status="active")` and `get_ads(status="on_hold")`. Use list `spent`/`cpm`/`budget`; do not fetch stats for every ad.
3. Pick at most 5 problem ads: Active with 0 views, Stopped with leftover budget, CTR crash.
4. For each: `get_ad_stats(period="5min")`; `period="day"` for lifetime. `summary.spend` is already scaled - never divide. See [stats](references/stats.md).
5. `preview_ad` only if the copy may be the issue.
6. Report: cabinet, currency, gate, ≤5 problems, **one** recommendation. Stop and wait.

## Output
Short table: ad_id, status, spent, views, CTR, problem. Field meanings: [fields](references/fields.md).
Saving a dump: gitignored `reports/` only, allowlisted fields.

Fill [the report template](templates/review-report.md).
