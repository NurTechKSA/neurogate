"""Отсев снятых бесплатных моделей OpenRouter на старте.

Каталог `:free` у OpenRouter ротируется каждые несколько недель: снятая модель
отвечает 404 «unavailable for free», и каждый запрос тратит на неё круг фоллбэка.
Публичный GET /api/v1/models (без ключа) отдаёт актуальный список — сверяемся с ним
и убираем из цепочек то, чего там уже нет. Сеть недоступна → ничего не трогаем.
"""

from __future__ import annotations

import logging

import httpx

from neurogate.config import ChainConfig

log = logging.getLogger(__name__)

_OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def _openrouter_free_ids(timeout: float = 8.0) -> set[str] | None:
    try:
        r = httpx.get(_OPENROUTER_MODELS_URL, timeout=timeout)
        r.raise_for_status()
        return {m["id"] for m in r.json().get("data", []) if m.get("id", "").endswith(":free")}
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("liveness: не удалось получить каталог OpenRouter (%s) — пропускаю сверку", exc)
        return None


def prune_dead_free_models(cfg: ChainConfig) -> list[str]:
    """Убрать из cfg openrouter-провайдеров с `:free`-моделью, которой нет в каталоге.
    Мутирует cfg на месте, возвращает имена убранных провайдеров."""
    candidates = [
        p for p in cfg.all_providers
        if getattr(p, "_kind", None) == "openrouter"
        and str(getattr(p, "_model", "")).endswith(":free")
    ]
    if not candidates:
        return []
    live = _openrouter_free_ids()
    if not live:
        return []
    dead = {p.name for p in candidates if p._model not in live}
    if not dead:
        return []

    cfg.all_providers = [p for p in cfg.all_providers if p.name not in dead]
    for chain_name in list(cfg.chains):
        kept = [p for p in cfg.chains[chain_name] if p.name not in dead]
        if kept:
            cfg.chains[chain_name] = kept
        else:
            del cfg.chains[chain_name]
            log.warning("liveness: цепочка %s опустела после отсева — убрана", chain_name)
    if cfg.default not in cfg.chains and cfg.chains:
        cfg.dropped_default = cfg.dropped_default or cfg.default
        cfg.default = next(iter(cfg.chains))
    log.warning(
        "liveness: OpenRouter снял с бесплатного тарифа %d моделей — пропускаю: %s",
        len(dead), ", ".join(sorted(dead)),
    )
    return sorted(dead)
