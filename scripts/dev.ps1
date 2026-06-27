$ErrorActionPreference = 'Stop'

Start-Process python -ArgumentList '-m', 'uvicorn', 'backend.main:app', '--reload', '--host', '127.0.0.1', '--port', '8000' -WorkingDirectory $PSScriptRoot\.. -WindowStyle Hidden
Set-Location $PSScriptRoot\..\frontend
npm run dev
