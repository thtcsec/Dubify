@echo off
echo Starting Dubify Dev Stack...

:: Start Backend
start cmd /k "echo Starting Backend... && cd backend && venv\Scripts\activate && uvicorn app.main:app --reload"

:: Start Frontend
start cmd /k "echo Starting Frontend... && cd frontend && pnpm dev"

echo Dubify is launching in separate windows!
pause
