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
import re
import shutil
import stat
import subprocess
import time
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


def ordered_services(catalog: dict) -> list[dict]:
    """Сначала быстрый старт (catalog.quick, в его порядке), дальше остальные по priority."""
    quick = catalog.get("quick", [])
    by_id = {s["id"]: s for s in catalog["services"]}
    head = [by_id[i] for i in quick if i in by_id]
    rest = sorted((s for s in catalog["services"] if s["id"] not in quick),
                  key=lambda s: s["priority"])
    return head + rest


def _services(catalog: dict, only: list[str] | None = None) -> list[dict]:
    services = ordered_services(catalog)
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
    quick_ids = set(catalog.get("quick", []))
    if not args.all and not args.services:
        services = [s for s in services if not current.get(s["env"])]
        if not args.more:
            # Быстрый старт: сначала только три главных ключа; остальные — по желанию
            first = [s for s in services if s["id"] in quick_ids]
            services = first or services
    if not services:
        print("Все ключи из каталога уже вписаны. Проверить их: neurogate keys")
        return 0

    print("Мастер ключей neurogate.")
    print("Для каждого сервиса откроется страница, где берут ключ. Вставьте ключ сюда —")
    print("его не будет видно на экране, он сохранится только в файле", env_path.resolve())
    print("Enter — открыть страницу, s — пропустить сервис, q — закончить.")

    saved = 0
    quit_early = False
    last_priority = None
    for n, s in enumerate(services, 1):
        if s["priority"] != last_priority:
            last_priority = s["priority"]
            print(f"\n=== {_PRIORITY_TITLES.get(last_priority, '')} ===")
        _print_service(s, n, len(services))
        answer = _ask("  [Enter / s / q] > ").lower()
        if answer == "q":
            quit_early = True
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

    rest = [s for s in _services(catalog) if not read_env_file(env_path).get(s["env"])
            and s["id"] not in quick_ids]
    if not quit_early and not args.all and not args.services and not args.more and rest and \
            all(s["id"] in quick_ids for s in services):
        print(f"\n⚡ Быстрый старт пройден. Ещё {len(rest)} сервисов — больше лимитов и моделей.")
        if _ask("  Добавить ещё ключи? [y/N] > ").lower() in ("y", "д", "да", "yes"):
            args.more = True
            return cmd_setup(args)

    print(f"\nГотово, сохранено ключей: {saved}.")
    if saved and not restart_service():
        print("Перезапустите сервер (Ctrl+C и снова `neurogate serve`), чтобы ключи подхватились.")
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
        has_task = subprocess.run(["schtasks", "/Query", "/TN", "neurogate"],
                                  capture_output=True, check=False).returncode == 0
        # Планировщик закрыт политикой — установщик ставит ярлык в «Автозагрузку».
        shortcut = Path(os.getenv("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup/neurogate.lnk"
        pythonw = Path.cwd() / ".venv" / "Scripts" / "pythonw.exe"
        if not has_task and not (shortcut.exists() and pythonw.exists()):
            return False
        if has_task:
            subprocess.run(["schtasks", "/End", "/TN", "neurogate"], capture_output=True, check=False)
        # /End может не дотянуться до python (старые установки шли через cmd + uv run) —
        # добиваем того, кто держит порт.
        port = _gateway()[0].rsplit(":", 1)[1]
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             (f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue"
              " | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }")],
            capture_output=True,
            check=False,
        )
        if not has_task:
            base = _gateway()[0]
            for _ in range(20):  # старый процесс отпускает порт не мгновенно
                if not _gateway_alive(base):
                    break
                time.sleep(0.25)
            # Как ярлык автозагрузки: pythonw без окна, вывод — в neurogate.log
            subprocess.Popen([str(pythonw), "-X", "utf8", "-m", "neurogate.background"], cwd=Path.cwd(),
                             creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                             | getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)
            for _ in range(30):
                if _gateway_alive(base):
                    print("Сервер перезапущен — новые ключи уже работают.")
                    return True
                time.sleep(1)
            print(f"⚠ Сервер не поднялся за 30 секунд — смотрите {Path.cwd() / 'neurogate.log'}")
            return True
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


