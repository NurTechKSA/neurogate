# Ревизия free-моделей — 2026-10-11

Полный итог сессии: аудит по пайплайну (`scans/audit_catalog.py` → `audit_verifier.py`),
сверка с тремя внешними индексами, разбор новых дверей, деплой и проверка free-тира OpenCode.
Краткая версия для дежурного чтения; детали по провайдерам — в `docs/providers-setup.md`
(раздел «Состояние провайдеров на 2026-10-11»).

---

## 1. Новые модели — добавлены в `config.yaml` и цепочки (7 шт.)

Все проверены живым вызовом 2026-10-11 (3 RU-пробы, замер латентности).

| Запись | Что это | Latency | Куда в цепочках |
|---|---|---|---|
| `nvidia:glm-5.3` | **Флагман GLM-5.3 бесплатно** — единственная дверь (z.ai direct PAYG $1.40/$4.40, Cloudflare — Workers Paid) | 213s avg (очень долгий thinker) | quality, reasoning_quality, reasoning_deep, code, chat_en |
| `nvidia:muse-glimmer-30b` | Meta **Muse** — новое семейство Meta | 10.4s | chat, quality, chat_en, reasoning_*, moa, debate |
| `nvidia:diffusiongemma-26b-a4b-it` | Gemma 4 на **diffusion-архитектуре** | **0.83s** — самый быстрый NIM | chat, chat_fast, latency, quality, chat_en, moa |
| `openrouter:apodex-1.1-mini:free` | Новый вендор Apodex (бэкенд Novita), thinking | 5.75s | chat, latency, quality, chat_en, reasoning_quality |
| `gemini:3.1-flash-lite` | **Stable** id (без `-preview`) = отдельный квотный бакет free-tier | 6.4s | chat, chat_fast, latency, quality, image, chat_en, translation |
| `zai:glm-4.7-flash` | **Бесплатный** на прямом z.ai (наследник glm-4.5-flash) | 23s (high variance) | chat, quality, unlimited, chat_en, reasoning_*, moa |
| `zenmux:dots3-note-prev` | 393K ctx, reasoning, **video+audio вход** | 4.0s | chat, quality, image |

Метрики `quality/ru` у новых — оценки по пробам («estimate» в комментариях конфига),
`latency_s` — измеренный. Полный бенч (`tests/ru_bench.py`) можно догнать позже.

## 2. Мёртвые двери — выведены из цепочек (7 шт.)

| Что | Дата смерти | Причина |
|---|---|---|
| `groq:qwen3.6-27b` | 2026-09-14 | EOL, замена `groq:qwen3.8-27b` (уже была в конфиге) |
| `groq:compound`, `groq:compound-mini` | 2026-09-21 | Decommissioned, 404. Замены нет |
| `openrouter:nex-n2.5-pro:free`, `nex-n2.5-mini:free` | ~октябрь | 404 «unavailable for free» — промо Nex AGI кончилось |
| `openrouter:ling-3.0-flash-fin:free`, `ling-3.0-flash-vl:free` | ~октябрь | 404 «unavailable for free» — промо inclusionAI кончилось |
| `sambanova:*` (3 записи) | 2026-10-11 | Ключ отозван (401 `invalid_api_key`) после сгоревших trial-кредитов. Вернуть только после перевыпуска ключа |

## 3. Gemini 2.5 — остаются, но дата спорная

- **Google Cloud lifecycle + OpenRouter** (`expiration_date`): retirement **2026-10-20**.
- **Gemini API deprecations**: «No shutdown date announced», served until further notice —
  но только для аккаунтов, кто уже юзал 2.5 (новые получают 404).
- Наш ключ старый → 2026-10-11 отвечают 200. **Решение: оставить**, router сам пропустит при 404.
  Пересмотреть **после 2026-10-20**.

## 4. Внешние индексы — что реально стоит из них брать

