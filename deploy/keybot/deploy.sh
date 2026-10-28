#!/usr/bin/env bash
# Выкладка бота ключей на общий сервер (как NurTools/CRM): снимок HEAD → сборка на сервере → запуск → проверки.
#   deploy/keybot/deploy.sh              # выкладка последнего коммита
#   deploy/keybot/deploy.sh --init-env   # один раз: .env на сервере (токен бота читается скрыто, ключи генерятся)
set -euo pipefail
VPS="${VPS:-root@45.77.66.108}"
DIR="${DIR:-/opt/neurogate-keybot}"
DOMAIN="${DOMAIN:-neurogate.nurtech.dev}"
SSH="ssh -o BatchMode=yes -o ConnectTimeout=15"
cd "$(dirname "$0")/../.."
TAG=$(git rev-parse --short HEAD)

if [[ "${1:-}" == "--init-env" ]]; then
  $SSH "$VPS" "mkdir -p $DIR/deploy/keybot && test ! -f $DIR/deploy/keybot/.env" \
    || { echo "На сервере уже есть $DIR/deploy/keybot/.env — не перезаписываю"; exit 1; }
  read -rsp "Вставьте токен бота от @BotFather и нажмите Enter: " token; echo
  [[ "$token" =~ ^[0-9]+:[A-Za-z0-9_-]{30,}$ ]] || { echo "Это не похоже на токен бота"; exit 1; }
  storage_key=$(python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())")
  printf 'DOMAIN=%s\nTELEGRAM_BOT_TOKEN=%s\nBOT_STORAGE_KEY=%s\nTELEGRAM_WEBHOOK_SECRET=%s\n' \
    "$DOMAIN" "$token" "$storage_key" "$(openssl rand -hex 24)" \
    | $SSH "$VPS" "umask 077 && cat > $DIR/deploy/keybot/.env"
  echo "Сохранено на сервере ($DIR/deploy/keybot/.env, права 600)."
  echo "Напишите Claude: готово"
  exit 0
fi

echo "▶ выкладка $TAG → $VPS:$DIR"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
git archive HEAD | tar -x -C "$tmp"
rsync -az --delete --exclude 'deploy/keybot/.env' "$tmp"/ "$VPS:$DIR/"
$SSH "$VPS" bash -s <<REMOTE
set -euo pipefail
cd $DIR
test -f deploy/keybot/.env || { echo "Нет deploy/keybot/.env — сначала deploy.sh --init-env"; exit 1; }
TAG=$TAG docker compose -f deploy/keybot/compose.yml --env-file deploy/keybot/.env up -d --build
for i in \$(seq 1 30); do
  docker exec neurogate-keybot python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/health')" 2>/dev/null && ok=1 && break
  sleep 2
done
test "\${ok:-}" = 1 || { echo "Бот не поднялся"; docker logs --tail 50 neurogate-keybot; exit 1; }
echo "▶ $TAG запущен"
REMOTE
curl -s -o /dev/null -w "https://$DOMAIN/health -> %{http_code}\n" --retry 15 --retry-delay 6 --retry-all-errors --max-time 20 "https://$DOMAIN/health" || true
