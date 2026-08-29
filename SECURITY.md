# Security

`STEL_TOKEN` / `STEL_SSID` are a full login to the advertiser cabinet. Anyone holding them can spend the balance.

- Keep them in `.env` (gitignored). Never commit, never paste into chat, **GitHub issues**, PRs, or tool arguments. Use the issue form; contact for EUR/Stars is https://t.me/zai_one only.
- `reload_session` re-reads `.env`. There is no `update_cookies` tool.
- `check_session` does not return `api_hash`.
- Logs go to stderr with cookie/hash redaction. Do not attach raw logs to tickets.
- This project scrapes an unofficial web API. Telegram may invalidate sessions, change HTML, or restrict accounts. Use at your own risk; follow the [Ad Guidelines](https://ads.telegram.org/guidelines) and [Terms](https://ads.telegram.org/tos).
- Stars cabinets are refused by HTML heuristics. We do not have a Stars cabinet, so that path is not live-tested.
- Cabinet money is **Gram**. `target_type=users` is valid. Do not call the currency TON.
