---
project: neurogate
public: true
backfilled: true
type: feature
audience: users
title: 'Исключение провайдеров в запросе'
summary: 'В запросе можно указать, каких провайдеров пропустить, например временно сломанного или нежелательного.'
user_impact:
  - 'Можно управлять выбором провайдера без правки настроек'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: 8d4261c..8d4261c
---

Notes for editor:
- What changed: Параметр ?exclude= с именами и шаблонами провайдеров или моделей.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
