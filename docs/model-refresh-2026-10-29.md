# neurogate — проверка model ID на 2026-10-29

Охват: все провайдеры `config.yaml.example`, кроме OpenRouter `:free`, NVIDIA и Gemini (их уже проверили).
GitHub Models, Voyage, Jina, OpenAI, AI Horde и Edge TTS в задачу не входили и не проверялись.

Как проверял:
1. Анонимный `GET {base}/models`. Список отдали: cerebras (`/public/v1/models`), sambanova, ovhcloud,
   huggingface, ollama, llm7, modelscope, kilo, orcarouter, inception, gonka, requesty, routeway,
   iteracompute, bazaarlink, nous, hackclub, aion, pollinations, opencode, vercel, zenmux.
2. Context7 (Groq, Mistral, Cloudflare Workers AI).
3. Официальные страницы документации через WebFetch.

Ключи из `.env` не понадобились и не использовались.

Статусы: **LIVE** — есть в списке провайдера или в доке. **RENAMED** — старый ID выведен, есть новый.
**GONE** — нет в списке или выведен по доке. **UNKNOWN** — подтвердить не удалось.

## Итог

| Статус | Кол-во |
|---|---|
| LIVE | 76 |
| RENAMED | 1 |
| GONE | 27 |
| UNKNOWN | 20 |

## По провайдерам

### DeepSeek — источник: api-docs.deepseek.com/quick_start/pricing
| name | model | статус | замена |
|---|---|---|---|
| deepseek:v4-pro | deepseek-v4-pro | LIVE (сейчас V4-Pro-0813) | — |
| deepseek:v4-flash | deepseek-v4-flash | RENAMED (старое имя пока принимается как алиас) | `deepseek-flash` (V4.1-Flash-1017) |

### Cerebras — источники: `GET api.cerebras.ai/public/v1/models`, inference-docs.cerebras.ai/models/overview
Сейчас в shared inference только `gpt-oss-120b` и `qwen-3.8-27b`.
| name | model | статус | замена |
|---|---|---|---|
| cerebras:qwen-3-235b | qwen-3-235b-a22b-instruct-2507 | GONE | `qwen-3.8-27b` |
| cerebras:llama3.1-8b | llama3.1-8b | GONE | `gpt-oss-120b` |
| cerebras:zai-glm-4.7 | zai-glm-4.7 | GONE | `qwen-3.8-27b` |

### SambaNova — источники: `GET api.sambanova.ai/v1/models`, docs.sambanova.ai/.../supported-models
API отдаёт: DeepSeek-V3.1, DeepSeek-V3.2, Meta-Llama-3.3-70B-Instruct, MiniMax-M3.1-Flash, gemma-4-31B-it, gpt-oss-120b.
| name | model | статус | замена |
|---|---|---|---|
| sambanova:deepseek-v3.2 | DeepSeek-V3.2 | LIVE (preview) | — |
| sambanova:deepseek-v3.1 | DeepSeek-V3.1 | LIVE | — |
| sambanova:llama-3.3-70b | Meta-Llama-3.3-70B-Instruct | LIVE | — |
| sambanova:llama-4-maverick | Llama-4-Maverick-17B-128E-Instruct | GONE | `MiniMax-M3.1-Flash` / `gpt-oss-120b` |
| sambanova:gemma-3-12b-it | gemma-3-12b-it | GONE | `gemma-4-31B-it` |

### Groq — источники: console.groq.com/docs/models, console.groq.com/docs/deprecations (+ Context7 /llmstxt/console_groq_llms-full_txt)
По странице deprecations сроки отключения 2026 года касаются free- и developer-тарифа. Страница models всё ещё показывает llama-3.3-70b и 3.1-8b среди production — видимо, для enterprise.
| name | model | статус | замена |
|---|---|---|---|
| groq:gpt-oss-120b | openai/gpt-oss-120b | LIVE | — |
| groq:gpt-oss-20b | openai/gpt-oss-20b | LIVE | — |
| groq:whisper-large-v3(-turbo) | whisper-large-v3(-turbo) | LIVE | — |
| groq:prompt-guard-2-86m | meta-llama/llama-prompt-guard-2-86m | LIVE (preview) | — |
| groq:llama-3.3-70b | llama-3.3-70b-versatile | GONE (free, с 16.08.2026) | `openai/gpt-oss-120b` / `qwen/qwen3.8-27b` |
| groq:llama-3.1-8b-instant | llama-3.1-8b-instant | GONE (free, с 16.08.2026) | `openai/gpt-oss-20b` |
| groq:qwen3-32b | qwen/qwen3-32b | GONE (17.07.2026) | `qwen/qwen3.8-27b` |
| groq:llama-4-scout | meta-llama/llama-4-scout-17b-16e-instruct | GONE (17.07.2026) | `openai/gpt-oss-120b` |
| groq:kimi-k2-instruct | kimi-k2-instruct | GONE (10.10.2025) | `openai/gpt-oss-120b` |
| groq:deepseek-r1-distill-70b | deepseek-r1-distill-llama-70b | GONE (02.10.2025) | `openai/gpt-oss-120b` |

