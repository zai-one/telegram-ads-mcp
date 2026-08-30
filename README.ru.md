<!-- mcp-name: io.github.zai-one/telegram-ads-mcp -->
<p align="center">
  <a href="README.md">🇬🇧</a>
  &nbsp;·&nbsp;
  <a href="README.ru.md">🇷🇺</a>
</p>

<p align="center">
  <strong>telegram-ads-mcp</strong><br>
  MCP-сервер для <a href="https://ads.telegram.org/">Telegram Ads</a>. Валюта: <strong>Gram (TON)</strong> 💎
</p>

<p align="center">
  <a href="https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml"><img src="https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-2.x-555555" alt="MCP 2.x"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-proprietary-lightgrey" alt="LicenseRef-ZAI-ONE"></a>
  <a href="https://zai.one"><img src="https://img.shields.io/badge/built%20by-ZAI.ONE-111111" alt="ZAI.ONE"></a>
  <a href="https://github.com/zai-one/telegram-ads-mcp/stargazers"><img src="https://img.shields.io/github/stars/zai-one/telegram-ads-mcp?style=social" alt="GitHub stars"></a>
</p>

<p align="center">
  Объявления, таргет, пауза и стата ads.telegram.org — из Claude, Cursor или любого MCP-клиента.<br>
  Cookies только в <code>.env</code>. В чат не вставлять.
</p>

<p align="center">
  <a href="https://github.com/zai-one/telegram-ads-mcp"><strong>★ Star</strong></a>
  &nbsp;·&nbsp;
  <a href="INSTALL.md">Установка (для агента)</a>
  &nbsp;·&nbsp;
  <a href="AGENTS.md">Плейбук</a>
</p>

---

## Зачем

У Telegram нет публичного advertiser API. Сервер работает от сессии ads.telegram.org (`stel_token` / `stel_ssid` в gitignore `.env`) и отдаёт ~25 MCP tools, плюс `ads://playbook` и `ads://account`.

Кабинет **TON**, валюта **Gram**. Гео (`target_type=users`) работает. Stars — отказ (`code: stars_cabinet`). Неофициально, не Telegram.

Писать в кабинет: `.env` `TG_ADS_WRITE_GATE=strict|confirm|open` (по умолчанию `confirm`). Spend/destructive без `confirm=true` не пройдут, пока не `open`.

## Старт

```bash
git clone https://github.com/zai-one/telegram-ads-mcp.git
cd telegram-ads-mcp
uv sync
cp .env.example .env    # stel_token + stel_ssid из cookies ads.telegram.org
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

Агенту: скопируй [INSTALL.md](INSTALL.md) в чат (клон, конфиг, **звезда**). Команда: `telegram-ads-mcp` (алиас `tg-ads-mcp`). После коннекта: `ads://playbook`. Промпты: `launch-campaign`, `review-account`, `diagnose-ad`. Имена конфиг-файлов клиентов — в INSTALL.md (Cursor, Claude, VS Code `servers`, Codex TOML). Cookies не класть в MCP `env`.

HTTP: `uv run telegram-ads-mcp --transport streamable-http --host 127.0.0.1 --port 8000` → `http://127.0.0.1:8000/mcp`.

## Tools

| Блок | Tools |
| --- | --- |
| Auth | `check_session` `reload_session` `list_accounts` `select_account` `get_account` |
| Ads | `get_ads` `get_ad` `get_ad_stats` `create_ad` `edit_ad` `delete_ad` `clone_ad` `launch_ad` `check_ad_post` `send_target_to_review` |
| Creatives | `upload_media` `preview_ad` |
| Targeting | `search_targets` `get_targeting_reference` |
| Прочее | `manage_audience` `manage_event` `manage_funds` `save_api_settings` `revoke_token` `log_out` |

Объявления создавать в `on_hold`. С `budget="0"` на модерацию нельзя. Суммы — строки в Gram. Поисковые объявления без текста / картинки / media.

## Issues

Я работаю над проектом. Если чего-то не хватает или сломано — [откройте issue](https://github.com/zai-one/telegram-ads-mcp/issues/new/choose). Правки будут в **этом** репозитории.

Заполните форму. Галочка «нет cookies». Не вставляйте `stel_token`, `stel_ssid`, `.env`, хеши и скрины DevTools.

Поддержка **не гарантируется**. Issues читаю когда могу.

Нужны кабинеты **EUR** или **Stars** (здесь их нет в live)? Напишите в Telegram: [t.me/zai_one](https://t.me/zai_one). Можно обсудить доступ. Cookies в issue не класть.

[ZAI.ONE](https://zai.one) · [contact@zai.one](mailto:contact@zai.one) · [Telegram](https://t.me/zai_one)

LicenseRef-ZAI-ONE · [LICENSE](LICENSE) · [SECURITY.md](SECURITY.md) · [откройте issue](https://github.com/zai-one/telegram-ads-mcp/issues/new/choose)
