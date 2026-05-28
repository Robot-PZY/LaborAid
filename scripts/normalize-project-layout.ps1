# 与 LaborAid/scripts/normalize-project-layout.ps1 相同
# 在仓库 git 根目录（含 .git 的文件夹）执行本脚本即可。

$innerScript = Join-Path $PSScriptRoot 'LaborAid\scripts\normalize-project-layout.ps1'
if (Test-Path $innerScript) {
  & $innerScript
} else {
  Write-Error "未找到内层脚本，请确认仓库结构。"
}
