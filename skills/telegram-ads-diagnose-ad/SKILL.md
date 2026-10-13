---
name: telegram-ads-diagnose-ad
description: Diagnose one Telegram Ads ad - card, stats, preview, why it does not deliver (budget, status, moderation, CTR). Use for "why is my Telegram ad not showing", "почему объявление не крутится".
license: LicenseRef-ZAI-ONE
compatibility: Needs the telegram-ads MCP server (zai-one/telegram-ads-mcp).
metadata:
  mcp-server: telegram-ads
  prompt: diagnose-ad
---

# Diagnose one ad

Input: `ad_id` (ask if missing; or find it with `get_ads`).

## Steps
1. `get_ad(ad_id)`. HTTP 400 on getAd is handled by fallback; do not probe again.
2. `get_ad_stats(ad_id, period="5min")`; `period="day"` for lifetime. Write the period next to numbers. See [stats](references/stats.md).
3. `preview_ad(ad_id)` and show the PNG.
4. Explain views/clicks/CTR/spend and what blocks delivery: status (Stopped = on_hold), budget, review, targeting.
5. Propose one fix. Writes (pause, CPM, budget) only after a yes; budget increase resumes delivery and is spend-class. See [danger](references/danger.md).

Error codes and what to do: [errors](references/errors.md).

Report format: [templates/diagnosis.md](templates/diagnosis.md).
