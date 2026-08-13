$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\.."
$Backend = Join-Path $Root "mihimura-backend"
$Frontend = Join-Path $Root "mihimura-web"

Write-Host "Starting MihiMura v4 locally..."
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$Backend'; if (-not (Test-Path .venv)) { py -m venv .venv }; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; uvicorn app.main:app --reload --port 8000"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$Frontend'; npm.cmd install; npm.cmd run dev"
Write-Host "Backend: http://127.0.0.1:8000/docs"
Write-Host "Frontend: http://localhost:5173"
