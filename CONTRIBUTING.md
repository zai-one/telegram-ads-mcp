# Contributing

Thin MCP wrapper over the `ads.telegram.org` internal API. Keep it small.

A future campaign-setup HTTP/job service is **out of this repository**. Contracts live in `telegram_ads_mcp/schemas/` (shipped next to `AGENTS.md`) so that service can stay a thin caller of these tools. Do not add an app tree, a 26th tool, or a bidding bot here.

This project is **not** MIT. Run it against your own cabinet. Do not copy, remix, or publish a competing server. If something is missing or broken, [open an issue](https://github.com/zai-one/telegram-ads-mcp/issues/new/choose). I will patch **this** repository when I can. Support is not guaranteed.

Do not add PR templates, a Contributors table, or “PRs welcome”. README must keep the Issues CTA (“I'm working on this”) and must **not** contain “don't fork” / “не форкайте” (tests fail).

```bash
git clone https://github.com/zai-one/telegram-ads-mcp.git
cd telegram-ads-mcp
uv sync --extra test
cp .env.example .env
uv run pytest
uv run telegram-ads-mcp   # stdio
```

| Path | Role |
| --- | --- |
| `telegram_ads_mcp/server.py` | MCP tools / resources / prompts |
| `telegram_ads_mcp/client.py` | Async HTTP + cabinet detection |
| `telegram_ads_mcp/parse.py` | HTML/JSON extraction |
| `telegram_ads_mcp/preview.py` | PNG card |
| `telegram_ads_mcp/gate.py` | `TG_ADS_WRITE_GATE` (`strict` / `confirm` / `open`) |
| `AGENTS.md` | Agent playbook (also `ads://playbook`) |
| `telegram_ads_mcp/schemas/` | JSON Schema for campaign brief / review artifact / stats dump (wheel package data). Not a SaaS. |
| `scripts/check_security.py` | Local leak scan; `--issue` prints `gh issue create` (does not open) |
| `CLAUDE.md` | Claude Code memory; must contain a bare `@AGENTS.md` line (not a Markdown link) |
| `server.json` | MCP registry descriptor (`io.github.zai-one/telegram-ads-mcp`) |

Client playbook is `AGENTS.md`; local project notes go in `AGENTS.local.md` (gitignored, never cookies).

Docstrings are the agent-facing spec. Money and IDs are strings. Multi-IDs are semicolon-separated. Never log cookies or `api_hash`. Never paste cookies into issues.

## File an Issue

Client ritual (offer → operator yes → draft, no cookies): [AGENTS.md](AGENTS.md) **Found a bug → Issue**. Form: https://github.com/zai-one/telegram-ads-mcp/issues/new/choose

Do not duplicate that ritual here. Maintainer scan before commit: `uv run python scripts/check_security.py`. A draft: `uv run python scripts/check_security.py --issue draft.md` prints `gh issue create` (does not open). Do not attach `.env` or DevTools screenshots.

## Before every commit and push

1. `uv run pytest -q` and `uv run python scripts/check_security.py` — both must be green (leak tests + `test_ci_import_entrypoint`).
2. `README.md` and `README.ru.md` in the **same** commit. Same tool names as `telegram_ads_mcp.server` (do not drop `get_account` / `get_ad_stats` / `launch_ad` / `reload_session` / `preview_ad`). Both start with 🇬🇧 / 🇷🇺. Both ask for a GitHub star. `<!-- mcp-name: io.github.zai-one/telegram-ads-mcp -->`. Issues CTA, no cookies, [t.me/zai_one](https://t.me/zai_one) for EUR/Stars. LicenseRef-ZAI-ONE (not MIT). No Contributors table.
3. `INSTALL.md` still clones `zai-one/telegram-ads-mcp`, stars the repo, documents client config files (Cursor / Claude / VS Code `servers` / Codex).
4. User-facing copy may say **Gram**, **TON**, or **Gram (TON)**. Keep HTML/CSS `currency-ton` in parse tests — that widget is the Gram/TON cabinet. `server.json` description ≤ 100 chars, no fake `packages`.
5. `.env` / `VERIFY.md` / `previews/` / `reports/` stay untracked. `git status` before push.
6. `CLAUDE.md` has a line that is exactly `@AGENTS.md`. After editing `AGENTS.md`, copy bytes to `telegram_ads_mcp/AGENTS.md`.
7. Keep the `tg_ads_mcp` shim + script `tg-ads-mcp`. Tool count 12–28. Do not restore `update_cookies` / cookie args.

## CI

`.github/workflows/tests.yml`: Ubuntu+Windows × py3.10/3.13. CI uses **pip** + `python scripts/check_security.py`, then `python -m pytest tests -q`, then `from telegram_ads_mcp.server import mcp` (name `telegram-ads-mcp`) and `import tg_ads_mcp` (version match). If you rename a package or entrypoint, add a pytest import for what CI runs — local green is not enough.

Local: `uv run pytest -q` and `uv run python scripts/check_security.py`.

## Version

`pyproject` version, `telegram_ads_mcp.__version__`, and `server.json` version stay equal. User-visible changes go under CHANGELOG Unreleased. Bump those three files together only when cutting a tagged release (move Unreleased into a version heading); ordinary commits keep the current version. Do not tag / PyPI until [OFFLINE.md](OFFLINE.md) live checks (operator machine, no cookies in chat).
