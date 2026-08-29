# Contributing

Thin MCP wrapper over the `ads.telegram.org` internal API. Keep it small.

```bash
git clone https://github.com/zai-one/tg-ads-mcp.git
cd tg-ads-mcp
uv sync --extra test
cp .env.example .env
uv run pytest
uv run tg-ads-mcp   # stdio
```

| Path | Role |
| --- | --- |
| `tg_ads_mcp/server.py` | MCP tools / resources / prompts |
| `tg_ads_mcp/client.py` | Async HTTP + cabinet detection |
| `tg_ads_mcp/parse.py` | HTML/JSON extraction |
| `tg_ads_mcp/preview.py` | PNG card |
| `AGENTS.md` | Agent playbook (also `ads://playbook`) |

Docstrings are the agent-facing spec. Money and IDs are strings. Multi-IDs are semicolon-separated. Never log cookies or `api_hash`.

PRs: one logical change, `pytest` green, say which ads.telegram.org method a new tool wraps.
