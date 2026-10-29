---
project: neurogate
public: true
backfilled: true
type: fix
audience: users
title: 'Исправлены запросы к новым моделям OpenAI'
summary: 'Модели GPT-5 и o-серии отклоняли каждый запрос из-за старого названия параметра. Теперь шлюз передаёт нужный.'
user_impact:
  - 'Запросы к GPT-5 больше не завершаются ошибкой 400'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: 8349e2e..8349e2e
---

Notes for editor:
- What changed: Настраиваемый параметр max_tokens / max_completion_tokens в провайдере.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
