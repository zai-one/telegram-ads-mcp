# tg-ads-mcp

Unofficial MCP server for [Telegram Ads](https://ads.telegram.org/). **TON cabinets are the primary target; EUR cabinets work; Stars cabinets are detected and refused.**

Built on the [MCP Python SDK v2](https://github.com/modelcontextprotocol/python-sdk) (`mcp>=2.1.1,<3`). Authenticates with session cookies from your browser — Telegram does not publish a public advertiser REST API. This is an unofficial wrapper; using it may violate Telegram's terms. See [SECURITY.md](./SECURITY.md) and the [Ad Guidelines](https://ads.telegram.org/guidelines).

## What you can do

~25 tools (down from 50) plus resources `ads://playbook` and `ads://account`.

- **Auth** — `check_session`, `reload_session` (re-reads `.env`, no cookies in tool args), `list_accounts`, `select_account`, `get_account` (balance + currency + cabinet type)
- **Ads** — `get_ads`, `get_ad`, `create_ad`, `edit_ad` (title/cpm/budget/status/picture-off/clear media), `delete_ad`, `clone_ad`, `launch_ad`, `check_ad_post`, `send_target_to_review`
- **Creatives** — `upload_media` (file path or base64), `preview_ad` (PNG attached to the tool result and saved under `previews/`)
- **Targeting** — `search_targets`, `get_targeting_reference` (EUR taxonomies)
- **Audiences / events** — `manage_audience`, `manage_event`
- **Funds** — `manage_funds` (currency follows the cabinet)
- **Account** — `save_api_settings`, `revoke_token`, `log_out`

Stars cabinets: `get_account` reports them, every ad/funds tool refuses until you `select_account` onto TON or EUR.

## Prerequisites

- Python ≥ 3.10
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- An ads.telegram.org login with a **TON** or **EUR** cabinet

## Install

```bash
git clone https://github.com/zai-one/tg-ads-mcp.git
cd tg-ads-mcp
uv sync
```

Or without cloning:

```bash
uvx --from git+https://github.com/zai-one/tg-ads-mcp tg-ads-mcp
```

## Configure

### 1. Cookies → `.env` only

1. Open https://ads.telegram.org/ and log in.
2. DevTools → Application → Cookies → `https://ads.telegram.org`.
3. Copy `stel_token` and `stel_ssid` into `.env` (see `.env.example`). Optional: `STEL_ADOWNER`.

**Never paste cookies into chat, screenshots, or tool arguments.** When they expire, update `.env` and call `reload_session`.

### 2. MCP client

**Claude Desktop / Claude Code / Cursor** — stdio:

```json
{
  "mcpServers": {
    "tg-ads": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/tg-ads-mcp", "run", "tg-ads-mcp"]
    }
  }
}
```

`.env` is loaded on startup; do not put `STEL_*` in the MCP `env` block unless you have to.

Remote / HTTP:

```bash
uv run tg-ads-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

Then point the client at `http://127.0.0.1:8000/mcp`.

## Notes

- `target_type` is fixed at creation (`channels` / `bots` / `search` / `users`). `users` is EUR-only.
- Status: `"active"` / `"on_hold"` (wire `"1"` / `"0"`).
- Amounts are strings in the cabinet currency. Do not assume TON.
- Search ads: no text, picture, or media.
- `preview_ad` writes PNGs to `TG_ADS_PREVIEW_DIR` (default `./previews`) so clients that cannot render MCP images still have a file.

## License

MIT — see [LICENSE](./LICENSE). Unofficial, not affiliated with Telegram.
