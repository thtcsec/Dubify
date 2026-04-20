Write-Host "Starting Dubify Dev Stack..." -ForegroundColor Cyan

# Start Backend
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Backend...' -ForegroundColor Green; cd backend; if (Test-Path '.\.venv\Scripts\Activate.ps1') { & .\.venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --reload } else { Write-Error 'Virtual environment not found! Run pip install -r requirements.txt first.' }"

# Start Frontend
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Frontend...' -ForegroundColor Yellow; cd frontend; if (Test-Path '.\node_modules') { pnpm dev } else { Write-Error 'node_modules not found! Run pnpm install first.' }"

Write-Host "Dubify is launching in separate PowerShell windows!" -ForegroundColor Cyan
