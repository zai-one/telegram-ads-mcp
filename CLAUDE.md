@AGENTS.md

# CLAUDE.md

**telegram-ads-mcp** — MCP for ads.telegram.org (TON cabinet, Gram currency).

`ads://playbook` is the MCP copy. Install/star: [INSTALL.md](INSTALL.md). Repo/CI: [CONTRIBUTING.md](CONTRIBUTING.md).

- Cookies: gitignored `.env` only. Never paste into chat.
- Money: **Gram (TON)** — both names are fine. User-geo (`users`) is valid. Stars: switch, do not mutate.
- `TG_ADS_WRITE_GATE=strict|confirm|open` (default confirm). Spend/destructive need `confirm=true` unless `open`.
- Two jobs: cabinet vs this git repo. Do not mix unless asked both. Never auto-push.
- README is bilingual: [README.md](README.md) (EN) and [README.ru.md](README.ru.md).
- License is not MIT. File Issues for changes. Do not copy or remix.
- No live mutations unless the operator asked (or gate=`open` and they asked to service the cabinet). Max 28 tools.
