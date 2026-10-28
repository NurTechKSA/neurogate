import json
import os
import time
from pathlib import Path

import httpx
import pytest

from conftest import FakeResponse
from neurogate import cli
from neurogate.envfile import read_env_file


# ---------------------------------------------------------------- каталог

def test_catalog_is_consistent():
    cat = cli.load_catalog()
    services = cat["services"]
    ids = [s["id"] for s in services]
    envs = [s["env"] for s in services]
    assert len(ids) == len(set(ids)), "повтор id"
    assert len(envs) == len(set(envs)), "повтор env"
    for s in services:
        for field in ("name", "env", "priority", "gives", "limits", "needs", "signup", "key_url", "steps"):
            assert s.get(field), (s["id"], field)
        assert s["key_url"].startswith("https://"), s["id"]
        assert s["priority"] in (1, 2, 3)
        chk = s.get("check") or {}
        assert chk.get("auth") in ("bearer", "query", "none"), s["id"]
        if chk.get("auth") != "none":
            assert chk.get("url", "").startswith("https://"), s["id"]
    assert set(cat["quick"]) <= set(ids)
    assert len(cat["quick"]) == 3
    assert cat["keyless"]


def test_ordered_services_puts_quick_first():
    cat = cli.load_catalog()
    order = [s["id"] for s in cli.ordered_services(cat)]
    assert order[:3] == cat["quick"]
    rest = cli.ordered_services(cat)[3:]
    assert [s["priority"] for s in rest] == sorted(s["priority"] for s in rest)


def test_services_filter_by_id_or_env():
    cat = cli.load_catalog()
    assert [s["id"] for s in cli._services(cat, ["groq", "NVIDIA_API_KEY"])] == ["nvidia", "groq"]


# ---------------------------------------------------------------- check_key

SVC_BEARER = {"check": {"url": "https://api.example/v1/models", "auth": "bearer"}}


@pytest.mark.parametrize("status,expected", [(200, True), (401, False), (403, False), (400, False),
                                             (500, None), (429, None)])
def test_check_key_statuses(monkeypatch, status, expected):
    seen = {}

    def fake_get(url, headers, params, timeout):
        seen.update(url=url, headers=headers, params=params)
        return FakeResponse(status, {})

    monkeypatch.setattr(httpx, "get", fake_get)
    ok, _msg = cli.check_key(SVC_BEARER, "k1")
    assert ok is expected
    assert seen["headers"] == {"Authorization": "Bearer k1"} and seen["params"] == {}


def test_check_key_query_param(monkeypatch):
    seen = {}
    monkeypatch.setattr(httpx, "get", lambda url, headers, params, timeout: seen.update(params=params)
                        or FakeResponse(200, {}))
    svc = {"check": {"url": "https://g.example/models", "auth": "query", "param": "key"}}
    assert cli.check_key(svc, "AIza")[0] is True
    assert seen["params"] == {"key": "AIza"}


def test_check_key_prefix_and_no_check_and_network(monkeypatch):
    assert cli.check_key({"check": {"url": "", "auth": "none", "prefix": "nvapi-"}}, "bad")[0] is False
    assert cli.check_key({"check": {"url": "", "auth": "none"}}, "anything")[0] is None
    assert cli.check_key({}, "anything")[0] is None

    def boom(*a, **k):
        raise httpx.ConnectError("x")

    monkeypatch.setattr(httpx, "get", boom)
    assert cli.check_key(SVC_BEARER, "k")[0] is None


def test_catalog_public_models_endpoints_have_no_check():
    """Сервисы с открытым без ключа /models не должны «принимать» любой ключ."""
    by_id = {s["id"]: s for s in cli.load_catalog()["services"]}
    for sid in ("zenmux", "inception", "gonka", "iteracompute", "nvidia"):
        assert (by_id[sid].get("check") or {}).get("auth") == "none", sid


# ---------------------------------------------------------------- setup

def _run_setup(monkeypatch, argv, answers, keys):
    answers, keys = list(answers), list(keys)
    monkeypatch.setattr(cli, "_ask", lambda prompt: answers.pop(0) if answers else "q")
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": keys.pop(0) if keys else "")
    monkeypatch.setattr(cli.webbrowser, "open", lambda url: None)
    monkeypatch.setattr(cli, "restart_service", lambda: False)
    return cli.main(["setup", "--no-browser", *argv])


