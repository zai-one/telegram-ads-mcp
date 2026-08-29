# Backlog

Items not done in 0.2.0. Live checks live in [OFFLINE.md](./OFFLINE.md).

- [ ] Live-verify `create_audience` / `manage_audience(action="create", file_path=...)` against `/file/upload`.
- [ ] `save_account_info` with an explicit field allowlist (email, name, company, phone, website). Not restored from the kwargs tool.
- [ ] `revoke_stats_url`.
- [ ] Pin `upload_media` `target` once a TON cabinet confirms which name the platform wants.
- [ ] Optional Playwright capture of the real “Preview Ad” UI (Pillow card is the default).
- [ ] Confirm `audience_id` is honored on `createAd` / `editAd`.
- [ ] Tune Stars detection if a real Stars HTML dump disagrees with `currency=XTR`.
- [ ] MCP elicitation for `confirm_hash` (user asked not to restrict destructive tools; elicitation would only prompt, not block).
