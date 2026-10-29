---
project: neurogate
public: true
type: fix
audience: users
title: 'Windows: оркестратор, переустановка и подсказки'
summary: 'На Windows neurogate теперь находится из Claude Code (Git Bash), длинные задачи доходят до исполнителя целиком, повторная установка не ломается об работающий сервер, а подключение к OpenCode объяснено прямо в установщике и на сайте.'
user_impact:
  - 'Режим оркестратора в Claude Code на Windows: команды neurogate, claude-free и codex-free находятся'
  - 'Многострочные задачи: neurogate delegate --file / ask --file, на Windows задача больше не обрезается'
  - 'Повторный запуск установщика сначала останавливает старый сервер — обновление не падает'
  - 'claude-free в окне cmd больше не «заражает» обычный claude настройками neurogate'
screenshots: []
checks:
  - '.venv/bin/python -m pytest tests -q → 97 passed'
  - 'install.sh целиком в изолированном HOME (NEUROGATE_NO_AUTOSTART=1, репозиторий из локальной копии) → exit 0, обёртки на месте'
  - 'neurogate ask --file с вопросом из двух строк → ответ от бесплатной модели'
  - 'Два независимых ревью кода под Windows PowerShell 5.1 и macOS'
deploy_url: https://neurogate.nurtech.dev
---

Notes for editor:
- What changed: sh-обёртки для Git Bash рядом с .cmd; setlocal в .cmd; --file у delegate/ask, задача через файл для npm-шимов .cmd; остановка старого сервера до uv sync и проверка его кода; .env без порчи кодировки; перезапуск без планировщика (ярлык автозагрузки); CLI-провайдеры сервера на Windows берут только .exe (npm .cmd пропускаются — иначе текст чата шёл бы в cmd.exe); install.sh не обрывается на сбое подключения одной программы.
- Where to verify: Windows — повторный запуск команды из бота; Claude Code в Git Bash — `neurogate doctor`.
- Risks: живого прогона на Windows нет; OpenCode 2.x на Windows подключается к neurogate руками (нет pty для auth login).
