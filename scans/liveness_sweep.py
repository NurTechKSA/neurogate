"""Liveness sweep over providers already present in config.yaml.

Sends a tiny chat request to every chat-capable provider and reports the HTTP
status/error class. Useful after model catalogs rotate: catches 404
`model_not_found`, 401/402 revoked keys, 429 exhausted free tiers.

Usage:
    uv run python scans/liveness_sweep.py [--only-kind kilo] [--chain code]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scans"))

import yaml  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from neurogate.config import _build_provider  # noqa: E402

CONFIG = ROOT / "config.yaml"

# Providers whose `chat` isn't an LLM completion (images, embeddings, TTS, …).
NON_CHAT_KINDS = {
    "gemini_image", "cloudflare_image", "pollinations_image", "together_image",
    "aihorde", "yandex_art", "gigachat_image", "freetheai_image",
    "edge_tts", "gemini_embed", "cohere_embed", "openai_embed",
    "cloudflare_embed", "rerank", "groq_whisper", "hf_space_audio",
    "libretranslate", "mymemory", "yandex_translate", "cohere_translate",
    "openai_moderation", "mistral_moderation", "llama_guard",
}

_HTTP_RE = re.compile(r"HTTP (\d{3})")


async def probe(entry: dict) -> dict:
    name = entry["name"]
    kind = entry.get("kind", "openai")
    if kind in NON_CHAT_KINDS:
        return {"name": name, "kind": kind, "status": "skipped_non_chat"}
    try:
        p = _build_provider({**entry, "rpm": 999, "rpd": 999, "timeout": 90})
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "kind": kind, "status": "build_error", "detail": repr(exc)[:200]}
    if p is None:
        return {"name": name, "kind": kind, "status": "skipped_build"}
    try:
        r = await p.chat(
            messages=[{"role": "user", "content": "ping"}],
            temperature=0.0,
            max_tokens=8,
        )
    except Exception as exc:  # noqa: BLE001
        msg = str(exc) or repr(exc)
        m = _HTTP_RE.search(msg)
        code = int(m.group(1)) if m else None
        if code is None and "timeout" in msg.lower():
            return {"name": name, "kind": kind, "status": "timeout", "detail": msg[:200]}
        if code is None:
            return {"name": name, "kind": kind, "status": "error", "detail": msg[:200]}
        return {"name": name, "kind": kind, "status": f"http_{code}", "detail": msg[:200]}
    text = (getattr(r, "text", "") or "").strip()
    if not text:
        # Thinking-only models burn the whole budget on reasoning tokens: retry
        # with a realistic budget before calling the provider dead.
        try:
            r = await p.chat(
                messages=[{"role": "user", "content": "Say OK"}],
                temperature=0.0,
                max_tokens=1200,
            )
        except Exception as exc:  # noqa: BLE001
            msg = str(exc) or repr(exc)
            m = _HTTP_RE.search(msg)
            code = int(m.group(1)) if m else None
            return {"name": name, "kind": kind, "status": f"http_{code}" if code else "error",
                    "detail": msg[:200]}
        text = (getattr(r, "text", "") or "").strip()
        if not text:
            return {"name": name, "kind": kind, "status": "empty", "detail": "200 but empty text (1200 tok)"}
        return {"name": name, "kind": kind, "status": "ok_slow_thinking"}
    return {"name": name, "kind": kind, "status": "ok"}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", action="append")
    ap.add_argument("--chain")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--json-out")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text())
    entries = [e for e in cfg.get("providers", []) if isinstance(e, dict)]
    chains = cfg.get("chains") or {}
    if args.chain:
        wanted = set(chains[args.chain])
        entries = [e for e in entries if e.get("name") in wanted]
    if args.kind:
        entries = [e for e in entries if (e.get("kind") or "").lower() in set(args.kind)]

    sem = asyncio.Semaphore(args.concurrency)

    async def run(e: dict) -> dict:
        async with sem:
            return await probe(e)

    results = await asyncio.gather(*(run(e) for e in entries))

    # Kinds the sweep tried but which aren't chat by nature.
    for r in results:
        d = r.get("detail") or ""
        if r["status"] == "error" and ("is embeddings-only" in d or "is rerank-only" in d or "is translation-only" in d):
            r["status"] = "skipped_non_chat"

    by_status: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_status[r["status"]].append(r)

    print(f"probed {len(results)} providers ({len(entries)} selected)\n")
    for status in sorted(by_status, key=lambda s: (s != "ok", s)):
        items = by_status[status]
        print(f"== {status} ({len(items)})")
        for r in items[:80]:
            detail = (r.get("detail") or "").replace("\n", " ")[:110]
            print(f"  {r['name']:<52} {detail}")
        print()

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
