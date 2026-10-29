---
project: neurogate
public: true
backfilled: true
type: feature
audience: users
title: 'Обновление каталога провайдеров: OpenCode, Vercel, Codestral'
summary: 'Добавлены новые виды провайдеров, часть моделей доступна без ключа, обновлён список живых моделей.'
user_impact:
  - 'Больше бесплатных вариантов, часть без регистрации'
  - 'Устаревшие модели убраны из цепочек'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: 51ada2a..4538770
---

Notes for editor:
- What changed: Новые kind: opencode, vercel, codestral; необязательный OPENCODE_API_KEY.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
