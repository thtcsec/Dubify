@echo off
echo Starting Dubify Dev Stack...

:: Start Backend
start cmd /k "echo Starting Backend... && cd backend && if exist .venv\Scripts\activate ( call .venv\Scripts\activate && .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload ) else ( echo ERROR: Virtual environment not found! && pause )"

:: Start Frontend
start cmd /k "echo Starting Frontend... && cd frontend && if exist node_modules ( pnpm dev ) else ( echo ERROR: node_modules not found! && pause )"

echo Dubify is launching in separate windows!
pause
