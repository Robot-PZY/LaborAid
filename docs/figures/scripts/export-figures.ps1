$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Test-Path "node_modules")) { npm install }
node export-png.js @args
Write-Host "Done. Open ../preview.html"
