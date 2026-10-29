---
project: neurogate
public: true
backfilled: true
type: feature
audience: users
title: 'Codex бесплатно через neurogate'
summary: 'Шлюз понимает формат Responses API, а команда connect codex подключает Codex к бесплатным моделям.'
user_impact:
  - 'Codex работает без платной подписки'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: fb2cfa0..0c771e4
---

Notes for editor:
- What changed: Эндпоинт /v1/responses с преобразованием в chat/completions, connect codex, codex-free на странице.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
