"""OpenAI Responses API (/v1/responses) поверх цепочек chat/completions — для Codex CLI.

Codex работает только по Responses API: вход — список items (message, function_call,
custom_tool_call, *_output, reasoning), инструменты — function и freeform `custom`
(apply_patch с грамматикой Lark). Бесплатные модели умеют лишь function calling, поэтому:

- custom-инструмент превращаем в функцию с одним строковым полем `input`, а вызов
  такой функции возвращаем Codex обратно как `custom_tool_call` (он ждёт сырой текст);
- поток отдаём «целиком»: ждём ответ цепочки (с её фоллбэком) и выпускаем полный набор
  событий response.* — Codex собирает ход по output_item.done и response.completed.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

_CUSTOM_PARAM = "input"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


def _text_of(content: Any) -> str:
    """Текст из content: строка или список частей input_text/output_text/text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for part in content:
        if isinstance(part, dict) and part.get("type") in ("input_text", "output_text", "text"):
            parts.append(part.get("text") or "")
    return "".join(parts)


def _user_content(content: Any) -> Any:
    """user-сообщение: картинки переводим в формат chat/completions, остальное — текстом."""
    if not isinstance(content, list) or not any(
        isinstance(p, dict) and p.get("type") == "input_image" for p in content
    ):
        return _text_of(content)
    out: list[dict[str, Any]] = []
    for p in content:
        if not isinstance(p, dict):
            continue
        if p.get("type") == "input_image" and p.get("image_url"):
            out.append({"type": "image_url", "image_url": {"url": p["image_url"]}})
        elif p.get("type") in ("input_text", "text"):
            out.append({"type": "text", "text": p.get("text") or ""})
    return out


def convert_tools(tools: list[dict[str, Any]] | None) -> tuple[list[dict[str, Any]] | None, set[str]]:
    """Responses-инструменты → chat-инструменты. Возвращает (tools, имена custom-инструментов)."""
    if not tools:
        return None, set()
    out: list[dict[str, Any]] = []
    custom: set[str] = set()
    for t in tools:
        kind = t.get("type")
        if kind == "function":
            out.append({"type": "function", "function": {
                "name": t["name"],
                "description": t.get("description") or "",
                "parameters": t.get("parameters") or {"type": "object", "properties": {}},
            }})
        elif kind == "custom":
            custom.add(t["name"])
            fmt = t.get("format") or {}
            grammar = fmt.get("definition") if fmt.get("type") == "grammar" else None
            desc = (t.get("description") or "")
            if grammar:
                desc += "\n\nThe `input` must follow this grammar exactly:\n" + grammar
            out.append({"type": "function", "function": {
                "name": t["name"],
                "description": desc,
                "parameters": {
                    "type": "object",
                    "properties": {_CUSTOM_PARAM: {"type": "string",
                                                   "description": "Raw tool input text"}},
                    "required": [_CUSTOM_PARAM],
                },
            }})
        # web_search, local_shell, file_search и т.п. — серверные инструменты OpenAI,
        # бесплатным моделям их не исполнить: пропускаем.
    return (out or None), custom


def convert_input(body: dict[str, Any]) -> list[dict[str, Any]]:
    """instructions + input (строка или items) → messages для chat/completions."""
    messages: list[dict[str, Any]] = []
    if body.get("instructions"):
        messages.append({"role": "system", "content": body["instructions"]})
    raw = body.get("input")
    if isinstance(raw, str):
        messages.append({"role": "user", "content": raw})
        return messages
    for item in raw or []:
        kind = item.get("type") or ("message" if "role" in item else None)
        if kind == "message":
            role = item.get("role", "user")
            if role == "developer":
                role = "system"
            if role == "user":
                messages.append({"role": "user", "content": _user_content(item.get("content"))})
            else:
                messages.append({"role": role, "content": _text_of(item.get("content"))})
        elif kind in ("function_call", "custom_tool_call"):
            args = item.get("arguments") if kind == "function_call" else \
                json.dumps({_CUSTOM_PARAM: item.get("input", "")}, ensure_ascii=False)
            call = {"id": item.get("call_id") or item.get("id") or _new_id("call"),
                    "type": "function",
                    "function": {"name": item.get("name", ""), "arguments": args or "{}"}}
            prev = messages[-1] if messages else None
            # Подряд идущие вызовы — одно сообщение ассистента с несколькими tool_calls
            if prev and prev["role"] == "assistant" and prev.get("tool_calls") is not None \
                    and not prev.get("content"):
                prev["tool_calls"].append(call)
            else:
                messages.append({"role": "assistant", "content": None, "tool_calls": [call]})
        elif kind in ("function_call_output", "custom_tool_call_output"):
            out = item.get("output")
            messages.append({"role": "tool", "tool_call_id": item.get("call_id", ""),
                             "content": out if isinstance(out, str) else _text_of(out)
                             or json.dumps(out, ensure_ascii=False)})
        # reasoning и прочие служебные items в историю модели не идут
    return messages


