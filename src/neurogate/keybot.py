"""Telegram-бот «ключи за пять минут»: ученик по очереди вставляет бесплатные ключи,
бот проверяет каждый, удаляет сообщение с ключом и в конце выдаёт одну команду
установки с одноразовым кодом (см. keydrop.py).

Запуск: `neurogate bot` (TELEGRAM_MODE=polling локально, webhook на сервере).
Окружение:
  TELEGRAM_BOT_TOKEN       — токен от @BotFather
  BOT_STORAGE_KEY          — Fernet-ключ для ключей в процессе сбора (`neurogate bot --gen-key`)
  BOT_DB                   — путь к sqlite (по умолчанию keybot.db)
  PUBLIC_URL               — https://neurogate.nurtech.dev (webhook и адрес выдачи ключей)
  TELEGRAM_WEBHOOK_SECRET  — секрет пути и заголовка вебхука
  TELEGRAM_MODE            — polling | webhook
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from cryptography.fernet import Fernet
from fastapi import FastAPI, Header, HTTPException, Request

from neurogate.cli import check_key, load_catalog
from neurogate.keydrop import DEFAULT_DROP_URL, new_code, seal

log = logging.getLogger("neurogate.keybot")

REPO_RAW = "https://raw.githubusercontent.com/RYAZHAPOVILNUR/neurogate/main"
DROP_TTL = 24 * 3600
SESSION_TTL = 7 * 24 * 3600
_PRIORITY_BADGE = {1: "⭐ начните с этого", 2: "➕ дополнительный", 3: "⚠️ с неудобствами"}


# ---------------------------------------------------------------- storage

class Store:
    def __init__(self, path: str, storage_key: str):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS sessions (chat_id INTEGER PRIMARY KEY, idx INTEGER NOT NULL,"
            " pending_extra TEXT, keys_enc TEXT NOT NULL, updated REAL NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS drops (id TEXT PRIMARY KEY, blob TEXT NOT NULL, expires REAL NOT NULL)"
        )
        self.db.commit()
        self.f = Fernet(storage_key.encode())

    def get(self, chat_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT idx, pending_extra, keys_enc FROM sessions WHERE chat_id=?", (chat_id,)
        ).fetchone()
        if not row:
            return None
        return {"idx": row[0], "pending_extra": row[1], "keys": json.loads(self.f.decrypt(row[2].encode()))}

    def put(self, chat_id: int, s: dict) -> None:
        enc = self.f.encrypt(json.dumps(s["keys"]).encode()).decode()
        self.db.execute(
            "INSERT INTO sessions (chat_id, idx, pending_extra, keys_enc, updated) VALUES (?,?,?,?,?)"
            " ON CONFLICT(chat_id) DO UPDATE SET idx=excluded.idx, pending_extra=excluded.pending_extra,"
            " keys_enc=excluded.keys_enc, updated=excluded.updated",
            (chat_id, s["idx"], s.get("pending_extra"), enc, time.time()),
        )
        self.db.commit()

    def drop_session(self, chat_id: int) -> None:
        self.db.execute("DELETE FROM sessions WHERE chat_id=?", (chat_id,))
        self.db.commit()

    def add_drop(self, drop_id: str, blob: str) -> None:
        self.db.execute("INSERT INTO drops (id, blob, expires) VALUES (?,?,?)",
                        (drop_id, blob, time.time() + DROP_TTL))
        self.db.commit()

    def take_drop(self, drop_id: str) -> str | None:
        row = self.db.execute(
            "DELETE FROM drops WHERE id=? AND expires>? RETURNING blob", (drop_id, time.time())
        ).fetchone()
        self.db.commit()
        return row[0] if row else None

    def cleanup(self) -> None:
        now = time.time()
        self.db.execute("DELETE FROM drops WHERE expires<=?", (now,))
        self.db.execute("DELETE FROM sessions WHERE updated<=?", (now - SESSION_TTL,))
        self.db.commit()


# ---------------------------------------------------------------- telegram

class TG:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.http = httpx.AsyncClient(timeout=60)

    async def call(self, method: str, **params: Any) -> Any:
        r = await self.http.post(f"{self.base}/{method}", json=params)
        data = r.json()
        if not data.get("ok"):
            log.warning("telegram %s failed: %s", method, data.get("description"))
            return None
        return data["result"]

    async def send(self, chat_id: int, text: str, buttons: list[list[dict]] | None = None) -> Any:
        params: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                                  "link_preview_options": {"is_disabled": True}}
        if buttons:
            params["reply_markup"] = {"inline_keyboard": buttons}
        return await self.call("sendMessage", **params)


# ---------------------------------------------------------------- bot logic

class KeyBot:
    def __init__(self, tg: TG, store: Store, drop_url: str):
        self.tg = tg
        self.store = store
        self.drop_url = drop_url
        catalog = load_catalog()
        self.services = sorted(catalog["services"], key=lambda s: s["priority"])
        # Последняя карточка с кнопками в каждом чате — у неё снимаем кнопки, когда
        # приходит следующая (иначе в чате копятся одинаковые «Пропустить»)
        self.last_card: dict[int, int] = {}
        self.keyless = catalog.get("keyless", [])

    # --- rendering

    def _progress(self, keys: dict) -> str:
        got = sum(1 for s in self.services if keys.get(s["env"]))
        filled = min(10, round(got / 15 * 10))  # 15 ключей — «отлично», дальше полоса полная
        return f"{'▰' * filled}{'▱' * (10 - filled)}  ключей: <b>{got}</b>"

    def _card(self, s: dict, idx: int, keys: dict, note: str = "") -> tuple[str, list[list[dict]]]:
        e = html.escape
        steps = "\n".join(f"{i}. {e(step)}" for i, step in enumerate(s.get("steps", []), 1))
        text = (
            f"🔑 <b>{e(s['name'])}</b>   <i>{idx + 1} из {len(self.services)} · "
            f"{_PRIORITY_BADGE.get(s['priority'], '')}</i>\n"
            f"{self._progress(keys)}\n\n"
            f"<b>Даёт:</b> {e(s['gives'])}\n"
            f"<b>Лимит:</b> {e(s['limits'])}\n"
            f"<b>Нужно:</b> {e(s['needs'])}\n\n"
            f"<b>Как получить ключ:</b>\n{steps}\n\n"
            "👇 Откройте страницу, создайте ключ и пришлите его сюда одним сообщением.\n"
            "<i>Сообщение с ключом я сразу удалю из чата.</i>"
        )
        if note:
            text = f"{note}\n\n{text}"
        buttons = [
            [{"text": "🌐 Открыть страницу ключа", "url": s["key_url"]}],
            [{"text": "⏭ Пропустить", "callback_data": "skip"},
             {"text": "✅ Хватит — выдать команду", "callback_data": "done"}],
        ]
        return text, buttons

    async def _show(self, chat_id: int, s_state: dict, note: str = "") -> None:
        idx = s_state["idx"]
        if idx >= len(self.services):
            await self.finish(chat_id)
            return
        text, buttons = self._card(self.services[idx], idx, s_state["keys"], note)
        await self._send_card(chat_id, text, buttons)

    async def _send_card(self, chat_id: int, text: str, buttons: list[list[dict]]) -> None:
        prev = self.last_card.pop(chat_id, None)
        if prev:
            await self.tg.call("editMessageReplyMarkup", chat_id=chat_id, message_id=prev,
                               reply_markup={"inline_keyboard": []})
        sent = await self.tg.send(chat_id, text, buttons)
        if sent and "message_id" in sent:
            self.last_card[chat_id] = sent["message_id"]

    # --- commands

    async def start(self, chat_id: int) -> None:
        state = self.store.get(chat_id)
        have = len(state["keys"]) if state else 0
        text = (
            "⚡ <b>neurogate — бесплатные нейросети для кода</b>\n\n"
            "Соберём ваши бесплатные ключи от сервисов ИИ (Gemini, OpenRouter, Groq, NVIDIA и ещё "
            f"{len(self.services) - 4}). Потом одна команда — и у вас на компьютере ИИ пишет код "
            "<b>в приложении OpenCode</b> (окно, как у Claude и ChatGPT) или в Claude Code — "
            "на бесплатных моделях, без подписок и карт.\n\n"
            "Как это идёт:\n"
            "1️⃣ Я показываю сервис и ссылку — вы создаёте ключ (1–2 минуты)\n"
            "2️⃣ Присылаете ключ сюда — я проверяю и удаляю сообщение\n"
            "3️⃣ Жмёте «Выдать команду» — вставляете её в терминал\n\n"
            "🎯 Минимум — 3 ключа, хорошо — 10–15. Чем больше, тем реже упрётесь в лимит.\n\n"
            "🔒 Ключи хранятся зашифрованными и стираются с сервера, как только установщик их заберёт."
        )
        buttons = [[{"text": "🚀 Начать", "callback_data": "go"}]]
        if have:
            buttons = [[{"text": f"▶️ Продолжить (ключей: {have})", "callback_data": "go"}],
                       [{"text": "✅ Выдать команду", "callback_data": "done"},
                        {"text": "🔄 Начать заново", "callback_data": "reset"}]]
        await self.tg.send(chat_id, text, buttons)

    async def status(self, chat_id: int) -> None:
        state = self.store.get(chat_id)
        keys = state["keys"] if state else {}
        got = [s["name"] for s in self.services if keys.get(s["env"])]
        text = "Пока ни одного ключа. Нажмите /start." if not got else (
            f"{self._progress(keys)}\n\n" + "\n".join(f"✅ {html.escape(n)}" for n in got)
        )
        await self.tg.send(chat_id, text)

    async def finish(self, chat_id: int) -> None:
        state = self.store.get(chat_id)
        keys = state["keys"] if state else {}
        if not keys:
            await self.tg.send(chat_id, "Нет ни одного ключа. Нужен хотя бы один — лучше Gemini или Groq. /start",
                               [[{"text": "▶️ К ключам", "callback_data": "go"}]])
            return
        drop_id, secret, code = new_code()
        self.store.add_drop(drop_id, seal(secret, keys))
        self.store.drop_session(chat_id)
        names = ", ".join(s["name"] for s in self.services if keys.get(s["env"]))
        drop_env = "" if self.drop_url == DEFAULT_DROP_URL else f"NEUROGATE_DROP_URL={self.drop_url} "
        text = (
            f"🎉 <b>Готово! Ключей: {sum(1 for s in self.services if keys.get(s['env']))}</b>\n"
            f"<i>{html.escape(names)}</i>\n\n"
            "🍏 <b>Mac / Linux</b> — откройте «Терминал», вставьте и нажмите Enter:\n"
            f"<code>curl -fsSL {REPO_RAW}/install.sh | {drop_env}NEUROGATE_CODE={code} bash</code>\n\n"
            "🪟 <b>Windows</b> — откройте PowerShell, вставьте и нажмите Enter:\n"
            f"<code>$env:NEUROGATE_CODE=\"{code}\"; irm {REPO_RAW}/install.ps1 | iex</code>\n\n"
            "♻️ <b>neurogate уже стоит?</b> Тогда достаточно:\n"
            f"<code>neurogate import {code}</code>\n\n"
            "⏳ Код срабатывает один раз и живёт 24 часа. Никому его не пересылайте.\n\n"
            "<b>Дальше:</b>\n"
            "⭐ Скачайте приложение <a href=\"https://opencode.ai/download\">OpenCode</a>, откройте "
            "папку проекта и пишите задачу в чат — модель «neurogate/code» уже выбрана.\n"
            "💻 Или в терминале: <code>claude-free</code> — Claude Code на бесплатных моделях.\n\n"
            "Добавить ещё ключей — снова /start."
        )
        await self.tg.send(chat_id, text)

    # --- updates

    async def on_callback(self, cq: dict) -> None:
        chat_id = cq["message"]["chat"]["id"]
        data = cq.get("data")
        await self.tg.call("answerCallbackQuery", callback_query_id=cq["id"])
        # Карточка, на которой нажали кнопку, больше не нужна — убираем кнопки
        await self.tg.call("editMessageReplyMarkup", chat_id=chat_id,
                           message_id=cq["message"]["message_id"], reply_markup={"inline_keyboard": []})
        state = self.store.get(chat_id) or {"idx": 0, "pending_extra": None, "keys": {}}
        if data == "reset":
            self.store.drop_session(chat_id)
            state = {"idx": 0, "pending_extra": None, "keys": {}}
            data = "go"
        if data == "go":
            self.store.put(chat_id, state)
            await self._show(chat_id, state)
        elif data == "skip":
            state["idx"] += 1
            state["pending_extra"] = None
            self.store.put(chat_id, state)
            await self._show(chat_id, state)
        elif data == "done":
            await self.finish(chat_id)

    async def on_message(self, msg: dict) -> None:
        chat_id = msg["chat"]["id"]
        if msg["chat"].get("type") != "private":
            return
        text = (msg.get("text") or "").strip()
        if text in ("/start", "/help") or text.startswith("/start "):
            await self.start(chat_id)
            return
        if text in ("/status", "/keys"):
            await self.status(chat_id)
            return
        if text == "/done":
            await self.finish(chat_id)
            return
        if text == "/reset":
            self.store.drop_session(chat_id)
            await self.start(chat_id)
            return

        state = self.store.get(chat_id)
        if not state or state["idx"] >= len(self.services) or not text:
            await self.start(chat_id)
            return
        # Сообщение с ключом не должно оставаться в истории чата
        await self.tg.call("deleteMessage", chat_id=chat_id, message_id=msg["message_id"])
        s = self.services[state["idx"]]

        if state.get("pending_extra"):
            state["keys"][state["pending_extra"]] = text
            state["pending_extra"] = None
            state["idx"] += 1
            self.store.put(chat_id, state)
            await self._show(chat_id, state, f"✅ <b>{html.escape(s['name'])}</b> подключён")
            return

        ok, why = await asyncio.to_thread(check_key, s, text)
        if ok is False:
            await self.tg.send(chat_id, f"❌ <b>{html.escape(s['name'])}</b>: {html.escape(why)}.\n"
                                        "Скопируйте ключ целиком и пришлите ещё раз — или «Пропустить» выше.")
            return
        state["keys"][s["env"]] = text
        extra = next(iter(s.get("extra_env", [])), None)
        if extra:
            state["pending_extra"] = extra["env"]
            self.store.put(chat_id, state)
            await self.tg.send(chat_id, f"✅ Ключ принят. Ещё нужно: <b>{html.escape(extra['prompt'])}</b>")
            return
        state["idx"] += 1
        self.store.put(chat_id, state)
        mark = "✅" if ok else "☑️"
        suffix = "" if ok else " <i>(у сервиса нет автопроверки — сохранил как есть)</i>"
        await self._show(chat_id, state, f"{mark} <b>{html.escape(s['name'])}</b> подключён{suffix}")

    async def on_update(self, update: dict) -> None:
        try:
            if "callback_query" in update:
                await self.on_callback(update["callback_query"])
            elif "message" in update:
                await self.on_message(update["message"])
        except Exception:  # одна сломанная апдейт не должна ронять бота
            log.exception("update failed")


# ---------------------------------------------------------------- app

def create_bot_app() -> FastAPI:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    store = Store(os.getenv("BOT_DB", "keybot.db"), os.environ["BOT_STORAGE_KEY"])
    public_url = os.getenv("PUBLIC_URL", DEFAULT_DROP_URL).rstrip("/")
    mode = os.getenv("TELEGRAM_MODE", "webhook")
    hook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    tg = TG(token)
    bot = KeyBot(tg, store, public_url)

    async def poll() -> None:
        await tg.call("deleteWebhook")
        offset = 0
        while True:
            try:
                r = await tg.http.post(f"{tg.base}/getUpdates",
                                       json={"offset": offset, "timeout": 50}, timeout=60)
                for u in r.json().get("result", []):
                    offset = u["update_id"] + 1
                    await bot.on_update(u)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("polling error")
                await asyncio.sleep(3)

    async def register_webhook() -> None:
        # Сразу после выкладки домен может ещё не резолвиться или SSL не выпущен —
        # Telegram отвергнет вебхук. Повторяем раз в минуту, пока не примет.
        while True:
            ok = await tg.call("setWebhook", url=f"{public_url}/tg/{hook_secret}",
                               secret_token=hook_secret,
                               allowed_updates=["message", "callback_query"])
            if ok:
                log.info("webhook установлен: %s/tg/…", public_url)
                return
            await asyncio.sleep(60)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await tg.call("setMyCommands", commands=[
            {"command": "start", "description": "Собрать бесплатные ключи"},
            {"command": "status", "description": "Какие ключи уже есть"},
            {"command": "done", "description": "Выдать команду установки"},
            {"command": "reset", "description": "Начать заново"},
        ])
        task = None
        if mode == "polling":
            task = asyncio.create_task(poll())
        else:
            if not hook_secret:
                raise RuntimeError("TELEGRAM_WEBHOOK_SECRET обязателен в режиме webhook")
            task = asyncio.create_task(register_webhook())
        try:
            yield
        finally:
            if task:
                task.cancel()
            await tg.http.aclose()

    app = FastAPI(title="neurogate keybot", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/p/{drop_id}")
    async def pickup(drop_id: str):
        store.cleanup()
        blob = store.take_drop(drop_id) if drop_id.isalnum() and len(drop_id) == 8 else None
        if blob is None:
            raise HTTPException(status_code=404, detail="not found")
        return {"blob": blob}

    @app.post("/tg/{secret}")
    async def webhook(secret: str, request: Request,
                      x_telegram_bot_api_secret_token: str | None = Header(default=None)):
        if not hook_secret or secret != hook_secret or x_telegram_bot_api_secret_token != hook_secret:
            raise HTTPException(status_code=404)
        await bot.on_update(await request.json())
        return {"ok": True}

    return app


def run_bot(argv: list[str]) -> int:
    if "--gen-key" in argv:
        print(Fernet.generate_key().decode())
        return 0
    import uvicorn

    from neurogate.envfile import load_env_file

    load_env_file()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uvicorn.run("neurogate.keybot:create_bot_app", factory=True,
                host=os.getenv("BOT_HOST", "127.0.0.1"), port=int(os.getenv("BOT_PORT", "8780")))
    return 0
