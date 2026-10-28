# Бесплатные нейросети для кода — инструкция для учеников

Это ваш личный шлюз к бесплатным нейросетям. Он работает **на вашем компьютере** и использует
**ваши** бесплатные ключи. Подписки не нужны, карта не нужна. Когда у одного сервиса кончается
лимит, шлюз сам переключается на следующий, поэтому чем больше ключей, тем дольше вы работаете без пауз.

> Не делитесь своими ключами и не просите чужие. У каждого свой бесплатный лимит. Общий ключ
> на группу кончится за час, а сервис может заблокировать аккаунт.

## 1. Установка — одна команда

**macOS / Linux** — откройте «Терминал» и вставьте:

```bash
curl -fsSL https://raw.githubusercontent.com/RYAZHAPOVILNUR/neurogate/main/install.sh | bash
```

**Windows** — откройте PowerShell (Пуск → «PowerShell») и вставьте:

```powershell
irm https://raw.githubusercontent.com/RYAZHAPOVILNUR/neurogate/main/install.ps1 | iex
```

Установщик сам скачает всё нужное, а потом запустит **мастер ключей**.

## 2. Мастер ключей

Мастер по очереди показывает сервисы, начиная с самых полезных. Для каждого он:

1. пишет, что даёт сервис, какие у него лимиты и что нужно для регистрации;
2. по Enter открывает в браузере страницу, где создают ключ, и пишет по шагам, что нажать;
3. просит вставить ключ. Ключ не виден на экране и сохраняется только у вас в файле `.env`;
4. сразу проверяет, работает ли ключ.

`s` — пропустить сервис, `q` — закончить. Вернуться и добавить ещё ключей можно в любой момент:

```bash
neurogate setup            # все сервисы, где ещё нет ключа
neurogate setup groq gemini   # только эти
neurogate keys             # какие ключи есть и работают ли они
```

**Минимум для старта — 3 ключа:** Groq, Gemini, OpenRouter (по 2 минуты на каждый).
**Хорошо — 8–10 ключей:** плюс Cerebras, NVIDIA, Mistral, Z.ai, Cloudflare, Cohere.

## 3. Пишем код

### Claude Code

```bash
claude-free
```

Это обычный Claude Code (файлы, терминал, правки), но вместо платного Claude в нём работают
бесплатные модели: Qwen3-Coder-480B, Gemini, DeepSeek и другие. Обычная команда `claude`
остаётся как была. Если Claude Code ещё не установлен:
`curl -fsSL https://claude.ai/install.sh | bash` (Windows: `irm https://claude.ai/install.ps1 | iex`).

### Cline, Roo Code, Kilo Code, Continue, OpenCode, Codex

```bash
neurogate connect cline      # или continue, opencode, codex, cursor
```

Команда покажет, что вписать в настройки: адрес `http://127.0.0.1:8765/v1`, ключ и модель `code`.

### Какую модель выбирать

| Модель | Когда |
|---|---|
| `code` | основная работа с кодом — самые сильные бесплатные кодовые модели |
| `code_fast` | быстрые мелкие правки |
| `auto` | шлюз сам выберет по запросу |
| `chat` | вопросы, объяснения, тексты |

## 4. Панель

`http://127.0.0.1:8765/dashboard` — тестовый чат, история запросов и статус каждого сервиса.

## Если что-то не так

| Что видите | Что делать |
|---|---|
| «Нет ни одного ключа для чата» | `neurogate setup`, добавьте хотя бы Groq или Gemini |
| Ответы медленные или ошибки 429 | лимиты кончаются — добавьте ещё ключей |
| Ключ «отвергнут» | создайте ключ заново и вставьте целиком, без пробелов |
| Добавили ключ, а он не работает | `neurogate restart` |
| `neurogate: command not found` | откройте новое окно терминала |

## Все сервисы и где брать ключи

Таблица собирается из каталога командой `neurogate keys --markdown`.

### Начните с этих — быстро, без карты, хорошо пишут код

