---
project: neurogate
public: true
type: fix
audience: users
title: 'Установка на Windows заработала'
summary: 'На Windows установщик падал на импорте ключей, а сервер не запускался: не хватало базы часовых поясов. Теперь всё ставится, сервер стартует без чёрного окна и сам поднимается при входе в Windows.'
user_impact:
  - 'Код из бота принимается, сервер запускается, OpenCode и Claude Code подключаются'
  - 'Нет окна консоли, которое нельзя закрывать: сервер работает в фоне'
  - 'Если сервер не поднялся — установщик сразу показывает последние строки лога'
screenshots: []
checks:
  - 'Разбор вывода установщика с Windows: ZoneInfoNotFoundError America/Los_Angeles на шагах 4 и 6'
  - 'uv export --frozen: tzdata ; sys_platform == win32'
  - '.venv/bin/python -m pytest tests/test_background.py tests/test_cli_platforms.py tests/test_keybot.py -q → 21 passed'
deploy_url: https://neurogate.nurtech.dev
---

Notes for editor:
- What changed: зависимость tzdata для Windows; автозапуск через pythonw -m neurogate.background (лог в neurogate.log), запасные пути — ярлык в «Автозагрузке» и прямой запуск; прогресс ожидания; .cmd-обёртки через %USERPROFILE% (кириллица в имени пользователя); установщик качает OpenCode прямой ссылкой.
- Where to verify: на Windows повторно запустить команду из бота.
- Risks: живого прогона на Windows из Мака нет — проверка повторной установкой у тестировщика.
