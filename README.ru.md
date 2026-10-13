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
  <a href="https://github.com/zai-one/telegram-ads-mcp/releases/tag/v0.4.0"><img src="https://img.shields.io/github/v/release/zai-one/telegram-ads-mcp" alt="v0.4.0"></a>
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

У Telegram нет публичного advertiser API. Сервер работает от сессии ads.telegram.org (`stel_token` / `stel_ssid` в gitignore `.env`) и отдаёт 26 MCP tools, плюс `ads://playbook` и `ads://account`.

Кабинет **TON**, валюта **Gram**. Гео (`target_type=users`) работает. Stars — отказ (`code: stars_cabinet`). Неофициально, не Telegram.

Писать в кабинет: `.env` `TG_ADS_WRITE_GATE=strict|confirm|open` (по умолчанию `confirm`). Spend/destructive без `confirm=true` не пройдут, пока не `open`. Блок: `code: write_gated` с `tool` / `class` / `would_send` (что собирались отправить, без секретов) и `sent: false` — это не dry-run платформы.

## Что нового в 0.4.0

- **Обновления.** Новый `check_update` (26-й tool, только чтение) сравнивает вашу версию с последним релизом на GitHub и возвращает ссылку на заметки, исполняемую команду `update_command` и `run_in` (где её запускать). Только подсказывает, сам ничего не ставит. Если в кэше есть более новый релиз, `check_session` добавляет `update_hint`. Отключить: `TG_ADS_DISABLE_UPDATE_CHECK=1`.
- **Защита.** Принимаются только обычные теги версий (`v1.2.3`). Один анонимный запрос к GitHub API, таймаут 3 с, кэш 24 ч, пауза 30 мин после неудачи, `force=true` не чаще раза в минуту; без сети — `status: unavailable`.
- **SDK.** В `uv.lock` MCP Python SDK 2.3.0 (исправления, API для этого сервера не менялся).

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

## Установка где угодно (uvx, плагины)

Cookies живут только в файле `.env` на диске (не в `env` MCP и не в чате). Для uvx укажите путь к нему в `TG_ADS_ENV_FILE` (только путь) или запускайте клиент из папки с `.env`.

```bash
# Claude Code: только MCP
claude mcp add telegram-ads --env TG_ADS_ENV_FILE=/path/to/telegram-ads.env -- uvx --from git+https://github.com/zai-one/telegram-ads-mcp telegram-ads-mcp
# Claude Code: плагин = MCP + skills (запуск / обзор / диагностика)
/plugin marketplace add zai-one/telegram-ads-mcp
/plugin install telegram-ads@telegram-ads-mcp
```

