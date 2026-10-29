---
project: neurogate
public: true
backfilled: true
type: fix
audience: users
title: 'Убраны снятые модели и добавлен OrcaRouter'
summary: 'Цепочка кода падала из-за модели, которую Kilo снял с бесплатного доступа. Мёртвые идентификаторы убраны, добавлен OrcaRouter.'
user_impact:
  - 'Меньше ошибок «все провайдеры недоступны» в цепочке code'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: efe4601..058dbd2
---

Notes for editor:
- What changed: Удалено 15 устаревших id, обновлён список Kilo, новый kind orcarouter, строка в таблице квот.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
