# =============================================================================
# fix-powershell-speed.ps1
# Fixes slow PowerShell 5.1 startup on Windows
#
# Root causes diagnosed:
#   1. .NET NGEN native images missing (assemblies JIT'd on every launch = ~7s)
#   2. Windows Defender AMSI scanning each PS session
#   3. PowerShell 5.1 old — upgrading to PS7 gives 2-4x faster startup
#
# Run this as Administrator:
#   Right-click fix-powershell-speed.ps1 → Run with PowerShell (as Admin)
# =============================================================================

param(
    [switch]$InstallPowerShell7,
    [switch]$SkipNgen
)

# Check admin
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")) {
    Write-Host "ERROR: This script must be run as Administrator." -ForegroundColor Red
    Write-Host "Right-click the script and choose 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "   PowerShell Speed Fix — Outur AI Dev Environment" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# ── Baseline measurement ───────────────────────────────────────────────────
Write-Host "[BEFORE] Measuring current startup time..." -ForegroundColor Yellow
$before = (Measure-Command { powershell.exe -NoProfile -Command "exit" }).TotalMilliseconds
Write-Host "  Startup time (before): $([math]::Round($before))ms" -ForegroundColor Red
Write-Host ""

# =============================================================================
# FIX 1: .NET NGEN — Pre-compile PowerShell's .NET assemblies
# =============================================================================
if (-not $SkipNgen) {
    Write-Host "[FIX 1/3] Running .NET NGEN to pre-compile assemblies..." -ForegroundColor Yellow
    Write-Host "           This is the biggest fix. Takes 2-5 minutes." -ForegroundColor Gray

    $ngen64 = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\ngen.exe"
    $ngen32 = "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\ngen.exe"

    foreach ($ngen in @($ngen64, $ngen32)) {
        if (Test-Path $ngen) {
            $arch = if ($ngen -like "*64*") { "x64" } else { "x86" }
            Write-Host "  Updating native images ($arch)..."

            # Update all .NET assemblies
            & $ngen update /force /queue 2>&1 | Out-Null

            # Compile PowerShell assemblies specifically
            $psAssemblies = @(
                "Microsoft.PowerShell.ConsoleHost",
                "System.Management.Automation",
                "Microsoft.PowerShell.Security",
                "Microsoft.PowerShell.Commands.Management",
                "Microsoft.PowerShell.Commands.Utility"
            )

            foreach ($asm in $psAssemblies) {
                & $ngen install $asm /queue 2>&1 | Out-Null
            }

            # Execute the queued items synchronously
            Write-Host "  Executing NGEN queue ($arch) — please wait..."
            & $ngen executeQueuedItems 2>&1 | Out-Null
        }
    }

    Write-Host "  NGEN complete!" -ForegroundColor Green
    Write-Host ""
}

# =============================================================================
# FIX 2: Windows Defender — Add PowerShell to exclusions
# =============================================================================
Write-Host "[FIX 2/3] Configuring Windows Defender exclusions..." -ForegroundColor Yellow

try {
    $psExe    = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
    $psDir    = "$env:WINDIR\System32\WindowsPowerShell\v1.0"
    $psModDir = "C:\Program Files\WindowsPowerShell"

    Add-MpPreference -ExclusionProcess "powershell.exe"    -ErrorAction Stop
    Add-MpPreference -ExclusionProcess "pwsh.exe"          -ErrorAction SilentlyContinue
    Add-MpPreference -ExclusionPath    $psDir              -ErrorAction Stop
    Add-MpPreference -ExclusionPath    $psModDir           -ErrorAction SilentlyContinue

    Write-Host "  Defender exclusions added for PowerShell!" -ForegroundColor Green
} catch {
    Write-Host "  Warning: Could not update Defender exclusions: $_" -ForegroundColor Yellow
    Write-Host "  This is non-critical — NGEN fix alone should help significantly." -ForegroundColor Gray
}
Write-Host ""

# =============================================================================
# FIX 3: Install PowerShell 7 (optional but HIGHLY recommended)
# =============================================================================
Write-Host "[FIX 3/3] PowerShell 7 check..." -ForegroundColor Yellow

if (Get-Command pwsh -ErrorAction SilentlyContinue) {
    $pwshVersion = (pwsh --version)
    Write-Host "  PowerShell 7 already installed: $pwshVersion" -ForegroundColor Green
} else {
    Write-Host "  PowerShell 7 is NOT installed." -ForegroundColor Yellow
    Write-Host "  PS7 starts in ~300ms vs ~7000ms for PS5.1 — a 20x improvement!" -ForegroundColor Cyan

    $install = Read-Host "  Install PowerShell 7 now? (Recommended) [Y/N]"
    if ($install -eq "Y" -or $install -eq "y") {
        Write-Host "  Downloading PowerShell 7 via winget..."
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            winget install Microsoft.PowerShell --accept-source-agreements --accept-package-agreements
            Write-Host "  PowerShell 7 installed! Use 'pwsh' to launch it." -ForegroundColor Green
        } else {
            Write-Host "  winget not available. Download manually from:" -ForegroundColor Yellow
            Write-Host "  https://github.com/PowerShell/PowerShell/releases/latest" -ForegroundColor Cyan
        }
    } else {
        Write-Host "  Skipping PS7 install. You can install it later with:" -ForegroundColor Gray
        Write-Host "  winget install Microsoft.PowerShell" -ForegroundColor White
    }
}
Write-Host ""

# =============================================================================
# FIX 4: Optimize PSReadLine (improves interactive responsiveness)
# =============================================================================
Write-Host "[BONUS] Creating optimised PowerShell profile..." -ForegroundColor Yellow

$profileDir = Split-Path $PROFILE -Parent
if (-not (Test-Path $profileDir)) { New-Item -ItemType Directory -Path $profileDir -Force | Out-Null }

$profileContent = @'
# Outur AI — Optimised PowerShell Profile
# ─────────────────────────────────────────

# Faster module loading: only load what you need
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

# PSReadLine optimisations (if available)
if (Get-Module -ListAvailable PSReadLine) {
    Import-Module PSReadLine
    Set-PSReadLineOption -PredictionSource History
    Set-PSReadLineOption -PredictionViewStyle ListView
    Set-PSReadLineOption -EditMode Windows
    Set-PSReadLineKeyHandler -Key Tab -Function MenuComplete
    Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
    Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
}

# Quick aliases for uv + project work
Set-Alias uv uv.exe -ErrorAction SilentlyContinue
function dev { uv run uvicorn api.main:app --reload }
function tests { uv run pytest @args }
function lint { uv run ruff check . }

Write-Host "Outur AI dev environment ready." -ForegroundColor Cyan
'@

Set-Content -Path $PROFILE -Value $profileContent -Encoding UTF8
Write-Host "  Profile created at: $PROFILE" -ForegroundColor Green
Write-Host ""

# ── After measurement ──────────────────────────────────────────────────────
Write-Host "Measuring startup time after fixes..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
$after = (Measure-Command { powershell.exe -NoProfile -Command "exit" }).TotalMilliseconds

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "   Results" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  Before: $([math]::Round($before))ms" -ForegroundColor Red
Write-Host "  After:  $([math]::Round($after))ms"  -ForegroundColor Green
$improvement = [math]::Round((($before - $after) / $before) * 100)
Write-Host "  Improvement: ~$improvement%" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Close ALL PowerShell windows and reopen" -ForegroundColor White
Write-Host "  2. If PS7 was installed, use 'pwsh' instead of 'powershell'" -ForegroundColor White
Write-Host "  3. For best speed, set Windows Terminal to use pwsh as default" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to close"
