# telegram-ads-mcp

**Язык:** [English](README.md) · Русский

Неофициальный MCP-сервер для [Telegram Ads](https://ads.telegram.org/). В живом кабинете валюта — **Gram** (💎). EUR в коде есть. Кабинеты Stars сервер отказывается обслуживать.

[![tests](https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Built by ZAI.ONE](https://img.shields.io/badge/built%20by-ZAI.ONE-111111.svg)](https://zai.one)

Если полезно — **[поставь звезду](https://github.com/zai-one/telegram-ads-mcp)**.

Установка агентом: скопируй **[INSTALL.md](INSTALL.md)** в чат.

Cookies только в `.env` (gitignore). В чат не вставлять. К Telegram отношения не имеет. [SECURITY.md](SECURITY.md), [правила объявлений](https://ads.telegram.org/guidelines).

## Инструменты

Около 25 tools. Плейбук: `ads://playbook` ([AGENTS.md](AGENTS.md)).

- **Auth** — `check_session`, `reload_session`, `list_accounts`, `select_account`, `get_account` (баланс в Gram)
- **Объявления** — `get_ads`, `get_ad`, `get_ad_stats`, `create_ad`, `edit_ad`, `delete_ad`, `clone_ad`, `launch_ad`, `check_ad_post`, `send_target_to_review`
- **Креативы** — `upload_media`, `preview_ad`
- **Таргет** — `search_targets`, `get_targeting_reference` (гео `users` на Gram допустим)
- **Аудитории / события / деньги** — `manage_audience`, `manage_event`, `manage_funds` (суммы в Gram)
- **Кабинет** — `save_api_settings`, `revoke_token`, `log_out`

Stars: `get_account` может показать; мутации отдают `code: "stars_cabinet"`.

## Установка

Полный текст для агента — **[INSTALL.md](INSTALL.md)**. Коротко:

```bash
git clone https://github.com/zai-one/telegram-ads-mcp.git
cd telegram-ads-mcp
uv sync
cp .env.example .env   # stel_token и stel_ssid
```

```json
{
  "mcpServers": {
    "telegram-ads": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/telegram-ads-mcp", "run", "telegram-ads-mcp"]
    }
  }
}
```

HTTP: `uv run telegram-ads-mcp --transport streamable-http --host 127.0.0.1 --port 8000` → `http://127.0.0.1:8000/mcp`.

## Заметки

- Создавать объявления в `on_hold`. С `budget="0"` на модерацию не отправить. `target_type` после создания не меняется.
- Гео (`users`) на Gram-кабинете работает.
- Статус: `"active"` / `"on_hold"` (в UI: Active / Stopped).
- Деньги — строки в Gram.
- Поисковые объявления: без текста, картинки и media.

## ZAI.ONE

Сделано в [ZAI.ONE](https://zai.one) — интернет-агентство (стратегия, бренд, сайт, реклама, аналитика).

[zai.one](https://zai.one) · [contact@zai.one](mailto:contact@zai.one) · [Telegram](https://t.me/Zai_one_bot)

MIT — [LICENSE](LICENSE).
