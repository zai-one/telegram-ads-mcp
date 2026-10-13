<!-- generated from AGENTS.md by scripts/sync_skills.py; do not edit -->

## Errors

Failures return `ok: false`, `error` (text), `code`, `retryable`, `hint`, `docs` (`ads://guide/errors#<code>`). Retry only when `retryable` is true; otherwise follow `hint`.

| `code` | Meaning | Do |
| --- | --- | --- |
| `config` | `.env` cookies missing | INSTALL.md → user edits `.env` → `reload_session` |
| `auth` | session dead | same as `config`; never `log_out` / `revoke_token` |
| `stars_cabinet` | Stars cabinet active | `list_accounts` → `select_account` |
| `write_gated` | gate blocked a write (`sent: false`) | show `would_send`, re-call with `confirm=true` after yes |
| `access_denied` | audience/event not allowed | `hint: skip`, do not retry |
| `error` | unexpected | retry once, then offer an Issue |
