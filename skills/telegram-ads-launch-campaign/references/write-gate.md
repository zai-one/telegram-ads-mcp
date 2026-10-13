<!-- generated from AGENTS.md by scripts/sync_skills.py; do not edit -->

## Write gate (`.env`)

`TG_ADS_WRITE_GATE=strict|confirm|open` (default **confirm**). Echoed on `check_session` / `get_account` as `write_gate`.

| Gate | Without `confirm=true` | Needs `confirm=true` |
| --- | --- | --- |
| `strict` | reads + `reload_session` | every WRITE/DEST |
| `confirm` | reads + pause/CPM/create `on_hold` budget `0` + `list`/`search` on audience/event/funds | spend, review, activate, funds add/transfer/withdraw, delete, log_out, revoke, IP whitelist |
| `open` | all of the above | nothing extra (Stars still refused; cookies still `.env` only) |

Blocked call: `code: "write_gated"` with `tool`, `class`, `would_send` (intended args, no secrets), `sent: false`. Not a platform dry-run. Show the operator, re-call with `confirm=true`.

Two jobs — do not mix unless they asked both: **cabinet** (`review-account`) vs **this git repo**.
