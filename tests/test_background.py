"""neurogate.background: автозапуск на Windows идёт через pythonw, у которого нет консоли."""

import sys

from neurogate import background, main


def test_background_sends_output_to_log_and_starts_server(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdout", None)  # как у pythonw
    monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.setattr(sys, "argv", ["pythonw"])
    seen = {}

    def fake_run():
        seen["argv"] = list(sys.argv)
        print("сервер стартовал")

    monkeypatch.setattr(main, "run", fake_run)
    background.main()
    sys.stdout.flush()

    assert seen["argv"][1:] == ["serve"]
    assert "сервер стартовал" in (tmp_path / "neurogate.log").read_text(encoding="utf-8")
