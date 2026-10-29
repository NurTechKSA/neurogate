---
project: neurogate
public: true
backfilled: true
type: feature
audience: users
title: 'Быстрый старт: три ключа вместо десятков'
summary: 'Бот и мастер предлагают сначала три ключа (Gemini, OpenRouter, NVIDIA), остальные по желанию; мастер не запускается, если ключи уже есть.'
user_impact:
  - 'Старт занимает минуты'
  - 'Не просят лишних ключей повторно'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: a43d5cc..6acc1f6
---

Notes for editor:
- What changed: Карточки «1 из 3» в боте, флаг more в базе, быстрый режим мастера.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
