---
project: neurogate
public: true
backfilled: true
type: release
audience: users
title: 'Первый публичный релиз neurogate (ранний доступ)'
summary: 'Бесплатный шлюз, совместимый с OpenAI: один адрес для запросов, который сам переключается между бесплатными провайдерами, если один из них не отвечает.'
user_impact:
  - 'Можно подключить любой клиент, понимающий OpenAI, и пользоваться бесплатными моделями'
  - 'Если провайдер недоступен, запрос автоматически уходит к другому'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: a14154f..a7a8249
---

Notes for editor:
- What changed: Публичный релиз прокси с автоматическим переключением между провайдерами (Groq, Gemini, Cerebras, SambaNova, OpenRouter и др.); недолгое переименование и возврат к имени neurogate.
- Where to verify: https://neurogate.nurtech.dev
- Risks: восстановлено по git log задним числом.
