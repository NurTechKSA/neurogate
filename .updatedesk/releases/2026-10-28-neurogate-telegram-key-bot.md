---
project: neurogate
public: true
backfilled: true
type: feature
audience: users
title: 'Telegram-бот для получения ключей и переноса на компьютер'
summary: 'Бот пошагово ведёт по сервисам: ссылка, шаги, лимиты, проверяет ключ, удаляет сообщение с ним и выдаёт команду установки с одноразовым кодом.'
user_impact:
  - 'Ключи оформляются в чате без возни с файлами'
  - 'Ключ не остаётся в переписке'
  - 'Перенос настроек на компьютер по одноразовому коду'
screenshots: []
checks: []
deploy_url: https://neurogate.nurtech.dev
commits: cbbe6d4..e6c0c39
---

Notes for editor:
- What changed: neurogate bot, keydrop, повтор setWebhook, описание бота @nurtechneurogatebot в README.
- Where to verify: @nurtechneurogatebot
- Risks: восстановлено по git log задним числом.
