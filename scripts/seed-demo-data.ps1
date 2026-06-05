# 填充管理端演示数据（用户 / 案件 / 材料库等）
$Backend = Join-Path $PSScriptRoot "..\LaborAid\backend"
Set-Location $Backend
python scripts/seed_demo_users.py @args
