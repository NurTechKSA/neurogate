#!/usr/bin/env bash
# Установка neurogate одной командой (macOS / Linux):
#   curl -fsSL https://raw.githubusercontent.com/RYAZHAPOVILNUR/neurogate/main/install.sh | bash
# С ключами из Telegram-бота: ... | NEUROGATE_CODE=NG-xxxx bash  (команду целиком выдаёт бот)
#
# NEUROGATE_NO_AUTOSTART=1 — не ставить автозапуск (сервер, тесты, «запущу сам»).
#
# Что делает: ставит uv, качает neurogate в ~/neurogate, ставит зависимости,
# запускает мастер ключей, включает автозапуск сервера и подключает OpenCode и Claude Code.
# Повторный запуск безопасен — обновит код и ничего не сотрёт.
set -euo pipefail

REPO="${NEUROGATE_REPO:-https://github.com/RYAZHAPOVILNUR/neurogate.git}"
DIR="${NEUROGATE_DIR:-$HOME/neurogate}"
PORT="${NEUROGATE_PORT:-8765}"

cat <<'BANNER'

  ███╗   ██╗███████╗██╗   ██╗██████╗  ██████╗  ██████╗  █████╗ ████████╗███████╗
  ████╗  ██║██╔════╝██║   ██║██╔══██╗██╔═══██╗██╔════╝ ██╔══██╗╚══██╔══╝██╔════╝
  ██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║   ██║██║  ███╗███████║   ██║   █████╗
  ██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██║   ██║██╔══██║   ██║   ██╔══╝
  ██║ ╚████║███████╗╚██████╔╝██║  ██║╚██████╔╝╚██████╔╝██║  ██║   ██║   ███████╗
  ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
  > access: free · 50 нейросетей · 0 ₽                     neurogate.nurtech.dev
BANNER

say() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }

say "1/6 Менеджер Python-окружений uv"
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV="$(command -v uv)"
# Свой Python 3.12 от uv: системный бывает сломан или собран под другую архитектуру
# (Homebrew под Rosetta), и тогда пакеты начинают компилироваться из исходников.
export UV_PYTHON_PREFERENCE=only-managed UV_PYTHON=3.12

say "2/6 Код neurogate → $DIR"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull --ff-only || echo "Не удалось обновить — работаю с текущей версией."
elif command -v git >/dev/null 2>&1; then
  git clone --depth 1 "$REPO" "$DIR"
else
  mkdir -p "$DIR"
  curl -fsSL "${REPO%.git}/archive/refs/heads/main.tar.gz" | tar -xz --strip-components=1 -C "$DIR"
fi
cd "$DIR"

say "3/6 Зависимости"
"$UV" sync --frozen
[ -f .env ] || cp .env.example .env
[ -f config.yaml ] || cp config.yaml.example config.yaml
chmod 600 .env

# Порт занят чужой программой (не нашим прошлым запуском) — берём следующий свободный.
port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
if port_busy "$PORT" && ! curl -fs "http://127.0.0.1:$PORT/health" 2>/dev/null | grep -q '"ok"'; then
  for p in $(seq $((PORT + 1)) $((PORT + 20))); do
    if ! port_busy "$p"; then echo "Порт $PORT занят другой программой — беру $p."; PORT=$p; break; fi
  done
fi
if grep -q '^NEUROGATE_PORT=' .env; then
  sed -i.bak "s/^NEUROGATE_PORT=.*/NEUROGATE_PORT=$PORT/" .env && rm -f .env.bak
else
  echo "NEUROGATE_PORT=$PORT" >> .env
fi
export NEUROGATE_PORT="$PORT"

if [ -n "${NEUROGATE_CODE:-}" ]; then
  say "4/6 Ключи из Telegram-бота"
  "$UV" run neurogate import "$NEUROGATE_CODE" --no-restart || {
    echo "Ключи по коду не забрались. Можно ввести их вручную: neurogate setup"
  }
elif [ "$(grep -cE '^[A-Z0-9_]+_(API_KEY|TOKEN|AUTH_KEY)=.+' .env 2>/dev/null)" -gt 0 ]; then
  say "4/6 Ключи уже есть — мастер пропускаю (добавить ещё: neurogate setup)"
else
  say "4/6 Ключи нейросетей (можно пропускать и вернуться позже: neurogate setup)"
  if (: < /dev/tty) 2>/dev/null; then
    "$UV" run neurogate setup < /dev/tty || true
  else
    echo "Нет интерактивного терминала — добавьте ключи потом: neurogate setup"
  fi
fi

