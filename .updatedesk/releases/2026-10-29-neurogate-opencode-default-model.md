---
project: neurogate
public: true
type: fix
audience: students
title: В OpenCode сразу выбран neurogate
summary: Окно OpenCode открывало новую сессию на последней использованной модели — у тех, кто до установки пробовал встроенные Free-модели (Big Pickle, DeepSeek Free), она так и оставалась, и через час всплывало «лимит закончился». Теперь установка ставит neurogate первой моделью окна. Бот в конце подсказывает, как добавить ключи, когда лимитов станет мало.
user_impact: После установки и перезапуска OpenCode ученик сразу пишет через neurogate, а не упирается в лимит встроенной модели.
screenshots: []
checks:
  - .venv/bin/python -m pytest -q tests/  (101 passed)
  - на Маке владельца _select_opencode_desktop_model() → True, neurogate/code первая в «недавних»
deploy_url: https://neurogate.nurtech.dev
---

## Что изменилось
- `neurogate connect opencode` (его зовёт установщик) ставит neurogate/code первой в «недавние» модели окна OpenCode 2.x (drafts.sqlite в данных приложения на Mac, Windows и Linux). Нет базы или другой формат — шаг пропускается.
- `small_model` теперь neurogate/code: модели code_fast в списке провайдера не было.
- Бот: «Станет мало лимитов — снова /start: новый ключ добавится к старым».

## Где проверить
- Установить по команде из бота, перезапустить OpenCode, открыть новую сессию.

## Риски
- Пока OpenCode открыт, он может перезаписать свой выбор — поэтому после установки его нужно перезапустить (установщик это пишет).
- На Windows путь %APPDATA%\ai.opencode.desktop не проверен вживую.
