#!/usr/bin/env pwsh
# ─── Dubify Dev Stack Launcher ───────────────────────────────────────────────
# Starts: Backend (FastAPI) + Frontend (Vite) + optional Supertonic TTS server
#
# Usage:
#   ./run_dev.ps1              # Backend + Frontend only
#   ./run_dev.ps1 -WithTTS     # Also start Supertonic TTS server
#   ./run_dev.ps1 -SetupOnly   # Install deps without starting servers

param(
    [switch]$WithTTS,
    [switch]$SetupOnly,
    [switch]$Help
)

$ErrorActionPreference = "Continue"

function Write-Banner {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║        Dubify — AI Video Studio          ║" -ForegroundColor Cyan
    Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step($msg) { Write-Host "  → $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Info($msg) { Write-Host "  ℹ $msg" -ForegroundColor DarkGray }

if ($Help) {
    Write-Banner
    Write-Host "  Usage:" -ForegroundColor White
    Write-Host "    ./run_dev.ps1              Start Backend + Frontend"
    Write-Host "    ./run_dev.ps1 -WithTTS     Also start Supertonic TTS server"
    Write-Host "    ./run_dev.ps1 -SetupOnly   Install dependencies only"
    Write-Host ""
    Write-Host "  Services:" -ForegroundColor White
    Write-Host "    Backend:    http://localhost:8000  (FastAPI + Worker)"
    Write-Host "    Frontend:   http://localhost:5173  (Vite + React)"
    Write-Host "    TTS Server: http://localhost:7788  (Supertonic, optional)"
    Write-Host ""
    Write-Host "  Requirements:" -ForegroundColor White
    Write-Host "    - Python 3.11+ with venv in backend/.venv"
    Write-Host "    - Node.js 18+ with pnpm"
    Write-Host "    - FFmpeg in PATH"
    Write-Host "    - (Optional) pip install 'supertonic[serve]' for local TTS"
    Write-Host "    - (Optional) playwright install chromium for HTML scene render"
    Write-Host ""
    exit 0
}

Write-Banner

# ─── Check Prerequisites ─────────────────────────────────────────────────────

Write-Step "Checking prerequisites..."

# Check Python venv
$venvPython = "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Warn "Python venv not found at backend/.venv"
    Write-Info "Run: cd backend && python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
    if (-not $SetupOnly) { exit 1 }
}

# Check node_modules
if (-not (Test-Path "frontend\node_modules")) {
    Write-Warn "frontend/node_modules not found"
    Write-Info "Run: cd frontend && pnpm install"
    if (-not $SetupOnly) { exit 1 }
}

# Check FFmpeg
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Warn "FFmpeg not found in PATH — video processing will fail"
    Write-Info "Download: https://ffmpeg.org/download.html"
}

# Check .env
if (-not (Test-Path ".env")) {
    Write-Warn ".env file not found — copying from .env.example"
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Info "Created .env from .env.example — edit API keys as needed"
    }
}

if ($SetupOnly) {
    Write-Step "Setup check complete. Run without -SetupOnly to start servers."
    exit 0
}

# ─── Start Services ──────────────────────────────────────────────────────────

Write-Host ""
Write-Step "Launching services..."
Write-Host ""

# Backend
Write-Info "Starting Backend (FastAPI + Worker)..."
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", @"
`$Host.UI.RawUI.WindowTitle = 'Dubify Backend'
Write-Host '═══ Dubify Backend ═══' -ForegroundColor Green
Write-Host 'API: http://localhost:8000' -ForegroundColor DarkGray
Write-Host 'Docs: http://localhost:8000/docs' -ForegroundColor DarkGray
Write-Host ''
cd backend
. .\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"@

Start-Sleep -Seconds 1

# Frontend
Write-Info "Starting Frontend (Vite + React)..."
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", @"
`$Host.UI.RawUI.WindowTitle = 'Dubify Frontend'
Write-Host '═══ Dubify Frontend ═══' -ForegroundColor Yellow
Write-Host 'UI: http://localhost:5173' -ForegroundColor DarkGray
Write-Host ''
cd frontend
pnpm dev
"@

# Optional: Supertonic TTS Server
if ($WithTTS) {
    Start-Sleep -Seconds 1
    $supertonicAvailable = & $venvPython -c "import supertonic; print('ok')" 2>$null
    if ($supertonicAvailable -eq "ok") {
        Write-Info "Starting Supertonic TTS Server..."
        Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", @"
`$Host.UI.RawUI.WindowTitle = 'Dubify TTS (Supertonic)'
Write-Host '═══ Supertonic TTS Server ═══' -ForegroundColor Magenta
Write-Host 'Endpoint: http://localhost:7788' -ForegroundColor DarkGray
Write-Host 'OpenAI-compatible: /v1/audio/speech' -ForegroundColor DarkGray
Write-Host ''
cd backend
. .\.venv\Scripts\Activate.ps1
supertonic serve --host 127.0.0.1 --port 7788
"@
    } else {
        Write-Warn "Supertonic not installed. Run: pip install 'supertonic[serve]'"
        Write-Info "Skipping TTS server — app will use Edge-TTS (online) instead."
    }
}

# ─── Summary ─────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ┌─────────────────────────────────────────┐" -ForegroundColor Cyan
Write-Host "  │  Dubify is running!                      │" -ForegroundColor Cyan
Write-Host "  │                                         │" -ForegroundColor Cyan
Write-Host "  │  UI:      http://localhost:5173          │" -ForegroundColor White
Write-Host "  │  API:     http://localhost:8000          │" -ForegroundColor White
Write-Host "  │  Docs:    http://localhost:8000/docs     │" -ForegroundColor DarkGray
if ($WithTTS) {
Write-Host "  │  TTS:     http://localhost:7788          │" -ForegroundColor Magenta
}
Write-Host "  │                                         │" -ForegroundColor Cyan
Write-Host "  │  Close all windows to stop.             │" -ForegroundColor DarkGray
Write-Host "  └─────────────────────────────────────────┘" -ForegroundColor Cyan
Write-Host ""

# Optional: open browser
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"
