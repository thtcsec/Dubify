@echo off
title Dubify Dev Launcher
echo.
echo   ╔══════════════════════════════════════════╗
echo   ║        Dubify — AI Video Studio          ║
echo   ╚══════════════════════════════════════════╝
echo.

:: ─── Check Prerequisites ─────────────────────────────────────────────────
echo   [*] Checking prerequisites...

if not exist "backend\.venv\Scripts\python.exe" (
    echo   [!] Python venv not found at backend/.venv
    echo       Run: cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo   [!] frontend/node_modules not found
    echo       Run: cd frontend ^&^& pnpm install
    pause
    exit /b 1
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo   [!] FFmpeg not found in PATH — video processing will fail
    echo       Download: https://ffmpeg.org/download.html
)

if not exist ".env" (
    echo   [!] .env not found — copying from .env.example
    if exist ".env.example" copy ".env.example" ".env" >nul
)

:: ─── Start Services ──────────────────────────────────────────────────────
echo.
echo   [*] Launching services...
echo.

:: Backend
echo   [-] Starting Backend (FastAPI)...
start "Dubify Backend" cmd /k "title Dubify Backend && echo === Dubify Backend === && echo API: http://localhost:8000 && echo. && cd backend && call .venv\Scripts\activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 2 /nobreak >nul

:: Frontend
echo   [-] Starting Frontend (Vite)...
start "Dubify Frontend" cmd /k "title Dubify Frontend && echo === Dubify Frontend === && echo UI: http://localhost:5173 && echo. && cd frontend && pnpm dev"

:: Optional: Supertonic TTS (if --tts flag passed)
if "%1"=="--tts" (
    timeout /t 1 /nobreak >nul
    echo   [-] Starting Supertonic TTS Server...
    start "Dubify TTS" cmd /k "title Dubify TTS && echo === Supertonic TTS === && echo Endpoint: http://localhost:7788 && echo. && cd backend && call .venv\Scripts\activate && supertonic serve --host 127.0.0.1 --port 7788"
)

:: ─── Summary ─────────────────────────────────────────────────────────────
echo.
echo   ┌─────────────────────────────────────────┐
echo   │  Dubify is running!                      │
echo   │                                         │
echo   │  UI:      http://localhost:5173          │
echo   │  API:     http://localhost:8000          │
echo   │  Docs:    http://localhost:8000/docs     │
if "%1"=="--tts" (
echo   │  TTS:     http://localhost:7788          │
)
echo   │                                         │
echo   │  Close all windows to stop.             │
echo   └─────────────────────────────────────────┘
echo.

:: Open browser after short delay
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo   Press any key to exit this launcher...
pause >nul