Новые на Groq (preview): `qwen/qwen3.8-27b`, `minimaxai/minimax-m2.7`, `meta-models/muse-spark-open`.

### Cloudflare Workers AI — источники: developers.cloudflare.com/workers-ai/models/ (+ Context7, changelog 2026-05-08)
| name | model | статус | замена |
|---|---|---|---|
| cloudflare:llama-3.3-70b-fp8-fast | @cf/meta/llama-3.3-70b-instruct-fp8-fast | LIVE | — |
| cloudflare:llama-4-scout | @cf/meta/llama-4-scout-17b-16e-instruct | LIVE | — |
| cloudflare:qwq-32b | @cf/qwen/qwq-32b | LIVE | — |
| cloudflare:deepseek-r1-distill-32b | @cf/deepseek-ai/deepseek-r1-distill-qwen-32b | LIVE | — |
| cloudflare:mistral-small-3.1-24b | @cf/mistralai/mistral-small-3.1-24b-instruct | LIVE | — |
| cloudflare:llama-guard-3-8b, bge-m3, flux-1-schnell, dreamshaper, sdxl-lightning, phoenix | — | LIVE (в каталоге) | — |

Новые для кода: `@cf/moonshotai/kimi-k2.7-code` (262k), `@cf/zai-org/glm-5.3` (1M), `@cf/qwen/qwen3.8-27b`, `@cf/zai-org/glm-4.7-flash`.
В каталоге также есть `gpt-oss-120b`, `deepseek-v4.1-flash-1017`, `glm-5.3-flash`. Полные `@cf/...` ID для них не проверял.

### Z.ai — источник: docs.z.ai/guides/overview/pricing
| name | model | статус | замена |
|---|---|---|---|
| zai:glm-4.5-flash | glm-4.5-flash | LIVE (Free) | — |

Бесплатные: GLM-4.7-Flash, GLM-4.5-Flash, GLM-4.6V-Flash. GLM-5.3-Flash платная. Добавил `glm-4.7-flash`.

### Mistral — источники: docs.mistral.ai models overview, Context7 /mistralai/platform-docs-public
| name | model | статус | замена |
|---|---|---|---|
| mistral:large | mistral-large-latest | LIVE (→ Large 3) | — |
| mistral:large-2512 | mistral-large-2512 | LIVE | — |
| mistral:mistral-small-2603 | mistral-small-2603 | LIVE (Small 4) | — |
| mistral:ministral-14b | ministral-14b-latest | LIVE | — |
| mistral:medium-latest | mistral-medium-latest | LIVE (→ Medium 3.5) | — |
| mistral:embed / codestral-embed | mistral-embed / codestral-embed | LIVE | — |
| mistral:moderation | mistral-moderation-latest | LIVE (алиас → Moderation 2; 2411 выведен 30.06.2026) | — |
| mistral:pixtral-large | pixtral-large-latest | GONE (31.05.2026) | `mistral-medium-latest` |
| mistral:magistral-medium | magistral-medium-latest | GONE (31.07.2026) | `mistral-medium-latest` |
| mistral:magistral-small | magistral-small-latest | GONE (31.07.2026) | `mistral-small-2603` |
| mistral:devstral-2512 | devstral-2512 | GONE (31.07.2026) | `mistral-medium-latest` / `codestral-latest` |
| llm7:codestral | codestral-latest | LIVE (список llm7) | — |

Новые: `codestral-latest` (Codestral 25.08), `zai-glm-5-3` (GLM 5.3 на la Plateforme), `mistral-large-4` (preview с 06.10.2026, 1M).

