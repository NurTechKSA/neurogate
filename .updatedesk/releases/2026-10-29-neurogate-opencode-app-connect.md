---
project: neurogate
public: true
backfilled: true
type: feature
audience: users
title: 'OpenCode работает на neurogate без подписки'
summary: 'Команда connect opencode сама прописывает шлюз в приложении OpenCode; в списке моделей одна понятная строка «50 бесплатных моделей, сам переключается».'
user_impact:
  - 'Приложение OpenCode сразу работает бесплатно'
  - 'Нет путаницы из четырёх одинаковых моделей'
  - 'Повторное подключение не зависает'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: 08ec0b3..36a0332
---

Notes for editor:
- What changed: Запись провайдера в opencode.json, reload фонового сервиса, type=chat и cost=0, дата выпуска для окна 2.x.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
