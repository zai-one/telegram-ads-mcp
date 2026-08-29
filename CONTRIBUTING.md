# Contributing

Thin MCP wrapper over the `ads.telegram.org` internal API. Keep it small.

This project is **not** MIT. Run it against your own cabinet. Do not copy, remix, or publish a fork. If something is missing or broken, [open an issue](https://github.com/zai-one/telegram-ads-mcp/issues/new/choose). I will patch **this** repository when I can. Support is not guaranteed.

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
| `AGENTS.md` | Agent playbook (also `ads://playbook`) |
| `CLAUDE.md` | Claude Code memory; must contain a bare `@AGENTS.md` line (not a Markdown link) |
| `server.json` | MCP registry descriptor (`io.github.zai-one/telegram-ads-mcp`) |

Docstrings are the agent-facing spec. Money and IDs are strings. Multi-IDs are semicolon-separated. Never log cookies or `api_hash`. Never paste cookies into issues.

Issues: one problem per ticket, `uv run pytest` notes if you have them, say which ads.telegram.org method is involved. Do not attach `.env` or DevTools screenshots.

CI (`.github/workflows/tests.yml`) is Ubuntu+Windows × py3.10/3.13. It runs **the same pytest** plus `from telegram_ads_mcp.server import mcp`. If you rename a package or entrypoint, add a test that performs that import — otherwise GitHub goes red after a green local suite.
