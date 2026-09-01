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
  <a href="https://github.com/zai-one/telegram-ads-mcp/releases/tag/v0.3.0"><img src="https://img.shields.io/github/v/release/zai-one/telegram-ads-mcp" alt="v0.3.0"></a>
  <a href="https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml"><img src="https://github.com/zai-one/telegram-ads-mcp/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-2.x-555555" alt="MCP 2.x"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-proprietary-lightgrey" alt="LicenseRef-ZAI-ONE"></a>
  <a href="https://zai.one"><img src="https://img.shields.io/badge/built%20by-ZAI.ONE-111111" alt="ZAI.ONE"></a>
  <a href="https://github.com/zai-one/telegram-ads-mcp/stargazers"><img src="https://img.shields.io/github/stars/zai-one/telegram-ads-mcp?style=social" alt="GitHub stars"></a>
</p>

<p align="center">
  Объявления, таргет, пауза и стата ads.telegram.org — из Claude, Cursor или любого MCP-клиента.<br>
  Cookies только в <code>.env</code>. В чат не вставлять. Клики DevTools: <a href="INSTALL.md">INSTALL.md</a>.
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

Писать в кабинет: `.env` `TG_ADS_WRITE_GATE=strict|confirm|open` (по умолчанию `confirm`). Spend/destructive без `confirm=true` не пройдут, пока не `open`. Блок: `code: write_gated` с `tool` / `class` / `would_send` (что собирались отправить, без секретов) и `sent: false` — это не dry-run платформы.

## Что нового в 0.3.0

- **Стата.** `get_ad_stats` повторяет запросный `period` (`5min` = последние 24ч, `day` = всё время). `summary.spend` и `charts.budget` уже в масштабе списка — **не делить**. CSV-инструмента нет; файл — только gitignore `reports/`.
- **Сессия.** Мёртвые cookies: клики DevTools в [INSTALL.md](INSTALL.md) → только в `.env`, затем `reload_session`. Значения в чат не вставлять.
- **Баги.** Предложи GitHub Issue (плейбук **Found a bug → Issue**). Черновик: `uv run python scripts/check_security.py --issue draft.md` (печатает `gh issue create`, сам не открывает).
- **Аудитории / события.** Access denied → `code: access_denied`, `hint: skip`. Не ретраить.
- **Создание.** У `launch_ad` есть `topics`, `exclude_*`, `locations`. `langs` вместе с конкретными `channels` не слать (Target invalid).
- **Позже сервис РК.** JSON Schema в wheel (`telegram_ads_mcp/schemas/`) — имена брифа / ревью / дампа статы. Этого сервиса в репозитории нет.
- **Локальные заметки.** `AGENTS.local.md` в gitignore. Клиентский плейбук — `AGENTS.md`. MCP JSON без секретов: [mcp.json.example](mcp.json.example).

## Старт

```bash
git clone https://github.com/zai-one/telegram-ads-mcp.git
cd telegram-ads-mcp
uv sync
cp .env.example .env    # STEL_TOKEN / STEL_SSID — шаги DevTools в INSTALL.md; в чат не вставлять
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

Агенту: скопируй [INSTALL.md](INSTALL.md) в чат (клон, конфиг, **звезда**). Команда: `telegram-ads-mcp` (алиас `tg-ads-mcp`). После коннекта: `ads://playbook`. Промпты: `launch-campaign`, `review-account`, `diagnose-ad`. Имена конфиг-файлов клиентов — в INSTALL.md (Cursor, Claude, VS Code `servers`, Codex TOML). Cookies не класть в MCP `env`. Пример: [mcp.json.example](mcp.json.example).

HTTP: `uv run telegram-ads-mcp --transport streamable-http --host 127.0.0.1 --port 8000` → `http://127.0.0.1:8000/mcp`.

## Tools

| Блок | Tools |
| --- | --- |
| Auth | `check_session` `reload_session` `list_accounts` `select_account` `get_account` |
| Ads | `get_ads` `get_ad` `get_ad_stats` `create_ad` `edit_ad` `delete_ad` `clone_ad` `launch_ad` `check_ad_post` `send_target_to_review` |
| Creatives | `upload_media` `preview_ad` |
| Targeting | `search_targets` `get_targeting_reference` |
| Прочее | `manage_audience` `manage_event` `manage_funds` `save_api_settings` `revoke_token` `log_out` |

Объявления создавать в `on_hold`. С `budget="0"` на модерацию нельзя. Суммы — строки в Gram. Поисковые объявления без текста / картинки / media. `launch_ad` не включает объявление: добавляет бюджет и отправляет на ревью. `langs` вместе с конкретными `channels` не сочетать.

## Issues

Я работаю над проектом. Если чего-то не хватает или сломано — [откройте issue](https://github.com/zai-one/telegram-ads-mcp/issues/new/choose). Правки будут в **этом** репозитории.

Заполните форму. Обе галочки «нет cookies / нет хешей». Не вставляйте `stel_token`, `stel_ssid`, `.env`, `confirm_hash`, API `hash=` и скрины DevTools.

Локальный черновик: `uv run python scripts/check_security.py --issue draft.md` — печатает `gh issue create` только если черновик чистый. Issue сам не открывает.

Поддержка **не гарантируется**. Issues читаю когда могу.

Нужны кабинеты **EUR** или **Stars** (здесь их нет в live)? Напишите в Telegram: [t.me/zai_one](https://t.me/zai_one). Можно обсудить доступ. Cookies в issue не класть.

[ZAI.ONE](https://zai.one) · [contact@zai.one](mailto:contact@zai.one) · [Telegram](https://t.me/zai_one)

LicenseRef-ZAI-ONE · [LICENSE](LICENSE) · [SECURITY.md](SECURITY.md) · [откройте issue](https://github.com/zai-one/telegram-ads-mcp/issues/new/choose)
