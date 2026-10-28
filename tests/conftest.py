"""Общие фикстуры: изолированный HOME/.env/Codex, без сети и без реальных ключей."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Тесты не должны писать в рабочие stats.db / keybot.db проекта
_TMP = tempfile.mkdtemp(prefix="neurogate-tests-")
os.environ["NEUROGATE_STATS_DB"] = str(Path(_TMP) / "stats.db")
os.environ["NEUROGATE_SKIP_LIVENESS"] = "1"


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Чистый HOME: ~/.local/bin, ~/.codex, ~/.config/opencode и .env живут во временной папке."""
    h = tmp_path / "home"
    h.mkdir()
    env = tmp_path / ".env"
    env.write_text("NEUROGATE_PORT=8799\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("CODEX_HOME", str(h / ".codex"))
    monkeypatch.setenv("NEUROGATE_ENV_FILE", str(env))
    for var in ("NEUROGATE_PORT", "NEUROGATE_HOST", "NEUROGATE_API_TOKEN", "NEUROGATE_CALLER_DIR"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: h))
    return h


class FakeResponse:
    def __init__(self, status: int = 200, payload=None, text: str = ""):
        self.status_code = status
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        import httpx

        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)
