---
project: neurogate
public: true
type: fix
audience: students
title: Понятнее, где взять ключ Gemini и куда его вставить
summary: Бот больше не пишет, что ключ Gemini начинается с AIza — Google с мая 2026 выдаёт ключи нового вида (AQ.…), и ученики думали, что взяли не тот. Карточка ключа прямо говорит, что кнопка открывает сайт Google, а ключ нужно вернуть в чат бота.
user_impact: Ученик не путается между ботом и сайтом Google и не бросает настройку из-за «неправильного» ключа.
screenshots: []
checks:
  - .venv/bin/python -m pytest -q tests/  (99 passed)
deploy_url: https://neurogate.nurtech.dev
---

## Что изменилось
- Шаги Gemini: «синяя кнопка Create API key», «спросит проект — Create project», «ключ начинается с AQ. или AIza».
- Карточка ключа: «Кнопка откроет сайт Google Gemini. Там: … Вернись в этот чат и пришли ключ».

## Где проверить
- @nurtechneurogatebot → /start → Mac или Windows

## Риски
- Ключи AQ. работают через официальный SDK Google (заголовок x-goog-api-key); на живом AQ-ключе шлюз не проверялся.
