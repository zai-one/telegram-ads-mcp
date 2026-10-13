<!-- generated from AGENTS.md by scripts/sync_skills.py; do not edit -->

## Create (always on_hold)

Prefer `launch_ad`. It does **not** activate. It **does** add budget (default `"1"` Gram) and `send_target_to_review`. Name cpm + budget + `target_type` first. If `steps.validate` fails, stop. Optional targeting on `launch_ad`: `topics`, `exclude_topics` / `exclude_channels`, `locations`, user excludes. Do **not** send `langs` together with specific `channels` (platform Target invalid) — the tool drops `langs` in that case. Full field set remains on `create_ad`.

Search ads: no text/picture/media. IDs from `search_targets` / `get_targeting_reference` (semicolon IDs, not @names). `target_type` immutable — `clone_ad`. Pause: `edit_ad(active="on_hold")`. Go live: `edit_ad(active="active")` only if asked. Budget: `budget_action` + `budget_amount` (not `budget=`). Increasing budget on Stopped **resumes delivery** — spend class (`confirm`/`strict` need `confirm=true`).