Cursor: [установка в один клик](cursor://anysphere.cursor-deeplink/mcp/install?name=telegram-ads&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyItLWZyb20iLCJnaXQraHR0cHM6Ly9naXRodWIuY29tL3phaS1vbmUvdGVsZWdyYW0tYWRzLW1jcCIsInRlbGVncmFtLWFkcy1tY3AiXSwiZW52Ijp7IlRHX0FEU19FTlZfRklMRSI6Ii9wYXRoL3RvL3RlbGVncmFtLWFkcy5lbnYifX0=) или `.cursor/mcp.json`:

```json
{"mcpServers": {"telegram-ads": {"command": "uvx", "args": ["--from", "git+https://github.com/zai-one/telegram-ads-mcp", "telegram-ads-mcp"], "env": {"TG_ADS_ENV_FILE": "/path/to/telegram-ads.env"}}}}
```

Codex `~/.codex/config.toml`:

```toml
[mcp_servers.telegram-ads]
command = "uvx"
args = ["--from", "git+https://github.com/zai-one/telegram-ads-mcp", "telegram-ads-mcp"]
env = { TG_ADS_ENV_FILE = "/path/to/telegram-ads.env" }
```

Claude Desktop `claude_desktop_config.json`: тот же блок `mcpServers`, что и для Cursor. Skills для Codex и других хостов: скопируйте `skills/*` в `.agents/skills/`.

Skills: `telegram-ads-launch-campaign`, `telegram-ads-review-account`, `telegram-ads-diagnose-ad` (их зеркала — prompts). Справка по запросу: `ads://guide/index` → `ads://guide/{topic}`.

Примеры задач: «Сделай обзор кабинета Telegram Ads», «Запусти объявление для t.me/my_channel, CPM 0.5, бюджет 5 Gram», «Почему у объявления 35 нет показов?», «Поставь объявление 35 на паузу», «Покажи статистику объявления 35 за всё время».

## Tools

| Блок | Tools |
| --- | --- |
| Auth | `check_session` `reload_session` `list_accounts` `select_account` `get_account` |
| Ads | `get_ads` `get_ad` `get_ad_stats` `create_ad` `edit_ad` `delete_ad` `clone_ad` `launch_ad` `check_ad_post` `send_target_to_review` |
| Creatives | `upload_media` `preview_ad` |
| Targeting | `search_targets` `get_targeting_reference` |
| Прочее | `manage_audience` `manage_event` `manage_funds` `save_api_settings` `revoke_token` `log_out` |
| Обновления | `check_update` |

Объявления создавать в `on_hold`. С `budget="0"` на модерацию нельзя. Суммы — строки в Gram. Поисковые объявления без текста / картинки / media. `launch_ad` не включает объявление: добавляет бюджет и отправляет на ревью. `langs` вместе с конкретными `channels` не сочетать.

**Обновления.** `check_update` сравнивает вашу версию с [последним релизом](https://github.com/zai-one/telegram-ads-mcp/releases) и возвращает ссылку на заметки к релизу и команду (`git pull --ff-only && uv sync` в клоне, иначе `pip install --upgrade "telegram-ads-mcp @ git+…@vX"`). Где её запускать — в поле `run_in`. Только подсказывает, сам ничего не ставит. Принимаются только обычные теги версий (`v1.2.3`). Один анонимный запрос к GitHub API, таймаут 3 с, кэш на 24 ч; после неудачного запроса пауза 30 мин, а `force=true` перепроверяет не чаще раза в минуту; без сети — `status: unavailable`. Если в кэше есть более новый релиз, `check_session` добавляет `update_hint`, а в инструкции сервера попадает одна строка. При запуске (и stdio, и HTTP) сервер сам обращается к `api.github.com` анонимно, не чаще раза в сутки, если проверка не отключена; для серверной установки или закрытого контура задайте `TG_ADS_DISABLE_UPDATE_CHECK=1` в `.env` или в окружении процесса.

## Issues

Я работаю над проектом. Если чего-то не хватает или сломано — [откройте issue](https://github.com/zai-one/telegram-ads-mcp/issues/new/choose). Правки будут в **этом** репозитории.

Заполните форму. Обе галочки «нет cookies / нет хешей». Не вставляйте `stel_token`, `stel_ssid`, `.env`, `confirm_hash`, API `hash=` и скрины DevTools.

Локальный черновик: `uv run python scripts/check_security.py --issue draft.md` — печатает `gh issue create` только если черновик чистый. Issue сам не открывает.

Поддержка **не гарантируется**. Issues читаю когда могу.

Нужны кабинеты **EUR** или **Stars** (здесь их нет в live)? Напишите в Telegram: [t.me/zai_one](https://t.me/zai_one). Можно обсудить доступ. Cookies в issue не класть.

## Кто делает этот MCP

[ZAI.ONE](https://zai.one) — интернет-агентство: сайты, SEO, реклама и аналитика. Мы также создаём инструменты, которые подключают AI-ассистентов к рабочим задачам. [Напишите в Telegram](https://t.me/zai_one), чтобы обсудить настройку, автоматизацию или внедрение для вашей команды.

LicenseRef-ZAI-ONE · [LICENSE](LICENSE) · [SECURITY.md](SECURITY.md) · [откройте issue](https://github.com/zai-one/telegram-ads-mcp/issues/new/choose)
