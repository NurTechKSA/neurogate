import json

import httpx
import pytest

from conftest import FakeResponse
from neurogate import liveness
from neurogate import responses_compat as rc
from neurogate.config import ChainConfig
from neurogate.providers import _messages_to_gemini, _sig_cache_put

# ---------------------------------------------------------------- responses_compat

CODEX_TOOLS = [
    {"type": "function", "name": "shell", "description": "run",
     "parameters": {"type": "object", "properties": {"command": {"type": "array"}}}},
    {"type": "custom", "name": "apply_patch", "description": "Edit files.",
     "format": {"type": "grammar", "syntax": "lark", "definition": "start: begin_patch hunk+ end_patch"}},
    {"type": "web_search"},
]


def test_convert_tools_function_custom_and_skip():
    tools, custom = rc.convert_tools(CODEX_TOOLS)
    assert custom == {"apply_patch"}
    assert [t["function"]["name"] for t in tools] == ["shell", "apply_patch"]
    patch = tools[1]["function"]
    assert patch["parameters"]["required"] == ["input"]
    assert "start: begin_patch" in patch["description"]
    assert rc.convert_tools(None) == (None, set())
    assert rc.convert_tools([{"type": "web_search"}]) == (None, set())


def test_convert_input_full_codex_history():
    body = {
        "instructions": "Ты Codex.",
        "input": [
            {"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "правила"}]},
            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "сделай"}]},
            {"type": "reasoning", "summary": []},
            {"type": "function_call", "call_id": "c1", "name": "shell", "arguments": '{"command":["ls"]}'},
            {"type": "custom_tool_call", "call_id": "c2", "name": "apply_patch", "input": "*** Begin Patch"},
            {"type": "function_call_output", "call_id": "c1", "output": "a.txt"},
            {"type": "custom_tool_call_output", "call_id": "c2", "output": [{"type": "input_text", "text": "ok"}]},
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "готово"}]},
        ],
    }
    msgs = rc.convert_input(body)
    assert [m["role"] for m in msgs] == ["system", "system", "user", "assistant", "tool", "tool", "assistant"]
    calls = msgs[3]["tool_calls"]
    assert [c["id"] for c in calls] == ["c1", "c2"], "подряд идущие вызовы — одно сообщение"
    assert json.loads(calls[1]["function"]["arguments"]) == {"input": "*** Begin Patch"}
    assert msgs[4] == {"role": "tool", "tool_call_id": "c1", "content": "a.txt"}
    assert msgs[5]["content"] == "ok"


def test_convert_input_string_and_images():
    assert rc.convert_input({"input": "привет"}) == [{"role": "user", "content": "привет"}]
    msgs = rc.convert_input({"input": [{"role": "user", "content": [
        {"type": "input_text", "text": "что тут"}, {"type": "input_image", "image_url": "data:x"}]}]})
    assert msgs[0]["content"] == [{"type": "text", "text": "что тут"},
                                  {"type": "image_url", "image_url": {"url": "data:x"}}]


def test_convert_tool_choice():
    assert rc.convert_tool_choice("auto") == "auto"
    assert rc.convert_tool_choice({"type": "custom", "name": "apply_patch"}) == \
        {"type": "function", "function": {"name": "apply_patch"}}
    assert rc.convert_tool_choice({"type": "web_search"}) is None


def test_build_output_text_function_custom_and_raw_fallback():
    out = rc.build_output("Готово", [
        {"id": "a", "function": {"name": "shell", "arguments": '{"command":["ls"]}'}},
        {"id": "b", "function": {"name": "apply_patch", "arguments": '{"input":"*** Begin Patch"}'}},
        {"id": "c", "function": {"name": "apply_patch", "arguments": "*** raw text"}},
    ], {"apply_patch"})
    assert [o["type"] for o in out] == ["message", "function_call", "custom_tool_call", "custom_tool_call"]
    assert out[0]["content"][0]["text"] == "Готово"
    assert out[1]["call_id"] == "a" and out[1]["arguments"] == '{"command":["ls"]}'
    assert out[2]["input"] == "*** Begin Patch" and out[3]["input"] == "*** raw text"