### Cohere — источник: docs.cohere.com/docs/models
Все 5 настроенных чат-моделей (command-r-08-2024, command-r-plus-08-2024, command-r7b-12-2024, command-a-03-2025, c4ai-aya-expanse-32b) — **LIVE**.
embed-v4.0, embed-multilingual-v3.0 и rerank-v3.5 тоже **LIVE**. Для новых проектов рекомендуют rerank-v5.0-pro.
Новые: `north-mini-code-1.0` (кодовая модель), `command-a-plus-05-2026`, `embed-v5.0-pro/fast`.

### Hugging Face router — источник: `GET router.huggingface.co/v1/models` (136 моделей)
| name | model | статус | замена |
|---|---|---|---|
| huggingface:llama-3.1-8b | meta-llama/Llama-3.1-8B-Instruct | LIVE | — |
| huggingface:llama-3.3-70b | meta-llama/Llama-3.3-70B-Instruct | LIVE | — |
| huggingface:deepseek-r1-distill-llama-8b | deepseek-ai/DeepSeek-R1-Distill-Llama-8B | LIVE | — |
| huggingface:qwen2.5-7b | Qwen/Qwen2.5-7B-Instruct | GONE | `Qwen/Qwen3-8B` |

Для кода: `moonshotai/Kimi-K2.7-Code`, `zai-org/GLM-5.3`, `Qwen/Qwen3.8-27B`, `deepseek-ai/DeepSeek-V4.1-Flash`.

### OVHcloud (анонимно) — источник: `GET oai.endpoints.kepler.ai.cloud.ovh.net/v1/models`
| name | model | статус | замена |
|---|---|---|---|
| ovhcloud:llama-3.3-70b | Meta-Llama-3_3-70B-Instruct | LIVE | — |
| ovhcloud:qwen2.5-vl-72b | Qwen2.5-VL-72B-Instruct | LIVE | — |
| ovhcloud:qwen3-32b | Qwen3-32B | GONE | `Qwen3.8-27B` |
| ovhcloud:deepseek-r1-distill-70b | DeepSeek-R1-Distill-Llama-70B | GONE | `gpt-oss-120b` |
| ovhcloud:qwen3-coder-30b | Qwen3-Coder-30B-A3B-Instruct | GONE | `Qwen3.8-27B` (есть ещё `Qwen3.5-397B-A17B`) |

### Ollama Cloud — источник: `GET ollama.com/v1/models` и `/api/tags` (23 модели)
**Все 5 настроенных — GONE.**
| name | model | замена |
|---|---|---|
| ollama:qwen3-coder-480b | qwen3-coder:480b | `kimi-k2.7-code` |
| ollama:qwen3-vl-235b | qwen3-vl:235b | `gemma4:31b` (выбрал как vision-замену — GUESS) |
| ollama:glm-4.7 | glm-4.7 | `glm-5.3` |
| ollama:devstral-123b | devstral-2:123b | `mistral-large-4` (GUESS) |
| ollama:minimax-m2.5 | minimax-m2.5 | `minimax-m2.7` |

Что ещё есть: deepseek-v4.1-flash, deepseek-v4-pro:0813, glm-5.2, glm-5.3-flash, kimi-k2.6, kimi-k3, minimax-m3, minimax-m3.1-flash, mistral-large-3:675b, nemotron-3-ultra/super, gpt-oss:120b/20b, beam.

### SiliconFlow — источник: siliconflow.cn/pricing (без ключа /models отдаёт 401)
В видимой части прайса бесплатные LLM: `tencent/Hunyuan-MT-7B`, `XingChenAGI/Xing4.0-29B`, `PaddlePaddle/PaddleOCR-VL-1.5`.
Пять настроенных моделей (Qwen3-8B, GLM-4.1V-9B-Thinking, R1-Distill-Qwen-7B, R1-0528-Qwen3-8B, DeepSeek-OCR) в видимой части нет. Блоки прайса свёрнуты, поэтому статус **UNKNOWN** (скорее всего, уже не бесплатные).
Добавил `XingChenAGI/Xing4.0-29B`.

