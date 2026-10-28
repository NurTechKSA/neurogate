# Установка neurogate одной командой (Windows, PowerShell):
#   irm https://raw.githubusercontent.com/RYAZHAPOVILNUR/neurogate/main/install.ps1 | iex
#
# Что делает: ставит uv, качает neurogate в %USERPROFILE%\neurogate, ставит зависимости,
# запускает мастер ключей, включает автозапуск при входе в Windows и подключает Claude Code.
# Повторный запуск безопасен — обновит код и ничего не сотрёт.
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

$Repo = if ($env:NEUROGATE_REPO) { $env:NEUROGATE_REPO } else { "https://github.com/RYAZHAPOVILNUR/neurogate" }
$Dir  = if ($env:NEUROGATE_DIR)  { $env:NEUROGATE_DIR }  else { Join-Path $HOME "neurogate" }
$Port = if ($env:NEUROGATE_PORT) { $env:NEUROGATE_PORT } else { "8765" }
$Bin  = Join-Path $HOME ".local\bin"

function Say($t) { Write-Host "`n> $t" -ForegroundColor Cyan }

Say "1/6 Менеджер Python-окружений uv"
New-Item -ItemType Directory -Force -Path $Bin | Out-Null
$env:Path = "$Bin;$env:Path"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
}
$Uv = (Get-Command uv).Source
# Свой Python 3.12 от uv — системный может быть любой версии или из Microsoft Store.
$env:UV_PYTHON_PREFERENCE = "only-managed"
$env:UV_PYTHON = "3.12"

Say "2/6 Код neurogate -> $Dir"
if (Test-Path (Join-Path $Dir ".git")) {
    git -C $Dir pull --ff-only
} elseif (Get-Command git -ErrorAction SilentlyContinue) {
    git clone --depth 1 "$Repo.git" $Dir
} else {
    $zip = Join-Path $env:TEMP "neurogate.zip"
    Invoke-WebRequest "$Repo/archive/refs/heads/main.zip" -OutFile $zip
    $tmp = Join-Path $env:TEMP "neurogate-src"
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive $zip $tmp
    New-Item -ItemType Directory -Force -Path $Dir | Out-Null
    Copy-Item (Join-Path (Get-ChildItem $tmp)[0].FullName "*") $Dir -Recurse -Force
}
Set-Location $Dir

Say "3/6 Зависимости"
& $Uv sync --frozen
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
if (-not (Test-Path "config.yaml")) { Copy-Item "config.yaml.example" "config.yaml" }

Say "4/6 Ключи нейросетей (можно пропускать и вернуться позже: neurogate setup)"
& $Uv run neurogate setup

Say "5/6 Автозапуск сервера при входе в Windows"
$serve = Join-Path $Dir "neurogate-serve.cmd"
@"
@echo off
set PYTHONUTF8=1
set NEUROGATE_PORT=$Port
cd /d "$Dir"
"$Uv" run neurogate serve >> "$Dir\neurogate.log" 2>&1
"@ | Set-Content -Encoding ASCII $serve
$action  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$serve`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0 -Hidden
Register-ScheduledTask -TaskName "neurogate" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Stop-ScheduledTask -TaskName "neurogate" -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName "neurogate"

$ok = $false
for ($i = 0; $i -lt 40; $i++) {
    try { Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2 | Out-Null; $ok = $true; break } catch { Start-Sleep 1 }
}
if ($ok) { Write-Host "Сервер работает: http://127.0.0.1:$Port/dashboard" }
else { Write-Host "Сервер пока не ответил. Лог: $Dir\neurogate.log" }

Say "6/6 Подключение инструментов"
@"
@echo off
set PYTHONUTF8=1
cd /d "$Dir"
"$Uv" run neurogate %*
"@ | Set-Content -Encoding ASCII (Join-Path $Bin "neurogate.cmd")
& $Uv run neurogate connect claude-code
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "Claude Code не найден. Поставить: irm https://claude.ai/install.ps1 | iex"
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$Bin*") {
    [Environment]::SetEnvironmentVariable("Path", "$Bin;$userPath", "User")
    Write-Host "Папка $Bin добавлена в PATH — откройте новое окно терминала."
}

Write-Host @"

Готово.
  Панель и тестовый чат:   http://127.0.0.1:$Port/dashboard
  Claude Code бесплатно:   claude-free
  Добавить ещё ключи:      neurogate setup
  Проверить ключи:         neurogate keys
  Cursor/Cline/OpenCode:   neurogate connect cline   (или cursor, opencode, codex, continue)
  Перезапустить сервер:    neurogate restart   (setup делает это сам)
"@
