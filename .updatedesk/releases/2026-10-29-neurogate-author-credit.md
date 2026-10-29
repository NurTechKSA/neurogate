---
project: neurogate
public: true
type: docs
audience: students
title: Указали автора neurogate — Мансура (Basalt Code)
summary: На сайте появился блок «neurogate создал Мансур» со ссылками на его канал SINGULAR, контакт @abu_js и исходный код. Благодарность автору есть и в конце бота, в итоге установки и в README.
user_impact: Ученики знают, кто сделал шлюз, и могут подписаться на канал автора.
screenshots: []
checks:
  - .venv/bin/python -m pytest -q tests/test_keybot.py
  - bash -n install.sh
deploy_url: https://neurogate.nurtech.dev
---

## Что изменилось
- Сайт: блок «// автор» перед подвалом, в подвале — «автор Мансур, Basalt Code».
- Бот: строка благодарности в последнем сообщении с командой.
- install.sh / install.ps1: строка об авторе в итоге установки.
- README: автор и ссылка на исходный репозиторий basaltcode/neurogate.

## Где проверить
- https://neurogate.nurtech.dev#author
