# Contributing

Thin MCP wrapper over the `ads.telegram.org` internal API. Keep it small.

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
| `CLAUDE.md` | Tells Claude Code to load `AGENTS.md` |

Docstrings are the agent-facing spec. Money and IDs are strings. Multi-IDs are semicolon-separated. Never log cookies or `api_hash`.

PRs: one logical change, `uv run pytest` green, say which ads.telegram.org method a new tool wraps.

CI (`.github/workflows/tests.yml`) is Ubuntu+Windows × py3.10/3.13. It runs **the same pytest** plus `from telegram_ads_mcp.server import mcp`. If you rename a package or entrypoint, add a test that performs that import — otherwise GitHub goes red after a green local suite.
