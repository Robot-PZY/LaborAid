# LaborAid local dev ports (avoid conflict with other Vite/FastAPI projects on 5173/8000)
$ErrorActionPreference = 'SilentlyContinue'

$FrontendPort = 5320
$BackendPort = 8010

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backend = Join-Path $root 'LaborAid\backend'
$frontend = Join-Path $root 'LaborAid\frontend'

Write-Host "Cleaning LaborAid ports only ($FrontendPort / $BackendPort)..."
foreach ($port in $FrontendPort, $BackendPort) {
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
Start-Sleep -Seconds 2

Write-Host "Starting backend http://127.0.0.1:$BackendPort"
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$backend'; python -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort --reload"
)

Start-Sleep -Seconds 3

Write-Host "Starting frontend http://127.0.0.1:$FrontendPort"
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$frontend'; npm run dev"
)

Start-Sleep -Seconds 4
Start-Process "http://127.0.0.1:$FrontendPort/"
Write-Host "Done. LaborAid: http://127.0.0.1:$FrontendPort (API :$BackendPort)"
