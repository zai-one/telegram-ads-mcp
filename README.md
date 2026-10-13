<!-- mcp-name: io.github.zai-one/telegram-ads-mcp -->
<p align="center">
  <a href="README.md">🇬🇧</a>
  &nbsp;·&nbsp;
  <a href="README.ru.md">🇷🇺</a>
</p>

<p align="center">
  <strong>telegram-ads-mcp</strong><br>
  MCP server for <a href="https://ads.telegram.org/">Telegram Ads</a>. Currency: <strong>Gram (TON)</strong> 💎
</p>

<p align="center">
  <a href="https://github.com/zai-one/telegram-ads-mcp/releases/tag/v0.4.0"><img src="https://img.shields.io/github/v/release/zai-one/telegram-ads-mcp" alt="v0.4.0"></a>
  <a href="https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml"><img src="https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-2.x-555555" alt="MCP 2.x"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-proprietary-lightgrey" alt="LicenseRef-ZAI-ONE"></a>
  <a href="https://zai.one"><img src="https://img.shields.io/badge/built%20by-ZAI.ONE-111111" alt="ZAI.ONE"></a>
  <a href="https://github.com/zai-one/telegram-ads-mcp/stargazers"><img src="https://img.shields.io/github/stars/zai-one/telegram-ads-mcp?style=social" alt="GitHub stars"></a>
</p>

<p align="center">
  Create, target, pause, and read stats from ads.telegram.org — from Claude, Cursor, or any MCP client.<br>
  Cookies stay in <code>.env</code>. Never paste them into chat. DevTools clicks: <a href="INSTALL.md">INSTALL.md</a>.
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

Telegram does not publish an advertiser API. This server wraps the logged-in ads.telegram.org session (`stel_token` / `stel_ssid` in a gitignored `.env`) and exposes 26 MCP tools, plus `ads://playbook` and `ads://account`.

Live cabinet is **TON**, billed in **Gram**. User-geo (`target_type=users`) works. Stars cabinets are refused (`code: stars_cabinet`). Unofficial — not Telegram.

Write permission is `.env` `TG_ADS_WRITE_GATE=strict|confirm|open` (default `confirm`). Spend/destructive tools need `confirm=true` unless `open`. A blocked call returns `code: write_gated` with `tool` / `class` / `would_send` (intended args, no secrets) and `sent: false` — not a platform dry-run.

## What's new in 0.4.0

- **Updates.** New `check_update` (26th tool, read-only) compares your version with the latest GitHub release and returns the notes link, the executable `update_command` and `run_in` (where to run it). It only suggests and never installs. `check_session` adds `update_hint` when a newer release is cached. Opt out: `TG_ADS_DISABLE_UPDATE_CHECK=1`.
- **Hardening.** Only plain version tags (`v1.2.3`) are accepted. One anonymous GitHub API call, 3 s timeout, 24 h cache, 30 min backoff after a failure, `force=true` at most once a minute; offline → `status: unavailable`.
- **SDK.** `uv.lock` pins MCP Python SDK 2.3.0 (fixes, no API changes for this server).

## Quick start

```bash
git clone https://github.com/zai-one/telegram-ads-mcp.git
cd telegram-ads-mcp
uv sync
cp .env.example .env    # STEL_TOKEN / STEL_SSID — DevTools steps in INSTALL.md; never paste into chat
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

Agent setup (clone, config, **star**): copy [INSTALL.md](INSTALL.md) into the chat. Command: `telegram-ads-mcp` (alias `tg-ads-mcp`). After connect: `ads://playbook`. Prompts: `launch-campaign`, `review-account`, `diagnose-ad`. Client file names are in INSTALL.md (Cursor, Claude, VS Code `servers`, Codex TOML). Do not put cookies in MCP `env`. Example: [mcp.json.example](mcp.json.example).

HTTP: `uv run telegram-ads-mcp --transport streamable-http --host 127.0.0.1 --port 8000` → `http://127.0.0.1:8000/mcp`.

## Install anywhere (uvx, plugins)

Cookies stay in a `.env` file on disk (never in MCP `env` values or chat). For uvx installs point `TG_ADS_ENV_FILE` at that file (path only), or start the client from a folder that has `.env`. From the working folder's `.env` (that folder only, not its parents) the server takes `STEL_*` cookies and nothing else; settings such as `TG_ADS_WRITE_GATE`, `MCP_TRANSPORT` / `MCP_HOST` / `MCP_PORT` or `TG_ADS_DISABLE_UPDATE_CHECK` are read only from `TG_ADS_ENV_FILE`, the clone's own `.env`, or the process environment, so an unrelated project's `.env` cannot open the write gate or expose the server on the network.

```bash
# Claude Code: MCP only
claude mcp add telegram-ads --env TG_ADS_ENV_FILE=/path/to/telegram-ads.env -- uvx --from git+https://github.com/zai-one/telegram-ads-mcp telegram-ads-mcp
# Claude Code: plugin = MCP + skills (launch / review / diagnose)
/plugin marketplace add zai-one/telegram-ads-mcp
/plugin install telegram-ads@telegram-ads-mcp
```

