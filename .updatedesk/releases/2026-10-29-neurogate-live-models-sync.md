---
project: neurogate
public: true
backfilled: true
type: fix
audience: users
title: 'Сверка моделей со всеми провайдерами'
summary: 'Проверены каталоги: NVIDIA сняла почти все модели из конфига, цепочка кода починена. Из 124 проверенных 76 живы.'
user_impact:
  - 'Цепочка code снова отвечает'
  - 'Снятые модели отсеиваются автоматически'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: cf75bb6..f339260
---

Notes for editor:
- What changed: Автоотсев по каталогу провайдера, отчёт docs/model-refresh-2026-10-29.md.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
