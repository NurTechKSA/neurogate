---
project: neurogate
public: true
backfilled: true
type: fix
audience: users
title: 'Ссылка в шапке дашборда ведёт на рабочий сайт'
summary: 'Старый домен партнёрской метки перестал работать, ссылка обновлена.'
user_impact:
  - 'Клик по метке в дашборде открывает живую страницу'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: af37181..af37181
---

Notes for editor:
- What changed: Ссылка Basalt заменена на basaltcode.com.
- Where to verify: дашборд шлюза
- Risks: восстановлено по git log задним числом.
