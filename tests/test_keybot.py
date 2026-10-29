import asyncio
import re
import sqlite3
import time

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from neurogate import keybot, keydrop
from neurogate.keybot import KeyBot, Store

CHAT = 42


class FakeTG:
    def __init__(self):
        self.sent: list[tuple[str, list | None]] = []
        self.calls: list[tuple[str, dict]] = []

    async def call(self, method, **params):
        self.calls.append((method, params))
        return {"ok": True}

    async def send(self, chat_id, text, buttons=None):
        self.sent.append((text, buttons))
        return {"message_id": 1000 + len(self.sent)}


@pytest.fixture
def bot(tmp_path, monkeypatch):
    tg = FakeTG()
    b = KeyBot(tg, Store(str(tmp_path / "kb.db"), Fernet.generate_key().decode()), "http://drop")
    # Проверка ключей без сети: «nvapi-…» — без проверки, «ok…» — принят, остальное — отвергнут
    monkeypatch.setattr(keybot, "check_key", lambda s, k: (None, "без проверки") if k.startswith("nvapi")
                        else (True, "ok") if k.startswith("ok") else (False, "сервис отверг ключ"))
    return b, tg


class Driver:
    def __init__(self, bot):
        self.bot, self.n = bot, 0

    def run(self, update):
        asyncio.run(self.bot.on_update(update))

    def msg(self, text, chat_type="private"):
        self.n += 1
        self.run({"message": {"message_id": self.n, "chat": {"id": CHAT, "type": chat_type}, "text": text}})

    def cb(self, data):
        self.run({"callback_query": {"id": "q", "data": data,
                                     "message": {"message_id": 7, "chat": {"id": CHAT}}}})


def last(tg):
    return tg.sent[-1][0]


def buttons(tg):
    return [b.get("callback_data") or b.get("url") for row in (tg.sent[-1][1] or []) for b in row]


def test_start_asks_computer(bot):
    b, tg = bot
    Driver(b).msg("/start")
    assert "3 бесплатных ключа" in last(tg) and "Какой у тебя компьютер" in last(tg)
    assert buttons(tg) == ["os:mac", "os:win"]


def test_one_button_per_key_then_command_for_chosen_os(bot):
    b, tg = bot
    d = Driver(b)
    d.cb("os:win")
    assert "Ключ 1 из 3 · Google Gemini" in last(tg) and "/skip" in last(tg)
    assert buttons(tg) == ["https://aistudio.google.com/apikey"], "одна кнопка — получить ключ"
    d.msg("bad-key")
    assert "сервис отверг ключ" in last(tg)
    assert ("deleteMessage", {"chat_id": CHAT, "message_id": 1}) in tg.calls
    d.msg("ok-gemini")
    assert "Gemini (AI Studio)</b> подключён" in last(tg) and "Ключ 2 из 3 · OpenRouter" in last(tg)
    d.msg("/skip")
    assert "Ключ 3 из 3 · NVIDIA" in last(tg)
    d.msg("nvapi-123")
    final = last(tg)
    code = re.search(r"NG-[0-9a-f]{8}-[A-Za-z0-9_-]+", final).group(0)
    assert "Ключи готовы (2)" in final and "PowerShell" in final and "install.ps1" in final
    assert "install.sh" not in final, "команда только под выбранный компьютер"
    assert tg.sent[-1][1] is None, "в итоге нет кнопок"
    assert b.store.get(CHAT) is None, "сессия с ключами стёрта после выдачи"
    drop_id, secret = keydrop.parse_code(code)
    blob = b.store.take_drop(drop_id)
    assert keydrop.unseal(secret, blob) == {"GEMINI_API_KEY": "ok-gemini", "NVIDIA_API_KEY": "nvapi-123"}
    assert b.store.take_drop(drop_id) is None, "выдаётся один раз"


def test_mac_command(bot):
    b, tg = bot
    d = Driver(b)
    d.cb("os:mac")
    d.msg("ok-gemini")
    d.msg("/skip")
    d.msg("/skip")
    assert "Терминал" in last(tg) and "install.sh" in last(tg) and "install.ps1" not in last(tg)


def test_all_quick_skipped_goes_to_spare_services(bot):
    b, tg = bot
    d = Driver(b)
    d.cb("os:mac")
    for _ in range(3):
        d.msg("/skip")
    assert "Ещё один ключ" in last(tg) and "Без ключа не обойтись" in last(tg)
    d.msg("ok-spare")
    assert "Ключи готовы (1)" in last(tg)


