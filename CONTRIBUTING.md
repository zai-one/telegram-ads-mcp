# Contributing to tg-ads-mcp

Thanks for your interest! This is a small, focused project — a thin MCP wrapper
over the `ads.telegram.org` internal API. Contributions that keep it simple and
well-documented are very welcome.

## Development setup

```bash
git clone https://github.com/NikitaZhidkov/tg-ads-mcp.git
cd tg-ads-mcp
uv sync
cp .env.example .env   # then fill in your ads.telegram.org cookies
```

Run the server standalone to sanity-check it:

```bash
uv run server.py
```

## Project layout

| File          | Responsibility                                                        |
| ------------- | --------------------------------------------------------------------- |
| `server.py`   | MCP tool definitions — one `@mcp.tool()` function per capability.      |
| `client.py`   | `TelegramAdsClient` — HTTP, cookie auth, HTML/JSON parsing.            |
| `AGENTS.md`   | Playbook for LLM agents using the server. Update it when flows change. |

## Adding or changing a tool

1. Add a new `@mcp.tool()` function in `server.py`. Keep the wrapper thin: build
   params, call `client.call(...)`, return `json.dumps(result, ensure_ascii=False)`.
2. **The docstring is the agent-facing spec.** Document every argument, note which
   cabinet (TON / EUR) a field applies to, and flag any two-step `confirm_hash`
   flow. Agents only see the docstring — if it's wrong, the agent is wrong.
3. If the tool adds or changes a user-visible workflow, update `AGENTS.md`.
4. Update the tool list and the `~N tools` count in `README.md`.

## Conventions

- **Money and IDs are strings**, never numbers (`cpm="0.15"`, not `0.15`).
- **Multi-value params are semicolon-separated** (`"id1;id2"`), never comma.
- **Never swallow errors.** Let `AuthError` and validation errors surface to the
  caller — the platform's error messages are usually specific enough to act on.
- **Cabinet-aware wording.** TON cabinets bill in TON, EUR (reseller) cabinets in
  EUR. Don't hardcode "TON" in a docstring for a field that also runs on EUR.

## Security — never commit credentials

`STEL_TOKEN` / `STEL_SSID` are equivalent to a full login to your ad account.
`.env` is git-ignored; keep it that way. Never paste cookies into an issue, PR,
screenshot, or test fixture.

## Pull requests

- One logical change per PR; keep the diff focused.
- Describe what you changed and, for a new tool, which `ads.telegram.org` method
  it wraps.
- Confirm `uv run server.py` still starts and `uv build` still succeeds.
