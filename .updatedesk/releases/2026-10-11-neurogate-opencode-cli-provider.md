---
project: neurogate
public: true
backfilled: true
type: feature
audience: users
title: 'Бесплатные модели OpenCode Zen через консольный OpenCode'
summary: 'HTTP-доступ к бесплатным моделям OpenCode закрыт, поэтому шлюз теперь обращается к ним через команду opencode run.'
user_impact:
  - 'Бесплатные модели OpenCode снова доступны через шлюз'
  - 'Работает с разными версиями OpenCode'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: 9a156e9..edf5e49
---

Notes for editor:
- What changed: Провайдер opencode_cli, автоопределение флага --standalone, заметки о версиях.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
