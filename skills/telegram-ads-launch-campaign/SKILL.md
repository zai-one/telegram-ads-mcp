---
name: telegram-ads-launch-campaign
description: Create and submit a Telegram Ads ad (ads.telegram.org, TON/Gram) safely - resolve targets, validate the post, launch on_hold with budget, preview. Use for "launch/create a Telegram ad", "запустить рекламу в Telegram Ads".
license: LicenseRef-ZAI-ONE
compatibility: Needs the telegram-ads MCP server (zai-one/telegram-ads-mcp) with cookies in .env.
metadata:
  mcp-server: telegram-ads
  prompt: launch-campaign
---

# Launch a Telegram Ads campaign

Goal: one ad created **on_hold**, budget added, sent to review, preview shown. Never activate unless the user asks.

## Steps
1. `check_session`. If `ok=false` (`code` auth/config) follow `hint`; see [auth](references/auth.md). Never ask for cookies in chat.
2. `get_account`: TON cabinet, `currency=GRAM`, note `write_gate`. Stars → `list_accounts` → `select_account`.
3. Agree with the user: `target_type`, promote URL, text, CPM, budget (Gram strings).
4. Resolve IDs with `search_targets` / `get_targeting_reference`. Never guess IDs or use @names. See [create](references/create.md).
5. `check_ad_post(promote_url, text)`. Stop on platform error.
6. Show the brief (target, CPM, budget, gate). After an explicit yes: `launch_ad(..., confirm=true)`.
7. If a step in `steps` failed, stop and report it. Do not retry spend blindly.
8. `preview_ad` and show the PNG.

## Guardrails
- Spend/destructive rules and the gate: [write-gate](references/write-gate.md), [danger](references/danger.md).
- No `langs` with specific `channels`. Search ads: no text/picture/media.
- `code=write_gated`: show `would_send`, ask, re-call with `confirm=true`.

Full text: MCP resource `ads://playbook`; one topic: `ads://guide/{topic}`.

Brief format: [templates/campaign-brief.md](templates/campaign-brief.md).
