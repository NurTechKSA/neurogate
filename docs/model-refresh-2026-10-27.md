# Ревью моделей 2026-10-27: ротация каталогов, OrcaRouter, Zenmux

Продолжение [`model-refresh-2026-10-11.md`](model-refresh-2026-10-11.md). Триггер — ошибка
`all providers failed on chain code: kilo:step-3.7-flash HTTP 404 ... does not exist`.
Дальше — что реально проверено живыми вызовами, что вычищено, что добавлено и что
осталось за человеком.

## 1. Почему падал `code`

`kilo:step-3.7-flash` смотрел на `stepfun/step-3.7-flash:free`, а Kilo снял free-вариант:
в каталоге остался только платный `stepfun/step-3.7-flash`. Ошибка всплывала последней,
потому что за ней в цепочке уже не было живых провайдеров.

Полный прогон цепочки `code` (36 провайдеров) живыми вызовами показал: живы 12, мёртвых
по HTTP — 13, остальное — дневные квоты (Gemini 429), thinking-модели с пустым `content`
на `max_tokens=8` и временные 429/530.

## 2. Каталог Kilo: 12 free-моделей, 2 наших id умерли

`GET https://api.kilo.ai/api/gateway/models` (суффикс `:free` обязателен) — сверка с конфигом:

| Было в конфиге | Статус | Замена |
|---|---|---|
| `nvidia/nemotron-3-super-120b-a12b:free` | 404 | `nvidia/nemotron-3-ultra-550b-a55b:free` → `kilo:nemotron-3-ultra` |
| `stepfun/step-3.7-flash:free` | 404 (остался платный) | `cohere/north-mini-code:free` → `kilo:north-mini-code` (в `code`), `nvidia/nemotron-3.5-lightning:free` (в `reasoning_quality`) |

Добавлены ещё три проверенные free-модели Kilo: `dots-studio/dots-3-note-preview:free`
(5.9s), `nvidia/nemotron-3.5-lightning:free` (23.2s, thinking-only — на `max_tokens<1000`
отдаёт пустой `content`), `nvidia/nemotron-3.5-super-vl:free` (2.9s, vision).

Не добавлены, хотя в каталоге есть: `liquid/lfm-2.5-2.6b:free`,
`recursive/flint-v1.0:free`, `xingchen-agi/xing4.0-29b-a4b:free`,
`poolside/laguna-xs-2.1:free` — все отдают `429 upstream temporarily rate limited`
на живом вызове (бесплатная ёмкость у провайдера кончилась).

## 3. Устаревшие модели, вычищены из конфига и цепочек (15 записей)

Проверено живыми запросами 2026-10-27:

- **404 / 410 (модели нет):** `openrouter:nemotron-3-super-free`,
  `openrouter:nex-n2.5-pro:free`, `openrouter:nex-n2.5-mini:free`,
  `openrouter:ling-3.0-flash-fin:free`, `openrouter:ling-3.0-flash-vl:free`,
  `openrouter:apodex-1.1-mini:free` (добавлен 16 дней назад — уже снят),
  `ovhcloud:qwen3-32b`, `ovhcloud:qwen3-coder-30b`,
  `nvidia:nemotron-3-super`, `nvidia:kimi-k3`,
  `nvidia:deepseek-v4-flash`, `nvidia:deepseek-v4-pro`,
  `groq:qwen3.6-27b`, `groq:compound`, `groq:compound-mini`.
- **NVIDIA:** `deepseek-v4-flash/pro` ушли в 410 Gone, в каталоге остался
  `deepseek-ai/deepseek-v4.1-flash`, но он у нас **висит 300s без ответа** (проверено
  дважды) и `moonshotai/kimi-k2.6` отдаёт 404 «not found for account» — замену не берём.
- **Замены в цепочках** (а не просто удаление, где есть равный по смыслу живой id):
  `openrouter:nemotron-3-super-free → openrouter:nemotron-3-ultra-free`,
  `nvidia:nemotron-3-super → nvidia:nemotron-3-ultra`,
  `ovhcloud:qwen3-32b → ovhcloud:llama-3.3-70b`,
  `ovhcloud:qwen3-coder-30b → kilo:north-mini-code`.

## 4. OrcaRouter: ключ заведён, free-модели ждут привязки GitHub

Каталог: `https://api.orcarouter.ai/v1/models` — 215 моделей, из них ровно 6 с нулевой
ценой: `z-ai/glm-5.3-flash-free`, `deepseek/deepseek-v4-flash-free`,
`deepseek/deepseek-v4.1-flash-free`, `tencent/hy3-free`, `tencent/hy4-preview-free`,
`orca/orcaverify-text1.0-free` (последняя — служебная проверка, не чат-модель).

**Все пять чат-моделей пока недоступны:** HTTP 429 `free_rate_limited` —
«Free models are not available to this account yet. They require the workspace owner to
link a GitHub account that has been registered for some time — a newly created GitHub
account does not qualify yet». То есть это анти-абьюз-гейт, а не тариф.

Что сделано:
- kind `orcarouter` (`base_url: https://api.orcarouter.ai/v1`, env `ORCAROUTER_API_KEY`)
  добавлен в `config.py`; ключ положен в `.env` локально и на проде (chmod 600).
