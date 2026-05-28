# 劳权智助 · LaborAid 项目目录整理脚本
# 用法：关闭 Cursor / 停止 npm 与 uvicorn 后，在 PowerShell 中执行：
#   cd <仓库根目录>
#   .\scripts\normalize-project-layout.ps1

$ErrorActionPreference = 'Stop'

# 自动检测：脚本在 scripts/ 下时，项目根为上级；若在已扁平化的根目录则直接用
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path (Join-Path $scriptDir 'backend')) {
  $repoRoot = $scriptDir
} elseif (Test-Path (Join-Path (Split-Path $scriptDir -Parent) 'backend')) {
  $repoRoot = Split-Path $scriptDir -Parent
} else {
  $repoRoot = Split-Path $scriptDir -Parent
}

$inner = Join-Path $repoRoot 'LaborAid'
if (Test-Path $inner) {
  Write-Host ">> 合并嵌套目录: $inner -> $repoRoot"
  Get-ChildItem -LiteralPath $inner -Force | ForEach-Object {
    $dest = Join-Path $repoRoot $_.Name
    if (Test-Path $dest) {
      Write-Warning "已存在，跳过: $($_.Name)"
    } else {
      Move-Item -LiteralPath $_.FullName -Destination $repoRoot -Force
    }
  }
  if ((Get-ChildItem -LiteralPath $inner -Force | Measure-Object).Count -eq 0) {
    Remove-Item -LiteralPath $inner -Force -Recurse
    Write-Host ">> 已删除空目录 LaborAid"
  } else {
    Write-Warning "内层目录仍有文件，请手动检查后删除: $inner"
  }
}

$parent = Split-Path $repoRoot -Parent
$leaf = Split-Path $repoRoot -Leaf
if ($leaf -ne 'LaborAid') {
  $target = Join-Path $parent 'LaborAid'
  if (Test-Path $target) {
    Write-Warning "目标已存在: $target ，请手动合并或删除后重试"
  } else {
    Rename-Item -LiteralPath $repoRoot -NewName 'LaborAid'
    Write-Host ">> 已重命名: $repoRoot -> $target"
    Write-Host ">> 请在 Cursor 中重新打开文件夹: $target"
  }
} else {
  Write-Host ">> 目录名已是 LaborAid，无需重命名"
}

Write-Host "完成。"