def test_stream_events_order_and_sse():
    output = rc.build_output("hi", [{"id": "a", "function": {"name": "shell", "arguments": "{}"}},
                                    {"id": "b", "function": {"name": "apply_patch", "arguments": '{"input":"p"}'}}],
                             {"apply_patch"})
    resp = rc.response_object("resp_1", "code", output, {"input": 3, "output": 4})
    assert resp["usage"]["total_tokens"] == 7 and resp["output_text"] == "hi"
    evs = rc.stream_events(resp)
    types = [e["type"] for e in evs]
    assert types[0] == "response.created" and types[-1] == "response.completed"
    assert [e["sequence_number"] for e in evs] == list(range(len(evs)))
    assert types.count("response.output_item.done") == 3
    assert "response.output_text.delta" in types and "response.function_call_arguments.done" in types
    assert "response.custom_tool_call_input.done" in types
    sse = rc.to_sse(evs).decode()
    assert sse.startswith("event: response.created\ndata: {") and sse.endswith("\n\n")


# ---------------------------------------------------------------- liveness

class P:
    def __init__(self, name, kind, model, base="https://api.x/v1", key="k"):
        self.name, self._kind, self._model, self._base_url, self._api_key = name, kind, model, base, key


def _cfg(providers, chains, default="code"):
    return ChainConfig(chains=chains, default=default, all_providers=providers)


def test_prune_dead_free_models(monkeypatch):
    live, dead, paid = P("or:a", "openrouter", "a:free"), P("or:b", "openrouter", "b:free"), \
        P("or:c", "openrouter", "c")
    cfg = _cfg([live, dead, paid], {"code": [dead, live, paid], "x": [dead]})
    monkeypatch.setattr(httpx, "get", lambda url, timeout: FakeResponse(200, {"data": [{"id": "a:free"}]}))
    assert liveness.prune_dead_free_models(cfg) == ["or:b"]
    assert [p.name for p in cfg.chains["code"]] == ["or:a", "or:c"]
    assert "x" not in cfg.chains, "опустевшая цепочка убирается"


def test_prune_dead_catalog_models_and_default_fallback(monkeypatch):
    gone, ok = P("nv:old", "nvidia", "old"), P("nv:new", "nvidia", "new")
    cfg = _cfg([gone, ok], {"code": [gone], "chat": [ok]}, default="code")

    def fake_get(url, headers, timeout):
        assert url == "https://api.x/v1/models" and headers == {"Authorization": "Bearer k"}
        return FakeResponse(200, {"data": [{"id": "new"}]})

    monkeypatch.setattr(httpx, "get", fake_get)
    assert liveness.prune_dead_catalog_models(cfg) == ["nv:old"]
    assert cfg.default == "chat" and cfg.dropped_default == "code"


def test_liveness_fails_open_on_network_error(monkeypatch):
    a = P("nv:a", "nvidia", "a")
    cfg = _cfg([a], {"code": [a]})

    def boom(*args, **kw):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", boom)
    assert liveness.prune_dead_catalog_models(cfg) == []
    assert liveness.prune_dead_free_models(_cfg([P("o", "openrouter", "z:free")], {"c": []})) == []
    assert cfg.chains["code"] == [a]


# ---------------------------------------------------------------- gemini thought_signature

def _history(call_id):
    return [{"role": "user", "content": "x"},
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": call_id, "type": "function", "function": {"name": "write", "arguments": '{"p":1}'}}]},
            {"role": "tool", "tool_call_id": call_id, "content": "ok"}]


def _sigs(messages):
    _, contents = _messages_to_gemini(messages)
    return [p.thought_signature for c in contents for p in c.parts if p.function_call]


def test_foreign_tool_call_gets_dummy_signature():
    assert _sigs(_history("foreign-call-xyz")) == [b"skip_thought_signature_validator"]


def test_cached_signature_wins_over_dummy():
    _sig_cache_put("gemini-call-1", b"real-sig")
    assert _sigs(_history("gemini-call-1")) == [b"real-sig"]


# ---------------------------------------------------------------- config

def test_load_config_dedupes_and_marks_dropped_default(tmp_path, monkeypatch):
    from neurogate.config import load_config

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text("""
providers:
  - name: a
    kind: groq
    model: m
    api_key: k
  - name: needs-key
    kind: groq
    model: m2
    api_key_env: GROQ_API_KEY
chains:
  chat: [needs-key]
  code: [a, a, a]
default_chain: chat
""", encoding="utf-8")
    cfg = load_config(cfg_path)
    assert [p.name for p in cfg.chains["code"]] == ["a"]
    assert cfg.default == "code" and cfg.dropped_default == "chat"