def cmd_doctor(args: argparse.Namespace) -> int:
    """Проверка всей связки простым языком: что работает, что нет, какой командой чинить."""
    base, token = _gateway()
    problems = 0

    def line(ok: bool | None, text: str, fix: str = "") -> None:
        nonlocal problems
        tag = {True: "[  OK  ]", False: "[ FAIL ]", None: "[ WARN ]"}[ok]
        print(f"{tag} {text}")
        if fix:
            print(f"         → {fix}")
        if ok is False:
            problems += 1

    print("neurogate doctor — сканирую систему…\n")
    env = read_env_file(default_env_path())
    services = load_catalog()["services"]
    got = [s["name"] for s in services if env.get(s["env"]) or os.getenv(s["env"])]
    if not got:
        line(False, "Ключей нет — бесплатные модели neurogate не работают",
             "neurogate setup  (или собери ключи в боте @nurtechneurogatebot)")
    elif len(got) < 3:
        line(None, f"Ключей: {len(got)} — мало, лимиты будут кончаться быстро",
             "neurogate setup — добавь ещё 2–3 (Gemini, OpenRouter, Groq)")
    else:
        line(True, f"Ключей: {len(got)} ({', '.join(got[:5])}{'…' if len(got) > 5 else ''})")

    alive = _gateway_alive(base)
    line(alive, f"Шлюз отвечает на {base}" if alive else f"Шлюз не отвечает на {base}",
         "" if alive else "neurogate restart  (или neurogate serve в отдельном окне)")

    if alive and got:
        try:
            r = httpx.post(f"{base}/v1/chat/completions", timeout=120,
                           headers={"Authorization": f"Bearer {token}"},
                           json={"model": "code_fast", "max_tokens": 20,
                                 "messages": [{"role": "user", "content": "Ответь одним словом: ок"}]})
            data = r.json()
            if r.status_code == 200:
                line(True, f"Модель ответила: {data.get('model')}")
            else:
                line(False, "Модели не ответили: " + str(data.get("detail") or data.get("error"))[:160],
                     "neurogate keys — проверь ключи; neurogate setup — добавь новые")
        except (httpx.HTTPError, ValueError) as exc:
            line(False, f"Запрос к модели упал ({type(exc).__name__})", "neurogate restart")

    oc = Path.home() / ".config" / "opencode" / "opencode.json"
    try:
        cfg = json.loads(oc.read_text(encoding="utf-8")) if oc.exists() else {}
    except ValueError:
        cfg = None
    if cfg is None:
        line(None, f"Настройки OpenCode не читаются ({oc})", "neurogate connect opencode")
    else:
        url = ((cfg.get("providers") or {}).get("neurogate") or {}).get("settings", {}).get("baseURL")
        if not url:
            line(None, "OpenCode не подключён к neurogate (встроенные бесплатные модели OpenCode работают и так)",
                 "neurogate connect opencode, затем перезапусти OpenCode")
        elif url != f"{base}/v1":
            line(False, f"OpenCode смотрит на {url}, а шлюз на {base}",
                 "neurogate connect opencode, затем перезапусти OpenCode")
        else:
            line(True, "OpenCode подключён к neurogate")
            # Окно OpenCode прячет модели старше ~182 дней — предупреждаем заранее
            rel = (((cfg.get("providers") or {}).get("neurogate") or {}).get("models") or {}) \
                .get("code", {}).get("releaseDate")
            try:
                age = (time.time() - time.mktime(time.strptime(rel, "%Y-%m-%d"))) / 86400 if rel else None
            except ValueError:
                age = None
            if age is not None and age > 150:
                line(None, f"Модель neurogate в OpenCode «выпущена» {int(age)} дн. назад — после 182 OpenCode "
                     "её спрячет", "neurogate connect opencode (обновит дату)")

    free = _bin_dir() / ("claude-free.cmd" if platform.system() == "Windows" else "claude-free")
    if free.exists():
        ok = base in free.read_text(encoding="utf-8")
        line(ok, "claude-free настроен" if ok else "claude-free смотрит на старый адрес шлюза",
             "" if ok else "neurogate connect claude-code")
    if str(_bin_dir()) not in os.environ.get("PATH", ""):
        line(None, f"{_bin_dir()} нет в PATH текущего окна", "открой новое окно терминала")

    print()
    if problems:
        print(f"Найдено проблем: {problems}. Выполни команды после «→» и запусти neurogate doctor снова.")
    else:
        print("ACCESS GRANTED. Всё работает — можно кодить.")
    return 1 if problems else 0


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