def test_previous_card_buttons_removed(bot):
    b, tg = bot
    d = Driver(b)
    d.cb("os:mac")
    first_card = 1000 + len(tg.sent)
    d.msg("/skip")
    assert ("editMessageReplyMarkup", {"chat_id": CHAT, "message_id": first_card,
                                      "reply_markup": {"inline_keyboard": []}}) in tg.calls


def test_done_without_keys_status_reset_and_old_buttons(bot):
    b, tg = bot
    d = Driver(b)
    d.cb("done")
    assert "Нет ни одного ключа" in last(tg)
    d.msg("/status")
    assert "ни одного ключа" in last(tg)
    d.cb("go")  # кнопка из старых сообщений бота — просто продолжаем
    assert "Ключ 1 из 3" in last(tg)
    d.msg("ok-1")
    d.msg("/status")
    assert "Ключей: <b>1</b>" in last(tg)
    d.msg("/start")
    assert "Ключей уже: <b>1</b>" in last(tg)
    d.msg("/reset")
    assert b.store.get(CHAT) is None and "Какой у тебя компьютер" in last(tg)


def test_cloudflare_asks_account_id(bot):
    b, tg = bot
    d = Driver(b)
    idx = next(i for i, s in enumerate(b.services) if s["id"] == "cloudflare")
    b.store.put(CHAT, {"idx": idx, "pending_extra": None, "keys": {}, "os": "mac"})
    d.msg("ok-cf-token")
    assert "Account ID" in last(tg)
    d.msg("acc-123")
    code = re.search(r"NG-[0-9a-f]{8}-[A-Za-z0-9_-]+", last(tg)).group(0)
    drop_id, secret = keydrop.parse_code(code)
    keys = keydrop.unseal(secret, b.store.take_drop(drop_id))
    assert keys == {"CLOUDFLARE_API_KEY": "ok-cf-token", "CLOUDFLARE_ACCOUNT_ID": "acc-123"}


def test_group_chats_ignored(bot):
    b, tg = bot
    Driver(b).msg("/start", chat_type="group")
    assert tg.sent == []


def test_store_migrates_old_schema_and_expires(tmp_path, monkeypatch):
    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE sessions (chat_id INTEGER PRIMARY KEY, idx INTEGER NOT NULL, "
                "pending_extra TEXT, keys_enc TEXT NOT NULL, updated REAL NOT NULL)")
    con.commit()
    con.close()
    st = Store(str(db), Fernet.generate_key().decode())
    secret = "gsk_SUPER_SECRET_VALUE_123"
    st.put(1, {"idx": 2, "pending_extra": None, "keys": {"A": secret}, "os": "win"})
    assert st.get(1) == {"idx": 2, "pending_extra": None, "os": "win", "keys": {"A": secret}}
    raw = sqlite3.connect(db).execute("SELECT keys_enc FROM sessions").fetchone()[0]
    assert secret not in raw, "ключи в базе зашифрованы"
    st.add_drop("abcd1234", "blob")
    real_time = time.time
    monkeypatch.setattr(keybot.time, "time", lambda: real_time() + keybot.DROP_TTL + 5)
    assert st.take_drop("abcd1234") is None, "просроченный код не выдаётся"


@pytest.fixture
def app(tmp_path, monkeypatch):
    async def noop(self, method, **params):
        return {"ok": True}

    monkeypatch.setattr(keybot.TG, "call", noop)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1:x")
    monkeypatch.setenv("BOT_STORAGE_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("BOT_DB", str(tmp_path / "app.db"))
    monkeypatch.setenv("TELEGRAM_MODE", "webhook")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    monkeypatch.setenv("PUBLIC_URL", "https://drop.example")
    with TestClient(keybot.create_bot_app()) as client:
        yield client


def test_http_health_landing_pickup_and_webhook_secret(app, tmp_path, monkeypatch):
    assert app.get("/health").json() == {"ok": True}
    page = app.get("/")
    assert page.status_code == 200 and "Пиши код с ИИ" in page.text and "@nurtechneurogatebot" in page.text
    assert app.get("/p/zzzz").status_code == 404
    assert app.get("/p/abcd1234").status_code == 404
    assert app.post("/tg/wrong", json={}).status_code == 404
    assert app.post("/tg/s3cret", json={}).status_code == 404, "нужен и заголовок секрета"
    ok = app.post("/tg/s3cret", json={"update_id": 1},
                  headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"})
    assert ok.json() == {"ok": True}
    st = Store(str(tmp_path / "app.db"), Fernet.generate_key().decode())
    st.add_drop("abcd1234", "blob-1")
    assert app.get("/p/abcd1234").json() == {"blob": "blob-1"}
    assert app.get("/p/abcd1234").status_code == 404
