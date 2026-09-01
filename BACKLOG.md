# Backlog

Live checks: [OFFLINE.md](./OFFLINE.md). Playbook: [AGENTS.md](./AGENTS.md).

## Improvement / speed (from Gram live read-only)

Done in tree (not a new tool family): Gram balance widget, TON≠EUR when `value=users`, Active/Stopped filter, stats spend ÷1e6 plus echoed request `period` / scaled `charts.budget` / `spend_already_scaled`, `tme_path`/`trg_type` mapping, skip `/account/budget` and `/account/ad/new` when `/account` already has `currency-ton`, `get_targeting_reference` on TON, `AGENTS.md` in the wheel, `hash=` query redaction, JSON `accounts` before chooser hrefs, structured `access_denied` on audience/event.

Still open:

- [ ] `getAd` JSON method returns **HTTP 400** on the live Gram cabinet — keep list/HTML fallback; pin if Telegram adds the method.
- [ ] `manage_audience` / `manage_event` `action=list` → **Access denied** on this cabinet. MCP returns `code: access_denied` `hint: skip` (do not retry). Confirm on a cabinet that has the UI.
- [ ] `searchBot("telegram")` → Username not found — playbook says use a real bot username.
- [ ] Pin `upload_media` `/file/upload` `target` (`media` / `adMedia` / `ad_media` / `picture`) on a live TON upload (write — operator-approved).
- [ ] Confirm `audience_id` on `createAd` / `editAd` (write).
- [ ] Optional Playwright capture of official Preview Ad UI (Pillow card is default).
- [ ] MCP elicitation for `confirm_hash` (prompt, do not block).
- [ ] `save_account_info` allowlist (email, name, company, phone, website) if needed.
- [ ] `revoke_stats_url` if shared stats links come back.
- [ ] Tune Stars detection if a real Stars HTML dump disagrees with `XTR`.

## Not doing

- Strategy-optimizer / bidding bot as extra tools (rules live in AGENTS.md).
- Growing past 28 tools or restoring `edit_ad_title` / `save_ads_columns` / `create_user_ad` / cookie args.
- Campaign-setup SaaS / HTTP job runner in this repo. Contracts (`telegram_ads_mcp/schemas/`) stay here so a later service can be a thin caller.
