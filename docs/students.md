# Бесплатные нейросети для кода — инструкция для учеников

> **Главная инструкция для учеников — https://neurogate.nurtech.dev** (там всё по шагам, с кнопками
> «копировать»). Этот файл — подробная версия для тех, кто читает на GitHub.

Это ваш личный шлюз к бесплатным нейросетям. Он работает **на вашем компьютере** и использует
**ваши** бесплатные ключи. Подписки не нужны, карта не нужна. Когда у одного сервиса кончается
лимит, шлюз сам переключается на следующий, поэтому чем больше ключей, тем дольше вы работаете без пауз.

> Не делитесь своими ключами и не просите чужие. У каждого свой бесплатный лимит. Общий ключ
> на группу кончится за час, а сервис может заблокировать аккаунт.

## Самый простой путь — Telegram-бот

1. Откройте бота **[@nurtechneurogatebot](https://t.me/nurtechneurogatebot)**, нажмите Start и выберите Mac или Windows.
2. Бот даёт кнопку «Получить ключ» на каждый из 3 сервисов (Gemini, OpenRouter, NVIDIA): создаёте
   ключ и присылаете в чат. Бот проверяет ключ и сразу удаляет сообщение с ним. Не получается — `/skip`.
3. После третьего ключа бот сразу выдаёт команду под ваш компьютер — вставьте её в терминал. Она
   поставит neurogate с ключами и приложение OpenCode.
4. Откройте OpenCode, выберите любую папку для проекта и пишите задачу — модель neurogate уже выбрана.

Есть ИИ-агент (Claude Code, Cline…)? Можно сказать ему:
«установи neurogate по инструкции https://github.com/NurTechKSA/neurogate/blob/main/docs/agent-install.md».

## Без бота: установка одной командой

**macOS / Linux** — откройте «Терминал» и вставьте:

```bash
curl -fsSL https://raw.githubusercontent.com/NurTechKSA/neurogate/main/install.sh | bash
```

**Windows** — откройте PowerShell (Пуск → «PowerShell») и вставьте:

```powershell
irm https://raw.githubusercontent.com/NurTechKSA/neurogate/main/install.ps1 | iex
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

**Минимум для старта — 3 ключа:** Gemini, OpenRouter, NVIDIA (по 2 минуты на каждый) — мастер
начинает именно с них.
**Хорошо — 10–15 ключей:** плюс NVIDIA, Inception, Gonka, Mistral, Z.ai, Requesty, Cloudflare, Cohere.
**Максимум:** в каталоге 43 сервиса с ключом и ещё 7 работают без ключа. Чем больше ключей, тем реже вы упрётесь в лимит.

## 3. Пишем код

### ⭐ OpenCode — приложение, как Claude и ChatGPT (рекомендуем)

1. Скачайте OpenCode (бесплатно):
   [Mac M1–M5](https://opencode.ai/download/stable/darwin-aarch64-dmg) ·
   [Mac Intel](https://opencode.ai/download/stable/darwin-x64-dmg) ·
   [Windows](https://opencode.ai/download/stable/windows-x64-nsis) ·
   [Windows ARM](https://opencode.ai/download/stable/windows-aarch64-nsis) ·
   остальное — https://opencode.ai/download
2. Откройте его и выберите папку проекта.
3. Пишите задачу в чат: «сделай сайт-визитку», «найди ошибку в main.py». Агент сам создаёт и
   правит файлы, запускает команды.

Модель **neurogate/code** уже выбрана установщиком — это бесплатные модели. Если OpenCode
поставили позже установки или модель слетела: `neurogate connect opencode`, затем перезапустите
OpenCode.

### Claude Code (в терминале)

```bash
claude-free
```

Подписка и аккаунт Anthropic не нужны. Это обычный Claude Code (файлы, терминал, правки), но вместо платного Claude в нём работают
бесплатные модели: Qwen3-Coder-480B, Gemini, DeepSeek и другие. Обычная команда `claude`
остаётся как была. Если Claude Code ещё не установлен:
`curl -fsSL https://claude.ai/install.sh | bash` (Windows: `irm https://claude.ai/install.ps1 | iex`).

### VS Code: Cline, Roo Code, Kilo Code, Continue

```bash
neurogate connect cline      # или continue, cursor
```

Команда покажет, что вписать в настройки: адрес `http://127.0.0.1:8765/v1`, ключ и модель `code`.

### Какую модель выбирать

| Модель | Когда |
|---|---|
| `code` | основная работа с кодом — самые сильные бесплатные кодовые модели |
| `code_fast` | быстрые мелкие правки |
| `auto` | шлюз сам выберет по запросу |
| `chat` | вопросы, объяснения, тексты |

### С подпиской Claude или ChatGPT — режим оркестратора

Платная модель в Claude Code или Codex планирует и проверяет, а код пишут бесплатные модели через
`neurogate delegate`. Лимит подписки уходит только на «мозги». Нужны установленные neurogate и
приложение OpenCode (оно и есть бесплатный исполнитель).

```bash
neurogate connect orchestrator --global   # для всех проектов; без --global — только текущая папка
```

Команда допишет правило в `~/.claude/CLAUDE.md` и `~/.codex/AGENTS.md`, а песочнице Codex разрешит
связь со шлюзом и запись в папки OpenCode (`[sandbox_workspace_write]` в `~/.codex/config.toml`).
Перезапустите Claude Code или Codex. Дальше работайте как обычно; можно прямо попросить:
«код поручи бесплатным моделям через neurogate delegate, сам проверь результат».
Повторный запуск команды обновит правило до новой версии — свой текст в файлах не трогается.

Длинную задачу удобнее передать файлом: `neurogate delegate --file задача.md` (так же
`neurogate ask --file вопрос.md`). На Windows оркестратор делает так сам — в командной строке
Windows перенос строки обрезает задачу.

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
| **Google Gemini (AI Studio)** | сильный код, длинный контекст (1М токенов), картинки на вход, веб-поиск | 10 запросов/мин, 250–1500 запросов/день | Google-аккаунт; из РФ нужен VPN при регистрации | [GEMINI_API_KEY](https://aistudio.google.com/apikey) |
| **OpenRouter** | десятки бесплатных моделей (:free) — Qwen-Coder, DeepSeek, Nemotron, GLM | 20 запросов/мин, 50 запросов/день (1000 после разового депозита $10) | Google/GitHub, карта не нужна | [OPENROUTER_API_KEY](https://openrouter.ai/keys) |
| **NVIDIA NIM** | Qwen3-Coder-480B (лучший бесплатный для кода), DeepSeek, Kimi, без суточного потолка | 40 запросов/мин, без лимита в день | только почта | [NVIDIA_API_KEY](https://build.nvidia.com/settings/api-keys) |
| **Groq** | чат и код, очень быстрые ответы, распознавание речи (Whisper) | 30 запросов/мин, 1–14 тыс. запросов/день на модель | почта или Google/GitHub; из некоторых стран и через VPN вход отклоняется — тогда пропустите | [GROQ_API_KEY](https://console.groq.com/keys) |
| **Inception (Mercury)** | очень быстрые модели Mercury для кода, контекст 1М токенов | 100 млн токенов разово на аккаунт | только почта, без карты | [INCEPTION_API_KEY](https://platform.inceptionlabs.ai) |
| **Gonka Broker** | DeepSeek V4 Flash, GLM-5.3 Flash, MiniMax M2.7 | не меньше 1 млн токенов в месяц, сброс 1-го числа | почта; иногда просят телефон | [GONKA_API_KEY](https://app.gonkabroker.com) |

### Дополнительные — больше квоты и моделей

| Сервис | Что даёт | Лимиты | Что нужно | Где взять ключ |
|---|---|---|---|---|
| **Cerebras** | очень быстрый Qwen-3-235B и gpt-oss, без суточного потолка | старые аккаунты — 5–30 запросов/мин без лимита в день; новым с 08.2026 — $5 на 30 дней | телефон; новым аккаунтам — карта | [CEREBRAS_API_KEY](https://cloud.cerebras.ai/platform) |
| **Mistral** | Mistral Large, Codestral (отдельная квота для кода), эмбеддинги | около 4 запросов/мин на чат + Codestral 30/мин; на бесплатном плане учится на запросах | почта и SMS | [MISTRAL_API_KEY](https://console.mistral.ai/api-keys) |
| **Z.ai (GLM)** | GLM-4.5-Flash навсегда бесплатно | только по числу одновременных запросов | почта; из РФ/СНГ иногда проще open.bigmodel.cn | [ZAI_API_KEY](https://z.ai/manage-apikey/apikey-list) |
| **Cloudflare Workers AI** | модели Llama/Qwen, генерация картинок FLUX и SDXL, эмбеддинги | 10 000 «нейронов» в сутки на весь аккаунт | только почта | [CLOUDFLARE_API_KEY](https://dash.cloudflare.com/profile/api-tokens) |
| **Hugging Face** | доступ к сотням открытых моделей через их роутер | около $0.10 кредита в месяц | только почта | [HF_TOKEN](https://huggingface.co/settings/tokens) |
| **Cohere** | Command-A, Aya (хорошо по-русски), поиск и rerank | 20 запросов/мин, 1000 запросов/месяц, только некоммерческое использование | Google/GitHub/почта | [COHERE_API_KEY](https://dashboard.cohere.com/api-keys) |
| **Poolside** | кодовые модели Laguna | бесплатно на ограниченное время, лимиты не опубликованы | почта | [POOLSIDE_API_KEY](https://platform.poolside.ai) |
| **Ollama Cloud** | DeepSeek V4, Kimi K2, Qwen 3.5, GLM 5 в облаке Ollama | бесплатный тариф с недельной квотой (цифры не опубликованы) | почта или GitHub | [OLLAMA_API_KEY](https://ollama.com/settings/keys) |
| **Kilo Code Gateway** | бесплатные модели шлюза Kilo (набор меняется) | около 200 запросов/час | Google/GitHub | [KILO_API_KEY](https://app.kilo.ai/profile) |
| **Vercel AI Gateway** | запасная квота к бесплатным Ling и Laguna | $5 кредита каждые 30 дней; не пополняйте баланс, иначе бесплатный кредит пропадёт | аккаунт Vercel (GitHub) | [AI_GATEWAY_API_KEY](https://vercel.com/dashboard) |
| **OrcaRouter** | агрегатор 200+ моделей, бесплатные *-free | free-модели работают после привязки GitHub-аккаунта «со стажем» | почта + GitHub | [ORCAROUTER_API_KEY](https://www.orcarouter.ai/console/token) |
| **LLM7** | gpt-4o-mini, DeepSeek, Qwen-Coder; работает и без ключа (30/мин) | 120 запросов/мин с токеном | необязательно | [LLM7_API_KEY](https://token.llm7.io) |
| **OpenCode Zen** | бесплатные DeepSeek V4 Flash, Nemotron Ultra; работает и без ключа | не опубликованы | необязательно | [OPENCODE_API_KEY](https://opencode.ai/zen) |
| **Pollinations** | текст и картинки; без ключа — базовый уровень | с ключом выше | необязательно, вход через GitHub | [POLLINATIONS_API_KEY](https://enter.pollinations.ai) |
| **Jina AI** | эмбеддинги и rerank (для поиска по документам) | 10 млн бесплатных токенов на ключ | ничего — ключ выдаётся прямо на сайте | [JINA_API_KEY](https://jina.ai/api-dashboard/key-manager) |
| **Requesty** | Nemotron 3 Ultra 550B, Gemma 4, Laguna — бесплатные модели роутера | 200 запросов/день на бесплатные модели | почта, без карты | [REQUESTY_API_KEY](https://app.requesty.ai/api-keys) |
| **Routeway** | бесплатные DeepSeek V4 Flash и MiniMax M2.7 | 5 запросов/мин, 200 в день | почта, без карты | [ROUTEWAY_API_KEY](https://routeway.ai) |
| **IteraCompute** | Qwen 3.8 27B | до 30 млн токенов в месяц; акция до 24.11.2026 | почта, без карты и телефона | [ITERACOMPUTE_API_KEY](https://iteracompute.com) |
| **Hetzner Inference (эксперимент)** | Qwen 3.6 35B и Qwen 3.8 27B в Европе | бесплатно, пока идёт эксперимент; около 10 запросов/мин | аккаунт Hetzner (могут попросить способ оплаты) | [HETZNER_INFERENCE_API_KEY](https://experiments.hetzner.com) |
| **Nous Portal** | бесплатные Step 3.7 Flash, Beam 501B, Laguna | лимиты не опубликованы | почта; иногда проверка карты на $0 | [NOUS_API_KEY](https://portal.nousresearch.com) |
| **BazaarLink** | бесплатные DeepSeek V4 Flash, Qwen 3.7 Flash, Nemotron | 10 запросов/мин, 60 «единиц» в день | почта, без карты | [BAZAARLINK_API_KEY](https://bazaarlink.ai/keys) |
| **UnoRouter** | 100+ бесплатных моделей с суффиксом :free | около 1 запроса/мин на модель | почта, без карты | [UNOROUTER_API_KEY](https://unorouter.com/en/token) |
| **Agnes AI** | модели Agnes Flash для чата | около 30 запросов/мин; команда заявляет, что API бесплатный | почта | [AGNES_API_KEY](https://platform.agnes-ai.com/settings/apiKeys) |

### С неудобствами — телефон РФ, верификация, ежедневный чек-ин

| Сервис | Что даёт | Лимиты | Что нужно | Где взять ключ |
|---|---|---|---|---|
| **SambaNova** | DeepSeek V3.x, Llama 4 — быстро | стартовые кредиты; кончились — сами не восстановятся (по free-llm.com с 10.2026 бесплатно больше не дают) | Google/почта | [SAMBANOVA_API_KEY](https://cloud.sambanova.ai/apis) |
| **DeepSeek** | DeepSeek V4 напрямую — сильный код | по free-llm.com бесплатных кредитов больше нет; дальше платно, но дёшево | почта или Google; иногда телефон | [DEEPSEEK_API_KEY](https://platform.deepseek.com/api_keys) |
| **ZenMux** | бесплатные DeepSeek V4 Flash и GLM-4.7 Flash (отдельная квота) | только модели -free; по данным 10.2026 на бесплатном плане API может быть закрыт | почта, без карты | [ZENMUX_API_KEY](https://zenmux.ai/settings/keys) |
| **Together AI** | бесплатная генерация картинок FLUX.1-schnell | по free-llm.com бесплатного больше нет; зависит от акций при регистрации | почта | [TOGETHER_API_KEY](https://api.together.ai/settings/api-keys) |
| **Voyage AI** | эмбеддинги для кода и rerank | 200 млн бесплатных токенов | почта | [VOYAGE_API_KEY](https://dashboard.voyageai.com/organization/api-keys) |
| **GigaChat (Сбер)** | русскоязычный чат и картинки Kandinsky | 1 млн токенов на 30 дней | Сбер ID, телефон РФ | [GIGACHAT_AUTH_KEY](https://developers.sber.ru/studio) |
| **FreeTheAi** | тысячи моделей, включая GPT-5 и Kimi | 10 запросов/мин; КАЖДЫЙ ДЕНЬ нужно вручную нажать /checkin в Discord | Discord | [FREETHEAI_API_KEY](https://discord.gg/secrets) |
| **Alibaba Qwen (DashScope Intl)** | флагманы Qwen 3.6 и Qwen3-Coder-480B, 1М контекст | 1 млн токенов на модель на 90 дней | аккаунт Alibaba Cloud International, телефон и карта, подтверждение личности | [DASHSCOPE_API_KEY](https://bailian.console.alibabacloud.com) |
| **SiliconFlow** | бесплатные Qwen3-8B, DeepSeek-R1-Distill, GLM-4.1V | 1000 запросов/мин; нужна верификация личности | китайский телефон или верификация | [SILICONFLOW_API_KEY](https://cloud.siliconflow.cn/account/ak) |
| **ModelScope** | свежие Qwen 3.5 | 2000 запросов/день; нужна real-name верификация Alibaba | аккаунт Alibaba Cloud с верификацией | [MODELSCOPE_API_KEY](https://modelscope.cn/my/myaccesstoken) |
| **Fireworks AI** | gpt-oss-120b и другие открытые модели | около $1 стартового кредита, 10 запросов/мин без карты | почта | [FIREWORKS_API_KEY](https://app.fireworks.ai/settings/users/api-keys) |
| **AI21 (Jamba)** | Jamba Large, длинный контекст | $10 на 7 дней | почта, без карты | [AI21_API_KEY](https://studio.ai21.com/account/api-key) |
| **Hack Club AI** | бесплатный доступ к моделям для участников Hack Club | только для участников Hack Club (подростки до 18), запросы логируются | членство в Hack Club | [HACKCLUB_AI_API_KEY](https://ai.hackclub.com) |
| **Aion Labs** | модели для текстов и ролевых диалогов (для кода слабо) | 20 тыс. токенов/день, 15 запросов/мин | почта, без карты | [AION_API_KEY](https://www.aionlabs.ai/app/api-keys/) |

**Без ключа работают:** OVHcloud AI Endpoints (открытые модели в EU, 2 запроса/мин), OpenCode Zen (бесплатные модели), LLM7 (30 запросов/мин), Pollinations (текст и картинки), AI Horde (картинки, общая очередь), Edge TTS (озвучка без лимита), LibreTranslate и MyMemory (перевод).
