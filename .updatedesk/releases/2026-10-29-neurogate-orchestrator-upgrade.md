---
project: neurogate
public: true
type: feature
audience: users
title: 'Правило оркестратора обновляется одной командой'
summary: 'Повторный запуск `neurogate connect orchestrator` теперь обновляет правило в CLAUDE.md и AGENTS.md до новой версии, не трогая ваш текст. В новой версии — передача длинных задач файлом.'
user_impact:
  - 'Подписчики получают улучшения режима оркестратора без ручной правки файлов'
  - 'Длинная задача: neurogate delegate --file задача.md — есть в шпаргалке на сайте'
  - 'Установщик Windows не оставляет свои настройки в окне PowerShell и не ждёт ввода, если терминала нет'
screenshots: []
checks:
  - '.venv/bin/python -m pytest tests -q → 98 passed'
deploy_url: https://neurogate.nurtech.dev
---

Notes for editor:
- What changed: блок оркестратора с закрывающей меткой; старые блоки (до «`neurogate doctor`.») заменяются; install.ps1 в блоке & { } с Push/Pop-Location, мастер ключей пропускается без терминала; итог установки на Windows говорит про ручное подключение в OpenCode; документация и шпаргалка про --file.
- Where to verify: `neurogate connect orchestrator --global` дважды — «обновлено», затем «уже есть».
- Risks: свой изменённый вариант блока без строки про doctor не трогается («свой вариант — не трогаю»).