def _unreachable_hint(base: str) -> str:
    """Почему шлюз не отвечает и что делать. В песочнице Codex сеть закрыта, хотя шлюз жив."""
    if os.getenv("CODEX_SANDBOX_NETWORK_DISABLED"):
        return (f"✗ Песочница Codex не пускает команду в сеть, поэтому {base} недоступен.\n"
                "  Разрешите этой команде выход в сеть, когда Codex спросит, или навсегда:\n"
                "  neurogate connect orchestrator  (включит network_access в ~/.codex/config.toml)\n"
                "  и перезапустите Codex.")
    return f"✗ neurogate не отвечает на {base}. Запустите: neurogate restart (или neurogate doctor)"


def _codex_sandbox_settings() -> dict[str, str]:
    """Что нужно песочнице Codex, чтобы `neurogate delegate` из неё работал: сеть до шлюза
    на 127.0.0.1 и запись в служебные папки OpenCode (лог, база сессий, кэш)."""
    home = Path.home()
    roots = [home / ".local/share/opencode", home / ".local/state/opencode", home / ".cache/opencode"]
    for r in roots:  # песочница не даст их создать: разрешение есть только на сами папки
        r.mkdir(parents=True, exist_ok=True)
    return {"network_access": "true",
            "writable_roots": "[" + ", ".join(json.dumps(str(r)) for r in roots) + "]"}


def _codex_allow_network() -> str | None:
    """Прописать _codex_sandbox_settings в [sandbox_workspace_write] ~/.codex/config.toml.
    Свои значения человека не переписываем. None — Codex не стоит, трогать нечего."""
    home = Path(os.getenv("CODEX_HOME") or Path.home() / ".codex")
    if not home.exists() and not shutil.which("codex"):
        return None
    path = home / "config.toml"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    want = _codex_sandbox_settings()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == "[sandbox_workspace_write]")
    except StopIteration:
        lines += ([""] if lines and lines[-1].strip() else []) + ["[sandbox_workspace_write]"]
        start = len(lines) - 1
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("[")
                and not lines[i].lstrip().startswith(("[\"", "['"))), len(lines))
    have = {m.group(1): i for i in range(start + 1, end)
            if (m := re.match(r"\s*(\w+)\s*=", lines[i]))}
    changed = False
    if "network_access" in have and not re.search(r"=\s*true\b", lines[have["network_access"]]):
        lines[have["network_access"]] = "network_access = true"
        changed = True
    for key, value in want.items():
        if key not in have:
            lines.insert(start + 1, f"{key} = {value}")
            changed = True
    if not changed:
        return "уже разрешена"
    home.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "разрешена"


