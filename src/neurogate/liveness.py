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


# Провайдеры, чей GET {base}/models надёжно перечисляет живые модели по ключу. Модель,
# которой там нет, точно снята (NVIDIA за полгода сняла 9 из 11 записей конфига → 410).
# Обратное не гарантировано (в каталоге бывают модели, отвечающие 404) — их ловит роутер.
_CATALOG_KINDS = {"nvidia", "groq", "cerebras", "mistral", "together", "deepseek"}


def _catalog_ids(base_url: str, api_key: str, timeout: float = 8.0) -> set[str] | None:
    try:
        r = httpx.get(f"{base_url}/models", headers={"Authorization": f"Bearer {api_key}"},
                      timeout=timeout)
        r.raise_for_status()
        return {m["id"] for m in r.json().get("data", []) if m.get("id")}
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("liveness: каталог %s недоступен (%s) — пропускаю сверку", base_url, exc)
        return None


def _drop(cfg: ChainConfig, dead: set[str]) -> None:
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


def prune_dead_catalog_models(cfg: ChainConfig) -> list[str]:
    """Убрать провайдеров из _CATALOG_KINDS, чьей модели нет в каталоге их же API."""
    by_endpoint: dict[tuple[str, str], list] = {}
    for p in cfg.all_providers:
        if getattr(p, "_kind", None) in _CATALOG_KINDS and getattr(p, "_api_key", ""):
            by_endpoint.setdefault((p._base_url, p._api_key), []).append(p)
    dead: set[str] = set()
    for (base, key), providers in by_endpoint.items():
        live = _catalog_ids(base, key)
        if live:
            dead |= {p.name for p in providers if p._model not in live}
    if dead:
        _drop(cfg, dead)
        log.warning("liveness: сняты у провайдера, пропускаю %d: %s", len(dead), ", ".join(sorted(dead)))
    return sorted(dead)


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

    _drop(cfg, dead)
    log.warning(
        "liveness: OpenRouter снял с бесплатного тарифа %d моделей — пропускаю: %s",
        len(dead), ", ".join(sorted(dead)),
    )
    return sorted(dead)
