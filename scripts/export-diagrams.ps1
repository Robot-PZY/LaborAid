# LaborAid — 批量导出 docs/diagrams 下的 Mermaid / D2 图为 PNG/SVG
# 用法: 在仓库根目录执行 .\scripts\export-diagrams.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DiagramDir = Join-Path $Root "docs\diagrams"
$ExportDir = Join-Path $DiagramDir "export"

if (-not (Test-Path $ExportDir)) {
    New-Item -ItemType Directory -Path $ExportDir | Out-Null
}

Write-Host "==> LaborAid diagram export" -ForegroundColor Cyan
Write-Host "    Source: $DiagramDir"
Write-Host "    Output: $ExportDir"
Write-Host ""

$mmdFiles = Get-ChildItem -Path $DiagramDir -Filter "*.mmd"
$d2Files = Get-ChildItem -Path $DiagramDir -Filter "*.d2"

$hasMmdc = $false
try {
    $null = Get-Command mmdc -ErrorAction Stop
    $hasMmdc = $true
} catch {
    Write-Host "[i] mmdc not in PATH — will try npx @mermaid-js/mermaid-cli" -ForegroundColor Yellow
}

foreach ($f in $mmdFiles) {
    $out = Join-Path $ExportDir ($f.BaseName + ".png")
    Write-Host "Mermaid: $($f.Name) -> export\$($f.BaseName).png"
    if ($hasMmdc) {
        & mmdc -i $f.FullName -o $out -b transparent
    } else {
        & npx -y @mermaid-js/mermaid-cli -i $f.FullName -o $out -b transparent
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    [skip] npx mmdc failed — use https://mermaid.live" -ForegroundColor Yellow
        }
    }
}

$hasD2 = $false
try {
    $null = Get-Command d2 -ErrorAction Stop
    $hasD2 = $true
} catch {
    Write-Host "[i] d2 CLI not installed — skip .d2 (see https://github.com/terrastruct/d2)" -ForegroundColor Yellow
}

if ($hasD2) {
    foreach ($f in $d2Files) {
        $out = Join-Path $ExportDir ($f.BaseName + ".svg")
        Write-Host "D2: $($f.Name) -> export\$($f.BaseName).svg"
        & d2 $f.FullName $out
    }
}

Write-Host ""
Write-Host "Done. Check docs/diagrams/export/" -ForegroundColor Green
