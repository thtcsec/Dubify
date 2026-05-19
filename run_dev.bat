@echo off
chcp 65001 >nul 2>&1
title Dubify Dev Launcher
echo.
echo   ========================================
echo        Dubify - AI Video Studio
echo   ========================================
echo.

:: Check Prerequisites
echo   [*] Checking prerequisites...

if not exist "backend\.venv\Scripts\python.exe" (
    echo   [!] Python venv not found at backend\.venv
    echo       Fix: cd backend ^& python -m venv .venv
    echo       Then: backend\.venv\Scripts\pip install -r backend\requirements.txt
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo   [!] frontend\node_modules not found
    echo       Fix: cd frontend ^& pnpm install
    pause
    exit /b 1
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo   [!] WARNING: FFmpeg not in PATH - video processing will fail
)

if not exist ".env" (
    if exist ".env.example" (
        echo   [*] Creating .env from .env.example...
        copy ".env.example" ".env" >nul
    )
)

:: Start Services
echo.
echo   [*] Launching services...
echo.

:: Backend
echo   [-] Starting Backend on http://localhost:8000 ...
start "Dubify-Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 2 /nobreak >nul

:: Frontend
echo   [-] Starting Frontend on http://localhost:5173 ...
start "Dubify-Frontend" cmd /k "cd /d %~dp0frontend && pnpm dev"

:: Optional TTS
if "%~1"=="--tts" (
    timeout /t 1 /nobreak >nul
    echo   [-] Starting Supertonic TTS on http://localhost:7788 ...
    start "Dubify-TTS" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && supertonic serve --host 127.0.0.1 --port 7788"
)

:: Summary
echo.
echo   ========================================
echo   Dubify is running!
echo.
echo     UI:   http://localhost:5173
echo     API:  http://localhost:8000
echo     Docs: http://localhost:8000/docs
if "%~1"=="--tts" echo     TTS:  http://localhost:7788
echo.
echo   Close the other windows to stop.
echo   ========================================
echo.

timeout /t 3 /nobreak >nul
start http://localhost:5173

pause
