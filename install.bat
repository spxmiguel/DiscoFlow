@echo off
:: DiscoFlow Installer
:: Extracts the PowerShell script below the header and runs it
more +13 "%~f0" > "%TEMP%\discoflow_install.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\discoflow_install.ps1"
set "EC=%ERRORLEVEL%"
del "%TEMP%\discoflow_install.ps1" 2>nul
if %EC% neq 0 ( echo. & echo Installation failed. See error above. & pause & exit /b 1 )
pause
exit /b 0
:: -----------------------------------------------------------------------
:: PowerShell script starts on line 14 (more +13 skips lines 1-13)
:: -----------------------------------------------------------------------
$ErrorActionPreference = 'Stop'
$REPO     = 'spxmiguel/DiscoFlow'
$DEST_DIR = Join-Path $env:LOCALAPPDATA 'DiscoFlow'

function Write-Step { param($msg) Write-Host "`n[DiscoFlow] $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host "  OK: $msg"        -ForegroundColor Green }
function Write-Fail { param($msg) Write-Host "`n  ERROR: $msg`n" -ForegroundColor Red; exit 1 }

Write-Host ''
Write-Host '  DiscoFlow Installer' -ForegroundColor Magenta
Write-Host '  Dead as Disco - Music Integration Mod'
Write-Host ''

# ── 1. Find Dead as Disco ─────────────────────────────────────────────────────
Write-Step 'Looking for Dead as Disco...'

$steamRoot = $null
foreach ($rp in @('HKLM:\SOFTWARE\WOW6432Node\Valve\Steam','HKLM:\SOFTWARE\Valve\Steam','HKCU:\SOFTWARE\Valve\Steam')) {
    try { $steamRoot = (Get-ItemProperty $rp -ErrorAction Stop).InstallPath; break } catch {}
}
if (-not $steamRoot) { Write-Fail 'Steam not found. Install Steam and launch it at least once.' }

$libraries = @(Join-Path $steamRoot 'steamapps')
$vdf = Join-Path $steamRoot 'steamapps\libraryfolders.vdf'
if (Test-Path $vdf) {
    Select-String -Path $vdf -Pattern '"path"' | ForEach-Object {
        if ($_.Line -match '"path"\s+"(.+?)"') {
            $lib = Join-Path ($Matches[1] -replace '\\\\','\\') 'steamapps'
            if (Test-Path $lib) { $libraries += $lib }
        }
    }
}

$gamePath = $null
foreach ($lib in $libraries) {
    $c = Join-Path $lib 'common\Dead as Disco'
    if (Test-Path $c) { $gamePath = $c; break }
}
if (-not $gamePath) { Write-Fail 'Dead as Disco not found. Make sure the game is installed on Steam.' }
Write-OK $gamePath

$headers = @{ 'User-Agent' = 'DiscoFlow-Installer' }

# Pagoda.exe is a thin launcher — real UE5 game is PagodaSteam-Win64-Shipping.exe
# UE4SS must live next to the shipping exe in Pagoda\Binaries\Win64\
$binDir   = Join-Path $gamePath 'Pagoda\Binaries\Win64'
$ue4ssDir = Join-Path $binDir 'ue4ss'

# ── 2. Install UE4SS experimental-latest ──────────────────────────────────────
if (Test-Path (Join-Path $ue4ssDir 'UE4SS.dll')) {
    Write-OK 'UE4SS already installed'
} else {
    Write-Step 'Downloading UE4SS (experimental)...'
    $ue4ssApi   = Invoke-RestMethod 'https://api.github.com/repos/UE4SS-RE/RE-UE4SS/releases/tags/experimental-latest' -Headers $headers
    $ue4ssAsset = $ue4ssApi.assets |
        Where-Object { $_.name -match '^UE4SS.*\.zip$' -and $_.name -notmatch 'DEV|debug' } |
        Select-Object -First 1
    if (-not $ue4ssAsset) { Write-Fail 'Could not find UE4SS zip in experimental-latest release.' }

    $ue4ssZip = Join-Path $env:TEMP 'ue4ss.zip'
    $ue4ssTmp = Join-Path $env:TEMP 'ue4ss_extract'
    Invoke-WebRequest -Uri $ue4ssAsset.browser_download_url -OutFile $ue4ssZip -Headers $headers
    if (Test-Path $ue4ssTmp) { Remove-Item $ue4ssTmp -Recurse -Force }
    Expand-Archive -Path $ue4ssZip -DestinationPath $ue4ssTmp -Force
    Remove-Item $ue4ssZip -Force

    # New structure: dwmapi.dll in binDir, ue4ss/ subfolder contains UE4SS.dll + settings + Mods/
    Copy-Item (Join-Path $ue4ssTmp 'dwmapi.dll') $binDir -Force
    New-Item -ItemType Directory -Path $ue4ssDir -Force | Out-Null
    Copy-Item (Join-Path $ue4ssTmp 'ue4ss\UE4SS.dll')          $ue4ssDir -Force
    Copy-Item (Join-Path $ue4ssTmp 'ue4ss\UE4SS-settings.ini') $ue4ssDir -Force

    Remove-Item $ue4ssTmp -Recurse -Force -ErrorAction SilentlyContinue
    Write-OK "UE4SS installed to Pagoda\Binaries\Win64\ue4ss\"
}

# ── 3. Escolha dos componentes ────────────────────────────────────────────────
Write-Host ''
Write-Host '  Componentes disponiveis:' -ForegroundColor Yellow
Write-Host '    [1] Biblioteca Manual  — app no desktop, adicione musicas do seu PC'
Write-Host '    [2] Automatico         — Spotify / Deezer (requer app instalado)'
Write-Host '    [3] Ambos              — recomendado' -ForegroundColor Green
Write-Host ''
$choice = Read-Host '  Escolha (1 / 2 / 3) [padrao: 3]'
if ($choice -eq '') { $choice = '3' }
if ($choice -notin @('1','2','3')) { Write-Fail "Opcao invalida: $choice" }

$installManual  = $choice -in @('1','3')
$installBackend = $choice -in @('2','3')

Write-Host ''
if ($installManual)  { Write-OK 'Biblioteca Manual sera instalada' }
if ($installBackend) { Write-OK 'Integracao automatica sera instalada' }

# ── 4. Fetch DiscoFlow release ────────────────────────────────────────────────
Write-Step 'Buscando release DiscoFlow...'
$dfApi    = Invoke-RestMethod "https://api.github.com/repos/$REPO/releases/latest" -Headers $headers
$modAsset = $dfApi.assets | Where-Object { $_.name -eq 'mod.zip' } | Select-Object -First 1
if (-not $modAsset) { Write-Fail "mod.zip nao encontrado na release $($dfApi.tag_name)" }

New-Item -ItemType Directory -Path $DEST_DIR -Force | Out-Null

# ── 4a. Install manual app ────────────────────────────────────────────────────
if ($installManual) {
    $manualAsset = $dfApi.assets | Where-Object { $_.name -eq 'discoflow-manual.exe' } | Select-Object -First 1
    if (-not $manualAsset) { Write-Fail "discoflow-manual.exe nao encontrado na release $($dfApi.tag_name)" }
    Write-Step 'Instalando app Biblioteca Manual...'
    $manualDst = Join-Path $DEST_DIR 'discoflow-manual.exe'
    Invoke-WebRequest -Uri $manualAsset.browser_download_url -OutFile $manualDst -Headers $headers
    Write-OK "Manual app: $manualDst"

    # create desktop shortcut
    try {
        $wsh  = New-Object -ComObject WScript.Shell
        $link = $wsh.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'DiscoFlow.lnk'))
        $link.TargetPath = $manualDst
        $link.Save()
        Write-OK 'Atalho criado na Area de Trabalho'
    } catch {}
}

