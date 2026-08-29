# telegram-ads-mcp

Unofficial MCP server for [Telegram Ads](https://ads.telegram.org/). **TON cabinets bill in Gram (💎). That is the live-tested unit. EUR is implemented. Stars is heuristic-only and refused.**

[![tests](https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-2.x-purple.svg)](https://modelcontextprotocol.io/)
[![Built by ZAI.ONE](https://img.shields.io/badge/built%20by-ZAI.ONE-111111.svg)](https://zai.one)

> Built by **[ZAI.ONE](https://zai.one)** — international internet agency.
> Marketing and development under one roof.

Built on the [MCP Python SDK v2](https://github.com/modelcontextprotocol/python-sdk) (`mcp>=2.1.1,<3`). Authenticates with session cookies from your browser — Telegram does not publish a public advertiser REST API. This is an unofficial wrapper; using it may violate Telegram's terms. See [SECURITY.md](./SECURITY.md) and the [Ad Guidelines](https://ads.telegram.org/guidelines).

## What you can do

~25 tools (down from 50) plus resources `ads://playbook` and `ads://account`.

- **Auth** — `check_session`, `reload_session` (re-reads `.env`, no cookies in tool args), `list_accounts`, `select_account`, `get_account` (balance + currency + cabinet type)
- **Ads** — `get_ads`, `get_ad`, `create_ad`, `edit_ad` (title/cpm/budget/status/picture-off/clear media), `delete_ad`, `clone_ad`, `launch_ad`, `check_ad_post`, `send_target_to_review`
- **Creatives** — `upload_media` (file path or base64), `preview_ad` (PNG attached to the tool result and saved under `previews/`)
- **Targeting** — `search_targets`, `get_targeting_reference` (user-geo countries/langs/topics on TON Gram as well as EUR)
- **Audiences / events** — `manage_audience`, `manage_event`
- **Funds** — `manage_funds` (currency follows the cabinet)
- **Account** — `save_api_settings`, `revoke_token`, `log_out`

## Cabinets: TON, EUR, Stars

| Cabinet | Billing | Status in this repo |
| --- | --- | --- |
| **TON / Gram** | Gram (💎), TON rail | **Primary, live-tested.** Header widget is Gram (`js-header_owner_budget`). `target_type=users` (live `trg_type=user`) is **valid on TON** — do not classify as EUR just because user-geo exists. |
| **EUR** | EUR (reseller) | Implemented (`currency-euro`). **Not live-verified** here. |
| **Stars** | Telegram Stars (`XTR`) | **No Stars cabinet**, so not live-tested. Heuristic detect (`XTR` / `cabinetType=stars`). Reads can report it; mutations return `code: "stars_cabinet"`. |

If you have a Stars cabinet and detection is wrong (false positive or missed Stars), send a **redacted** HTML snippet from `/account` (strip cookies, `stel_*`, `api_hash`) and open an issue. Do not paste session cookies.

## Prerequisites

- Python ≥ 3.10
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`
- An ads.telegram.org login with a **TON/Gram** cabinet (EUR should work; Stars is refused)

Claude Code: this repo has `CLAUDE.md` pointing at `AGENTS.md` (the agent playbook). Other MCP clients should still load `ads://playbook`.

## Install

```bash
git clone https://github.com/zai-one/telegram-ads-mcp.git
cd telegram-ads-mcp
uv sync
```

Or without cloning:

```bash
uvx --from git+https://github.com/zai-one/telegram-ads-mcp telegram-ads-mcp
```

(`tg-ads-mcp` remains a deprecated console-script alias for one release.)

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
      "args": ["--directory", "/absolute/path/to/telegram-ads-mcp", "run", "telegram-ads-mcp"]
    }
  }
}
```

`.env` is loaded on startup; do not put `STEL_*` in the MCP `env` block unless you have to.

Remote / HTTP:

```bash
uv run telegram-ads-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

Then point the client at `http://127.0.0.1:8000/mcp`.

## Notes

- `target_type` is fixed at creation (`channels` / `bots` / `search` / `users`). `users` (geo) works on TON/Gram as well as EUR.
- Status: `"active"` / `"on_hold"` (wire `"1"` / `"0"`).
- Amounts are strings in the cabinet currency. TON cabinets use **Gram**, not a hardcoded “TON” label.
- Search ads: no text, picture, or media.
- `preview_ad` writes PNGs to `TG_ADS_PREVIEW_DIR` (default `./previews`) so clients that cannot render MCP images still have a file.

## Who builds this

<div align="center">

## [ZAI.ONE](https://zai.one)

**International internet agency — marketing and development under one roof**

*Strategy · Brand & design · Video production · PR & events · Web, SEO,
advertising and analytics*

</div>

ZAI.ONE is a full-cycle agency: one team takes a product from positioning and offer through the creative and the site to the traffic and the numbers that say whether it worked.

This MCP came out of running Telegram Ads for real Gram cabinets, not a lab. Agents needed the same rules we use on the account — create on hold, budget before review, Gram not EUR, never paste session cookies — without a 50-tool kitchen sink.

| | |
|---|---|
| **Marketing** | positioning, offer and messaging, launch planning, PR and events, creative, video and photo production |
| **Development** | websites and web products, SEO, advertising, analytics, AI tooling and automation — this repository is a sample of it |

**Talk to us:** [zai.one](https://zai.one) · [contact@zai.one](mailto:contact@zai.one) · [Telegram](https://t.me/Zai_one_bot)

---

MIT — see [LICENSE](./LICENSE). Unofficial, not affiliated with Telegram.
