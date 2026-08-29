# Changelog

## Unreleased

- Rename: package/repo `telegram-ads-mcp` (GitHub `zai-one/telegram-ads-mcp`). Import `telegram_ads_mcp`. Script `telegram-ads-mcp`; `tg-ads-mcp` is a deprecated alias.
- CI Import step + pytest `test_ci_import_entrypoint` use `telegram_ads_mcp.server` (the previous workflow still imported `tg_ads_mcp.server` and went red after a green suite).
- Docs: bilingual README, INSTALL.md (agent setup + star), Gram-only wording, file-hygiene rules in AGENTS.md.
- Issues template (no cookies). README: don’t fork, contact t.me/zai_one for EUR/Stars. Contributors: Grok (xai-org), Codex 5.6.
- Ads-list 30s cache; skip `getAd` after the first HTTP 400. Redact `hash=` in logs. Ship `AGENTS.md` in the wheel. Prompt `review-account`.

- Gram/TON live parse: header balance widget, `currency-ton` beats `value="users"` (not EUR).
- `get_ads` status filter accepts live `Active` / `Stopped` as well as `1` / `0`.
- `get_ad_stats` divides Gram chart spend by `1000000`.
- `get_ad` / list map `tme_path` → `promote_url`, `trg_type` → `target_type`.
- Skip extra `/account/budget` and `/account/ad/new` fetches when `/account` already has a currency widget.
- `get_targeting_reference` works on TON Gram user-geo (not EUR-only).
- `AGENTS.md` playbook + `CLAUDE.md` include. Tool count still ~25.
- `create_ad` / `launch_ad` allow `target_type=users` on TON/Gram (no EUR-only refuse).
- Leak tests: `.env` untracked; live cookie values must not appear in git files.
- README: Built by ZAI.ONE (same voice as grok-build-mcp).

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
