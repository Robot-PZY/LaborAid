# 停止 LaborAid 本地开发服务（仅释放 5320 / 8010 端口）
$ErrorActionPreference = 'SilentlyContinue'

$FrontendPort = 5320
$BackendPort = 8010

Write-Host "Stopping LaborAid on ports $FrontendPort / $BackendPort ..."

foreach ($port in $FrontendPort, $BackendPort) {
  $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if (-not $conns) {
    Write-Host "  port $port : not running"
    continue
  }
  $conns | ForEach-Object {
    $proc = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
    if ($proc) {
      Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
      Write-Host "  port $port : stopped $($proc.ProcessName) (pid $($_.OwningProcess))"
    }
  }
}

Write-Host ""
Write-Host "Done."