say "5/6 Автозапуск сервера"
if [ -n "${NEUROGATE_NO_AUTOSTART:-}" ]; then
  echo "Автозапуск пропущен (NEUROGATE_NO_AUTOSTART). Запуск вручную: neurogate serve"
elif [ "$(uname)" = "Darwin" ]; then
  PLIST="$HOME/Library/LaunchAgents/dev.neurogate.plist"
  mkdir -p "$(dirname "$PLIST")"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>dev.neurogate</string>
  <key>ProgramArguments</key><array>
    <string>$UV</string><string>run</string><string>neurogate</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>EnvironmentVariables</key><dict><key>NEUROGATE_PORT</key><string>$PORT</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$DIR/neurogate.log</string>
  <key>StandardErrorPath</key><string>$DIR/neurogate.log</string>
</dict></plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
elif command -v systemctl >/dev/null 2>&1; then
  UNIT="$HOME/.config/systemd/user/neurogate.service"
  mkdir -p "$(dirname "$UNIT")"
  cat > "$UNIT" <<EOF
[Unit]
Description=neurogate
After=network-online.target

[Service]
WorkingDirectory=$DIR
Environment=NEUROGATE_PORT=$PORT
ExecStart=$UV run neurogate
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now neurogate
  systemctl --user restart neurogate
else
  echo "Автозапуск не настроен. Запускайте вручную: cd $DIR && uv run neurogate"
fi

if [ -z "${NEUROGATE_NO_AUTOSTART:-}" ]; then
  for _ in $(seq 1 40); do
    curl -fs "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break
    sleep 1
  done
  if curl -fs "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    echo "Сервер работает: http://127.0.0.1:$PORT/dashboard"
  else
    echo "Сервер пока не ответил. Лог: $DIR/neurogate.log"
  fi
fi

say "6/6 Подключение программ"
"$UV" run neurogate connect opencode
"$UV" run neurogate connect claude-code
"$UV" run neurogate connect codex
if ! command -v claude >/dev/null 2>&1; then
  echo "Claude Code не найден. Поставить: curl -fsSL https://claude.ai/install.sh | bash"
fi

# Короткая команда `neurogate` из любой папки. Сразу из .venv, без `uv run`: в песочнице
# Codex uv падает — ему некуда писать кэш (~/.cache/uv).
cat > "$HOME/.local/bin/neurogate" <<EOF
#!/bin/sh
NEUROGATE_CALLER_DIR="\$PWD" && export NEUROGATE_CALLER_DIR && cd "$DIR" || exit 1
[ -x "$DIR/.venv/bin/neurogate" ] && exec "$DIR/.venv/bin/neurogate" "\$@"
exec "$UV" run neurogate "\$@"
EOF
chmod +x "$HOME/.local/bin/neurogate"

# ~/.local/bin в PATH — иначе ни neurogate, ни claude-free, ни claude не найдутся.
case "${SHELL##*/}" in
  zsh) RC="$HOME/.zshrc" ;;
  bash) if [ "$(uname)" = "Darwin" ]; then RC="$HOME/.bash_profile"; else RC="$HOME/.bashrc"; fi ;;
  *) RC="$HOME/.profile" ;;
esac
if ! grep -qs '\.local/bin' "$RC"; then
  printf '\n# neurogate: claude, claude-free, neurogate, uv\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$RC"
  NEW_PATH=1
fi

cat <<EOF

🔓 ACCESS GRANTED. Всё бесплатно, подписки не нужны.

  ⭐ Приложение OpenCode (окно, как у Claude/ChatGPT):
     скачайте https://opencode.ai/download → откройте → выберите папку проекта → пишите задачу.
     Модель «neurogate/code» уже выбрана.
  Claude Code в терминале: claude-free
  Codex бесплатно:         codex-free
  Панель и тестовый чат:   http://127.0.0.1:$PORT/dashboard
  Добавить ещё ключи:      neurogate setup
  Проверить ключи:         neurogate keys
  VS Code (Cline и др.):   neurogate connect cline   (или continue, cursor)
  Перезапустить сервер:    neurogate restart   (setup делает это сам)
  Что-то не так?           neurogate doctor
  Инструкция:              https://neurogate.nurtech.dev
EOF
if [ "$(uname)" = "Darwin" ] && [ ! -d /Applications/OpenCode.app ]; then
  echo
  echo "OpenCode ещё не установлен — открываю страницу скачивания…"
  open "https://opencode.ai/download" 2>/dev/null || true
fi
if [ -n "${NEW_PATH:-}" ]; then
  echo
  echo "⚠ Откройте НОВОЕ окно терминала — в этом команды neurogate и claude-free ещё не видны."
fi
