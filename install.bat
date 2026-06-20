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
:: PowerShell script starts on line 11 (more +6 skips lines 1-6 = header)
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

# ── 2. Install UE4SS (skip if already present) ───────────────────────────────
if (Test-Path (Join-Path $gamePath 'UE4SS.dll')) {
    Write-OK 'UE4SS already installed'
} else {
    Write-Step 'Downloading UE4SS...'
    $ue4ssApi   = Invoke-RestMethod 'https://api.github.com/repos/UE4SS-RE/RE-UE4SS/releases/latest' -Headers $headers
    $ue4ssAsset = $ue4ssApi.assets |
        Where-Object { $_.name -match '\.zip$' -and $_.name -notmatch 'debug|[Ss]ource' } |
        Select-Object -First 1
    if (-not $ue4ssAsset) { Write-Fail 'Could not find UE4SS zip in the latest release.' }

    $ue4ssZip = Join-Path $env:TEMP 'ue4ss.zip'
    Invoke-WebRequest -Uri $ue4ssAsset.browser_download_url -OutFile $ue4ssZip -Headers $headers
    Expand-Archive -Path $ue4ssZip -DestinationPath $gamePath -Force
    Remove-Item $ue4ssZip -Force
    Write-OK "UE4SS $($ue4ssApi.tag_name) installed"
}

# ── 3. Fetch DiscoFlow release ────────────────────────────────────────────────
Write-Step 'Fetching DiscoFlow release...'
$dfApi        = Invoke-RestMethod "https://api.github.com/repos/$REPO/releases/latest" -Headers $headers
$backendAsset = $dfApi.assets | Where-Object { $_.name -eq 'discoflow-backend.exe' } | Select-Object -First 1
$modAsset     = $dfApi.assets | Where-Object { $_.name -eq 'mod.zip' }              | Select-Object -First 1
if (-not $backendAsset) { Write-Fail "discoflow-backend.exe not found in release $($dfApi.tag_name)" }
if (-not $modAsset)     { Write-Fail "mod.zip not found in release $($dfApi.tag_name)" }

# ── 4. Install backend ────────────────────────────────────────────────────────
Write-Step 'Installing backend...'
New-Item -ItemType Directory -Path $DEST_DIR -Force | Out-Null
$backendDst = Join-Path $DEST_DIR 'discoflow-backend.exe'
Invoke-WebRequest -Uri $backendAsset.browser_download_url -OutFile $backendDst -Headers $headers
Write-OK "Backend: $backendDst"

# ── 5. Install mod ────────────────────────────────────────────────────────────
Write-Step 'Installing mod...'
$modZip  = Join-Path $env:TEMP 'discoflow-mod.zip'
$modsDir = Join-Path $gamePath 'Mods\DiscoFlow'
Invoke-WebRequest -Uri $modAsset.browser_download_url -OutFile $modZip -Headers $headers
if (Test-Path $modsDir) { Remove-Item $modsDir -Recurse -Force }
New-Item -ItemType Directory -Path $modsDir -Force | Out-Null
Expand-Archive -Path $modZip -DestinationPath $modsDir -Force
Remove-Item $modZip -Force
Write-OK "Mod: $modsDir"

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ''
Write-Host '  All done!' -ForegroundColor Green
Write-Host '  Launch Dead as Disco. DiscoFlow starts automatically.' -ForegroundColor White
Write-Host ''
