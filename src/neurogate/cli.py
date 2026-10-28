"""Команды для учеников: `neurogate setup` (ключи), `neurogate keys` (проверка),
`neurogate connect <tool>` (подключить Claude Code / Cursor / Cline / OpenCode).

Без аргументов `neurogate` по-прежнему запускает сервер — см. main.run().
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import stat
import subprocess
import sys
import webbrowser
from importlib import resources
from pathlib import Path

import httpx
import yaml

from neurogate.envfile import default_env_path, read_env_file, set_env_value

_PRIORITY_TITLES = {
    1: "Начните с этих — быстро, без карты, хорошо пишут код",
    2: "Дополнительные — больше квоты и моделей",
    3: "С неудобствами — телефон РФ, верификация, ежедневный чек-ин",
}


def load_catalog() -> dict:
    text = resources.files("neurogate").joinpath("keys_catalog.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _services(catalog: dict, only: list[str] | None = None) -> list[dict]:
    services = sorted(catalog["services"], key=lambda s: s["priority"])
    if only:
        wanted = {o.lower() for o in only}
        services = [s for s in services if s["id"] in wanted or s["env"].lower() in wanted]
    return services


def check_key(service: dict, key: str) -> tuple[bool | None, str]:
    """True — ключ принят, False — отвергнут, None — проверить не удалось."""
    check = service.get("check") or {}
    prefix = check.get("prefix")
    if prefix and not key.startswith(prefix):
        return False, f"ключ должен начинаться с {prefix}"
    url = check.get("url")
    if not url or check.get("auth") == "none":
        return None, "автопроверки нет — ключ сохранён как есть"
    headers, params = {}, {}
    if check["auth"] == "bearer":
        headers["Authorization"] = f"Bearer {key}"
    elif check["auth"] == "query":
        params[check.get("param", "key")] = key
    try:
        r = httpx.get(url, headers=headers, params=params, timeout=15)
    except httpx.HTTPError as exc:
        return None, f"сервис не ответил ({type(exc).__name__})"
    if r.status_code in (400, 401, 403):
        return False, f"сервис отверг ключ (HTTP {r.status_code})"
    if 200 <= r.status_code < 300:
        return True, "ключ работает"
    return None, f"не удалось проверить (HTTP {r.status_code})"


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return "q"


def _ensure_env_file(path: Path) -> None:
    if path.exists():
        return
    example = Path(".env.example")
    path.write_text(example.read_text(encoding="utf-8") if example.exists() else "", encoding="utf-8")


def _print_service(s: dict, n: int, total: int) -> None:
    print(f"\n━━━ [{n}/{total}] {s['name']} ━━━")
    print(f"  Даёт:     {s['gives']}")
    print(f"  Лимиты:   {s['limits']}")
    print(f"  Нужно:    {s['needs']}")
    print(f"  Ключ тут: {s['key_url']}")
    for i, step in enumerate(s.get("steps", []), 1):
        print(f"    {i}. {step}")


def cmd_setup(args: argparse.Namespace) -> int:
    catalog = load_catalog()
    env_path = default_env_path()
    _ensure_env_file(env_path)
    current = read_env_file(env_path)
    services = _services(catalog, args.services)
    if not args.all and not args.services:
        services = [s for s in services if not current.get(s["env"])]
    if not services:
        print("Все ключи из каталога уже вписаны. Проверить их: neurogate keys")
        return 0

    print("Мастер ключей neurogate.")
    print("Для каждого сервиса откроется страница, где берут ключ. Вставьте ключ сюда —")
    print("его не будет видно на экране, он сохранится только в файле", env_path.resolve())
    print("Enter — открыть страницу, s — пропустить сервис, q — закончить.")

    saved = 0
    last_priority = None
    for n, s in enumerate(services, 1):
        if s["priority"] != last_priority:
            last_priority = s["priority"]
            print(f"\n=== {_PRIORITY_TITLES.get(last_priority, '')} ===")
        _print_service(s, n, len(services))
        answer = _ask("  [Enter / s / q] > ").lower()
        if answer == "q":
            break
        if answer == "s":
            continue
        if not args.no_browser:
            webbrowser.open(s["key_url"])
        while True:
            key = getpass.getpass("  Вставьте ключ и нажмите Enter (пусто — пропустить): ").strip()
            if not key:
                break
            ok, msg = check_key(s, key)
            mark = {True: "✓", False: "✗", None: "•"}[ok]
            print(f"  {mark} {msg}")
            if ok is False and _ask("  Ввести заново? [Y/n] > ").lower() != "n":
                continue
            if ok is False:
                break
            set_env_value(env_path, s["env"], key)
            for extra in s.get("extra_env", []):
                reader = getpass.getpass if extra.get("secret", True) else input
                value = reader(f"  {extra['prompt']}: ").strip()
                if value:
                    set_env_value(env_path, extra["env"], value)
            saved += 1
            print(f"  Сохранено: {s['env']}")
            break

    print(f"\nГотово, сохранено ключей: {saved}.")
    if saved and not restart_service():
        print("Перезапустите сервер (Ctrl+C и снова `neurogate`), чтобы ключи подхватились.")
    print("Проверить все ключи: neurogate keys")
    return 0


def restart_service() -> bool:
    """Перезапустить сервер, поставленный установщиком как служба. False — службы нет."""
    system = platform.system()
    if system == "Darwin":
        unit = Path.home() / "Library/LaunchAgents/dev.neurogate.plist"
        if not unit.exists():
            return False
        cmd = ["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/dev.neurogate"]
    elif system == "Linux":
        unit = Path.home() / ".config/systemd/user/neurogate.service"
        if not unit.exists():
            return False
        cmd = ["systemctl", "--user", "restart", "neurogate"]
    elif system == "Windows":
        if subprocess.run(["schtasks", "/Query", "/TN", "neurogate"],
                          capture_output=True, check=False).returncode != 0:
            return False
        subprocess.run(["schtasks", "/End", "/TN", "neurogate"], capture_output=True, check=False)
        # /End гасит cmd.exe, но python под `uv run` может остаться и держать порт.
        port = _gateway()[0].rsplit(":", 1)[1]
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             (f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue"
              " | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }")],
            capture_output=True,
            check=False,
        )
        cmd = ["schtasks", "/Run", "/TN", "neurogate"]
    else:
        return False
    if subprocess.run(cmd, capture_output=True, check=False).returncode != 0:
        return False
    print("Сервер перезапущен — новые ключи уже работают.")
    return True


def cmd_import(args: argparse.Namespace) -> int:
    from neurogate.keydrop import DropError, fetch

    try:
        values = fetch(args.code)
    except DropError as exc:
        print(f"✗ {exc}")
        return 1
    env_path = default_env_path()
    _ensure_env_file(env_path)
    for key, value in values.items():
        set_env_value(env_path, key, value)
    names = {s["env"]: s["name"] for s in load_catalog()["services"]}
    got = [names.get(k, k) for k in values if k in names]
    print(f"✓ Ключи из бота сохранены ({len(got)}): {', '.join(got)}")
    if not args.no_restart and not restart_service():
        print("Перезапустите сервер, чтобы ключи подхватились: neurogate restart")
    return 0


def cmd_bot(args: argparse.Namespace) -> int:
    from neurogate.keybot import run_bot

    return run_bot(args.rest)


def cmd_restart(args: argparse.Namespace) -> int:
    if restart_service():
        return 0
    print("Служба neurogate не найдена. Запустите сервер вручную: neurogate serve")
    return 1


def catalog_markdown(catalog: dict) -> str:
    """Таблица сервисов для docs/students.md — генерится из каталога, руками не править."""
    out = []
    last_priority = None
    for s in _services(catalog):
        if s["priority"] != last_priority:
            last_priority = s["priority"]
            out += ["", f"### {_PRIORITY_TITLES.get(last_priority, '')}", "",
                    "| Сервис | Что даёт | Лимиты | Что нужно | Где взять ключ |",
                    "|---|---|---|---|---|"]
        out.append(f"| **{s['name']}** | {s['gives']} | {s['limits']} | {s['needs']} "
                   f"| [{s['env']}]({s['key_url']}) |")
    out += ["", "**Без ключа работают:** " + ", ".join(catalog.get("keyless", [])) + "."]
    return "\n".join(out).strip() + "\n"


def cmd_keys(args: argparse.Namespace) -> int:
    catalog = load_catalog()
    if args.markdown:
        print(catalog_markdown(catalog), end="")
        return 0
    current = read_env_file(default_env_path())
    have = 0
    last_priority = None
    for s in _services(catalog):
        if s["priority"] != last_priority:
            last_priority = s["priority"]
            print(f"\n{_PRIORITY_TITLES.get(last_priority, '')}:")
        key = current.get(s["env"]) or os.getenv(s["env"], "")
        if not key:
            print(f"  ·  {s['name']:<30} нет ключа → {s['key_url']}")
            continue
        have += 1
        if args.offline:
            print(f"  ✓  {s['name']:<30} вписан")
            continue
        ok, msg = check_key(s, key)
        mark = {True: "✓", False: "✗", None: "•"}[ok]
        print(f"  {mark}  {s['name']:<30} {msg}")
    print(f"\nБез ключа работают: {', '.join(catalog.get('keyless', []))}.")
    print(f"Ключей вписано: {have} из {len(catalog['services'])}. Добавить: neurogate setup")
    return 0


# ---------------------------------------------------------------- connect

def _gateway() -> tuple[str, str]:
    env = read_env_file(default_env_path())
    host = os.getenv("NEUROGATE_HOST") or env.get("NEUROGATE_HOST") or "127.0.0.1"
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    port = os.getenv("NEUROGATE_PORT") or env.get("NEUROGATE_PORT") or "8765"
    token = os.getenv("NEUROGATE_API_TOKEN") or env.get("NEUROGATE_API_TOKEN") or "neurogate-local"
    return f"http://{host}:{port}", token


def _bin_dir() -> Path:
    d = Path.home() / ".local" / "bin"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _connect_claude_code(base: str, token: str) -> None:
    env = {
        "ANTHROPIC_BASE_URL": base,
        "ANTHROPIC_AUTH_TOKEN": token,
        "ANTHROPIC_MODEL": "code",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "code",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "code",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "code_fast",
        "CLAUDE_CODE_SUBAGENT_MODEL": "code",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    }
    if platform.system() == "Windows":
        path = _bin_dir() / "claude-free.cmd"
        lines = ["@echo off"] + [f"set {k}={v}" for k, v in env.items()] + ["claude %*"]
        path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    else:
        path = _bin_dir() / "claude-free"
        lines = ["#!/bin/sh"] + [f"export {k}='{v}'" for k, v in env.items()] + ['exec claude "$@"']
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Создана команда: {path}")
    print("Запуск Claude Code на бесплатных моделях:  claude-free")
    print("Обычный `claude` остаётся как был (с вашей подпиской, если она есть).")
    print("Модель внутри — цепочка `code` neurogate (Qwen3-Coder, Gemini, DeepSeek и др.),")
    print("а не сам Claude: Claude Code здесь — только оболочка с инструментами.")
    if str(_bin_dir()) not in os.environ.get("PATH", ""):
        print(f"\n⚠ Папки {_bin_dir()} нет в PATH. Добавьте её или запускайте полным путём.")


_OPENCODE_MODELS = {
    "code": "Код — бесплатные модели (neurogate)",
    "code_fast": "Код быстро — бесплатные модели (neurogate)",
    "auto": "Авто — neurogate сам выберет",
    "chat": "Чат и тексты — бесплатные модели (neurogate)",
}


def _connect_opencode(base: str, token: str) -> None:
    """Прописать neurogate провайдером в глобальный конфиг OpenCode (приложение и CLI)
    и сделать бесплатную модель моделью по умолчанию. Остальной конфиг не трогаем."""
    path = Path.home() / ".config" / "opencode" / "opencode.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg: dict = {"$schema": "https://opencode.ai/config.json"}
    if path.exists():
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            print(f"✗ {path} — не чистый JSON (комментарии?). Добавьте провайдер вручную:")
            _print_openai_settings("OpenCode", base, token, "provider «neurogate», npm @ai-sdk/openai-compatible")
            return
        backup = path.with_suffix(".json.bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    cfg.setdefault("provider", {})["neurogate"] = {
        "npm": "@ai-sdk/openai-compatible",
        "name": "neurogate (бесплатно)",
        "options": {"baseURL": f"{base}/v1", "apiKey": token},
        "models": {
            mid: {"name": title, "tool_call": True,
                  "limit": {"context": 128000, "output": 16384}}
            for mid, title in _OPENCODE_MODELS.items()
        },
    }
    cfg["model"] = "neurogate/code"
    cfg["small_model"] = "neurogate/code_fast"
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenCode настроен: {path}")
    print("Модель по умолчанию — «neurogate/code» (бесплатно). Откройте приложение OpenCode,")
    print("выберите папку проекта и пишите задачу в чат. Сменить модель — список моделей внизу окна.")


def _print_openai_settings(tool: str, base: str, token: str, where: str) -> None:
    print(f"{tool}: {where}")
    print(f"  Base URL / API Base:  {base}/v1")
    print(f"  API Key:              {token}")
    print("  Model:                code   (или code_fast — быстрее, auto — сам выберет)")


def cmd_connect(args: argparse.Namespace) -> int:
    base, token = _gateway()
    tool = args.tool
    if tool == "claude-code":
        _connect_claude_code(base, token)
    elif tool == "cursor":
        _print_openai_settings(
            "Cursor", base, token,
            "Settings → Models → OpenAI API Key + «Override OpenAI Base URL», добавьте модель `code`.\n"
            "  ⚠ Cursor ходит к моделям со своих серверов, поэтому localhost ему недоступен —\n"
            "  нужен neurogate на VPS или туннель (например, `cloudflared tunnel --url " + base + "`).",
        )
    elif tool == "cline":
        _print_openai_settings(
            "Cline / Roo Code / Kilo Code (VS Code)", base, token,
            "API Provider → «OpenAI Compatible»",
        )
    elif tool == "continue":
        _print_openai_settings(
            "Continue (VS Code / JetBrains)", base, token,
            "config.yaml → models: provider: openai, apiBase, apiKey, model",
        )
    elif tool == "opencode":
        _connect_opencode(base, token)
    elif tool == "codex":
        print("Codex CLI пока не поддерживается: он работает только по протоколу Responses API")
        print("(/v1/responses), а neurogate отдаёт /v1/chat/completions и /v1/messages.")
        print("Используйте claude-free (Claude Code) или Cline / OpenCode / Continue.")
        return 1
    else:  # pragma: no cover — argparse ограничивает choices
        return 2
    return 0


CONNECT_TOOLS = ["claude-code", "cursor", "cline", "continue", "opencode", "codex"]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="neurogate", description="Бесплатный шлюз к нейросетям")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("setup", help="мастер ключей: ссылки, инструкции, сохранение в .env")
    p.add_argument("services", nargs="*", help="id сервисов (groq gemini …); пусто — все без ключа")
    p.add_argument("--all", action="store_true", help="пройти и по уже вписанным")
    p.add_argument("--no-browser", action="store_true", help="не открывать страницы в браузере")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("keys", help="какие ключи вписаны и работают ли они")
    p.add_argument("--offline", action="store_true", help="не обращаться к сервисам")
    p.add_argument("--markdown", action="store_true", help="таблица сервисов для документации")
    p.set_defaults(func=cmd_keys)

    p = sub.add_parser("import", help="забрать ключи из Telegram-бота по коду NG-…")
    p.add_argument("code")
    p.add_argument("--no-restart", action="store_true", help="не перезапускать сервер (для установщика)")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("bot", help="запустить Telegram-бот выдачи ключей (для преподавателя)")
    p.add_argument("rest", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_bot)

    p = sub.add_parser("restart", help="перезапустить сервер (после новых ключей)")
    p.set_defaults(func=cmd_restart)

    sub.add_parser("serve", help="запустить сервер (то же, что `neurogate` без аргументов)")

    p = sub.add_parser("connect", help="подключить инструмент к neurogate")
    p.add_argument("tool", choices=CONNECT_TOOLS)
    p.set_defaults(func=cmd_connect)

    if argv[:1] == ["bot"]:  # флаги бота (--gen-key) argparse.REMAINDER не пропускает
        from neurogate.keybot import run_bot

        return run_bot(argv[1:])
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
