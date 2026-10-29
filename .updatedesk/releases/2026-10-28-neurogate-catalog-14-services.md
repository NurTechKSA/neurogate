---
project: neurogate
public: true
backfilled: true
type: feature
audience: users
title: 'Каталог на 50 бесплатных сервисов и живые модели'
summary: 'Добавлено 14 новых бесплатных сервисов, в мастере 43 сервиса с ключом и 7 без. Мёртвые модели заменены живыми, свободные порты подбираются сами.'
user_impact:
  - 'Больше вариантов получить бесплатные модели'
  - 'Цепочка чата перестала падать целиком на закрытых моделях'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: ed9d1e8..251fe90
---

Notes for editor:
- What changed: Новые kind, автоотсев :free-моделей OpenRouter, выбор свободного порта.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
