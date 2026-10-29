---
project: neurogate
public: true
type: design
audience: students
title: Один путь — бот, 3 ключа, одна команда
summary: Сайт и бот стали в разы короче. Больше нет уровней «Старт» и «Прокачка» и выбора «ещё ключи / хватит» — бот спрашивает Mac или Windows, даёт по одной кнопке на каждый из трёх ключей и сразу выдаёт одну команду под твой компьютер. Команда сама ставит и приложение OpenCode.
user_impact: Ученики не теряются в кнопках и текстах и не застревают на встроенных Free-моделях OpenCode, которые быстро упираются в общий лимит. Скачивать OpenCode руками больше не нужно.
screenshots: []
checks:
  - .venv/bin/python -m pytest -q tests/  (100 passed)
  - uvx ruff check src/neurogate/keybot.py tests/test_keybot.py
  - bash -n install.sh
  - монтирование dmg OpenCode и копирование OpenCode.app проверено на Mac
deploy_url: https://neurogate.nurtech.dev
---

## Что изменилось
- Сайт: один экран с кнопкой «Начать в боте», три шага, команда для подписчиков и короткая помощь.
- Бот: выбор Mac/Windows → «Ключ 1 из 3» с одной кнопкой «Получить ключ» → после третьего ключа сразу команда только под выбранную систему. Пропуск — /skip.
- install.sh на Mac сам скачивает и ставит OpenCode в «Программы» до подключения; install.ps1 на Windows ставит его тихо (/S).

## Где проверить
- https://neurogate.nurtech.dev
- @nurtechneurogatebot → /start

## Риски
- Тихая установка OpenCode на Windows ещё не запускалась на живой Windows; при сбое установщик открывается обычным окном.
