# Установка neurogate одной командой (Windows, PowerShell):
#   irm https://raw.githubusercontent.com/NurTechKSA/neurogate/main/install.ps1 | iex
#
# Что делает: ставит uv, качает neurogate в %USERPROFILE%\neurogate, ставит зависимости,
# запускает мастер ключей, включает автозапуск при входе в Windows и подключает Claude Code.
# Повторный запуск безопасен — обновит код и ничего не сотрёт.
#
# Весь скрипт — в блоке & { }: под `irm | iex` иначе $ErrorActionPreference и функции оставались
# бы в окне ученика после установки.
& {
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

$Repo = if ($env:NEUROGATE_REPO) { $env:NEUROGATE_REPO } else { "https://github.com/NurTechKSA/neurogate" }
$Dir  = if ($env:NEUROGATE_DIR)  { $env:NEUROGATE_DIR }  else { Join-Path $HOME "neurogate" }
$Port = if ($env:NEUROGATE_PORT) { $env:NEUROGATE_PORT } else { "8765" }
$Bin  = Join-Path $HOME ".local\bin"

function Say($t) { Write-Host "`n> $t" -ForegroundColor Cyan }
$ProgressPreference = "SilentlyContinue"   # полоса загрузки в PS 5.1 замедляет скачивание в разы

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
    Invoke-WebRequest "$Repo/archive/refs/heads/main.zip" -OutFile $zip -UseBasicParsing
    $tmp = Join-Path $env:TEMP "neurogate-src"
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive $zip $tmp
    New-Item -ItemType Directory -Force -Path $Dir | Out-Null
    Copy-Item (Join-Path (Get-ChildItem $tmp)[0].FullName "*") $Dir -Recurse -Force
}
Push-Location $Dir

# Повторная установка: работающий сервер держит файлы пакетов (.pyd), и uv sync не сможет их
# обновить («Отказано в доступе») — гасим его до обновления.
# Прошлая установка могла взять другой порт (свой занят) — он записан в .env
$envFile = Join-Path $Dir ".env"
if (-not $env:NEUROGATE_PORT -and (Test-Path $envFile)) {
    $m = Select-String -Path $envFile -Pattern '^NEUROGATE_PORT=(\d+)' | Select-Object -First 1
    if ($m) { $Port = $m.Matches[0].Groups[1].Value }
}
$ours = $false
try { $ours = (Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2 -UseBasicParsing).ok } catch {}
Stop-ScheduledTask -TaskName "neurogate" -ErrorAction SilentlyContinue
if ($ours) {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep 1
}

Say "3/6 Зависимости"
& $Uv sync --frozen
if ($LASTEXITCODE -ne 0) { throw "Не установились зависимости (uv sync). Закройте программы neurogate и запустите команду ещё раз." }
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
if (-not (Test-Path "config.yaml")) { Copy-Item "config.yaml.example" "config.yaml" }

# Порт занят чужой программой (не нашим прошлым запуском) — берём следующий свободный.
function PortBusy($p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }
if ((PortBusy $Port) -and -not $ours) {
    foreach ($p in ([int]$Port + 1)..([int]$Port + 20)) {
        if (-not (PortBusy $p)) { Write-Host "Порт $Port занят другой программой — беру $p."; $Port = "$p"; break }
    }
}
# .env в UTF-8 без BOM: PS 5.1 по умолчанию читает его как cp1251, а пишет с BOM — комментарии портились
$envPath = Join-Path $Dir ".env"
$envText = [IO.File]::ReadAllText($envPath, [Text.Encoding]::UTF8)
if ($envText -match "(?m)^NEUROGATE_PORT=") { $envText = $envText -replace "(?m)^NEUROGATE_PORT=.*", "NEUROGATE_PORT=$Port" }
else { $envText += "`nNEUROGATE_PORT=$Port`n" }
[IO.File]::WriteAllText($envPath, $envText, (New-Object Text.UTF8Encoding $false))
$env:NEUROGATE_PORT = $Port