- 5 записей `orcarouter:*` в `config.yaml`, quality/ru/latency — **оценки**, не замеры
  (живой пробы не было, ловят 429). Так и помечено в конфиге.
- `orcarouter:glm-5.3-flash-free` и `orcarouter:deepseek-v4.1-flash-free` стоят в
  хвостах `chat` и `code`: после привязки GitHub они оживают без правок конфига.

**Действие человека:** orcarouter.ai → профиль → Link GitHub (аккаунт «со стажем»).
После этого — перепроверить пробы, снять пометку «estimate» и, если модели быстрые,
поднять их выше в цепочках.

## 5. Zenmux — записано, денег не вносили

`Zenmux`-модели с ценой `$0` (`ling-3.1-flash`, `agnes-2.5-flash`, `ling-0.1-tiny`,
`atria-dawn-preview`, `ming-image-0.1-design*`) требуют **баланс > $0** как анти-абьюз;
минимальный топ-ап — **$5** (Stripe/Alipay), деньги не списываются, пока модель $0.
Кампаний с бесплатными кредитами сейчас нет, «Token Free Plan» — реферальная программа
для блогеров (аппрув + $200/мес Ultra при аудитории 500+), не быстрый путь.
Итог: не добавляем, пока не появится баланс. `zenmux:dots3-note-prev` работает и так.

## 6. Что ещё проверили и НЕ добавили (анти-галлюцинации)

Stage 1 `scans/audit_catalog.py --free-only`: 37 кандидатов из 7 вендоров.
Stage 2 `scans/audit_verifier.py`: подтверждённых с совпавшей identity — **0**.

- `zai:glm-4.5`, `zai:glm-4.6`, `zai:glm-4.7` — HTTP 200, но на identity-промпт все три
  отвечают «I am Gemini, a large language model from Google». Похоже на silent routing;
  по правилу пайплайна такие кандидаты не берём.
- `mistral:mistral-code-latest` / `-code-fim-latest` — 200, но identity «Mistral Large»
  (алиас, не кодовая модель).
- `cerebras:*` — 402 (trial только с картой), `sambanova:*` — 401 (ключ отозван),
  `openrouter:thinkingmachines/inkling*` и `lyria-*` — 403 (закрыты для free-тира).
- `nvidia:stepfun-ai/step-5-preview`, `nvidia:minimax-m3.1-flash` — таймаут/пустой ответ.

## 7. Текущее состояние провайдеров (свип 2026-10-27, 196 записей)

Новый инструмент: `uv run python scans/liveness_sweep.py [--chain code] [--kind kilo]`
— шлёт крошечный запрос каждому чат-провайдеру из конфига, у thinking-моделей
перепроверяет пустой ответ с `max_tokens=1200`, и раскладывает по статусам.
Это не заменяет identity-пробу, но ловит 404/410/401/402/403/530 пачкой.

| Статус | Кол-во | Комментарий |
|---|---|---|
| ok | 41 | живы и отвечают |
| empty (после ретрая) | 24 | thinking-only либо CLI-обёртки (см. ниже) |
| 429 | 15+5 | дневные квоты (Gemini — мои пробы), free-ёмкость OR/laguna, OrcaRouter-гейт |
| 404/410 | 15 | модели удалены у вендора → вычищены (см. §3) |
| 401/402/403 | 16 | аккаунт: SambaNova (ключ), HuggingFace (кредиты), SiliconFlow (KYC), OpenAI (ключ), DeepSeek (баланс), Cerebras (карта) |
| 530 | 6 | FreeTheAi — Cloudflare origin error, лежит целиком |

Из 24 «empty» шесть — локальные CLI-обёртки (`claude_cli:*`, три `opencode_cli:*`):
они отвечают при одиночном запуске, но не переживают 8 параллельных спавнов процесса —
для свипа это ложная тревога, для прода — повод не ставить их рядом в одной цепочке.

Аккаунтные истории (403 SiliconFlow «complete identity verification», 402 HF
«no remaining credits», 401 SambaNova, 402 DeepSeek, 401 OpenAI, 530 FreeTheAi) —
это не ротация моделей, а ключи/квоты; они остаются в конфиге и оживут после
пополнения/верификации.

## 8. Проверка цепочки после правок

`code` — 35 провайдеров, живой прогон: Gemini 3.8 отдал 429 (дневная квота),
`groq:qwen3.8-27b` ответил за 6.5s корректным кодом. То есть fallback работает,
а `all providers failed` больше не воспроизводится.

## 9. Файлы

- `config.yaml` (gitignored): −15 мёртвых провайдеров, +4 Kilo, +5 OrcaRouter,
  перестановки в `code`/`reasoning_quality`/`reasoning_deep`.
- `src/neurogate/config.py`: kind `orcarouter` (base_url + env).
- `scans/liveness_sweep.py`: свип живых провайдеров (новый инструмент).
- `scans/audit-2026-10-27-candidates.json`, `scans/audit-2026-10-27-verified.json`,
  `scans/catalog-snapshot.json`: результаты Stage 1/2.
