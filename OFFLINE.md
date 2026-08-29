# Offline — what Grok Build could not finish

Do these on your machine against a real TON cabinet. The sandbox has no ads.telegram.org cookies and cannot push git tags or repo metadata.

## Must verify live (TON first, EUR if you have it)

1. **`uvx --from git+https://github.com/zai-one/tg-ads-mcp tg-ads-mcp`** after this is on `master`. Confirm the wheel imports `tg_ads_mcp.server:main`.
2. **`get_account` balance** — confirm the parsed number matches the UI on `/account` and `/account/budget`. If it's null, dump a redacted snippet of the page state (no cookies) and we can add another extractor key.
3. **`get_ad`** — the JSON method `getAd` may 404 on some cabinets. Fallback is HTML state then `getAdsList`. Confirm which source wins (`source` field in the result).
4. **`upload_media`** — tries targets `media`, `adMedia`, `ad_media`, `picture` on `/file/upload`. Live-test a 16:9 JPEG <5 MB and an MP4 3–60s. Note which `target` the platform accepts; we should pin it.
5. **`preview_ad`** — MCP image in Claude/Cursor chat. If the client strips images, confirm `previews/ad-*-*.png` is written. Optional: Playwright screenshot of the real UI preview to replace the Pillow card.
6. **`audience_id` on `create_ad` / `edit_ad`** — not documented by Telegram. If the platform ignores it, drop the field.
7. **`manage_audience(action="list")`** uses `updateAudiencesState`. Confirm it returns the list; if not, scrape `/account/audiences`.
8. **`manage_event(action="list")`** same for `updateEventsState`.
9. **EUR** — `target_type=users` + `get_targeting_reference`. Skip if you don't care.
10. **Stars** — `select_account` onto a Stars cabinet and confirm we refuse with `code: stars_cabinet` and still allow `list_accounts`. Tune `detect_cabinet` if a Stars page is misclassified as TON.
11. **`search_targets(kind="bot", purpose="target")`** uses `field=bots`. Confirm placements vs `purpose=promote` (`field=promote_url`).
12. **`create_audience` via `file_path`** — live upload of a user-id list. (Left as-is; `user_ids` writes a temp file.)
13. **`save_account_info`** — still not a tool (kwargs were a schema hole). If you need it, add an explicit allowlist: `email`, `name`, `company_name`, `phone`, `website`.
14. **`revoke_stats_url`** — dropped. Add back if you share stats links.

## GitHub / release (no API from here)

15. **Topics** on https://github.com/zai-one/tg-ads-mcp : `mcp`, `model-context-protocol`, `telegram`, `telegram-ads`, `ton`, `python`.
16. **Default branch** — still `master`. Rename to `main` if you want it aligned with grok-build-mcp; then fix CI (`branches: [master, main]` already accepts both).
17. **Tag `v0.2.0`** after you're happy with live tests: `git tag v0.2.0 && git push origin v0.2.0`. GitHub Release from CHANGELOG.
18. **Delete leftover root files** if the push did not: old `server.py`, `client.py`, `uv.lock` from 0.1.0. New lock: `uv lock` in this tree.
19. **README clone URL** — already `zai-one`. Confirm GitHub About description.
20. **PyPI** — optional. Name `tg-ads-mcp` may be free; don't publish until live tests pass.

## MCP 2 vs 1 (why we jumped)

SDK 2.1.1 implements spec **2026-07-28**: `MCPServer` (was FastMCP), Streamable HTTP without a handshake, `server/discover`, structured tool output, `ToolAnnotations`, `Image` helper, elicitation/sampling as resolvers. `pip install mcp` now installs 2.x; 1.x is security-fix only. Decorator `@mcp.tool()` survived. We pin `mcp>=2.1.1,<3`.

Clients still on MCP 1.x stdio generally keep working; remote HTTP clients should use streamable HTTP.

## If `github push` from this session failed

The rewritten tree is in this workspace under `tg-ads-mcp/`. Copy it over the clone:

```bash
cd ~/src
git clone https://github.com/zai-one/tg-ads-mcp.git
rsync -a --delete --exclude .git path/to/this/tg-ads-mcp/ tg-ads-mcp/
cd tg-ads-mcp
uv sync --extra test
uv run pytest
git add -A
git status   # old server.py / client.py should be deleted
git commit -m "0.2.0: MCP SDK 2, .env-only secrets, TON/EUR, Stars refused"
git push origin master
```
