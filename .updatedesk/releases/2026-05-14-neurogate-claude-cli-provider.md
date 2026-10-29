---
project: neurogate
public: true
backfilled: true
type: feature
audience: users
title: 'Подключение подписки Claude через локальный Claude Code'
summary: 'Теперь тем, у кого есть подписка Claude, можно направлять запросы к Opus, Sonnet и Haiku через установленный Claude Code.'
user_impact:
  - 'Модели Claude доступны через тот же единый адрес'
  - 'Добавлена инструкция для запуска на сервере'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: 84605fc..1e8dfeb
---

Notes for editor:
- What changed: Провайдер claude_cli вызывает claude -p; описана установка на VPS (setup-token).
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