| Сервис | Что даёт | Лимиты | Что нужно | Где взять ключ |
|---|---|---|---|---|
| **Groq** | чат и код, очень быстрые ответы, распознавание речи (Whisper) | 30 запросов/мин, 1–14 тыс. запросов/день на модель | только почта или Google/GitHub | [GROQ_API_KEY](https://console.groq.com/keys) |
| **Google Gemini (AI Studio)** | сильный код, длинный контекст (1М токенов), картинки на вход, веб-поиск | 10 запросов/мин, 250–1500 запросов/день | Google-аккаунт; из РФ нужен VPN при регистрации | [GEMINI_API_KEY](https://aistudio.google.com/apikey) |
| **OpenRouter** | десятки бесплатных моделей (:free) — Qwen-Coder, DeepSeek, Nemotron, GLM | 20 запросов/мин, 50 запросов/день (1000 после разового депозита $10) | Google/GitHub, карта не нужна | [OPENROUTER_API_KEY](https://openrouter.ai/keys) |
| **Cerebras** | очень быстрый Qwen-3-235B и gpt-oss, без суточного потолка | 5–30 запросов/мин, без лимита в день | подтверждение телефона | [CEREBRAS_API_KEY](https://cloud.cerebras.ai/platform) |
| **NVIDIA NIM** | Qwen3-Coder-480B (лучший бесплатный для кода), DeepSeek, Kimi, без суточного потолка | 40 запросов/мин, без лимита в день | только почта | [NVIDIA_API_KEY](https://build.nvidia.com/settings/api-keys) |

### Дополнительные — больше квоты и моделей

| Сервис | Что даёт | Лимиты | Что нужно | Где взять ключ |
|---|---|---|---|---|
| **Mistral** | Mistral Large, Codestral (отдельная квота для кода), эмбеддинги | около 4 запросов/мин на чат + Codestral 30/мин; на бесплатном плане учится на запросах | почта и SMS | [MISTRAL_API_KEY](https://console.mistral.ai/api-keys) |
| **Z.ai (GLM)** | GLM-4.5-Flash навсегда бесплатно | только по числу одновременных запросов | почта; из РФ/СНГ иногда проще open.bigmodel.cn | [ZAI_API_KEY](https://z.ai/manage-apikey/apikey-list) |
| **Cloudflare Workers AI** | модели Llama/Qwen, генерация картинок FLUX и SDXL, эмбеддинги | 10 000 «нейронов» в сутки на весь аккаунт | только почта | [CLOUDFLARE_API_KEY](https://dash.cloudflare.com/profile/api-tokens) |
| **Hugging Face** | доступ к сотням открытых моделей через их роутер | около $0.10 кредита в месяц | только почта | [HF_TOKEN](https://huggingface.co/settings/tokens) |
| **Cohere** | Command-A, Aya (хорошо по-русски), поиск и rerank | 20 запросов/мин, 1000 запросов/месяц, только некоммерческое использование | Google/GitHub/почта | [COHERE_API_KEY](https://dashboard.cohere.com/api-keys) |
| **SambaNova** | DeepSeek V3.x, Llama 4 — быстро | стартовые кредиты; кончились — сами не восстановятся | Google/почта | [SAMBANOVA_API_KEY](https://cloud.sambanova.ai/apis) |
| **DeepSeek** | DeepSeek V4 напрямую — сильный код | стартовые кредиты при регистрации (если дают), дальше платно и дёшево | почта или Google; иногда телефон | [DEEPSEEK_API_KEY](https://platform.deepseek.com/api_keys) |
| **Poolside** | кодовые модели Laguna | бесплатно на ограниченное время, лимиты не опубликованы | почта | [POOLSIDE_API_KEY](https://platform.poolside.ai) |
| **Ollama Cloud** | DeepSeek V4, Kimi K2, Qwen 3.5, GLM 5 в облаке Ollama | бесплатный тариф с недельной квотой (цифры не опубликованы) | почта или GitHub | [OLLAMA_API_KEY](https://ollama.com/settings/keys) |
| **Kilo Code Gateway** | бесплатные модели шлюза Kilo (набор меняется) | около 200 запросов/час | Google/GitHub | [KILO_API_KEY](https://app.kilo.ai/profile) |
| **ZenMux** | бесплатные DeepSeek V4 Flash и GLM-4.7 Flash (отдельная квота) | только модели с суффиксом -free | почта, без карты | [ZENMUX_API_KEY](https://zenmux.ai/settings/keys) |
| **Vercel AI Gateway** | запасная квота к бесплатным Ling и Laguna | ежемесячный бесплатный кредит; не пополняйте баланс, иначе он пропадёт | аккаунт Vercel (GitHub) | [AI_GATEWAY_API_KEY](https://vercel.com/dashboard) |
| **OrcaRouter** | агрегатор 200+ моделей, бесплатные *-free | free-модели работают после привязки GitHub-аккаунта «со стажем» | почта + GitHub | [ORCAROUTER_API_KEY](https://www.orcarouter.ai/console/token) |
| **LLM7** | gpt-4o-mini, DeepSeek, Qwen-Coder; работает и без ключа (30/мин) | 120 запросов/мин с токеном | необязательно | [LLM7_API_KEY](https://token.llm7.io) |
| **OpenCode Zen** | бесплатные DeepSeek V4 Flash, Nemotron Ultra; работает и без ключа | не опубликованы | необязательно | [OPENCODE_API_KEY](https://opencode.ai/zen) |
| **Together AI** | бесплатная генерация картинок FLUX.1-schnell | зависит от акций при регистрации | почта | [TOGETHER_API_KEY](https://api.together.ai/settings/api-keys) |
| **Pollinations** | текст и картинки; без ключа — базовый уровень | с ключом выше | необязательно, вход через GitHub | [POLLINATIONS_API_KEY](https://enter.pollinations.ai) |
| **Jina AI** | эмбеддинги и rerank (для поиска по документам) | 10 млн бесплатных токенов на ключ | ничего — ключ выдаётся прямо на сайте | [JINA_API_KEY](https://jina.ai/api-dashboard/key-manager) |

### С неудобствами — телефон РФ, верификация, ежедневный чек-ин

| Сервис | Что даёт | Лимиты | Что нужно | Где взять ключ |
|---|---|---|---|---|
| **Voyage AI** | эмбеддинги для кода и rerank | 200 млн бесплатных токенов | почта | [VOYAGE_API_KEY](https://dashboard.voyageai.com/organization/api-keys) |
| **GigaChat (Сбер)** | русскоязычный чат и картинки Kandinsky | 1 млн токенов на 30 дней | Сбер ID, телефон РФ | [GIGACHAT_AUTH_KEY](https://developers.sber.ru/studio) |
| **FreeTheAi** | тысячи моделей, включая GPT-5 и Kimi | 10 запросов/мин; КАЖДЫЙ ДЕНЬ нужно вручную нажать /checkin в Discord | Discord | [FREETHEAI_API_KEY](https://discord.gg/secrets) |
| **Alibaba Qwen (DashScope Intl)** | флагманы Qwen 3.6 и Qwen3-Coder-480B, 1М контекст | 1 млн токенов на модель на 90 дней | аккаунт Alibaba Cloud International, телефон и карта, подтверждение личности | [DASHSCOPE_API_KEY](https://bailian.console.alibabacloud.com) |
| **SiliconFlow** | бесплатные Qwen3-8B, DeepSeek-R1-Distill, GLM-4.1V | 1000 запросов/мин; нужна верификация личности | китайский телефон или верификация | [SILICONFLOW_API_KEY](https://cloud.siliconflow.cn/account/ak) |
| **ModelScope** | свежие Qwen 3.5 | 2000 запросов/день; нужна real-name верификация Alibaba | аккаунт Alibaba Cloud с верификацией | [MODELSCOPE_API_KEY](https://modelscope.cn/my/myaccesstoken) |

**Без ключа работают:** OVHcloud AI Endpoints (открытые модели в EU, 2 запроса/мин), OpenCode Zen (бесплатные модели), LLM7 (30 запросов/мин), Pollinations (текст и картинки), AI Horde (картинки, общая очередь), Edge TTS (озвучка без лимита), LibreTranslate и MyMemory (перевод).
