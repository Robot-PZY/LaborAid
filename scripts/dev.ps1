# LaborAid local dev ports (avoid conflict with other Vite/FastAPI projects on 5173/8000)
$ErrorActionPreference = 'SilentlyContinue'

$FrontendPort = 5320
$BackendPort = 8010

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backend = Join-Path $root 'LaborAid\backend'
$frontend = Join-Path $root 'LaborAid\frontend'

function Test-PortListening([int]$Port) {
  return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-ServiceReady {
  param(
    [string]$Label,
    [scriptblock]$Test,
    [int]$MaxSeconds = 90
  )
  $deadline = (Get-Date).AddSeconds($MaxSeconds)
  while ((Get-Date) -lt $deadline) {
    if (& $Test) {
      Write-Host "  OK $Label"
      return $true
    }
    Start-Sleep -Seconds 2
  }
  Write-Host "  FAIL $Label (timeout ${MaxSeconds}s)"
  return $false
}

Write-Host "Cleaning LaborAid ports only ($FrontendPort / $BackendPort)..."
foreach ($port in $FrontendPort, $BackendPort) {
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
Start-Sleep -Seconds 2

Write-Host "Starting backend http://127.0.0.1:$BackendPort ..."
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$backend'; Write-Host 'LaborAid Backend :$BackendPort'; python -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort --reload"
)

Write-Host "Waiting for backend (first start may take 30-60s)..."
$backendOk = Wait-ServiceReady -Label "backend /health" -MaxSeconds 90 -Test {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/health" -UseBasicParsing -TimeoutSec 5
    return $r.StatusCode -eq 200
  } catch { return $false }
}

Write-Host "Starting frontend http://127.0.0.1:$FrontendPort ..."
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$frontend'; Write-Host 'LaborAid Frontend :$FrontendPort'; npm run dev"
)

Write-Host "Waiting for frontend..."
$frontendOk = Wait-ServiceReady -Label "frontend" -MaxSeconds 60 -Test {
  Test-PortListening $FrontendPort
}

if ($backendOk -and $frontendOk) {
  Start-Process "http://127.0.0.1:$FrontendPort/login"
  Write-Host ""
  Write-Host "Done. User: http://127.0.0.1:$FrontendPort  Admin: http://127.0.0.1:$FrontendPort/login?portal=admin"
  Write-Host "Default admin: Admin / 123456  (or admin@laboraid.local / 123456)"
} else {
  Write-Host ""
  Write-Host "WARNING: Service not ready. Login will fail until BOTH windows show no errors."
  if (-not $backendOk) { Write-Host "  - Check the Backend PowerShell window (python/uvicorn errors?)" }
  if (-not $frontendOk) { Write-Host "  - Check the Frontend PowerShell window (npm run dev errors?)" }
}

Write-Host "API docs: http://127.0.0.1:$BackendPort/docs"