def test_setup_quick_mode_saves_valid_key_and_rejects_bad(home, monkeypatch, capsys):
    results = iter([(False, "сервис отверг ключ"), (True, "ключ работает")])
    monkeypatch.setattr(cli, "check_key", lambda s, k: next(results))
    # Gemini: Enter, плохой ключ, «ввести заново» = да, хороший; затем q
    rc = _run_setup(monkeypatch, [], ["", "y", "q"], ["bad", "AIza-good"])
    assert rc == 0
    env = read_env_file(Path(os.environ["NEUROGATE_ENV_FILE"]))
    assert env["GEMINI_API_KEY"] == "AIza-good"
    out = capsys.readouterr().out
    assert "[1/3] Google Gemini" in out
    assert "Быстрый старт пройден" not in out  # вышли по q


def test_setup_quick_mode_offers_more_after_three(home, monkeypatch, capsys):
    monkeypatch.setattr(cli, "check_key", lambda s, k: (None, "без проверки"))
    rc = _run_setup(monkeypatch, [], ["s", "s", "s", "n"], [])
    assert rc == 0
    assert "Быстрый старт пройден" in capsys.readouterr().out


def test_setup_extra_env_for_cloudflare(home, monkeypatch):
    monkeypatch.setattr(cli, "check_key", lambda s, k: (True, "ok"))
    monkeypatch.setattr("builtins.input", lambda prompt="": "acc123")
    rc = _run_setup(monkeypatch, ["cloudflare"], [""], ["cf-token"])
    assert rc == 0
    env = read_env_file(Path(os.environ["NEUROGATE_ENV_FILE"]))
    assert env["CLOUDFLARE_API_KEY"] == "cf-token" and env["CLOUDFLARE_ACCOUNT_ID"] == "acc123"


def test_keys_markdown_lists_every_service(home, capsys):
    cli.main(["keys", "--markdown"])
    out = capsys.readouterr().out
    assert out.count("\n| **") == len(cli.load_catalog()["services"])


def test_keys_offline_counts(home, capsys):
    Path(os.environ["NEUROGATE_ENV_FILE"]).write_text("GROQ_API_KEY=gsk\n", encoding="utf-8")
    cli.main(["keys", "--offline"])
    assert "Ключей вписано: 1 из" in capsys.readouterr().out


# ---------------------------------------------------------------- import

def test_import_writes_keys(home, monkeypatch, capsys):
    from neurogate import keydrop

    monkeypatch.setattr(keydrop, "fetch", lambda code: {"GEMINI_API_KEY": "AIza", "NVIDIA_API_KEY": "nvapi-x"})
    assert cli.main(["import", "NG-12345678-abcdefghijklmnopqrstuv", "--no-restart"]) == 0
    env = read_env_file(Path(os.environ["NEUROGATE_ENV_FILE"]))
    assert env["GEMINI_API_KEY"] == "AIza" and env["NVIDIA_API_KEY"] == "nvapi-x"
    assert "Google Gemini" in capsys.readouterr().out


def test_import_error_message(home, monkeypatch, capsys):
    from neurogate import keydrop

    def fail(code):
        raise keydrop.DropError("Код уже использован")

    monkeypatch.setattr(keydrop, "fetch", fail)
    assert cli.main(["import", "NG-x"]) == 1
    assert "Код уже использован" in capsys.readouterr().out


# ---------------------------------------------------------------- connect

def test_gateway_reads_env_and_token(home, monkeypatch):
    assert cli._gateway() == ("http://127.0.0.1:8799", "neurogate-local")
    Path(os.environ["NEUROGATE_ENV_FILE"]).write_text(
        "NEUROGATE_HOST=0.0.0.0\nNEUROGATE_PORT=9000\nNEUROGATE_API_TOKEN=tok\n", encoding="utf-8")
    assert cli._gateway() == ("http://127.0.0.1:9000", "tok")


def test_connect_claude_code_shim(home):
    cli.main(["connect", "claude-code"])
    shim = (home / ".local/bin/claude-free").read_text(encoding="utf-8")
    assert "ANTHROPIC_BASE_URL='http://127.0.0.1:8799'" in shim
    assert "ANTHROPIC_MODEL='code'" in shim and 'exec claude "$@"' in shim
    assert os.access(home / ".local/bin/claude-free", os.X_OK)


