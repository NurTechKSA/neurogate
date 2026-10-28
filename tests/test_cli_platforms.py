"""Ветки по ОС и внешним программам: перезапуск службы, Windows-обёртки, OpenCode auth."""

import asyncio

import pytest

from neurogate import cli, keybot


class R:
    def __init__(self, rc=0, out=""):
        self.returncode, self.stdout = rc, out


@pytest.mark.parametrize("system,unit,expect", [
    ("Darwin", "Library/LaunchAgents/dev.neurogate.plist", ["launchctl", "kickstart", "-k"]),
    ("Linux", ".config/systemd/user/neurogate.service", ["systemctl", "--user", "restart", "neurogate"]),
])
def test_restart_service_posix(home, monkeypatch, system, unit, expect):
    monkeypatch.setattr(cli.platform, "system", lambda: system)
    calls = []
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or R())
    assert cli.restart_service() is False, "службы нет — False"
    (home / unit).parent.mkdir(parents=True)
    (home / unit).write_text("x")
    assert cli.restart_service() is True
    assert calls[-1][:len(expect)] == expect


def test_restart_service_windows(home, monkeypatch):
    monkeypatch.setattr(cli.platform, "system", lambda: "Windows")
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        return R(0)

    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli.restart_service() is True
    assert ["schtasks", "/Query", "/TN", "neurogate"] in calls
    assert ["schtasks", "/Run", "/TN", "neurogate"] in calls
    assert any(c[0] == "powershell" and "8799" in c[-1] for c in calls), "гасим процесс на порту"
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: R(1))
    assert cli.restart_service() is False


def test_restart_command_message(home, monkeypatch, capsys):
    monkeypatch.setattr(cli, "restart_service", lambda: False)
    assert cli.main(["restart"]) == 1
    assert "не найдена" in capsys.readouterr().out


def test_windows_shims(home, monkeypatch):
    monkeypatch.setattr(cli.platform, "system", lambda: "Windows")
    cli.main(["connect", "claude-code"])
    cli.main(["connect", "codex"])
    claude = (home / ".local/bin/claude-free.cmd").read_text(encoding="utf-8")
    assert "set ANTHROPIC_BASE_URL=http://127.0.0.1:8799" in claude and "claude %*" in claude
    assert "codex --profile free %*" in (home / ".local/bin/codex-free.cmd").read_text(encoding="utf-8")


@pytest.mark.parametrize("tool,needle", [("cline", "OpenAI Compatible"), ("continue", "Continue"),
                                         ("cursor", "туннель")])
def test_connect_prints_settings(home, capsys, tool, needle):
    assert cli.main(["connect", tool]) == 0
    out = capsys.readouterr().out
    assert needle in out and "http://127.0.0.1:8799/v1" in out and "neurogate-local" in out


def test_opencode_auth_paths(home, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "_opencode_cli", lambda prefer_app=False: None)
    assert cli._opencode_auth("t") is None, "нет OpenCode — нечего подключать"

    monkeypatch.setattr(cli, "_opencode_cli", lambda prefer_app=False: "/app/opencode-cli")

    def run(cmd, **kw):
        calls.append(cmd)
        if cmd[1:] == ["--version"]:
            return R(0, "opencode v1.19.5")
        return R(0, "")

    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli._opencode_auth("t") is None, "1.x берёт ключ из options.apiKey"

    def run2(cmd, **kw):
        calls.append(cmd)
        if cmd[1:] == ["--version"]:
            return R(0, "opencode v2.2.0")
        if cmd[1:] == ["auth", "list"]:
            return R(0, "neurogate  neurogate  stored")
        return R(0)

    monkeypatch.setattr(cli.subprocess, "run", run2)
    assert cli._opencode_auth("t") is True
    assert ["/app/opencode-cli", "reload"] in calls, "уже подключён — только reload, без входа"


def test_opencode_cli_lookup(monkeypatch, tmp_path):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/opencode")
    assert cli._opencode_cli() == "/usr/bin/opencode"
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    monkeypatch.setattr(cli.Path, "exists", lambda self: str(self).endswith("opencode-cli"))
    assert cli._opencode_cli(prefer_app=True).endswith("opencode-cli")


def test_bot_gen_key(capsys):
    assert cli.main(["bot", "--gen-key"]) == 0
    assert len(capsys.readouterr().out.strip()) == 44


def test_tg_client_call_and_send(monkeypatch):
    posted = []

    class Resp:
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    async def post(self, url, json):
        posted.append((url, json))
        return Resp({"ok": url.endswith("sendMessage"), "result": {"message_id": 5},
                     "description": "bad"})

    monkeypatch.setattr(keybot.httpx.AsyncClient, "post", post)
    tg = keybot.TG("123:abc")
    assert asyncio.run(tg.send(1, "<b>hi</b>", [[{"text": "x", "callback_data": "y"}]])) == {"message_id": 5}
    assert asyncio.run(tg.call("deleteMessage", chat_id=1, message_id=2)) is None
    url, body = posted[0]
    assert url == "https://api.telegram.org/bot123:abc/sendMessage"
    assert body["parse_mode"] == "HTML" and body["reply_markup"]["inline_keyboard"][0][0]["text"] == "x"
