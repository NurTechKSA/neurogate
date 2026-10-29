"""Запуск сервера без окна — для автозапуска на Windows (pythonw из планировщика задач).

У pythonw нет консоли: sys.stdout и sys.stderr равны None, и первый же print или лог
uvicorn роняет сервер. Поэтому весь вывод сначала уводим в neurogate.log в папке
запуска (планировщик ставит её рабочей), а потом стартуем обычный сервер.
"""

import os
import sys


def main() -> None:
    log = open(os.path.join(os.getcwd(), "neurogate.log"), "a", encoding="utf-8", buffering=1)  # noqa: SIM115
    sys.stdout = sys.stderr = log
    sys.argv = [sys.argv[0], "serve"]

    from neurogate.main import run

    run()


if __name__ == "__main__":
    main()