def test_connect_opencode_merges_and_keeps_backup(home, monkeypatch):
    monkeypatch.setattr(cli, "_opencode_auth", lambda token: None)
    cfg_path = home / ".config/opencode/opencode.json"
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text(json.dumps({"mcp": {"ctx": {"type": "remote", "url": "u"}}}), encoding="utf-8")
    cli.main(["connect", "opencode"])
    cli.main(["connect", "opencode"])  # повтор не должен затереть исходный бэкап
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert cfg["mcp"]["ctx"]["url"] == "u"
    assert cfg["model"] == "neurogate/code"
    v1 = cfg["provider"]["neurogate"]
    v2 = cfg["providers"]["neurogate"]
    assert v1["options"]["baseURL"] == "http://127.0.0.1:8799/v1"
    assert v2["settings"]["baseURL"] == "http://127.0.0.1:8799/v1"
    model = v2["models"]["code"]
    assert model["type"] == "chat" and model["releaseDate"] == time.strftime("%Y-%m-%d")
    assert model["capabilities"]["reasoning"] == {"supported": False}
    assert list(v2["models"]) == ["code"]
    backup = json.loads(cfg_path.with_suffix(".json.bak").read_text(encoding="utf-8"))
    assert "provider" not in backup


def test_connect_opencode_refuses_non_json(home, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_opencode_auth", lambda token: None)
    cfg_path = home / ".config/opencode/opencode.json"
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text("{ // comment\n}", encoding="utf-8")
    cli.main(["connect", "opencode"])
    assert cfg_path.read_text(encoding="utf-8") == "{ // comment\n}"
    assert "не чистый JSON" in capsys.readouterr().out


def test_connect_codex_profile_file_and_legacy_cleanup(home):
    codex = home / ".codex"
    codex.mkdir()
    (codex / "config.toml").write_text(
        'model = "gpt"\n\n' + cli.CODEX_MARK + '\n[model_providers.neurogate]\nname = "x"\n\n'
        '[profiles.free]\nmodel = "code"\nmodel_context_window = 128000\n\n[mcp_servers.keep]\ncommand = "y"\n',
        encoding="utf-8")
    cli.main(["connect", "codex"])
    base = (codex / "config.toml").read_text(encoding="utf-8")
    assert "[profiles.free]" not in base and "[mcp_servers.keep]" in base and 'model = "gpt"' in base
    prof = (codex / "free.config.toml").read_text(encoding="utf-8")
    assert 'wire_api = "responses"' in prof and 'base_url = "http://127.0.0.1:8799/v1"' in prof
    assert 'model_provider = "neurogate"' in prof
    assert "--profile free" in (home / ".local/bin/codex-free").read_text(encoding="utf-8")


def test_connect_orchestrator_local_and_global_idempotent(home, tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "AGENTS.md").write_text("# мои правила\n", encoding="utf-8")
    monkeypatch.setenv("NEUROGATE_CALLER_DIR", str(proj))
    cli.main(["connect", "orchestrator"])
    cli.main(["connect", "orchestrator"])
    agents = (proj / "AGENTS.md").read_text(encoding="utf-8")
    assert agents.startswith("# мои правила") and agents.count(cli.ORCHESTRATOR_MARK) == 1
    assert (proj / "CLAUDE.md").read_text(encoding="utf-8").count("neurogate delegate") >= 1
    cli.main(["connect", "orchestrator", "--global"])
    assert cli.ORCHESTRATOR_MARK in (home / ".codex/AGENTS.md").read_text(encoding="utf-8")
    assert cli.ORCHESTRATOR_MARK in (home / ".claude/CLAUDE.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- doctor

def _doctor_env(home, monkeypatch, *, keys="GEMINI_API_KEY=a\nOPENROUTER_API_KEY=b\nNVIDIA_API_KEY=c\n",
                alive=True, reply=200):
    for var in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    Path(os.environ["NEUROGATE_ENV_FILE"]).write_text("NEUROGATE_PORT=8799\n" + keys, encoding="utf-8")
    monkeypatch.setattr(cli, "_gateway_alive", lambda base: alive)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse(
        reply, {"model": "nvidia:x", "choices": [{"message": {"content": "ок"}}]} if reply == 200
        else {"detail": "all failed"}))


def test_doctor_all_green(home, monkeypatch, capsys):
    _doctor_env(home, monkeypatch)
    monkeypatch.setattr(cli, "_opencode_auth", lambda token: None)
    cli.main(["connect", "opencode"])
    cli.main(["connect", "claude-code"])
    monkeypatch.setenv("PATH", str(home / ".local/bin") + os.pathsep + os.environ.get("PATH", ""))
    assert cli.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "ACCESS GRANTED" in out and "[ FAIL ]" not in out


def test_doctor_reports_no_keys_and_dead_gateway(home, monkeypatch, capsys):
    _doctor_env(home, monkeypatch, keys="", alive=False)
    assert cli.main(["doctor"]) == 1
    out = capsys.readouterr().out
    assert "Ключей нет" in out and "Шлюз не отвечает" in out and "neurogate restart" in out


def test_doctor_reports_models_failing(home, monkeypatch, capsys):
    _doctor_env(home, monkeypatch, reply=502)
    assert cli.main(["doctor"]) == 1
    assert "Модели не ответили" in capsys.readouterr().out


def test_doctor_warns_old_opencode_date_and_wrong_port(home, monkeypatch, capsys):
    _doctor_env(home, monkeypatch)
    monkeypatch.setattr(cli, "_opencode_auth", lambda token: None)
    cli.main(["connect", "opencode"])
    p = home / ".config/opencode/opencode.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg["providers"]["neurogate"]["models"]["code"]["releaseDate"] = "2020-01-01"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    cli.main(["doctor"])
    assert "OpenCode её спрячет" in capsys.readouterr().out
    cfg["providers"]["neurogate"]["settings"]["baseURL"] = "http://127.0.0.1:1/v1"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    assert cli.main(["doctor"]) == 1
    assert "OpenCode смотрит на" in capsys.readouterr().out


# ---------------------------------------------------------------- delegate / ask

def test_delegate_uses_opencode_in_caller_dir(home, tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    proj.mkdir()
    monkeypatch.setenv("NEUROGATE_CALLER_DIR", str(proj))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-leak")
    monkeypatch.setattr(cli, "_gateway_alive", lambda base: True)
    monkeypatch.setattr(cli, "_opencode_cli", lambda prefer_app=False: "/bin/opencode")
    calls = []

    class R:
        returncode = 0
        stdout = ""

    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw)) or R())
    assert cli.main(["delegate", "сделай", "тесты"]) == 0
    cmd, kw = calls[0]
    assert cmd[:4] == ["/bin/opencode", "run", "-m", "neurogate/code"]
    assert cmd[4].endswith("Задача:\nсделай тесты")
    assert kw["cwd"] == proj and kw["env"]["PWD"] == str(proj)
    assert "ANTHROPIC_API_KEY" not in kw["env"]


