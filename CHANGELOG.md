# Changelog

## 0.2.0 — 2026-08-29

Rewrite on MCP Python SDK **2.1.x** (spec 2026-07-28).

- Package layout `tg_ads_mcp/` (setuptools), script `tg-ads-mcp`.
- Secrets only from `.env`. `update_cookies` is gone; use `reload_session`.
- `check_session` no longer returns `api_hash`.
- Stars cabinets are detected and refused; TON is primary, EUR still works.
- Tool surface collapsed (~25 tools): merged quick-edits, searches, audiences, events, funds. Dropped UI chrome (`save_ads_columns`, drafts).
- New: `get_account` (balance + currency), `get_ad`, `preview_ad` (PNG to chat + `previews/`), `upload_media`, `launch_ad`, `audience_id` on create/edit.
- Empty strings are not sent on create (search ads). `picture=false` / `clear_media` actually detach creatives.
- Balanced JSON parser (nested arrays). Stats grow CTR/CPC/actual CPM. Async `httpx` with retries. Re-auth on `AUTH_REQUIRED`.
- Resources `ads://playbook`, `ads://account`. Prompts `launch-campaign`, `diagnose-ad`.
- Transports: stdio (default) and `--transport streamable-http`.
- Tests + GitHub Actions. Unofficial wrapper — see README / SECURITY.md.

## 0.1.0 — 2026-07-01

Initial FastMCP (mcp 1.x) wrapper, 50 tools, cookie args on `update_cookies`.
