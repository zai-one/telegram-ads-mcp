# CLAUDE.md

This repository is **telegram-ads-mcp**, an MCP server for ads.telegram.org.

**Always read [AGENTS.md](./AGENTS.md) before using or changing tools** (same text as MCP resource `ads://playbook`). Include it in Claude sessions with `@AGENTS.md` if the client does not load this file automatically.

Rules that override improvisation:

- Cookies only in gitignored `.env` (`STEL_TOKEN`, `STEL_SSID`). Never paste them into chat, commits, or tool arguments. No `update_cookies` tool — use `reload_session`.
- Live cabinet here is **TON billed in Gram**, not EUR. `trg_type=user` / `target_type=users` is valid on TON.
- Do not add tools past 28 or restore `edit_ad_title` / `save_ads_columns` / `create_user_ad`.
- Do not run live mutations (create/edit/delete/funds/upload/log_out/revoke) unless the operator explicitly asked.
