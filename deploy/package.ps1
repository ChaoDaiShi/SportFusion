# ============================================================
# 本地打包脚本 (Windows PowerShell)
# 将项目打包为 tar.gz 用于上传到服务器
# 使用方法: .\deploy\package.ps1
# ============================================================

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$OutputFile = Join-Path $RootDir "sports-industry-deploy.tar.gz"

Write-Host "============================================" -ForegroundColor Blue
Write-Host "  体育产业测算平台 — 部署打包" -ForegroundColor Blue
Write-Host "============================================" -ForegroundColor Blue
Write-Host ""

# 先构建前端
Write-Host "[1/2] 构建前端生产版本..." -ForegroundColor Yellow
Set-Location (Join-Path $RootDir "frontend")

if (-not (Test-Path "node_modules")) {
    Write-Host "  安装前端依赖..." -ForegroundColor Gray
    npm install
}
npm run build
Write-Host "  前端构建完成" -ForegroundColor Green

# 打包
Write-Host "[2/2] 打包项目文件..." -ForegroundColor Yellow
Set-Location $RootDir

# 使用 tar 打包（Windows 10 1803+ 自带）
tar --exclude='frontend/node_modules' `
    --exclude='backend/.venv' `
    --exclude='backend/venv' `
    --exclude='backend/__pycache__' `
    --exclude='.uploads' `
    --exclude='node_modules' `
    --exclude='*.zip' `
    --exclude='项目 (2)*' `
    --exclude='__pycache__' `
    --exclude='*.tar.gz' `
    --exclude='.git' `
    --exclude='citation-verification-report.html' `
    --exclude='docx_structure.txt' `
    --exclude='full_text.txt' `
    --exclude='体融识界·*.docx' `
    --exclude='数据掘金·*.docx' `
    --exclude='~$*.docx' `
    -czf "$OutputFile" `
    backend/ frontend/dist/ deploy/ data/

$SizeMB = [math]::Round((Get-Item $OutputFile).Length / 1MB, 1)
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  打包完成！" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  文件: $OutputFile"
Write-Host "  大小: $SizeMB MB"
Write-Host ""
Write-Host "  上传到服务器:"
Write-Host "  scp $OutputFile root@YOUR_IP:/tmp/" -ForegroundColor Cyan
Write-Host ""
Write-Host "  服务器上部署:"
Write-Host "  ssh root@YOUR_IP" -ForegroundColor Cyan
Write-Host "  cd /tmp && tar -xzf sports-industry-deploy.tar.gz" -ForegroundColor Cyan
Write-Host "  chmod +x deploy/deploy.sh && sudo ./deploy/deploy.sh" -ForegroundColor Cyan
Write-Host ""
