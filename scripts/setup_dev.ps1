# Outur AI — Windows Dev Environment Setup
# =========================================
# Run this script once to bootstrap your local development environment.
#
# Usage:
#   .\scripts\setup_dev.ps1
#
# Requirements:
#   - Python 3.12+ on PATH
#   - uv installed (https://docs.astral.sh/uv/getting-started/installation/)
#   - Docker Desktop running (for PostgreSQL)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Outur AI — Dev Environment Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check uv ────────────────────────────────────────────────────────────
Write-Host "[1/6] Checking uv..." -ForegroundColor Yellow
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "     uv not found. Installing..." -ForegroundColor Red
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
} else {
    $uvVersion = (uv --version)
    Write-Host "     uv found: $uvVersion" -ForegroundColor Green
}

# ── 2. Create / sync virtual environment ───────────────────────────────────
Write-Host "[2/6] Syncing Python environment with uv..." -ForegroundColor Yellow
uv sync
Write-Host "     Virtual environment ready." -ForegroundColor Green

# ── 3. Copy .env if not exists ─────────────────────────────────────────────
Write-Host "[3/6] Setting up .env file..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "     .env created from .env.example — update your secrets!" -ForegroundColor Yellow
} else {
    Write-Host "     .env already exists — skipping." -ForegroundColor Green
}

# ── 4. Install pre-commit hooks ────────────────────────────────────────────
Write-Host "[4/6] Installing pre-commit hooks..." -ForegroundColor Yellow
uv run pre-commit install
Write-Host "     Pre-commit hooks installed." -ForegroundColor Green

# ── 5. Start Docker services ───────────────────────────────────────────────
Write-Host "[5/6] Starting Docker services (PostgreSQL)..." -ForegroundColor Yellow
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose up -d postgres
    Write-Host "     Waiting 5s for PostgreSQL to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    Write-Host "     PostgreSQL started." -ForegroundColor Green
} else {
    Write-Host "     Docker not found — skipping. Start PostgreSQL manually." -ForegroundColor Red
}

# ── 6. Run Alembic migrations ──────────────────────────────────────────────
Write-Host "[6/6] Running database migrations..." -ForegroundColor Yellow
uv run alembic upgrade head
Write-Host "     Migrations complete." -ForegroundColor Green

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Setup complete! Start the server with:" -ForegroundColor Cyan
Write-Host "  uv run uvicorn api.main:app --reload" -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
