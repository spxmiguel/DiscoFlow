@echo off
setlocal enabledelayedexpansion
title DiscoFlow Installer

powershell -NoProfile -ExecutionPolicy Bypass -Command "& {

$ErrorActionPreference = 'Stop'
$REPO     = 'spxmiguel/DiscoFlow'
$DEST_DIR = Join-Path $env:LOCALAPPDATA 'DiscoFlow'

function Write-Step { param($msg) Write-Host \"`n[DiscoFlow] $msg\" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host \"  OK: $msg\" -ForegroundColor Green }
function Write-Fail { param($msg) Write-Host \"`n  ERROR: $msg\`n\" -ForegroundColor Red; exit 1 }

Write-Host ''
Write-Host '  DiscoFlow Installer' -ForegroundColor Magenta
Write-Host '  Dead as Disco - Music Integration Mod'
Write-Host ''

# ── 1. Find Dead as Disco ─────────────────────────────────────────────────────
Write-Step 'Looking for Dead as Disco...'

$steamRoot = $null
$regPaths = @(
    'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam',
    'HKLM:\SOFTWARE\Valve\Steam',
    'HKCU:\SOFTWARE\Valve\Steam'
)
foreach ($rp in $regPaths) {
    try { $steamRoot = (Get-ItemProperty $rp -ErrorAction Stop).InstallPath; break } catch {}
}
if (-not $steamRoot) { Write-Fail 'Steam not found. Install Steam and launch it at least once.' }

$libraries = @(Join-Path $steamRoot 'steamapps')
$vdf = Join-Path $steamRoot 'steamapps\libraryfolders.vdf'
if (Test-Path $vdf) {
    Select-String -Path $vdf -Pattern '\"path\"' | ForEach-Object {
        if (\$_.Line -match '\"path\"\s+\"(.+?)\"') {
            \$lib = Join-Path (\$Matches[1] -replace '\\\\\\\\','\\') 'steamapps'
            if (Test-Path \$lib) { \$libraries += \$lib }
        }
    }
}

\$gamePath = \$null
foreach (\$lib in \$libraries) {
    \$c = Join-Path \$lib 'common\Dead as Disco'
    if (Test-Path \$c) { \$gamePath = \$c; break }
}
if (-not \$gamePath) { Write-Fail 'Dead as Disco not found. Make sure the game is installed on Steam.' }
Write-OK \$gamePath

# Find Binaries\Win64
\$binDir = Get-ChildItem -Path \$gamePath -Recurse -Filter '*.exe' |
    Where-Object { \$_.Name -notmatch 'ninstall' } |
    Select-Object -First 1 |
    ForEach-Object { \$_.DirectoryName }
if (-not \$binDir) { Write-Fail 'Could not find game executable.' }

# ── 2. Download UE4SS ─────────────────────────────────────────────────────────
Write-Step 'Downloading UE4SS...'

\$ue4ssApi = Invoke-RestMethod 'https://api.github.com/repos/UE4SS-RE/RE-UE4SS/releases/latest' `
    -Headers @{UserAgent='DiscoFlow-Installer'}
\$ue4ssAsset = \$ue4ssApi.assets | Where-Object {
    \$_.name -match '\.zip$' -and \$_.name -notmatch 'debug' -and \$_.name -notmatch '[Ss]ource'
} | Select-Object -First 1
if (-not \$ue4ssAsset) { Write-Fail 'Could not find UE4SS zip in the latest release.' }

\$ue4ssZip = Join-Path \$env:TEMP 'ue4ss.zip'
Invoke-WebRequest -Uri \$ue4ssAsset.browser_download_url -OutFile \$ue4ssZip `
    -Headers @{UserAgent='DiscoFlow-Installer'}
Write-OK \"Downloaded \$(\$ue4ssAsset.name)\"

Write-Step 'Installing UE4SS...'
Expand-Archive -Path \$ue4ssZip -DestinationPath \$binDir -Force
Remove-Item \$ue4ssZip -Force
Write-OK \"Extracted to \$binDir\"

# ── 3. Get latest DiscoFlow release assets ────────────────────────────────────
Write-Step 'Fetching DiscoFlow release info...'

\$dfApi = Invoke-RestMethod \"https://api.github.com/repos/\$REPO/releases/latest\" `
    -Headers @{UserAgent='DiscoFlow-Installer'}
\$dfTag = \$dfApi.tag_name

\$backendAsset = \$dfApi.assets | Where-Object { \$_.name -eq 'discoflow-backend.exe' } | Select-Object -First 1
\$modAsset     = \$dfApi.assets | Where-Object { \$_.name -eq 'mod.zip' }              | Select-Object -First 1

if (-not \$backendAsset) { Write-Fail \"discoflow-backend.exe not found in release \$dfTag\" }
if (-not \$modAsset)     { Write-Fail \"mod.zip not found in release \$dfTag\" }

# ── 4. Download + install backend ─────────────────────────────────────────────
Write-Step 'Installing DiscoFlow backend...'

New-Item -ItemType Directory -Path \$DEST_DIR -Force | Out-Null
\$backendDst = Join-Path \$DEST_DIR 'discoflow-backend.exe'
Invoke-WebRequest -Uri \$backendAsset.browser_download_url -OutFile \$backendDst `
    -Headers @{UserAgent='DiscoFlow-Installer'}
Write-OK \"Backend installed to \$backendDst\"

# ── 5. Download + install mod ─────────────────────────────────────────────────
Write-Step 'Installing DiscoFlow mod...'

\$modZip  = Join-Path \$env:TEMP 'discoflow-mod.zip'
\$modsDir = Join-Path \$binDir 'Mods\DiscoFlow'
Invoke-WebRequest -Uri \$modAsset.browser_download_url -OutFile \$modZip `
    -Headers @{UserAgent='DiscoFlow-Installer'}
if (Test-Path \$modsDir) { Remove-Item \$modsDir -Recurse -Force }
Expand-Archive -Path \$modZip -DestinationPath \$modsDir -Force
Remove-Item \$modZip -Force
Write-OK \"Mod installed to \$modsDir\"

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ''
Write-Host '  All done!' -ForegroundColor Green
Write-Host '  Launch Dead as Disco. DiscoFlow starts automatically.' -ForegroundColor White
Write-Host ''

}"

if %ERRORLEVEL% neq 0 (
    echo.
    echo Installation failed. See error above.
    pause
    exit /b 1
)

pause
