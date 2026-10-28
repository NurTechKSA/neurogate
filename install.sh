#!/usr/bin/env bash
# Установка neurogate одной командой (macOS / Linux):
#   curl -fsSL https://raw.githubusercontent.com/RYAZHAPOVILNUR/neurogate/main/install.sh | bash
#
# Что делает: ставит uv, качает neurogate в ~/neurogate, ставит зависимости,
# запускает мастер ключей, включает автозапуск сервера и подключает Claude Code.
# Повторный запуск безопасен — обновит код и ничего не сотрёт.
set -euo pipefail

REPO="${NEUROGATE_REPO:-https://github.com/RYAZHAPOVILNUR/neurogate.git}"
DIR="${NEUROGATE_DIR:-$HOME/neurogate}"
PORT="${NEUROGATE_PORT:-8765}"

say() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }

say "1/6 Менеджер Python-окружений uv"
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
UV="$(command -v uv)"

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

say "4/6 Ключи нейросетей (можно пропускать и вернуться позже: neurogate setup)"
"$UV" run neurogate setup < /dev/tty || true

say "5/6 Автозапуск сервера"
if [ "$(uname)" = "Darwin" ]; then
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

for _ in $(seq 1 40); do
  curl -fs "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break
  sleep 1
done
if curl -fs "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "Сервер работает: http://127.0.0.1:$PORT/dashboard"
else
  echo "Сервер пока не ответил. Лог: $DIR/neurogate.log"
fi

say "6/6 Подключение инструментов"
"$UV" run neurogate connect claude-code
if ! command -v claude >/dev/null 2>&1; then
  echo "Claude Code не найден. Поставить: curl -fsSL https://claude.ai/install.sh | bash"
fi

# Короткая команда `neurogate` из любой папки.
cat > "$HOME/.local/bin/neurogate" <<EOF
#!/bin/sh
cd "$DIR" && exec "$UV" run neurogate "\$@"
EOF
chmod +x "$HOME/.local/bin/neurogate"

cat <<EOF

✅ Готово.
  Панель и тестовый чат:   http://127.0.0.1:$PORT/dashboard
  Claude Code бесплатно:   claude-free
  Добавить ещё ключи:      neurogate setup
  Проверить ключи:         neurogate keys
  Cursor/Cline/OpenCode:   neurogate connect cline   (или cursor, opencode, codex, continue)

  Перезапустить сервер:     neurogate restart   (setup делает это сам)
EOF
