import json

import pytest
from fastapi.testclient import TestClient

from neurogate import main
from neurogate.providers import ProviderCallResult
from neurogate.router import LLMRouter

WITH_KEY = """
providers:
  - name: fake:coder
    kind: groq
    model: m
    api_key: k
chains:
  chat: [fake:coder]
  code: [fake:coder]
default_chain: chat
"""

NO_KEYS = """
providers:
  - name: fake:needs-key
    kind: groq
    model: m
    api_key_env: GROQ_API_KEY_MISSING_FOR_TESTS
  - name: libretranslate:fedilab
    kind: libretranslate
chains:
  chat: [fake:needs-key]
  translation: [libretranslate:fedilab]
default_chain: chat
"""


def _client(tmp_path, monkeypatch, cfg_text):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(cfg_text, encoding="utf-8")
    monkeypatch.setenv("NEUROGATE_CONFIG", str(cfg))
    monkeypatch.delenv("NEUROGATE_API_TOKEN", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_MISSING_FOR_TESTS", raising=False)
    return TestClient(main.create_app())


@pytest.fixture
def fake_router(monkeypatch):
    seen = {}

    async def chat(self, **kw):
        seen.update(kw)
        return ProviderCallResult(
            text=seen.get("reply_text", "готово"), prompt_tokens=5, completion_tokens=7,
            tool_calls=seen.get("reply_tools"), finish_reason="stop"), "fake:coder", kw["chain_name"]

    async def chat_stream(self, **kw):
        chunk = {"id": "x", "object": "chat.completion.chunk", "choices": [
            {"index": 0, "delta": {"content": "hi"}, "finish_reason": None}]}
        yield f"data: {json.dumps(chunk)}\n\n".encode(), "fake:coder", kw["chain_name"]
        yield b"data: [DONE]\n\n", "fake:coder", kw["chain_name"]

    monkeypatch.setattr(LLMRouter, "chat", chat)
    monkeypatch.setattr(LLMRouter, "chat_stream", chat_stream)
    return seen


def test_no_llm_keys_gives_clear_503_everywhere(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, NO_KEYS)
    for path, body in [
        ("/v1/chat/completions", {"model": "auto", "messages": [{"role": "user", "content": "x"}]}),
        ("/v1/messages", {"model": "claude", "max_tokens": 10, "messages": [{"role": "user", "content": "x"}]}),
        ("/v1/responses", {"model": "code", "input": "x"}),
    ]:
        r = c.post(path, json=body)
        assert r.status_code == 503, path
        assert "/keys" in r.json()["detail"], path


def test_responses_non_stream_with_custom_tool(tmp_path, monkeypatch, fake_router):
    c = _client(tmp_path, monkeypatch, WITH_KEY)
    fake_router["reply_text"] = ""
    fake_router["reply_tools"] = [{"id": "c1", "type": "function",
                                   "function": {"name": "apply_patch", "arguments": '{"input":"*** Begin Patch"}'}}]
    r = c.post("/v1/responses", json={
        "model": "code", "instructions": "sys", "input": "сделай",
        "tools": [{"type": "custom", "name": "apply_patch", "format": {"type": "grammar", "definition": "g"}}],
        "tool_choice": "auto", "max_output_tokens": 99})
    data = r.json()
    assert r.status_code == 200 and data["object"] == "response" and data["status"] == "completed"
    assert data["output"] == [{**data["output"][0], "type": "custom_tool_call", "call_id": "c1",
                               "name": "apply_patch", "input": "*** Begin Patch"}]
    assert data["usage"]["input_tokens"] == 5 and data["usage"]["output_tokens"] == 7
    assert fake_router["chain_name"] == "code" and fake_router["max_tokens"] == 99
    assert fake_router["messages"][0] == {"role": "system", "content": "sys"}
    assert fake_router["tools"][0]["function"]["parameters"]["required"] == ["input"]


def test_responses_stream_events(tmp_path, monkeypatch, fake_router):
    c = _client(tmp_path, monkeypatch, WITH_KEY)
    with c.stream("POST", "/v1/responses", json={"model": "code", "input": "x", "stream": True}) as r:
        body = "".join(r.iter_text())
    events = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
    assert events[0]["type"] == "response.created" and events[-1]["type"] == "response.completed"
    assert events[-1]["response"]["output_text"] == "готово"


def test_responses_upstream_failure(tmp_path, monkeypatch):
    async def boom(self, **kw):
        raise RuntimeError("all down")

    monkeypatch.setattr(LLMRouter, "chat", boom)
    c = _client(tmp_path, monkeypatch, WITH_KEY)
    assert c.post("/v1/responses", json={"model": "code", "input": "x"}).status_code == 502
    with c.stream("POST", "/v1/responses", json={"model": "code", "input": "x", "stream": True}) as r:
        body = "".join(r.iter_text())
    assert "response.failed" in body and "upstream_exhausted" in body


def test_chat_stream_meta_event_only_on_header(tmp_path, monkeypatch, fake_router):
    c = _client(tmp_path, monkeypatch, WITH_KEY)
    req = {"model": "code", "stream": True, "messages": [{"role": "user", "content": "x"}]}
    with c.stream("POST", "/v1/chat/completions", json=req) as r:
        plain = "".join(r.iter_text())
    with c.stream("POST", "/v1/chat/completions", json=req, headers={"X-Neurogate-Meta": "1"}) as r:
        meta = "".join(r.iter_text())
    assert "event: neurogate" not in plain and plain.startswith("data: ")
    assert meta.startswith("event: neurogate\ndata: ") and '"provider": "fake:coder"' in meta


def test_models_lists_chains(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, WITH_KEY)
    ids = [m["id"] for m in c.get("/v1/models").json()["data"]]
    assert {"auto", "chat", "code"} <= set(ids)


def test_exhausted_chain_tells_where_to_add_key(tmp_path, monkeypatch):
    async def boom(self, **kw):
        raise RuntimeError("429 quota")

    monkeypatch.setattr(LLMRouter, "chat", boom)
    c = _client(tmp_path, monkeypatch, WITH_KEY)
    r = c.post("/v1/chat/completions", json={"model": "code", "messages": [{"role": "user", "content": "x"}]})
    msg = r.json()["error"]["message"]
    assert "Бесплатные лимиты кончились" in msg and "http://testserver/keys" in msg

    async def boom_stream(self, **kw):
        raise RuntimeError("429 quota")
        yield  # pragma: no cover — делает функцию генератором

    monkeypatch.setattr(LLMRouter, "chat_stream", boom_stream)
    # Стрим: подсказка приходит обычным текстом ответа, а не ошибкой (её OpenCode повторяет по кругу)
    with c.stream("POST", "/v1/chat/completions", json={"model": "code", "stream": True,
                                                          "messages": [{"role": "user", "content": "x"}]}) as s:
        body = "".join(s.iter_text())
    assert '"content": "⚠️ Бесплатные лимиты кончились' in body and '"finish_reason": "stop"' in body
    assert '"error"' not in body and body.rstrip().endswith("data: [DONE]")
    with c.stream("POST", "/v1/messages", json={"model": "claude", "max_tokens": 10, "stream": True,
                                                 "messages": [{"role": "user", "content": "x"}]}) as s:
        body = "".join(s.iter_text())
    assert "testserver/keys" in body and "text_delta" in body and "event: error" not in body


def test_keys_page_list_add_and_hot_reload(tmp_path, monkeypatch):
    from neurogate import cli

    env = tmp_path / ".env"
    env.write_text("", encoding="utf-8")
    monkeypatch.setenv("NEUROGATE_ENV_FILE", str(env))
    monkeypatch.delenv("GROQ_API_KEY_MISSING_FOR_TESTS", raising=False)
    monkeypatch.setattr(cli, "check_key", lambda s, k: (k.startswith("ok"), "сервис отверг ключ"))
    c = _client(tmp_path, monkeypatch, NO_KEYS)
    assert "Добавь" in c.get("/keys").text
    services = c.get("/keys/list").json()["services"]
    assert services[0]["quick"] and services[0]["key_url"]
    bad = c.post("/keys/add", json={"id": "groq", "key": "bad"}).json()
    assert bad["ok"] is False and "отверг" in bad["message"]
    # NO_KEYS берёт ключ groq из GROQ_API_KEY_MISSING_FOR_TESTS — подменим env сервиса каталога
    monkeypatch.setattr(cli, "load_catalog", lambda: {"quick": [], "services": [
        {"id": "groq", "name": "Groq", "env": "GROQ_API_KEY_MISSING_FOR_TESTS", "priority": 1}]})
    assert c.post("/v1/chat/completions", json={"model": "auto", "messages": [
        {"role": "user", "content": "x"}]}).status_code == 503
    ok = c.post("/keys/add", json={"id": "groq", "key": "ok-123"}).json()
    assert ok["ok"] is True and "подключён" in ok["message"]
    assert "GROQ_API_KEY_MISSING_FOR_TESTS=ok-123" in env.read_text(encoding="utf-8")
    assert c.get("/keys/list").json()["have"] == 1
    # ключ подхватился без перезапуска: цепочка chat больше не пустая
    assert "fake:needs-key" in c.get("/v1/health").json()["chains"]["chat"]


def test_keys_add_refuses_other_sites(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, WITH_KEY)
    r = c.post("/keys/add", json={"id": "groq", "key": "x"}, headers={"Origin": "https://evil.example",
                                                                      "Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403
