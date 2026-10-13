# Changelog

## 0.5.0 — 2026-10-13

Operator-facing: agent layer per the ZAI.ONE MCP standard (router instructions, skills, guides, plugins), compact `get_ads` / `get_ad_stats` by default, working-directory `.env` limited to `STEL_*` cookies, LicenseRef-ZAI-ONE 2.0.

- License: LicenseRef-ZAI-ONE 2.0 (source-available). Free install and use for yourself and your organisation, including commercial work; issues and pull requests welcome; copying code into other projects, redistribution, embedding and competing hosted services need written permission. Releases published under MIT before 2026-10-13 stay MIT for those versions (see NOTICE). README first screen: one-line scope, why this MCP, maintenance and update check.
- Router `instructions` (<=1200 chars) and template tool descriptions + titles (`telegram_ads_mcp/descriptions.py`, each <=300 chars).
- Skills `skills/telegram-ads-{launch-campaign,review-account,diagnose-ad}` (Agent Skills spec) with `references/` generated from AGENTS.md (`scripts/sync_skills.py`) and self-contained output templates.
- Resources `ads://guide/index` and `ads://guide/{topic}` (one playbook section at a time); `ads://playbook` unchanged.
- Structured errors add `retryable`, `hint`, `docs`; new playbook section **Errors**.
- Output change — compact by default: `get_ads` and `get_ad_stats` now default to `detail="summary"`. `get_ads` drops null/empty fields; `get_ad_stats` omits per-bucket `charts`. Pass `detail="full"` for the 0.4.0 payload.
- Security: `.env` lookup no longer walks up from the working directory. `TG_ADS_ENV_FILE` if set (read in full); otherwise the checkout's `.env` as before, plus only the `STEL_*` cookies from `.env` in the working directory itself (no parent walk). Settings (`TG_ADS_WRITE_GATE`, `MCP_TRANSPORT` / `MCP_HOST` / `MCP_PORT`, ...) in a working-directory `.env` are ignored, so an unrelated project's `.env` cannot open the write gate or expose the server on the network.
- Claude Code (`.claude-plugin/plugin.json`) and Cursor (`.cursor-plugin/plugin.json`) plugins plus a single-plugin marketplace (`.claude-plugin/marketplace.json`); README install snippets for Claude Code, Cursor, Codex, Claude Desktop. Plugin manifests and uvx snippets pin `git+https://github.com/zai-one/telegram-ads-mcp@v0.5.0`.
- CI: `scripts/token_budget.py --strict` (also checks unknown SKILL.md keys and folded descriptions) and skill reference sync check.

## 0.4.0 — 2026-10-12

Operator-facing: suggest-only update check (26th tool), MCP SDK 2.3.0 lock.

- `check_update` (READ): suggest-only check of the latest GitHub release (one anonymous API call, 3 s timeout, 24 h cache, offline → `unavailable`) with release notes link and update command. `check_session` adds `update_hint` and the server instructions add one line when the cache already knows of a newer release; a stale cache refreshes on a background thread at startup. Opt out: `TG_ADS_DISABLE_UPDATE_CHECK=1`.
- Update check hardening: only plain version tags (`v1.2.3`, ASCII digits) are accepted, from GitHub and from the cache, so a crafted tag or cached value never reaches `latest_version`, `update_command`, `update_hint` or the server instructions. Every fetch attempt is cached: after a failure the check waits 30 min, and `force=true` re-checks at most once a minute (the startup refresh obeys the same rules). `update_command` is now only the executable command (`git pull --ff-only && uv sync` in a clone); where to run it moved to the new `run_in` field. The unused release-wheel lookup is gone. README and `.env.example` note that the server calls `api.github.com` at startup unless disabled.
- `uv.lock`: MCP Python SDK 2.1.1 → 2.3.0 (fixes, no API changes for this server; `pyproject.toml` range `mcp>=2.1.1,<3` unchanged).
- Explain ZAI.ONE as a digital agency and link integration support in English and Russian.

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
