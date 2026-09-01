# Changelog

## 0.3.0 — 2026-09-01

Operator-facing: stats contract, Issue ritual, DevTools cookie walkthrough, structured skips, safer `launch_ad` targeting.

- Local leak scan: `uv run python scripts/check_security.py` (tracked `.env` / cookie assignments / confirm hashes). `--issue draft.md` prints `gh issue create` or refuses; does not open the Issue.
- Issue form + CONTRIBUTING: no cookies, `.env`, or platform hashes in GitHub Issues.
- Client playbook: **Found a bug → Issue** — offer a ticket (do not open unasked); `ads://playbook` / `AGENTS.md`.
- INSTALL.md + playbook: Windows Chrome/Edge DevTools steps to refresh `STEL_*` into gitignored `.env` (never echo values; then `reload_session`). Tracked MCP config: `mcp.json.example` (no `STEL_*`).
- Gitignore `AGENTS.local.md` / `CLAUDE.local.md` for repo-dev notes (client playbook `AGENTS.md` stays tracked).
- Client playbook: **Reports / stats** — `get_ad_stats` echoes request `period`; `summary.spend` already scaled (`spend_already_scaled`); `charts.budget` scaled (`values_already_scaled`); no CSV tool; gitignored `reports/`.
- Wheel JSON Schema (`telegram_ads_mcp/schemas/`): campaign brief, review-account artifact, stats dump — contracts for a later campaign-setup service (service itself is out of this repo).
- `write_gated` now includes `tool`, `class`, `would_send` (no secrets), `sent: false`. Not a platform dry-run.
- Audience/event Access denied → `code: access_denied`, `hint: skip` (do not retry).
- `launch_ad` accepts a safe targeting subset (`topics`, `exclude_*`, `locations`). Drops `langs` when specific `channels` are set (platform Target invalid).

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
