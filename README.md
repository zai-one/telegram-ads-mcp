# tg-ads-mcp

MCP server for the [Telegram Ads](https://ads.telegram.org/) platform — supports both **TON cabinets** (direct, TON-billed) and **EUR cabinets** (reseller, EUR-billed). Exposes ~50 tools so AI agents can create, edit, target, monitor, and analyze Telegram Ads campaigns end-to-end.

Built on top of [FastMCP](https://github.com/modelcontextprotocol/python-sdk). Authenticates via session cookies — no official Telegram Ads public API is required.

## What you can do

- **Auth & accounts** — `check_session`, `list_accounts`, `select_account`, `update_cookies`
- **Ads CRUD** — `get_ads_list`, `create_ad`, `edit_ad`, `clone_ad`, `delete_ad`, `send_target_to_review`
- **Quick edits** — `edit_ad_title`, `edit_ad_cpm`, `edit_ad_budget`, `edit_ad_daily_budget`, `edit_ad_status`
- **Targeting search** — `search_channel`, `search_bot`, `search_target_query`, `search_location`, `get_similar_channels`, `get_similar_bots`
- **Audiences & events** — `create_audience`, `edit_audience_title`, `delete_audience`, `clone_audience`, `create_event`, `create_pixel`, …
- **Funds** — `send_add_funds_request`, `transfer_funds`, `withdraw_funds`, `search_account_for_transfer`
- **Stats** — `get_ad_stats` (5-min buckets over last 24h, or daily buckets for full lifetime), `revoke_stats_url`
- **User-level targeting (EUR cabinet only)** — `check_cabinet_type`, `get_user_targeting_reference`, `create_user_ad` (target Telegram users by country, language, interest topic, subscribed channels, device — independent of channel placement)
- **Account settings** — `save_account_info`, `save_api_settings`, `revoke_token`, `log_out`

Full per-tool documentation lives in the docstrings inside [`server.py`](./server.py) — they are surfaced to the agent at tool-call time.

## Prerequisites

- Python ≥ 3.11
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- An account on [ads.telegram.org](https://ads.telegram.org/) with a **TON cabinet** (direct, TON-billed) or an **EUR cabinet** (reseller, EUR-billed), and a funded balance for any operations that touch real money

## Install

```bash
git clone https://github.com/NikitaZhidkov/tg-ads-mcp.git
cd tg-ads-mcp
uv sync
```

Or run it without cloning, straight from GitHub, via [`uvx`](https://docs.astral.sh/uv/guides/tools/):

```bash
uvx --from git+https://github.com/NikitaZhidkov/tg-ads-mcp tg-ads-mcp
```

## Configure

### 1. Get your session cookies

The server logs into ads.telegram.org as you, using cookies from your browser:

1. Open <https://ads.telegram.org/> in your browser and log in.
2. Open DevTools → **Application** → **Storage** → **Cookies** → `https://ads.telegram.org`.
3. Copy the values of:
   - `stel_token`
   - `stel_ssid`
   - `stel_adowner` *(optional — pre-selects an ad account; otherwise the first one is used)*

Cookies expire periodically. When they do, repeat the steps above and either restart the server with new env vars or call the `update_cookies` tool from the agent.

### 2. Set environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

…and fill in the values.

### 3. Wire it into your MCP client

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tg-ads": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/tg-ads-mcp", "run", "server.py"],
      "env": {
        "STEL_TOKEN": "...",
        "STEL_SSID": "...",
        "STEL_ADOWNER": ""
      }
    }
  }
}
```

**Claude Code** — `.mcp.json` in your project root, same shape as above.

**Cursor** — `~/.cursor/mcp.json`, same shape as above.

If you set the values in `.env`, you can omit the `env` block — `server.py` calls `load_dotenv()` on startup.

To avoid a local checkout entirely, use the `uvx`-from-GitHub form as the command:

```json
{
  "mcpServers": {
    "tg-ads": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/NikitaZhidkov/tg-ads-mcp", "tg-ads-mcp"],
      "env": { "STEL_TOKEN": "...", "STEL_SSID": "...", "STEL_ADOWNER": "" }
    }
  }
}
```

## Run standalone (for debugging)

```bash
uv run server.py
```

The server speaks MCP over stdio.

## Notes on the Telegram Ads API

- **TON vs EUR cabinets.** Both work. TON cabinets fund and bill in TON; EUR cabinets are reseller-operated (e.g. Click Reklam) and bill in EUR. Switch between them with `select_account`. The MCP detects which type you're on automatically when needed (`check_cabinet_type`).
- **User-level targeting is EUR-only.** EUR cabinets expose a fourth `target_type=users` that reaches Telegram users by country / language / interest topic / subscribed channels / device — independent of channel placement. TON cabinets only have `channels` / `bots` / `search`. The `create_user_ad`, `get_user_targeting_reference`, and `check_cabinet_type` tools refuse cleanly when run on a TON cabinet.
- `target_type` (`channels` / `bots` / `search` / `users`) is fixed at ad creation — you can't switch it later.
- Search ads have **no text, picture, or media** — only a CPM and search keywords.
- Status values inside the platform are `"1"` (active) / `"0"` (on hold). The wrappers accept human-readable `"active"` / `"on_hold"` and translate.

## Security

Your `STEL_TOKEN` and `STEL_SSID` are the equivalent of an unscoped login — anyone holding them can manage your ad account and spend your TON. Treat them like passwords. **Never commit `.env`, never paste cookies into shared chats, screenshots, or remote agents you don't trust.**

## License

MIT — see [LICENSE](./LICENSE).

## See also

- [`AGENTS.md`](./AGENTS.md) — playbook for LLM agents using this server.
