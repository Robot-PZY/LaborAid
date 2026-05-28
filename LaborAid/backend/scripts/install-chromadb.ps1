# 安装 ChromaDB（向量检索 / 知识库索引）
# 在 backend 目录执行: .\scripts\install-chromadb.ps1
#
# Windows 若报错 “Microsoft Visual C++ 14.0 or greater is required”：
# 1. 安装 https://visualstudio.microsoft.com/visual-cpp-build-tools/ （勾选“使用 C++ 的桌面开发”）
# 2. 重新打开终端后再运行本脚本

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "Installing chromadb==0.5.23 (may take several minutes on first run) ..."
python -m pip install --upgrade pip
python -m pip install "chromadb==0.5.23"
if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Install failed. On Windows this usually means MSVC Build Tools are missing."
  Write-Host "Install Build Tools, then re-run: .\scripts\install-chromadb.ps1"
  exit 1
}
python -c "import chromadb; print('ChromaDB', chromadb.__version__, 'OK')"
Write-Host "Done. Restart the backend (uvicorn) to enable vector search."