def _write_sh(path: Path, text: str) -> None:
    """sh-обёртка: на macOS/Linux — основная команда, на Windows — для Git Bash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))  # \n без \r\n: Git Bash спотыкается о CR
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _gateway_alive(base: str) -> bool:
    try:
        return httpx.get(f"{base}/health", timeout=5).status_code == 200
    except httpx.HTTPError:
        return False


def _bin_dir() -> Path:
    d = Path.home() / ".local" / "bin"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _free_claude_env(base: str, token: str, model: str = "code") -> dict[str, str]:
    """Переменные, с которыми Claude Code ходит в neurogate вместо Anthropic."""
    return {
        "ANTHROPIC_BASE_URL": base,
        "ANTHROPIC_AUTH_TOKEN": token,
        "ANTHROPIC_MODEL": model,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": model,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": model,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "code_fast",
        "CLAUDE_CODE_SUBAGENT_MODEL": model,
        # окно контекста цепочки — иначе Claude Code ругается на незнакомую модель
        "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "128000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    }


def _connect_claude_code(base: str, token: str) -> None:
    env = _free_claude_env(base, token)
    sh = _bin_dir() / "claude-free"
    lines = ["#!/bin/sh"] + [f"export {k}='{v}'" for k, v in env.items()] + ['exec claude "$@"']
    # На Windows sh-версия — для Git Bash (в нём работает Claude Code): .cmd оттуда не находится
    _write_sh(sh, "\n".join(lines) + "\n")
    path = sh
    if platform.system() == "Windows":
        path = _bin_dir() / "claude-free.cmd"
        # setlocal — переменные не остаются в окне cmd, и обычный `claude` потом не уходит в neurogate
        lines = ["@echo off", "setlocal"] + [f"set {k}={v}" for k, v in env.items()] + ["claude %*"]
        path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(f"Создана команда: {path}")
    print("Запуск Claude Code на бесплатных моделях:  claude-free")
    print("Обычный `claude` остаётся как был (с вашей подпиской, если она есть).")
    print("Модель внутри — цепочка `code` neurogate (Qwen3-Coder, Gemini, DeepSeek и др.),")
    print("а не сам Claude: Claude Code здесь — только оболочка с инструментами.")
    if str(_bin_dir()) not in os.environ.get("PATH", ""):
        print(f"\n⚠ Папки {_bin_dir()} нет в PATH. Добавьте её или запускайте полным путём.")


# Одна модель: выбирать внутри neurogate ученику незачем — шлюз сам берёт свободную модель
# и переключается при лимитах. Цепочка `code` — лучшие бесплатные модели для кода.
_OPENCODE_MODELS = {
    "code": "50 бесплатных моделей · сам переключается",
}


def _opencode_auth(token: str) -> bool | None:
    """OpenCode 2.x показывает в окне только «подключённых» провайдеров (`auth login`).
    Команде нужен интерактивный терминал — даём ей псевдотерминал и вводим токен.
    None — не к чему подключать (нет CLI 2.x или нет pty, как на Windows)."""
    cli = _opencode_cli(prefer_app=True)
    if not cli:
        return None
    try:
        import pty  # noqa: F401 — только POSIX
    except ImportError:
        return None
    ver = subprocess.run([cli, "--version"], capture_output=True, text=True, timeout=60, check=False)
    if "v1." in ver.stdout or not ver.stdout.strip():
        return None  # 1.x берёт ключ из options.apiKey, вход не нужен
    before = subprocess.run([cli, "auth", "list"], capture_output=True, text=True, timeout=60, check=False)
    if "neurogate" in before.stdout:  # уже подключён — повторный вход ждал бы минуту впустую
        subprocess.run([cli, "reload"], capture_output=True, timeout=60, check=False)
        return True
    master, slave = os.openpty()
    try:
        proc = subprocess.Popen([cli, "auth", "login", "neurogate", "--method", "key"],
                                stdin=slave, stdout=slave, stderr=slave, cwd=Path.home())
        time.sleep(5)
        os.write(master, f"{token}\r".encode())
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
    finally:
        os.close(slave)
        os.close(master)
    listed = subprocess.run([cli, "auth", "list"], capture_output=True, text=True, timeout=60, check=False)
    # Фоновый сервис OpenCode переживает перезапуск окна и держит старый конфиг — перечитываем
    subprocess.run([cli, "reload"], capture_output=True, timeout=60, check=False)
    return "neurogate" in listed.stdout


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
        if not backup.exists():  # храним исходник до первого подключения, не затираем
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    cfg.setdefault("provider", {})["neurogate"] = {
        "npm": "@ai-sdk/openai-compatible",
        "name": "neurogate",
        "options": {"baseURL": f"{base}/v1", "apiKey": token},
        "models": {
            mid: {"name": title, "tool_call": True, "release_date": time.strftime("%Y-%m-%d"),
                  "limit": {"context": 128000, "output": 16384}}
            for mid, title in _OPENCODE_MODELS.items()
        },
    }
    # OpenCode 2.x (приложение) читает провайдеров в новом формате `providers` и в
    # нём приоритетнее; 1.x (CLI) понимает только `provider`. Пишем оба — так велит
    # migrate-v1: форматы могут сосуществовать.
    released = time.strftime("%Y-%m-%d")
    cfg.setdefault("providers", {})["neurogate"] = {
        "name": "neurogate",
        "package": "aisdk:@ai-sdk/openai-compatible",
        "settings": {"baseURL": f"{base}/v1", "apiKey": token},
        "models": {
            # type=chat: окно OpenCode 2.x показывает только такие; cost=0 → пометка «Бесплатно»
            # Окно показывает только модели с датой выпуска не старше ~полугода (каждая
            # — «новейшая» в своём family) — ставим дату подключения; connect её обновляет.
            mid: {"name": title, "type": "chat", "family": f"neurogate-{mid}",
                  # reasoning.supported=false — без кнопок Low/Medium/High: выбор модели и её
                  # «силы мысли» делает сам neurogate
                  "releaseDate": released,
                  "capabilities": {"tools": True, "input": ["text"], "output": ["text"],
                                   "reasoning": {"supported": False}},
                  "cost": {"input": 0, "output": 0},
                  "limit": {"context": 128000, "output": 16384}}
            for mid, title in _OPENCODE_MODELS.items()
        },
    }
    cfg["model"] = "neurogate/code"
    cfg["small_model"] = "neurogate/code_fast"
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenCode настроен: {path}")
    try:
        authed = _opencode_auth(token)
    except (OSError, subprocess.TimeoutExpired):  # зависший или сломанный CLI OpenCode не валит установку
        authed = False
    if authed is False or (authed is None and platform.system() == "Windows"):
        # На Windows нет pty для `opencode auth login` — подключение в окне OpenCode руками
        print("⚠ Подключите neurogate внутри OpenCode (один раз). В OpenCode: список")
        print(f"  моделей → «+» → «neurogate (бесплатно)» → вставьте ключ {token}")
    elif authed:
        print("Провайдер «neurogate (бесплатно)» подключён в OpenCode.")
    print("Модель по умолчанию — «neurogate/code» (бесплатно). В OpenCode откройте список моделей —")
    print("там группа «neurogate (бесплатно)». Не видно — закройте OpenCode (⌘Q / Alt+F4) и откройте.")


CODEX_MARK = "# neurogate: бесплатный профиль"


def _connect_codex(base: str, token: str) -> None:
    """Профиль `free` для Codex: отдельный файл ~/.codex/free.config.toml (profile v2 —
    накладывается поверх config.toml). Основной конфиг и модель Codex не трогаем."""
    home = Path(os.getenv("CODEX_HOME") or Path.home() / ".codex")
    home.mkdir(parents=True, exist_ok=True)
    base_cfg = home / "config.toml"
    if base_cfg.exists() and CODEX_MARK in base_cfg.read_text(encoding="utf-8"):
        # ранняя версия писала legacy [profiles.free] в config.toml — Codex с ним падает
        text = base_cfg.read_text(encoding="utf-8")
        text = re.sub(r"\n?" + re.escape(CODEX_MARK) + r"\n.*?model_context_window = \d+\n", "\n",
                      text, flags=re.S)
        base_cfg.write_text(text.rstrip("\n") + "\n", encoding="utf-8")
    path = home / "free.config.toml"
    path.write_text(
        f"{CODEX_MARK} — создан `neurogate connect codex`, запуск: codex-free\n"
        'model_provider = "neurogate"\n'
        'model = "code"\n'
        "model_context_window = 128000\n"
        "\n[model_providers.neurogate]\n"
        'name = "neurogate (бесплатно)"\n'
        f'base_url = "{base}/v1"\n'
        'wire_api = "responses"\n'
        f'experimental_bearer_token = "{token}"\n',
        encoding="utf-8",
    )
    _write_sh(_bin_dir() / "codex-free", '#!/bin/sh\nexec codex --profile free "$@"\n')
    if platform.system() == "Windows":
        (_bin_dir() / "codex-free.cmd").write_text("@echo off\r\ncodex --profile free %*\r\n", encoding="utf-8")
    print(f"Codex настроен: профиль «free» в {path}")
    print("Запуск Codex на бесплатных моделях:  codex-free   (или codex --profile free)")
    print("Обычный `codex` остаётся как был.")


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
    elif tool == "orchestrator":
        targets = ([Path.home() / ".codex" / "AGENTS.md", Path.home() / ".claude" / "CLAUDE.md"]
                   if args.global_ else [_caller_dir() / "AGENTS.md", _caller_dir() / "CLAUDE.md"])
        for t in targets:
            print(f"{t}: {_write_orchestrator(t)}")
        where = "во всех проектах" if args.global_ else "в этой папке"
        print(f"Готово: Codex и Claude Code {where} будут поручать работу бесплатным моделям")
        print("через `neurogate delegate` / `neurogate ask`, а подписку тратить на план и проверку.")
        net = _codex_allow_network()
        if net:
            print(f"Codex: сеть и папки OpenCode для команд в песочнице — {net} (~/.codex/config.toml,")
            print("[sandbox_workspace_write]) — иначе delegate не достучится до шлюза на 127.0.0.1.")
            print("Перезапустите Codex, чтобы он это подхватил.")
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
        _connect_codex(base, token)
    else:  # pragma: no cover — argparse ограничивает choices
        return 2
    return 0


# ---------------------------------------------------------------- orchestrator

ORCHESTRATOR_MARK = "<!-- neurogate:orchestrator -->"
ORCHESTRATOR_BLOCK = f"""{ORCHESTRATOR_MARK}
## Бесплатные исполнители (neurogate)

