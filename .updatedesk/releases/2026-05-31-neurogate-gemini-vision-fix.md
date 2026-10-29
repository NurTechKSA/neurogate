---
project: neurogate
public: true
backfilled: true
type: fix
audience: users
title: 'Картинки снова доходят до Gemini'
summary: 'Раньше при запросе с изображением Gemini получал только текст. Теперь изображения передаются, и распознавание работает.'
user_impact:
  - 'Распознавание изображений через Gemini заработало'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: 24e34be..24e34be
---

Notes for editor:
- What changed: Адаптер Gemini перестал отбрасывать части image_url.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
