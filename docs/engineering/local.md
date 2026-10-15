# Project development guidance

- Python 3.10+; development is separate from cabinet operations.
- Cookies stay in local .env; preserve TG_ADS_WRITE_GATE, exact Gram/TON money and spend confirmation; never auto-push.
- Checks: `python -m pytest -q`; `python scripts/check_engineering.py --check`. Run install checks before release.

Read only the task-relevant public documentation. Personal workspace notes are optional and remain outside Git.

- [README](../../README.md): supported features and installation.
- [Contributing](../../CONTRIBUTING.md): development and release checks.

For cabinet operations use [the packaged playbook](../../telegram_ads_mcp/PLAYBOOK.md), not the development index. Update the playbook directly, run `python scripts/sync_skills.py` to regenerate, then `python scripts/sync_skills.py --check`. Preserve cookie custody, currency scaling, write gates and confirmation semantics.

- Mutate a live cabinet only when the operator requests that action; preserve cookie and spending gates.
- Preserve LicenseRef-ZAI-ONE and NOTICE; this package is not MIT and copying/redistribution needs the license authorization.
- Keep the tool-count budget 12–28; follow CONTRIBUTING for the full offline test/packaging checklist.