Ты — оркестратор: понимаешь задачу, дробишь её на шаги и проверяешь результат. Объёмную
работу — написание и правку кода, тесты, рефакторинг, документацию — поручай бесплатным
моделям через neurogate, чтобы не тратить лимит подписки:

- `neurogate delegate "<задача>"` — бесплатный агент сам правит файлы в текущей папке и
  возвращает короткий отчёт и список изменённых файлов. Он НЕ видит этот разговор: пиши
  задачу полностью — какие файлы, что сделать, как проверить, что считается готовым.
- `neurogate ask "<вопрос>"` — быстрый ответ бесплатной модели без правки файлов
  (объяснить код, предложить варианты, написать текст).
- Многострочную задачу запиши в файл и передай `neurogate delegate --file <файл>`
  (так же `ask --file`). На Windows — всегда так: перенос строки обрезает аргумент.

Порядок: большие задачи дроби на шаги по 1–3 файла → `delegate` → посмотри `git diff` и
запусти тесты → если плохо, поручи исправление с конкретикой (что сломано, где, как надо).
Сам пиши код, только если объяснить дольше, чем сделать. Команды идут 1–10 минут — ставь
большой таймаут. Команде нужен доступ к локальной сети (127.0.0.1) — в песочнице разреши
её запуск. Не отвечает neurogate — `neurogate doctor`.
"""


def _caller_dir() -> Path:
    """Папка, из которой человек вызвал `neurogate`: обёртка в ~/.local/bin переходит в
    ~/neurogate (там .env и config.yaml) и передаёт исходную папку в NEUROGATE_CALLER_DIR."""
    return Path(os.getenv("NEUROGATE_CALLER_DIR") or os.getcwd())


def _write_orchestrator(path: Path) -> str:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if ORCHESTRATOR_MARK in text:
        return "уже есть"
    sep = "\n\n" if text and not text.endswith("\n\n") else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + sep + ORCHESTRATOR_BLOCK, encoding="utf-8")
    return "дописано" if text else "создан"


WORKER_PROMPT = (
    "Ты исполнитель, задачу поручил другой агент; он не видит твою работу, только отчёт. "
    "Сделай задачу целиком, правя файлы в текущей папке, и проверь результат (запусти тесты "
    "или код, если можно). В конце — короткий отчёт до 15 строк: что изменил (файлы), как "
    "проверил, что не получилось или требует решения."
)


def _opencode_cli(prefer_app: bool = False) -> str | None:
    """CLI OpenCode: из PATH или встроенная в приложение. prefer_app — сначала встроенная
    (её фоновый сервис и показывает модели в окне приложения)."""
    found = shutil.which("opencode")
    if found and not prefer_app:
        return found
    for cand in ("/Applications/OpenCode.app/Contents/Resources/opencode-cli",
                 str(Path.home() / "Applications/OpenCode.app/Contents/Resources/opencode-cli"),
                 str(Path(os.getenv("LOCALAPPDATA", "")) / "Programs/OpenCode/resources/opencode-cli.exe")):
        if cand and Path(cand).exists():
            return cand
    return found


def _arg_text(parts: list[str], file: str | None) -> str:
    """Текст задачи: из аргументов или из файла (--file, путь от папки вызова)."""
    if file:
        path = _caller_dir() / file
        if not path.is_file():
            raise SystemExit(f"✗ Нет файла {path}")
        return path.read_text(encoding="utf-8-sig").strip()
    return " ".join(parts).strip()


def _batch_safe(exe: str, prompt: str, task_file: Path) -> str:
    """На Windows .cmd/.bat-шим (npm) запускается через cmd.exe: аргумент обрезается на первом
    переносе строки, а & | > в тексте становятся командами. Тогда кладём задачу в файл и
    передаём однострочную ссылку на него."""
    if os.name != "nt" or not exe.lower().endswith((".cmd", ".bat")):
        return prompt
    task_file.write_text(prompt, encoding="utf-8")
    return (f"Прочитай файл {task_file.name} в текущей папке — там вся задача и правила, — и выполни её. "
            "Сам этот файл не меняй.")


def cmd_delegate(args: argparse.Namespace) -> int:
    base, token = _gateway()
    if not _gateway_alive(base):
        print(_unreachable_hint(base))
        return 2
    task = _arg_text(args.task, args.file)
    if not task:
        print("✗ Нет задачи: neurogate delegate \"<задача>\" или --file <файл>")
        return 2
    workdir = (_caller_dir() / args.dir).resolve()
    # Окружение оркестратора (Claude Code, Codex) не должно утечь исполнителю
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("ANTHROPIC_", "CLAUDECODE", "CLAUDE_CODE_", "CODEX_"))}
    env["PWD"] = str(workdir)  # OpenCode берёт проект из PWD, а не из cwd процесса
    # Windows: встроенный opencode-cli.exe, а не npm-шим opencode.cmd (см. _batch_safe)
    opencode = None if args.worker == "claude" else _opencode_cli(prefer_app=os.name == "nt")
    claude = shutil.which("claude") or str(Path.home() / ".local/bin/claude")
    task_file = workdir / f".neurogate-task-{os.getpid()}.md"  # свой на каждый запуск
    if opencode:
        prompt = _batch_safe(opencode, f"{WORKER_PROMPT}\n\nЗадача:\n{task}", task_file)
        cmd = [opencode, "run", "-m", f"neurogate/{args.model}", prompt]
        who = "OpenCode"
    elif Path(claude).exists():
        env.update(_free_claude_env(base, token, args.model))
        cmd = [claude, "-p", _batch_safe(claude, task, task_file), "--permission-mode", "acceptEdits",
               "--allowedTools", "Read", "Edit", "Write", "Glob", "Grep", "Bash",
               "--append-system-prompt", WORKER_PROMPT, "--output-format", "text"]
        who = "Claude Code"
    else:
        print("✗ Нет исполнителя: поставьте OpenCode (https://opencode.ai/download) "
              "или Claude Code (curl -fsSL https://claude.ai/install.sh | bash)")
        return 2
    print(f"▶ Исполнитель: {who} на бесплатных моделях (neurogate/{args.model}), папка {workdir}",
          flush=True)
    try:
        r = subprocess.run(cmd, cwd=workdir, env=env, check=False)
    finally:
        if os.name == "nt":  # файл пишет только _batch_safe и только на Windows
            task_file.unlink(missing_ok=True)
    if r.returncode and os.getenv("CODEX_SANDBOX"):
        print("\n⚠ Песочница Codex могла не пустить исполнителя. Выполните `neurogate connect "
              "orchestrator`, откройте приложение OpenCode (нужен его фоновый сервис) и "
              "перезапустите Codex — или разрешите этой команде запуск без песочницы.")
    in_git = subprocess.run(["git", "-C", str(workdir), "rev-parse"],
                            capture_output=True, check=False).returncode == 0
    if in_git:
        st = subprocess.run(["git", "-C", str(workdir), "status", "--short"],
                            capture_output=True, text=True, check=False).stdout.strip()
        print("\n── изменённые файлы (git status) ──\n" + (st or "нет изменений"))
    return r.returncode


def cmd_ask(args: argparse.Namespace) -> int:
    base, token = _gateway()
    question = _arg_text(args.question, args.file)
    if not question:
        print("✗ Нет вопроса: neurogate ask \"<вопрос>\" или --file <файл>")
        return 2
    try:
        r = httpx.post(f"{base}/v1/chat/completions", timeout=300,
                       headers={"Authorization": f"Bearer {token}"},
                       json={"model": args.model,
                             "messages": [{"role": "user", "content": question}]})
        data = r.json()
    except httpx.ConnectError:
        print(_unreachable_hint(base))
        return 2
    except (httpx.HTTPError, ValueError) as exc:
        print(f"✗ neurogate не отвечает ({type(exc).__name__}). Запустите: neurogate doctor")
        return 2
    if r.status_code != 200:
        print(f"✗ {data.get('detail') or data.get('error')}")
        return 1
    print(data["choices"][0]["message"]["content"])
    print(f"\n— {data.get('model')} (бесплатно)", file=sys.stderr)
    return 0


CONNECT_TOOLS = ["claude-code", "orchestrator", "cursor", "cline", "continue", "opencode", "codex"]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="neurogate", description="Бесплатный шлюз к нейросетям")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("setup", help="мастер ключей: ссылки, инструкции, сохранение в .env")
    p.add_argument("services", nargs="*", help="id сервисов (groq gemini …); пусто — все без ключа")
    p.add_argument("--all", action="store_true", help="пройти и по уже вписанным")
    p.add_argument("--more", action="store_true", help="сразу все сервисы, без быстрого старта")
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

    p = sub.add_parser("doctor", help="проверить всю систему и подсказать, что починить")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("restart", help="перезапустить сервер (после новых ключей)")
    p.set_defaults(func=cmd_restart)

    sub.add_parser("serve", help="запустить сервер (то же, что `neurogate` без аргументов)")

    p = sub.add_parser("delegate", help="поручить задачу бесплатному агенту (сам правит файлы)")
    p.add_argument("task", nargs="*")
    p.add_argument("--file", help="взять задачу из файла (многострочные задачи, Windows)")
    p.add_argument("--dir", default=".", help="папка проекта (по умолчанию текущая)")
    p.add_argument("--model", default="code", help="модель neurogate: code, code_fast, auto")
    p.add_argument("--worker", choices=["auto", "opencode", "claude"], default="auto")
    p.set_defaults(func=cmd_delegate)

    p = sub.add_parser("ask", help="быстрый вопрос бесплатной модели (без правки файлов)")
    p.add_argument("question", nargs="*")
    p.add_argument("--file", help="взять вопрос из файла")
    p.add_argument("--model", default="auto")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("connect", help="подключить инструмент к neurogate")
    p.add_argument("tool", choices=CONNECT_TOOLS)
    p.add_argument("--global", dest="global_", action="store_true",
                   help="orchestrator: для всех проектов (~/.codex/AGENTS.md, ~/.claude/CLAUDE.md)")
    p.set_defaults(func=cmd_connect)

    if argv[:1] == ["bot"]:  # флаги бота (--gen-key) argparse.REMAINDER не пропускает
        from neurogate.keybot import run_bot

        return run_bot(argv[1:])
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