if ($env:NEUROGATE_CODE) {
    Say "4/6 Ключи из Telegram-бота"
    & $Uv run neurogate import $env:NEUROGATE_CODE --no-restart
    if ($LASTEXITCODE -ne 0) { Write-Host "Ключи по коду не забрались. Можно ввести их вручную: neurogate setup" }
} else {
    Say "4/6 Ключи нейросетей (можно пропускать и вернуться позже: neurogate setup)"
    if ([Console]::IsInputRedirected) {
        Write-Host "Нет интерактивного терминала — добавьте ключи потом: neurogate setup"
    } else {
        & $Uv run neurogate setup
    }
}

Say "5/6 Автозапуск сервера при входе в Windows"
# pythonw — без окна: раньше задача открывала чёрную консоль cmd, и закрыть её значило убить
# сервер. Вывод сервера модуль neurogate.background сам пишет в neurogate.log.
$pyw = Join-Path $Dir ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pyw)) { $pyw = Join-Path $Dir ".venv\Scripts\python.exe" }
$pyArgs = "-X utf8 -m neurogate.background"
Remove-Item (Join-Path $Dir "neurogate-serve.cmd") -ErrorAction SilentlyContinue

$started = $false
try {
    $action  = New-ScheduledTaskAction -Execute $pyw -Argument $pyArgs -WorkingDirectory $Dir
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0
    Register-ScheduledTask -TaskName "neurogate" -Action $action -Trigger $trigger -Settings $settings -Force -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName "neurogate" -ErrorAction Stop
    $started = $true
} catch {
    # Планировщик закрыт политикой компьютера — ярлык в «Автозагрузке» прав администратора не требует.
    Write-Host "Планировщик задач недоступен ($($_.Exception.Message)) — ставлю ярлык в автозагрузку." -ForegroundColor Yellow
    try {
        $lnk = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath("Startup")) "neurogate.lnk"))
        $lnk.TargetPath = $pyw; $lnk.Arguments = $pyArgs; $lnk.WorkingDirectory = $Dir; $lnk.WindowStyle = 7
        $lnk.Save()
    } catch { Write-Host "Автозапуск не включился. После перезагрузки компьютера запускайте: neurogate serve" }
}

function WaitHealth($sec) {
    for ($i = 0; $i -lt $sec; $i++) {
        try { Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2 | Out-Null; Write-Host ""; return $true }
        catch { Write-Host -NoNewline "."; Start-Sleep 1 }
    }
    Write-Host ""
    return $false
}

$ok = $false
if ($started) { Write-Host -NoNewline "Жду, пока сервер ответит "; $ok = WaitHealth 30 }
if (-not $ok) {
    # Задача не стартовала или не поднялась (антивирус, политика) — запускаем сервер напрямую.
    Write-Host -NoNewline "Запускаю сервер напрямую "
    Start-Process -FilePath $pyw -ArgumentList $pyArgs -WorkingDirectory $Dir -WindowStyle Hidden
    $ok = WaitHealth 30
}
if ($ok) { Write-Host "Сервер работает: http://127.0.0.1:$Port/dashboard" -ForegroundColor Green }
else {
    Write-Host "Сервер не ответил. Последние строки лога $Dir\neurogate.log:" -ForegroundColor Yellow
    Get-Content (Join-Path $Dir "neurogate.log") -Tail 15 -ErrorAction SilentlyContinue
    Write-Host "Пришлите этот вывод или запустите: neurogate doctor"
}

