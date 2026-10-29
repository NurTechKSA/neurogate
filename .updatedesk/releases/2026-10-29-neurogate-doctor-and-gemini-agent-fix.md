---
project: neurogate
public: true
backfilled: true
type: fix
audience: users
title: 'Диагностика doctor и стабильные агентные сессии'
summary: 'Команда doctor предупреждает об устаревшей дате модели в OpenCode, а переключение на Gemini в середине агентной сессии больше не ломает диалог.'
user_impact:
  - 'Проще найти причину, если модели не видны'
  - 'Нет ошибки 400 при смене модели посреди задачи'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: 9390f4c..dbf2c5c
---

Notes for editor:
- What changed: Заглушка thought_signature для чужих вызовов инструментов; проверка даты в doctor.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
