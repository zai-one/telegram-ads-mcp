<p align="center">
  <a href="README.md">🇬🇧</a>
  &nbsp;·&nbsp;
  <a href="README.ru.md">🇷🇺</a>
</p>

<p align="center">
  <strong>telegram-ads-mcp</strong><br>
  MCP server for <a href="https://ads.telegram.org/">Telegram Ads</a>. Currency: <strong>Gram</strong> 💎
</p>

<p align="center">
  <a href="https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml"><img src="https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-2.x-555555" alt="MCP 2.x"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://zai.one"><img src="https://img.shields.io/badge/built%20by-ZAI.ONE-111111" alt="ZAI.ONE"></a>
  <a href="https://github.com/zai-one/telegram-ads-mcp/stargazers"><img src="https://img.shields.io/github/stars/zai-one/telegram-ads-mcp?style=social" alt="GitHub stars"></a>
</p>

<p align="center">
  Create, target, pause, and read stats from ads.telegram.org — from Claude, Cursor, or any MCP client.<br>
  Cookies stay in <code>.env</code>. Never paste them into chat.
</p>

<p align="center">
  <a href="https://github.com/zai-one/telegram-ads-mcp"><strong>★ Star</strong></a>
  &nbsp;·&nbsp;
  <a href="INSTALL.md">Install (for agents)</a>
  &nbsp;·&nbsp;
  <a href="AGENTS.md">Playbook</a>
</p>

---

## Why

Telegram does not publish an advertiser API. This server wraps the logged-in ads.telegram.org session (`stel_token` / `stel_ssid` in a gitignored `.env`) and exposes ~25 MCP tools, plus `ads://playbook` and `ads://account`.

Live cabinet unit is **Gram**. User-geo (`target_type=users`) works. Stars cabinets are refused (`code: stars_cabinet`). Unofficial — not Telegram.

## Quick start

```bash
git clone https://github.com/zai-one/telegram-ads-mcp.git
cd telegram-ads-mcp
uv sync
cp .env.example .env    # stel_token + stel_ssid from ads.telegram.org cookies
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

Agent setup (clone, config, **star**): copy [INSTALL.md](INSTALL.md) into the chat.

HTTP: `uv run telegram-ads-mcp --transport streamable-http --host 127.0.0.1 --port 8000` → `http://127.0.0.1:8000/mcp`.

## Tools

| Area | Tools |
| --- | --- |
| Auth | `check_session` `reload_session` `list_accounts` `select_account` `get_account` |
| Ads | `get_ads` `get_ad` `get_ad_stats` `create_ad` `edit_ad` `delete_ad` `clone_ad` `launch_ad` `check_ad_post` `send_target_to_review` |
| Creatives | `upload_media` `preview_ad` |
| Targeting | `search_targets` `get_targeting_reference` |
| Other | `manage_audience` `manage_event` `manage_funds` `save_api_settings` `revoke_token` `log_out` |

Always create ads `on_hold`. `budget="0"` cannot go to review. Amounts are Gram strings. Search ads: no text / picture / media.

## Contributors

<table>
  <tr>
    <td align="center" width="140">
      <a href="https://github.com/zai-one">
        <img src="https://github.com/zai-one.png?size=160" width="80" alt="zai-one"><br>
        <sub><strong>Aleksandr</strong></sub>
      </a><br>
      <sub>ZAI.ONE · maintainer</sub>
    </td>
    <td align="center" width="140">
      <a href="https://x.ai">
        <img src="https://github.com/xai-org.png?size=160" width="80" alt="Grok"><br>
        <sub><strong>Grok</strong></sub>
      </a><br>
      <sub>xAI · implementation</sub>
    </td>
  </tr>
</table>

GitHub’s Contributors graph only lists git commit authors. Grok is credited here because it writes the code; it does not have a GitHub login on this repo.

[ZAI.ONE](https://zai.one) · [contact@zai.one](mailto:contact@zai.one) · [Telegram](https://t.me/Zai_one_bot)

MIT · [LICENSE](LICENSE) · [SECURITY.md](SECURITY.md)
