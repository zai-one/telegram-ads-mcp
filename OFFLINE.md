# Offline — what still needs a real cabinet

Pushed as **0.2.0** on `master` (`db69ac8`). Topics set. CI workflow is in-tree.

Do these on your machine against a **TON** cabinet. The sandbox has no ads.telegram.org cookies.

## Live checks

1. **`uvx --from git+https://github.com/zai-one/tg-ads-mcp tg-ads-mcp`** — confirm the wheel starts (stdio). Put cookies in `.env`, Claude/Cursor config as in README (no `STEL_*` in the MCP `env` block).
2. **`get_account` balance** — must match the UI. If null, dump a redacted page-state snippet (no cookies).
3. **`get_ad`** — look at `source` (`getAd` / `html` / `getAdsList`).
4. **`upload_media`** — 16:9 JPEG <5 MB and MP4 3–60s. Note which `/file/upload` `target` the platform accepts (`media` / `adMedia` / `ad_media` / `picture`); we should pin it.
5. **`preview_ad`** — image in chat; also `previews/ad-*-*.png`. Pillow card, not the official UI screenshot.
6. **`audience_id` on create/edit** — if ignored, drop the field.
7. **`manage_audience(action="list")`** via `updateAudiencesState`.
8. **`manage_event(action="list")`** via `updateEventsState`.
9. **EUR** (optional) — `target_type=users` + `get_targeting_reference`.
10. **Stars** — `select_account` onto Stars, expect `code: stars_cabinet`, `list_accounts` still works.
11. **`search_targets(kind="bot", purpose="target")`** vs `purpose="promote"`.
12. **`create_audience` file_path** live upload. `user_ids` already writes a temp file.
13. **`save_account_info`** — not a tool. Allowlist if you need it: email, name, company_name, phone, website.
14. **`revoke_stats_url`** — dropped. Add back if you share stats links.

## After live tests pass

```bash
git tag v0.2.0
git push origin v0.2.0
# GitHub → Releases → paste CHANGELOG 0.2.0
```

Optional: rename default branch `master` → `main` (CI already listens to both). PyPI only after live tests.

## MCP 2 vs 1 (why we jumped)

SDK 2.1.1 = spec **2026-07-28**: `MCPServer` (was FastMCP), Streamable HTTP, structured output, `ToolAnnotations`, `ImageContent`. `pip install mcp` installs 2.x; 1.x is security-fix only. Pin is `mcp>=2.1.1,<3`. Stdio clients on the old protocol generally still work.
