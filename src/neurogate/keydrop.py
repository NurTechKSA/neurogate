"""Перенос ключей из Telegram-бота на компьютер ученика по одноразовому коду.

Код вида `NG-<id>-<secret>`: по id сервер находит запись, secret — ключ шифрования.
Сервер хранит только шифротекст и id; secret есть лишь у ученика в сообщении бота,
поэтому база бота без кода бесполезна. Запись отдаётся один раз и стирается.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets

import httpx
from cryptography.fernet import Fernet, InvalidToken

DEFAULT_DROP_URL = "https://neurogate.nurtech.dev"
_CODE = re.compile(r"^NG-([A-Za-z0-9]{8})-([A-Za-z0-9_-]{20,64})$")


class DropError(Exception):
    """Понятная ученику ошибка импорта (текст показывается как есть)."""


def _fernet(secret: str) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def new_code() -> tuple[str, str, str]:
    """(drop_id, secret, code)."""
    drop_id = secrets.token_hex(4)
    secret = secrets.token_urlsafe(18)
    return drop_id, secret, f"NG-{drop_id}-{secret}"


def parse_code(code: str) -> tuple[str, str]:
    m = _CODE.match(code.strip())
    if not m:
        raise DropError("Код не похож на код из бота — он начинается с NG- и копируется целиком.")
    return m.group(1), m.group(2)


def seal(secret: str, values: dict[str, str]) -> str:
    return _fernet(secret).encrypt(json.dumps(values).encode()).decode()


def unseal(secret: str, blob: str) -> dict[str, str]:
    try:
        return json.loads(_fernet(secret).decrypt(blob.encode()))
    except (InvalidToken, ValueError) as exc:
        raise DropError("Код не подошёл к ключам — скопируйте его из бота ещё раз целиком.") from exc


def fetch(code: str, base_url: str | None = None) -> dict[str, str]:
    """Забрать и расшифровать ключи. Запись на сервере после этого удаляется."""
    drop_id, secret = parse_code(code)
    url = (base_url or os.getenv("NEUROGATE_DROP_URL") or DEFAULT_DROP_URL).rstrip("/")
    try:
        r = httpx.get(f"{url}/p/{drop_id}", timeout=20)
    except httpx.HTTPError as exc:
        raise DropError(f"Сервер ключей не ответил ({type(exc).__name__}). Проверьте интернет.") from exc
    if r.status_code == 404:
        raise DropError("Код уже использован или устарел (живёт 24 часа). Нажмите в боте «Выдать команду» ещё раз.")
    if r.status_code != 200:
        raise DropError(f"Сервер ключей ответил HTTP {r.status_code}. Попробуйте позже.")
    return unseal(secret, r.json()["blob"])
