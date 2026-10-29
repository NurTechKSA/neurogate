---
project: neurogate
public: true
type: feature
audience: students
title: Хватит одного ключа
summary: Бот выдаёт команду установки сразу после первого рабочего ключа — обычно это Gemini со входом через Google. Регистрироваться в трёх сервисах больше не нужно; не получилось с Gemini — /skip, и бот предложит OpenRouter, потом NVIDIA.
user_impact: Новичок проходит настройку с одной регистрацией вместо трёх. Остальные ключи можно добавить позже командой neurogate setup, если начнут мешать лимиты.
screenshots: []
checks:
  - .venv/bin/python -m pytest -q tests/  (99 passed)
  - uvx ruff check src/neurogate/keybot.py tests/test_keybot.py
deploy_url: https://neurogate.nurtech.dev
---

## Что изменилось
- Бот: «Нужен один бесплатный ключ» → кнопка «Получить ключ» → сразу команда под Mac или Windows.
- /skip ведёт к следующему сервису («Другой вариант»), пока не найдётся рабочий ключ.
- Сайт и инструкции: «1 ключ · 1 команда».

## Где проверить
- @nurtechneurogatebot → /start

## Риски
- На одном ключе лимиты кончаются быстрее; добавить ключи — `neurogate setup`.
