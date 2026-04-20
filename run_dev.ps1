Write-Host "Starting Dubify Dev Stack..." -ForegroundColor Cyan

# Start Backend
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Backend...' -ForegroundColor Green; cd backend; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --reload"

# Start Frontend
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Frontend...' -ForegroundColor Yellow; cd frontend; pnpm dev"

Write-Host "Dubify is launching in separate PowerShell windows!" -ForegroundColor Cyan
