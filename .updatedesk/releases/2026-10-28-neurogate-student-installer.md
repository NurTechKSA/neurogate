---
project: neurogate
public: true
backfilled: true
type: feature
audience: users
title: 'Установка для учеников одной командой'
summary: 'Появились установщики для macOS, Linux и Windows: ставят шлюз, ведут по получению ключей, настраивают автозапуск и подключают Claude Code.'
user_impact:
  - 'Ученик ставит всё одной командой'
  - 'Шлюз запускается сам при включении компьютера'
  - 'Команды claude-free и neurogate находятся сразу после установки'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: f5e87a8..a7c0764
---

Notes for editor:
- What changed: install.sh/install.ps1, мастер ключей, свой Python 3.12 через uv, запись ~/.local/bin в PATH.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