Источники: [freellm.sh](https://freellm.sh/) (163 модели / 18 провайдеров),
[cheahjs/free-llm-api-resources](https://github.com/cheahjs/free-llm-api-resources) (29k ★),
[OpenRouter blog «Free LLM APIs Compared»](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/).
Все три **отстают и врут в деталях** — каждая позиция проверялась вызовом.

### Стоит сделать (открытые действия)

| Действие | Что даёт |
|---|---|
| **Завести ключ OrcaRouter** (`sk-orca-`, регистрация без карты) | `orcarouter/free` (difficulty-роутер) + `z-ai/glm-5.3-flash-free`, `deepseek/deepseek-v4-flash-free`, `tencent/hy3-free`, `hy4-preview-free`. Каталог free-id анонимный: `GET https://api.orcarouter.ai/api/free-package/public` |
| **Кинуть ~$1 на Zenmux** (списаний не будет) | Открывает 6 моделей $0, которые сейчас отдают 402 `reject_no_credit`: `ling-3.1-flash`, `agnes-2.5-flash` (524K ctx, vision), `ling-3.0-tiny`, `atria-dawn-preview`, `ming-image-0.1-design(-layer)`. Требование баланса > $0 — анти-абус, не тарификация |
| Проверить **nano-banana** после 20.10 | По Firebase release notes shutdown был 2026-10-02, но модель в каталоге Gemini API есть |

### Не брать (проверено, отсечено)

- **OpenCode Zen free-модели по HTTP** — 403 `FreeTierError: free tier can only be used from
  within OpenCode` (см. §6 — через CLI работает).
- **B.AI, Duck.ai, Arena** — web-chat без API (в B.AI есть бесплатный GLM-5.3-Flash, но только в браузере).
- **Free.ai** — каталог `/v1/models` анонимный (503 модели: TTS/OCR/image/video/3d), но chat POST
  отдаёт 403/405, пулы крошечные (анон ~2.5-6K токенов/день). TTS (kokoro/chatterbox) — интересно,
  но нужен отдельный kind.
- **mistral-code-latest / mistral-code-fim-latest** — alias'ы `codestral-2508`, не новые модели.
- **labs-leanstral-1-5** — Labs-модель, требует включения в admin.mistral.ai.
- **nvidia:deepseek-v4.1-flash** — существует, но на NIM таймаутится (2/3 > 300s).
- **Cerebras** — 402, free-тир закрыт (только trial с картой).
- **KiosAPI** — 401 без токена, «skip until a key works» (по их же индексу).

## 5. OpenRouter — статус на 2026-10-11

Каталог: 19 бесплатных моделей, все учтены. Ключ жив (`openrouter/free` → 200).
Новые: `apodex-1.1-mini:free` (добавлена). Не для нас: `thinkingmachines/inkling*:free`
(403 — только клиенты из openrouter.ai/apps), `inclusionai/ling-3.1-flash` (pricing 0/0, но
403 key-limit — фактически платная), `nvidia/nemotron-3.5-content-safety:free` (guard),
`google/lyria-*` (музыка). Умерли 4 `:free` — см. §2.

## 6. OpenCode free-tier — можно ли юзать в терминале и «отдавать на выход»?

**Да, проверено 2026-10-11 живьём.**

Что выяснено:

- HTTP-дверь (`https://opencode.ai/zen/v1/chat/completions`) закрыта: `403 FreeTierError
  «OpenCode's free tier can only be used from within OpenCode»`. Аккаунт тут не причём —
  ворота по идентичности клиента.
- **CLI — это и есть OpenCode**, поэтому из терминала всё работает. Проверено без аккаунта:

  ```bash
  opencode run --format json -m opencode/muse-spark-1.3-contributor-free "Скажи привет по-русски"
  # → {"type":"text",...,"text":"Привет!"}
  ```

- CLI видит все free-модели: `muse-spark-1.2/1.3-contributor-free`, `nemotron-3-ultra-free`,
  `nemotron-3.5-lightning-free`, `ling-3.0/3.1-flash-free`, `mimo-v2.6-flash-free`,
  `step-5-preview-free`, `longcat-2.5-preview-free`, `space-bunny-free`, `big-pickle`.
  (`exo-free` — 410 deprecated.)
- `opencode run` умеет `--model provider/model`, `--format json` (JSONL-события: `step_start`,
  `text`, …), `--file`, `--session`. Есть и `opencode api` для локального сервера.

### Как «отдать на выход» через neurogate — ✅ РЕАЛИЗОВАНО

Заведён kind **`opencode_cli`** (по образцу `claude_cli`): провайдер шеллит
`opencode run --standalone --format json --model <opencode/модель> "<prompt>"`,
парсит JSONL-события и склеивает все `type:text`. Записи `opencode_cli:*`
добавлены в `config.yaml`, цепочка `local` (claude_cli → opencode_cli).

Проверено живыми вызовами 2026-10-11 (чистый RU-промпт с маркером):

| Модель | Latency | Ответ |
|---|---|---|
| `opencode/nemotron-3.5-lightning-free` | 3.9s | ✅ |
| `opencode/muse-spark-1.3-contributor-free` | 6.8s | ✅ |
| `opencode/mimo-v2.6-flash-free` | 7.6s | ✅ |
| `opencode/ling-3.1-flash-free` | 15.0s | ✅ |
| `opencode/step-5-preview-free` | 44.8s | ✅ |

**Грабли, пойманные при реализации** (записаны в комментарии провайдера):
`opencode run` БЕЗ `--standalone` цепляется к общему фоновому сервису opencode
и получает контекст чужой сессии — модель отвечала «выполняю твой скрипт…»,
видя контекст моей рабочей сессии. Плюс подпроцесс наследовал stdin-пайп и вис.
Лечение: `--standalone` (private server) + `stdin=DEVNULL`. Проверка чистоты —
маркерный промпт («МАРКЕР-7391, ответь ровно двумя словами») → ровно `чисто 5`.

### Ограничения (честно)

- Free-модели: **«data may be used to improve the model»** — не гонять чувствительное.
- Ворота «only from within OpenCode» — рассчитаны на личное использование в клиенте;
  публичная пересдача через шлюз может быть прикрыта в любой момент. Держать в хвосте цепочек.
- Лимиты free-тира не опубликованы; состав free-моделей ротируется (`big-pickle` и прочие
  «free for a limited time» уходят).
- Бесплатный аккаунт (opencode.ai/zen, без карты) для CLI не обязателен, но поднимает лимиты
  и даёт стабильную идентичность — рекомендуется завести.

## 7. Деплой 2026-10-11

- Коммит `8a77102` запушен в `basaltcode/neurogate` (pre-push чеклист из `deploy.md` пройден:
  2 скана на токены/IP — 0 совпадений, секреты не в диффе; из аудит-файла заредактированы
  ID ключа OpenRouter и фрагмент ключа SambaNova).
- rsync на прод: dry-run с **0 удалений** (в exclude-паттернах `deploy.md` был баг:
  `config.yaml.bak.*` не матчит `config.yaml.bak-<дата>` с дефисом — исправлено на `*.bak-*`,
  иначе на проде сносились два бэкапа и уезжал локальный).
- Сервис перезапущен: `active`, `/health` → 200, ошибок с рестарта — 0.
- Активных провайдеров: **176 из 183** (7 отвалились за старыми ключами `SILICONFLOW_API_KEY`
  и `MODELSCOPE_API_KEY` — они и раньше были нерабочие, см. «Состояние провайдеров»).
