import os
import stat

import httpx
import pytest

from conftest import FakeResponse
from neurogate import keydrop
from neurogate.envfile import load_env_file, read_env_file, set_env_value


# ---------------------------------------------------------------- envfile

def test_read_env_file_parses_comments_quotes_export_bom(tmp_path):
    p = tmp_path / ".env"
    p.write_bytes(
        "﻿A=1\n# комментарий\n\nexport B='два слова'\nC=\"x\"\nD=val  # хвост\nE=\nnot a line\n"
        .encode("utf-8")
    )
    assert read_env_file(p) == {"A": "1", "B": "два слова", "C": "x", "D": "val", "E": ""}


def test_read_env_file_missing_returns_empty(tmp_path):
    assert read_env_file(tmp_path / "nope") == {}


def test_load_env_file_does_not_override_existing(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text("KEEP=file\nNEW=file\nEMPTY=\n", encoding="utf-8")
    monkeypatch.setenv("KEEP", "env")
    monkeypatch.delenv("NEW", raising=False)
    monkeypatch.delenv("EMPTY", raising=False)
    assert load_env_file(p) == 1
    assert os.environ["KEEP"] == "env"
    assert os.environ["NEW"] == "file"
    assert "EMPTY" not in os.environ


def test_set_env_value_replaces_appends_and_chmods(tmp_path):
    p = tmp_path / ".env"
    p.write_text("GROQ_API_KEY=\nOTHER=1\n", encoding="utf-8")
    set_env_value(p, "GROQ_API_KEY", "gsk_x")
    set_env_value(p, "NEW_KEY", "v")
    set_env_value(p, "GROQ_API_KEY", "gsk_y")
    assert p.read_text(encoding="utf-8") == "GROQ_API_KEY=gsk_y\nOTHER=1\nNEW_KEY=v\n"
    assert stat.S_IMODE(p.stat().st_mode) == 0o600


def test_set_env_value_creates_file(tmp_path):
    p = tmp_path / "new.env"
    set_env_value(p, "K", "v")
    assert read_env_file(p) == {"K": "v"}


# ---------------------------------------------------------------- keydrop

def test_new_code_roundtrip_and_parse():
    drop_id, secret, code = keydrop.new_code()
    assert code == f"NG-{drop_id}-{secret}"
    assert keydrop.parse_code(f"  {code}\n") == (drop_id, secret)


@pytest.mark.parametrize("bad", ["", "NG-short-x", "XX-12345678-abcdefghijklmnopqrstuv", "NG-1234567-" + "a" * 24])
def test_parse_code_rejects_garbage(bad):
    with pytest.raises(keydrop.DropError):
        keydrop.parse_code(bad)


def test_seal_unseal_roundtrip_and_wrong_secret():
    blob = keydrop.seal("secret-one-abcdefghijk", {"GEMINI_API_KEY": "AIza1"})
    assert "AIza1" not in blob
    assert keydrop.unseal("secret-one-abcdefghijk", blob) == {"GEMINI_API_KEY": "AIza1"}
    with pytest.raises(keydrop.DropError):
        keydrop.unseal("other-secret-abcdefghijk", blob)


def test_fetch_ok_404_and_network_error(monkeypatch):
    drop_id, secret, code = keydrop.new_code()
    blob = keydrop.seal(secret, {"K": "v"})
    calls = []

    def ok(url, timeout):
        calls.append(url)
        return FakeResponse(200, {"blob": blob})

    monkeypatch.setattr(httpx, "get", ok)
    assert keydrop.fetch(code, "https://drop.example/") == {"K": "v"}
    assert calls == [f"https://drop.example/p/{drop_id}"]

    monkeypatch.setattr(httpx, "get", lambda url, timeout: FakeResponse(404, {}))
    with pytest.raises(keydrop.DropError, match="использован или устарел"):
        keydrop.fetch(code, "https://drop.example")

    monkeypatch.setattr(httpx, "get", lambda url, timeout: FakeResponse(500, {}))
    with pytest.raises(keydrop.DropError, match="HTTP 500"):
        keydrop.fetch(code, "https://drop.example")

    def boom(url, timeout):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", boom)
    with pytest.raises(keydrop.DropError, match="не ответил"):
        keydrop.fetch(code, "https://drop.example")


def test_fetch_uses_env_url(monkeypatch):
    _, secret, code = keydrop.new_code()
    seen = []
    monkeypatch.setenv("NEUROGATE_DROP_URL", "http://local:1")
    monkeypatch.setattr(httpx, "get", lambda url, timeout: seen.append(url) or FakeResponse(
        200, {"blob": keydrop.seal(secret, {})}))
    keydrop.fetch(code)
    assert seen[0].startswith("http://local:1/p/")
