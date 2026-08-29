# telegram-ads-mcp

**Language:** English · [Русский](README.ru.md)

Unofficial MCP server for [Telegram Ads](https://ads.telegram.org/). Money in the live cabinet is **Gram** (💎). EUR works in code. Stars cabinets are refused.

[![tests](https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Built by ZAI.ONE](https://img.shields.io/badge/built%20by-ZAI.ONE-111111.svg)](https://zai.one)

If this is useful, **[star the repo](https://github.com/zai-one/telegram-ads-mcp)**.

Setup for an agent: copy **[INSTALL.md](INSTALL.md)** into the chat.

Cookies stay in gitignored `.env`. Never paste them into chat. Unofficial — not affiliated with Telegram. See [SECURITY.md](SECURITY.md) and the [Ad Guidelines](https://ads.telegram.org/guidelines).

## Tools

About 25 tools. Playbook: `ads://playbook` ([AGENTS.md](AGENTS.md)).

- **Auth** — `check_session`, `reload_session`, `list_accounts`, `select_account`, `get_account` (Gram balance)
- **Ads** — `get_ads`, `get_ad`, `get_ad_stats`, `create_ad`, `edit_ad`, `delete_ad`, `clone_ad`, `launch_ad`, `check_ad_post`, `send_target_to_review`
- **Creatives** — `upload_media`, `preview_ad`
- **Targeting** — `search_targets`, `get_targeting_reference` (user-geo is valid on Gram)
- **Audiences / events / funds** — `manage_audience`, `manage_event`, `manage_funds` (amounts in Gram)
- **Account** — `save_api_settings`, `revoke_token`, `log_out`

Stars: `get_account` can report them; ad/funds tools return `code: "stars_cabinet"`.

## Install

See **[INSTALL.md](INSTALL.md)**. Short version:

```bash
git clone https://github.com/zai-one/telegram-ads-mcp.git
cd telegram-ads-mcp
uv sync
cp .env.example .env   # then stel_token + stel_ssid
```

```json
{
  "mcpServers": {
    "telegram-ads": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/telegram-ads-mcp", "run", "telegram-ads-mcp"]
    }
  }
}
```

HTTP: `uv run telegram-ads-mcp --transport streamable-http --host 127.0.0.1 --port 8000` → `http://127.0.0.1:8000/mcp`.

## Notes

- Create ads `on_hold`. `budget="0"` cannot go to review. `target_type` is immutable.
- `users` targeting (geo) is valid on Gram cabinets.
- Status: `"active"` / `"on_hold"` (live UI: Active / Stopped).
- Amounts are Gram strings.
- Search ads: no text, picture, or media.

## ZAI.ONE

Built by [ZAI.ONE](https://zai.one) — internet agency (strategy, brand, web, ads, analytics).

[zai.one](https://zai.one) · [contact@zai.one](mailto:contact@zai.one) · [Telegram](https://t.me/Zai_one_bot)

MIT — [LICENSE](LICENSE).