Cursor: [one-click install](cursor://anysphere.cursor-deeplink/mcp/install?name=telegram-ads&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyItLWZyb20iLCJnaXQraHR0cHM6Ly9naXRodWIuY29tL3phaS1vbmUvdGVsZWdyYW0tYWRzLW1jcCIsInRlbGVncmFtLWFkcy1tY3AiXSwiZW52Ijp7IlRHX0FEU19FTlZfRklMRSI6Ii9wYXRoL3RvL3RlbGVncmFtLWFkcy5lbnYifX0=) or `.cursor/mcp.json`:

```json
{"mcpServers": {"telegram-ads": {"command": "uvx", "args": ["--from", "git+https://github.com/zai-one/telegram-ads-mcp", "telegram-ads-mcp"], "env": {"TG_ADS_ENV_FILE": "/path/to/telegram-ads.env"}}}}
```

Codex `~/.codex/config.toml`:

```toml
[mcp_servers.telegram-ads]
command = "uvx"
args = ["--from", "git+https://github.com/zai-one/telegram-ads-mcp", "telegram-ads-mcp"]
env = { TG_ADS_ENV_FILE = "/path/to/telegram-ads.env" }
```

Claude Desktop `claude_desktop_config.json`: the same `mcpServers` block as Cursor. Skills for Codex and other hosts: copy `skills/*` into `.agents/skills/`.

Skills: `telegram-ads-launch-campaign`, `telegram-ads-review-account`, `telegram-ads-diagnose-ad` (mirrored by the prompts). Guides on demand: `ads://guide/index` → `ads://guide/{topic}`.

Example asks: "Review my Telegram Ads cabinet", "Launch an ad for t.me/my_channel with CPM 0.5 and budget 5 Gram", "Why does ad 35 get no views?", "Pause ad 35", "Show stats for ad 35 for its lifetime".

## Tools

| Area | Tools |
| --- | --- |
| Auth | `check_session` `reload_session` `list_accounts` `select_account` `get_account` |
| Ads | `get_ads` `get_ad` `get_ad_stats` `create_ad` `edit_ad` `delete_ad` `clone_ad` `launch_ad` `check_ad_post` `send_target_to_review` |
| Creatives | `upload_media` `preview_ad` |
| Targeting | `search_targets` `get_targeting_reference` |
| Other | `manage_audience` `manage_event` `manage_funds` `save_api_settings` `revoke_token` `log_out` |
| Updates | `check_update` |

Always create ads `on_hold`. `budget="0"` cannot go to review. Amounts are Gram strings. Search ads: no text / picture / media. `launch_ad` does not activate; it adds budget and sends review. Do not combine `langs` with specific `channels`.

**Updates.** `check_update` compares your version with the [latest release](https://github.com/zai-one/telegram-ads-mcp/releases) and returns the release notes link plus the command to run (`git pull --ff-only && uv sync` in a clone, otherwise `pip install --upgrade "telegram-ads-mcp @ git+…@vX"`). `run_in` says where to run it. It only suggests and never installs. Only plain version tags (`v1.2.3`) are accepted. One anonymous GitHub API call, 3 s timeout, cached 24 h; after a failed call it waits 30 min, and `force=true` re-checks at most once a minute; offline returns `status: unavailable`. When the cache knows of a newer release, `check_session` adds `update_hint` and the server instructions get one line. At startup (stdio and HTTP alike) the server itself calls `api.github.com` anonymously, at most once a day, unless disabled; for a server or firewalled deployment set `TG_ADS_DISABLE_UPDATE_CHECK=1` in `.env` or the process environment.

## Issues

I'm working on this. If something is missing or broken, [open an issue](https://github.com/zai-one/telegram-ads-mcp/issues/new/choose). I will patch **this** repo.

Use the form. Tick both “no cookies / no hashes” boxes. Never paste `stel_token`, `stel_ssid`, `.env`, `confirm_hash`, API `hash=`, or DevTools screenshots.

Local draft: `uv run python scripts/check_security.py --issue draft.md` — prints `gh issue create` only if the draft is clean. It does not open the Issue.

Support is **not guaranteed**. Issues are read when I can.

Need **EUR** or **Stars** cabinets (not live here)? Write on Telegram: [t.me/zai_one](https://t.me/zai_one). We can talk about access. Do not send cookies in the GitHub issue.

## Built by ZAI.ONE

[ZAI.ONE](https://zai.one) is a digital agency working on websites, SEO, advertising and analytics. We also build tools that connect AI assistants to everyday work. [Talk to us on Telegram](https://t.me/zai_one) about setup, automation or an integration for your team.

LicenseRef-ZAI-ONE · [LICENSE](LICENSE) · [SECURITY.md](SECURITY.md) · [open an issue](https://github.com/zai-one/telegram-ads-mcp/issues/new/choose)
