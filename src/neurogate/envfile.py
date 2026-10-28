"""Минимальная работа с .env без внешних зависимостей.

`uv run neurogate` сам .env не читает (на сервере его подгружает systemd через
EnvironmentFile), поэтому run() вызывает load_env_file перед стартом. Значения из
настоящего окружения важнее файла — так systemd/docker-переменные не перетираются.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def default_env_path() -> Path:
    return Path(os.getenv("NEUROGATE_ENV_FILE", ".env"))


def _unquote(raw: str) -> str:
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        return raw[1:-1]
    # Комментарий в конце строки: `KEY=value  # note`
    return re.split(r"\s+#", raw, maxsplit=1)[0]


def read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _LINE.match(line)
        if m:
            values[m.group(1)] = _unquote(m.group(2))
    return values


def load_env_file(path: Path | None = None) -> int:
    """Подгрузить .env в os.environ, не перетирая уже выставленные непустые значения.
    Возвращает число подставленных переменных."""
    loaded = 0
    for key, value in read_env_file(path or default_env_path()).items():
        if value and not os.environ.get(key):
            os.environ[key] = value
            loaded += 1
    return loaded


def set_env_value(path: Path, key: str, value: str) -> None:
    """Записать KEY=value: заменить существующую строку (в т.ч. пустую `KEY=`),
    иначе дописать в конец. Файл остаётся с правами 600."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    new_line = f"{key}={value}"
    for i, line in enumerate(lines):
        m = _LINE.match(line)
        if m and m.group(1) == key:
            lines[i] = new_line
            break
    else:
        lines.append(new_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
