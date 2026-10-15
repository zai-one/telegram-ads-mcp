# telegram-ads-mcp development

<!-- mcp-standard:begin version=1.0.8 sha256=6b82b27a398ff879c3b406af62daf4d87def673721da4f0fe4c5c3e4c80bef56 -->
- Follow the applicable workspace task and verification protocol when present.
- Preserve tool names, schemas, defaults and existing local work; document intentional compatibility changes.
- Enforce principal/account/target scopes and budgets on every path, including new tools, aliases, batches and metadata reads.
- Keep approval consumption, cost reservation and idempotency atomic; reconcile unknown outcomes before retrying writes or paid calls.
- Preserve server approval policy and the user's granted authority; never self-approve, widen access or expose secrets in errors/logs.
- Preserve units, dates, filters, pagination and continuation in compact output; label partial results explicitly.
- Use offline synthetic tests; report the checked revision, results and unrun checks. Visibility is not authorization.
- Read [contracts](docs/engineering/contracts.md) for API/tools, transport, output or packaging changes.
- Read [safety](docs/engineering/safety.md) for authorization, secrets, money, writes, retries or concurrent state.
- Read [releases](docs/engineering/releases.md) for releases, upstream integration or runtime verification.
- Read [project guidance](docs/engineering/local.md) for the relevant subsystem; use its linked topics only as needed.
- If `AGENTS.local.md` exists, read its short private workspace notes; never publish personal configuration.
<!-- mcp-standard:end -->

## Local profile
- Python 3.10+; development is separate from cabinet operations.
- Cookies stay in local .env; preserve TG_ADS_WRITE_GATE, exact Gram/TON money and spend confirmation; never auto-push.
- Checks: `python -m pytest -q`; `python scripts/check_engineering.py --check`. Run install checks before release.