def test_delegate_falls_back_to_claude(home, tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROGATE_CALLER_DIR", str(tmp_path))
    monkeypatch.setattr(cli, "_gateway_alive", lambda base: True)
    monkeypatch.setattr(cli, "_opencode_cli", lambda prefer_app=False: None)
    claude = home / ".local/bin/claude"
    claude.parent.mkdir(parents=True)
    claude.write_text("#!/bin/sh\n")
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    calls = []

    class R:
        returncode = 0
        stdout = ""

    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw)) or R())
    cli.main(["delegate", "--model", "code_fast", "задача"])
    cmd, kw = calls[0]
    assert cmd[0] == str(claude) and "-p" in cmd
    assert kw["env"]["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:8799"
    assert kw["env"]["ANTHROPIC_MODEL"] == "code_fast"


def test_delegate_refuses_when_gateway_down(home, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_gateway_alive", lambda base: False)
    assert cli.main(["delegate", "x"]) == 2
    assert "не отвечает" in capsys.readouterr().out


def test_ask_prints_answer_and_errors(home, monkeypatch, capsys):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse(
        200, {"model": "m1", "choices": [{"message": {"content": "ответ"}}]}))
    assert cli.main(["ask", "вопрос"]) == 0
    assert "ответ" in capsys.readouterr().out
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse(503, {"detail": "нет ключей"}))
    assert cli.main(["ask", "вопрос"]) == 1
    assert "нет ключей" in capsys.readouterr().out
