# Changelog

## Unreleased

## 0.2.0 — 2026-08-30

First public GitHub release of `zai-one/telegram-ads-mcp`. MCP Python SDK **2.1.x**.

- Package `telegram-ads-mcp` (`telegram_ads_mcp`). Script `telegram-ads-mcp`; `tg-ads-mcp` is a deprecated alias.
- License **LicenseRef-ZAI-ONE** (not MIT): run against your own cabinet; do not copy or remix; file Issues.
- TON cabinet billed in Gram. User-geo (`users`) works. Stars cabinets refused.
- `TG_ADS_WRITE_GATE=strict|confirm|open` (default `confirm`). Spend/destructive tools need `confirm=true` unless `open`.
- Secrets only from gitignored `.env`. `reload_session` re-reads the file. No cookie args. Leak tests in CI.
- ~25 tools, resources `ads://playbook` / `ads://account`, prompts `launch-campaign` / `review-account` / `diagnose-ad`.
- Bilingual README, INSTALL.md (agent setup + star), `CLAUDE.md` bare `@AGENTS.md`, `server.json`.
- CI: Ubuntu+Windows × py3.10/3.13. Import `telegram_ads_mcp.server`.

## 0.1.0 — 2026-07-01

Initial FastMCP (mcp 1.x) wrapper, 50 tools, cookie args on `update_cookies`.
