<!-- generated from AGENTS.md by scripts/sync_skills.py; do not edit -->

## Auth

Cookies only in gitignored `.env` (`STEL_TOKEN`, `STEL_SSID`). Never paste into chat, Issues, MCP `env`, or tool args. First call: `check_session`. Dead session: **offer** the INSTALL.md DevTools steps (do not ask them to paste values into chat). Chrome/Edge Windows: stay logged in at https://ads.telegram.org → **F12** or **Ctrl+Shift+I** → **Application** (Edge: **Storage**) → Cookies → `https://ads.telegram.org` → copy `stel_token` / `stel_ssid` **into `.env` only**. Not Network headers, not telegram.org / web.telegram.org. Last resort is not a browser/CDP cookie dump into the transcript: the operator (or an agent that can write the gitignored file **without echoing contents**) updates `.env`, then `reload_session` → `check_session` (no cookie args). Never `log_out` / `revoke_token` to “fix” auth — `revoke_token` is the IP-whitelist **API** token, not cookies. Do not file an Issue to “fix” a dead session. DevTools dumps still forbidden in Issues.

Money and IDs are strings. Multi-IDs are semicolon-separated.