# ── 4b. Install streaming backend ─────────────────────────────────────────────
if ($installBackend) {
    $backendAsset = $dfApi.assets | Where-Object { $_.name -eq 'discoflow-backend.exe' } | Select-Object -First 1
    if (-not $backendAsset) { Write-Fail "discoflow-backend.exe nao encontrado na release $($dfApi.tag_name)" }
    Write-Step 'Instalando backend de streaming...'
    $backendDst = Join-Path $DEST_DIR 'discoflow-backend.exe'
    Invoke-WebRequest -Uri $backendAsset.browser_download_url -OutFile $backendDst -Headers $headers
    Write-OK "Backend: $backendDst"
}

# ── 5. Install mod + UE4SS signatures ────────────────────────────────────────
Write-Step 'Installing mod...'
$modZip    = Join-Path $env:TEMP 'discoflow-mod.zip'
$modTmp    = Join-Path $env:TEMP 'discoflow-mod-extract'
$modsDir   = Join-Path $ue4ssDir 'Mods\DiscoFlow'
$sigDir    = Join-Path $ue4ssDir 'UE4SS_Signatures'
Invoke-WebRequest -Uri $modAsset.browser_download_url -OutFile $modZip -Headers $headers
if (Test-Path $modTmp) { Remove-Item $modTmp -Recurse -Force }
Expand-Archive -Path $modZip -DestinationPath $modTmp -Force
Remove-Item $modZip -Force

if (Test-Path $modsDir) { Remove-Item $modsDir -Recurse -Force }
New-Item -ItemType Directory -Path $modsDir -Force | Out-Null
Copy-Item (Join-Path $modTmp 'Scripts')     $modsDir -Recurse -Force
Copy-Item (Join-Path $modTmp 'enabled.txt') $modsDir -Force

New-Item -ItemType Directory -Path $sigDir -Force | Out-Null
if (Test-Path (Join-Path $modTmp 'UE4SS_Signatures')) {
    Copy-Item (Join-Path $modTmp 'UE4SS_Signatures\*') $sigDir -Force
}
Remove-Item $modTmp -Recurse -Force -ErrorAction SilentlyContinue
Write-OK "Mod: $modsDir"
Write-OK "Signatures: $sigDir"

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ''
Write-Host '  Tudo pronto!' -ForegroundColor Green
if ($installManual) {
    Write-Host '  1. Abra o DiscoFlow pelo atalho na Area de Trabalho.' -ForegroundColor White
    Write-Host '     Adicione musicas e feche o app.' -ForegroundColor White
}
if ($installBackend) {
    Write-Host '  - Abra o Spotify ou Deezer antes de iniciar o jogo.' -ForegroundColor White
}
Write-Host '  - Inicie Dead as Disco. No Free Play, o menu DiscoFlow aparece automaticamente.' -ForegroundColor White
Write-Host ''