# OpenCode ставим сами и без вопросов (/S) — ученику не надо ничего скачивать и запускать.
$ocPaths = @("$env:LOCALAPPDATA\Programs\OpenCode\OpenCode.exe", "$env:ProgramFiles\OpenCode\OpenCode.exe")
if (-not ($ocPaths | Where-Object { Test-Path $_ })) {
    Say "Приложение OpenCode (~260 МБ, 1–3 минуты)"
    $ocArch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "windows-aarch64-nsis" } else { "windows-x64-nsis" }
    $ocUrl = "https://opencode.ai/download/stable/$ocArch"
    $ocExe = Join-Path $env:TEMP "OpenCode-Setup.exe"
    try {
        Invoke-WebRequest -UseBasicParsing $ocUrl -OutFile $ocExe
        Start-Process $ocExe -ArgumentList "/S" -Wait
        if ($ocPaths | Where-Object { Test-Path $_ }) { Write-Host "OpenCode установлен." }
        else { Write-Host "Открываю установщик OpenCode — нажмите «Установить»."; Start-Process $ocExe }
    } catch {
        Write-Host "OpenCode не скачался — скачайте сами: $ocUrl"
    }
}

Say "6/6 Подключение программ"
# .cmd читается в кодировке консоли — кириллицу из имени пользователя заменяем на %USERPROFILE%.
function CmdPath($p) { if ($p.StartsWith($HOME, [StringComparison]::OrdinalIgnoreCase)) { "%USERPROFILE%" + $p.Substring($HOME.Length) } else { $p } }
$cmdDir = CmdPath $Dir
@"
@echo off
setlocal
set PYTHONUTF8=1
set NEUROGATE_CALLER_DIR=%CD%
cd /d "$cmdDir"
if exist "$cmdDir\.venv\Scripts\neurogate.exe" ("$cmdDir\.venv\Scripts\neurogate.exe" %*) else ("$(CmdPath $Uv)" run neurogate %*)
"@ | Set-Content -Encoding ASCII (Join-Path $Bin "neurogate.cmd")
# То же для Git Bash (в нём работает Claude Code на Windows): .cmd оттуда по имени не находится.
# Сразу .exe, без cmd.exe — многострочные задачи доходят целиком. $USERPROFILE, а не $HOME:
# HOME в Git Bash часто переопределяют под git/ssh.
$shDir = if ($Dir.StartsWith($HOME, [StringComparison]::OrdinalIgnoreCase)) { '$USERPROFILE' + $Dir.Substring($HOME.Length).Replace('\', '/') } else { $Dir.Replace('\', '/') }
$sh = "#!/bin/sh`nexport PYTHONUTF8=1`nNEUROGATE_CALLER_DIR=`"`$(pwd -W 2>/dev/null || pwd)`"`nexport NEUROGATE_CALLER_DIR`ncd `"$shDir`" || exit 1`n[ -x ./.venv/Scripts/neurogate.exe ] || exec uv run neurogate `"`$@`"`nexec ./.venv/Scripts/neurogate.exe `"`$@`"`n"
[IO.File]::WriteAllText((Join-Path $Bin "neurogate"), $sh, (New-Object Text.UTF8Encoding $false))
& $Uv run neurogate connect opencode
& $Uv run neurogate connect claude-code
& $Uv run neurogate connect codex
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "Claude Code не найден. Поставить: irm https://claude.ai/install.ps1 | iex"
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$Bin*") {
    [Environment]::SetEnvironmentVariable("Path", "$Bin;$userPath", "User")
    Write-Host "Папка $Bin добавлена в PATH — откройте новое окно терминала."
}

Write-Host @"

ACCESS GRANTED. Всё бесплатно, подписки не нужны.

  * Откройте приложение OpenCode. Один раз подключите neurogate:
     список моделей -> «+» -> neurogate (бесплатно) -> вставьте ключ выше. Пишите задачу.
  Панель и тестовый чат:   http://127.0.0.1:$Port/dashboard
  Claude Code в терминале: claude-free
  Codex бесплатно:         codex-free
  Добавить ещё ключи:      neurogate setup
  Проверить ключи:         neurogate keys
  VS Code (Cline и др.):   neurogate connect cline   (или continue, cursor)
  Перезапустить сервер:    neurogate restart   (setup делает это сам)
  Что-то не так?           neurogate doctor
  Инструкция:              https://neurogate.nurtech.dev
"@
Pop-Location
}
