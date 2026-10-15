<!-- generated from telegram_ads_mcp/PLAYBOOK.md by scripts/sync_skills.py; do not edit -->

## Danger

- Spend: `launch_ad`, `send_target_to_review`, `edit_ad(budget_action=…)` / activate.
- `manage_funds`: `list`/`search` = lookup. `add` = top-up *request*. `transfer`/`withdraw` **move money in that one call** — no platform `confirm_hash`. Never guess `account_id`.
- Platform `confirm_hash` (two HTTP steps): `delete_ad`, `clone_ad`, `manage_audience` delete|clone, `manage_event` delete. Call 1 without hash; call 2 with the returned hash after yes (`open` may do both). Do not invent or print hashes. Gate `confirm=` is a different flag.
- One-shot DEST (no hash): `manage_funds` add/transfer/withdraw, `log_out`, `revoke_token`, `save_api_settings`.
- `preview_ad` writes gitignored `previews/*.png` — do not commit.
- Access denied on audience/event: tool returns `code: "access_denied"`, `hint: "skip"`. Do not retry. getAd 400: use fallback, do not probe JSON again.
