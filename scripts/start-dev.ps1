$ErrorActionPreference = "Stop"
Write-Host "Starting MihiMura backend and frontend..."
Start-Process powershell -ArgumentList '-NoExit','-Command','cd "'+(Resolve-Path "$PSScriptRoot\..\mihimura-backend")+'"; uv sync; uv run uvicorn app.main:app --reload --port 8000'
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList '-NoExit','-Command','cd "'+(Resolve-Path "$PSScriptRoot\..\mihimura-web")+'"; npm.cmd install; npm.cmd run dev'
Write-Host "Backend: http://127.0.0.1:8000/docs"
Write-Host "Frontend: http://localhost:5173"