### Poolside — источники: docs.poolside.ai supported-models, api/overview, release-notes/models
| name | model | статус | замена |
|---|---|---|---|
| poolside:laguna-m.1 | poolside/laguna-m.1 | LIVE (Laguna M.1 в списке поддерживаемых) | — |
| poolside:laguna-xs.2 | poolside/laguna-xs.2 | UNKNOWN (в supported-models нет, вместо неё XS 2.1) | `poolside/laguna-xs-2.1` (GUESS) |

Новая: `poolside/laguna-s-2.1` (ID из примера в api/overview, 1M ctx).

### GigaChat — источник: developers.sber.ru/docs/ru/gigachat/models (+ страница gigachat-3-ultra)
GigaChat-2, GigaChat-2-Pro, GigaChat-2-Max — **LIVE**.
Новая: `GigaChat-3-Ultra` — по доке доступна физлицам во freemium.

### Yandex AI Studio — источник: aistudio.yandex.ru/docs/ru/ai-studio/concepts/generation/models.html
| name | model | статус | примечание |
|---|---|---|---|
| yandex:alice | aliceai-llm/latest | LIVE (`aliceai-llm`) | есть также `aliceai-llm-flash` |
| yandex:art | yandex-art/latest | UNKNOWN | дока называет только `aliceai-image-art-3.0` |

В доке Yandex gpt-oss-120b/20b значатся только до 30.10.2026, а deepseek-v4-flash и yandexgpt-5-lite — до 15.11.2026. В конфиге этих моделей нет.

### Together — источник: docs.together.ai/docs/serverless-models
| name | model | статус |
|---|---|---|
| together:flux-1-schnell-free | black-forest-labs/FLUX.1-schnell-Free | GONE |
| together:llama-guard-4 | meta-llama/Llama-Guard-4-12B | GONE («no moderation models offered via serverless») |
| together:qwen3-guard | Qwen/Qwen3-Guard-Stream-8B | GONE |

Сейчас бесплатна только `Prism-ML/Ternary-Bonsai-27B`, в конфиг её не добавлял.

### Агрегаторы и сервисы из списка /models (все LIVE)
| name | model | источник |
|---|---|---|
| kilo:auto-free / nemotron-3-ultra / north-mini-code | kilo-auto/free, nvidia/nemotron-3-ultra-550b-a55b:free, cohere/north-mini-code:free | api.kilo.ai/api/gateway/models |
| orcarouter:glm-5.3-flash-free | z-ai/glm-5.3-flash-free | api.orcarouter.ai/v1/models |
| modelscope:qwen3.5-35b / 27b | Qwen/Qwen3.5-35B-A3B, Qwen/Qwen3.5-27B | api-inference.modelscope.cn/v1/models |
| inception:mercury-3 / 2.5 | mercury-3, mercury-2.5 | api.inceptionlabs.ai/v1/models |
| gonka:* (3) | DeepSeek-V4-Flash-0731, GLM-5.3-Flash, MiniMax-M2.7 | proxy.gonkabroker.com/v1/models |
| requesty:* (2) | nvidia/nemotron-3-ultra-550b-a55b, google/gemma-4-31b-it | router.requesty.ai/v1/models |
| routeway:* (2) | deepseek-v4-flash:free, minimax-m2.7:free | api.routeway.ai/v1/models |
| iteracompute:qwen3.8-27b | qwen/qwen3.8-27b | api.iteracompute.com/v1/models |
| bazaarlink:* (2) | deepseek/deepseek-v4-flash-0731free:free, qwen/qwen3.7-flash:free | bazaarlink.ai/api/v1/models |
| nous:* (2) | stepfun/step-3.7-flash:free, reflection/beam-1.0-501b-a23b:free | inference-api.nousresearch.com/v1/models |
| hackclub:qwen3-32b | qwen/qwen3-32b | ai.hackclub.com/proxy/v1/models |
| aion:aion-2.0 | aion-labs/aion-2.0 | api.aionlabs.ai/v1/models (есть уже 3.0 и 3.5) |
| pollinations:gpt-oss-20b | openai-fast | text.pollinations.ai/models |
| fireworks:gpt-oss-120b | accounts/fireworks/models/gpt-oss-120b | fireworks.ai/models (Ready, serverless) |
| ai21:jamba-large | jamba-large (→ jamba-large-1.7-2025-07) | docs.ai21.com/docs/jamba-foundation-models |
| agnes:agnes-2.0-flash | agnes-2.0-flash | LIVE по вторичным источникам (mastra.ai/models/providers/agnes, freellm.net); официальная дока отдала 404 |
| hetzner:qwen3.6-35b / qwen3.8-27b | Qwen/Qwen3.6-35B-A3B-FP8, Qwen3.8-27B | пример в доке Hetzner + интеграции Haystack/mastra; без ключа /models отдаёт 401 |