def convert_tool_choice(choice: Any) -> Any:
    if isinstance(choice, dict) and choice.get("type") in ("function", "custom") and choice.get("name"):
        return {"type": "function", "function": {"name": choice["name"]}}
    if choice in ("auto", "none", "required"):
        return choice
    return None


def build_output(text: str, tool_calls: list[dict[str, Any]] | None,
                 custom: set[str]) -> list[dict[str, Any]]:
    """Ответ модели → output items Responses API."""
    output: list[dict[str, Any]] = []
    if text:
        output.append({"type": "message", "id": _new_id("msg"), "status": "completed",
                       "role": "assistant",
                       "content": [{"type": "output_text", "text": text, "annotations": []}]})
    for tc in tool_calls or []:
        fn = tc.get("function") or {}
        name = fn.get("name", "")
        args = fn.get("arguments") or "{}"
        call_id = tc.get("id") or _new_id("call")
        if name in custom:
            try:
                raw = json.loads(args).get(_CUSTOM_PARAM, "")
            except (ValueError, AttributeError):
                raw = args  # модель прислала сырой текст вместо JSON — отдаём как есть
            output.append({"type": "custom_tool_call", "id": _new_id("ctc"), "status": "completed",
                           "call_id": call_id, "name": name, "input": raw})
        else:
            output.append({"type": "function_call", "id": _new_id("fc"), "status": "completed",
                           "call_id": call_id, "name": name, "arguments": args})
    return output


def response_object(resp_id: str, model: str, output: list[dict[str, Any]], usage: dict[str, int],
                    status: str = "completed") -> dict[str, Any]:
    return {
        "id": resp_id, "object": "response", "created_at": int(time.time()),
        "status": status, "model": model, "output": output,
        "output_text": "".join(c.get("text", "") for o in output if o["type"] == "message"
                               for c in o["content"]),
        "usage": {"input_tokens": usage.get("input", 0), "output_tokens": usage.get("output", 0),
                  "total_tokens": usage.get("input", 0) + usage.get("output", 0),
                  "input_tokens_details": {"cached_tokens": 0},
                  "output_tokens_details": {"reasoning_tokens": 0}},
        "error": None, "incomplete_details": None,
    }


def stream_events(resp: dict[str, Any]) -> list[dict[str, Any]]:
    """Полный набор SSE-событий для уже готового ответа."""
    seq = 0
    events: list[dict[str, Any]] = []

    def emit(ev: dict[str, Any]) -> None:
        nonlocal seq
        ev["sequence_number"] = seq
        seq += 1
        events.append(ev)

    shell = {**resp, "status": "in_progress", "output": []}
    emit({"type": "response.created", "response": shell})
    emit({"type": "response.in_progress", "response": shell})
    for idx, item in enumerate(resp["output"]):
        if item["type"] == "message":
            emit({"type": "response.output_item.added", "output_index": idx,
                  "item": {**item, "status": "in_progress", "content": []}})
            part = item["content"][0]
            emit({"type": "response.content_part.added", "item_id": item["id"], "output_index": idx,
                  "content_index": 0, "part": {"type": "output_text", "text": "", "annotations": []}})
            emit({"type": "response.output_text.delta", "item_id": item["id"], "output_index": idx,
                  "content_index": 0, "delta": part["text"]})
            emit({"type": "response.output_text.done", "item_id": item["id"], "output_index": idx,
                  "content_index": 0, "text": part["text"]})
            emit({"type": "response.content_part.done", "item_id": item["id"], "output_index": idx,
                  "content_index": 0, "part": part})
        elif item["type"] == "function_call":
            emit({"type": "response.output_item.added", "output_index": idx,
                  "item": {**item, "status": "in_progress", "arguments": ""}})
            emit({"type": "response.function_call_arguments.delta", "item_id": item["id"],
                  "output_index": idx, "delta": item["arguments"]})
            emit({"type": "response.function_call_arguments.done", "item_id": item["id"],
                  "output_index": idx, "arguments": item["arguments"]})
        elif item["type"] == "custom_tool_call":
            emit({"type": "response.output_item.added", "output_index": idx,
                  "item": {**item, "status": "in_progress", "input": ""}})
            emit({"type": "response.custom_tool_call_input.delta", "item_id": item["id"],
                  "output_index": idx, "delta": item["input"]})
            emit({"type": "response.custom_tool_call_input.done", "item_id": item["id"],
                  "output_index": idx, "input": item["input"]})
        emit({"type": "response.output_item.done", "output_index": idx, "item": item})
    emit({"type": "response.completed", "response": resp})
    return events


def to_sse(events: list[dict[str, Any]]) -> bytes:
    return b"".join(
        f"event: {e['type']}\ndata: {json.dumps(e, ensure_ascii=False)}\n\n".encode() for e in events
    )
