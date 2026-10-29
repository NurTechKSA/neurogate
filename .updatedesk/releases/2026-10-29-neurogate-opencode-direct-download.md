---
project: neurogate
public: true
type: feature
audience: users
title: 'OpenCode скачивается в один клик'
summary: 'На сайте neurogate.nurtech.dev и в боте @nurtechneurogatebot теперь прямые кнопки скачивания OpenCode Desktop для Mac и Windows — искать нужный файл на чужом сайте больше не надо.'
user_impact:
  - 'Ученик нажимает «Скачать для Mac» или «Скачать для Windows» и сразу получает установщик'
  - 'Отдельные кнопки для Mac на Intel и Windows на ARM с подсказкой, как узнать свой вариант'
screenshots: []
checks:
  - 'curl -sIL https://opencode.ai/download/stable/{darwin-aarch64-dmg,darwin-x64-dmg,windows-x64-nsis,windows-aarch64-nsis} → 200, файлы opencode-desktop 2.2.1'
  - '.venv/bin/python -m pytest tests/test_keybot.py tests/test_cli_platforms.py -q → 20 passed'
  - 'Страница проверена в браузере: кнопки меняются при выборе macOS/Windows'
deploy_url: https://neurogate.nurtech.dev
---

Notes for editor:
- What changed: кнопки прямого скачивания OpenCode Desktop (ссылки /download/stable/* всегда ведут на последнюю версию) на странице учеников, в сообщении бота после ключей и в docs/students.md.
- Where to verify: https://neurogate.nurtech.dev → путь A → шаг 01.
- Risks: если OpenCode сменит адреса /download/stable/*, кнопки сломаются — проверять при сверке моделей.