### UNKNOWN без ключа
- **unorouter** — `gpt-oss-120b:free` и `minimax-m3.1-flash:free` среди `:free` на unorouter.com/models не видно. Страница — SPA, список мог обрезаться.
  Видны: beam:free, xing4.0-29b-a4b:free, nemotron-3.5-super-vl:free, sage-a1.5:free, step-5-preview:free, nemotron-3.5-bolt-e4b:free, mercury-decide:free.
- **freetheai** (6 чат-моделей + 5 картиночных) — `api.freetheai.xyz/v1/models` сейчас отдаёт HTTP 530 (Cloudflare: origin недоступен).
  На главной сайта в примере стоит `opc/deepseek-v4-flash-free`.

## Что стоит добавить в code / code_fast / chat (бесплатные)
Все ID ниже взяты из списков /models или из доки, и все они уже есть в патче:

- **code:** `cloudflare:kimi-k2.7-code`, `hackclub:kimi-k2.7-code`, `ollama:kimi-k2.7-code`, `huggingface:kimi-k2.7-code`,
  `llm7:kimi-k2.7-code`, `mistral:zai-glm-5.3`, `cloudflare:glm-5.3`, `hackclub:glm-5.3`, `ollama:glm-5.3`,
  `poolside:laguna-s-2.1`, `kilo:laguna-s-2.1`, `cohere:north-mini-code`, `mistral:codestral`,
  `sambanova:minimax-m3.1-flash`, `groq:qwen3.8-27b`, `cerebras:qwen-3.8-27b`, `opencode:deepseek-v4.1-flash-free`.
- **code_fast:** `cerebras:qwen-3.8-27b`, `cerebras:gpt-oss-120b`, `groq:qwen3.8-27b`, `sambanova:minimax-m3.1-flash`,
  `poolside:laguna-xs-2.1` (GUESS ID), `cloudflare:glm-4.7-flash`, `mistral:codestral`, `hackclub:deepseek-v4.1-flash`, `opencode:glm-5.3-flash-free`.
- **chat:** `sambanova:minimax-m3.1-flash`, `cerebras:qwen-3.8-27b`, `groq:qwen3.8-27b`, `gigachat:3-ultra`, `cohere:command-a-plus`,
  `sambanova:gemma-4-31b-it`, `zai:glm-4.7-flash`, `ovhcloud:qwen3.8-27b`, `modelscope:qwen3.8-27b`, `hackclub:glm-5.3`, `opencode:deepseek-v4.1-flash-free`.

Кроме того, в конфиге нет ни одной записи `kind: opencode`, хотя провайдер работает без ключа. Добавил три бесплатные модели из `opencode.ai/zen/v1/models`:
`deepseek-v4.1-flash-free`, `glm-5.3-flash-free`, `mimo-v2.6-flash-free`.

## Патч
`model-refresh.patch` — unified diff к `config.yaml.example`: 622 строки добавлено, 1 изменена.
- Единственная правка ID на месте: `deepseek:v4-flash` → `deepseek-flash`.
- У GONE и UNKNOWN записей над строкой `model:` стоит комментарий со статусом, источником и заменой. Сами записи не удалял и ID не трогал: их имена используются в цепочках, а на 404 роутер сам выкинет провайдера.
- 48 новых записей провайдеров в блоке «2026-10-29 model refresh» в конце `providers:`. У всех `quality/latency_s/ru = 0` — бенчи ещё не гонялись.
- В цепочках chat, code и code_fast новые имена вставлены сразу после шапки «2026-10-28 (форк)».
- Сомнительные ID помечены `GUESS`: `ollama:gemma4-31b` и `ollama:mistral-large-4` (замена выбрана по назначению), `poolside:laguna-xs-2.1`, `unorouter:step-5-preview-free`.
- Проверка: `git apply --check` проходит. PyYAML читает файл: дублей имён нет, все имена в цепочках существуют. `neurogate.config.load_config()` загружает патченую копию без ошибок.
