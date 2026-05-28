# 启动 LaborAid 开发环境（单实例：前端 5173 + 后端 8000）
$ErrorActionPreference = 'SilentlyContinue'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backend = Join-Path $root 'LaborAid\backend'
$frontend = Join-Path $root 'LaborAid\frontend'

Write-Host '清理旧进程 (5173/5174/5175/8000)...'
foreach ($port in 5173, 5174, 5175, 8000) {
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
Start-Sleep -Seconds 2

Write-Host '启动后端 http://127.0.0.1:8000'
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$backend'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)

Start-Sleep -Seconds 3

Write-Host '启动前端 http://127.0.0.1:5173'
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$frontend'; npm run dev"
)

Start-Sleep -Seconds 4
Start-Process 'http://127.0.0.1:5173/'
Write-Host '完成。请使用 http://127.0.0.1:5173 （不要用 5174/5175）'
