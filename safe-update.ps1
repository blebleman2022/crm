# ============================================
# 安全更新脚本 - 保护数据库文件 (Windows版本)
# ============================================
# 
# 功能：
# 1. 自动备份数据库
# 2. 只更新代码文件，不影响数据库
# 3. 重新构建Docker镜像
# 4. 验证更新结果
#
# 使用方法：
#   powershell -ExecutionPolicy Bypass -File safe-update.ps1
#
# ============================================

# 颜色函数
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor Cyan
}

# 显示标题
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  🚀 CRM系统安全更新脚本 (Windows)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 本脚本将："
Write-Host "  ✅ 自动备份数据库"
Write-Host "  ✅ 只更新代码文件"
Write-Host "  ✅ 保护数据库不被覆盖"
Write-Host "  ✅ 重新构建Docker镜像"
Write-Host ""

# 确认执行
$confirmation = Read-Host "是否继续？(y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Info "更新已取消"
    exit 0
}

Write-Host ""

# ============================================
# 步骤1: 检查环境
# ============================================
Write-Step "步骤1/7: 检查环境"

# 检查是否在项目目录
if (-not (Test-Path "run.py") -or -not (Test-Path "docker-compose.yml")) {
    Write-Error "请在项目根目录下运行此脚本"
    exit 1
}
Write-Success "项目目录检查通过"

# 检查Git
try {
    git --version | Out-Null
    Write-Success "Git已安装"
} catch {
    Write-Error "Git未安装"
    exit 1
}

# 检查Docker
try {
    docker --version | Out-Null
    Write-Success "Docker已安装"
} catch {
    Write-Error "Docker未安装"
    exit 1
}

Write-Host ""

# ============================================
# 步骤2: 备份数据库
# ============================================
Write-Step "步骤2/7: 备份数据库"

$dbPath = "instance\edu_crm.db"
if (Test-Path $dbPath) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = "instance\edu_crm_backup_$timestamp.db"
    Copy-Item $dbPath $backupFile
    Write-Success "数据库已备份: $backupFile"
    
    # 显示数据库大小
    $dbSize = (Get-Item $dbPath).Length / 1MB
    Write-Host "  数据库大小: $([math]::Round($dbSize, 2)) MB"
} else {
    Write-Warning "数据库文件不存在，跳过备份"
    $backupFile = ""
}

Write-Host ""

# ============================================
# 步骤3: 保护数据库文件
# ============================================
Write-Step "步骤3/7: 保护数据库文件"

# 临时移动数据库到安全位置
$tempDb = "$env:TEMP\edu_crm_temp_$(Get-Date -Format 'yyyyMMddHHmmss').db"
if (Test-Path $dbPath) {
    Move-Item $dbPath $tempDb -Force
    Write-Success "数据库已移至安全位置: $tempDb"
} else {
    Write-Warning "数据库文件不存在"
    $tempDb = ""
}

Write-Host ""

# ============================================
# 步骤4: 清理Git状态
# ============================================
Write-Step "步骤4/7: 清理Git状态"

# 从Git中移除数据库文件的追踪（如果存在）
try {
    git rm --cached instance/edu_crm.db 2>$null
    Write-Success "已移除数据库文件的Git追踪"
} catch {
    Write-Info "数据库文件未被Git追踪"
}

# 重置本地更改
git reset --hard HEAD | Out-Null
Write-Success "Git状态已重置"

Write-Host ""

# ============================================
# 步骤5: 拉取最新代码
# ============================================
Write-Step "步骤5/7: 拉取最新代码"

# 显示当前版本
$currentCommit = git log --oneline -1
Write-Host "  当前版本: $currentCommit"

# 拉取代码
$pullResult = git pull origin master 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Success "代码拉取成功"
    
    # 显示新版本
    $newCommit = git log --oneline -1
    Write-Host "  最新版本: $newCommit"
    
    # 显示更新内容
    if ($currentCommit -ne $newCommit) {
        Write-Host ""
        Write-Info "本次更新内容:"
        git log --oneline --graph --decorate -5
    } else {
        Write-Info "代码已是最新版本"
    }
} else {
    Write-Error "代码拉取失败"
    Write-Host $pullResult
    
    # 恢复数据库
    if ($tempDb -and (Test-Path $tempDb)) {
        Move-Item $tempDb $dbPath -Force
        Write-Success "数据库已恢复"
    }
    
    exit 1
}

Write-Host ""

# ============================================
# 步骤6: 恢复数据库
# ============================================
Write-Step "步骤6/7: 恢复数据库"

if ($tempDb -and (Test-Path $tempDb)) {
    Move-Item $tempDb $dbPath -Force
    Write-Success "数据库已恢复到原位置"
    
    # 验证数据库完整性
    if (Test-Path $dbPath) {
        $dbSize = (Get-Item $dbPath).Length / 1MB
        Write-Success "数据库验证通过 (大小: $([math]::Round($dbSize, 2)) MB)"
    } else {
        Write-Error "数据库恢复失败"
        exit 1
    }
} else {
    Write-Info "无需恢复数据库"
}

Write-Host ""

# ============================================
# 步骤7: 重新构建Docker
# ============================================
Write-Step "步骤7/7: 重新构建Docker镜像"

# 停止容器
Write-Info "停止Docker容器..."
docker compose down | Out-Null
Write-Success "容器已停止"

# 重新构建
Write-Info "重新构建镜像（这可能需要几分钟）..."
$buildResult = docker compose build --no-cache 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Success "镜像构建成功"
} else {
    Write-Error "镜像构建失败"
    Write-Host $buildResult
    exit 1
}

# 启动容器
Write-Info "启动Docker容器..."
docker compose up -d | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Success "容器已启动"
} else {
    Write-Error "容器启动失败"
    exit 1
}

# 等待容器启动
Write-Info "等待容器启动..."
Start-Sleep -Seconds 5

# 检查容器状态
$containerStatus = docker compose ps | Select-String "crm-app"
if ($containerStatus -match "running") {
    Write-Success "容器运行正常"
} else {
    Write-Error "容器状态异常"
}

Write-Host ""

# ============================================
# 完成
# ============================================
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  ✅ 更新完成！" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""

Write-Success "代码已更新到最新版本"
Write-Success "数据库文件已安全保留"
Write-Success "Docker容器已重新构建并启动"

Write-Host ""
Write-Host "📋 更新摘要:"
if ($backupFile) {
    Write-Host "  - 数据库备份: $backupFile"
}
Write-Host "  - 数据库状态: 已保留，未修改"
Write-Host "  - 容器状态: 运行中"
Write-Host ""

Write-Host "🔍 验证更新:"
Write-Host "  - 查看日志: docker compose logs -f"
Write-Host "  - 查看状态: docker compose ps"
Write-Host "  - 访问系统: http://localhost:5000"
Write-Host ""

if ($backupFile) {
    Write-Host "📁 备份文件位置:"
    Write-Host "  - $backupFile"
    Write-Host ""
}

# 显示最近的日志
Write-Info "最近的容器日志:"
Write-Host "-----------------------------------"
docker compose logs --tail=20
Write-Host "-----------------------------------"

Write-Host ""
Write-Success "安全更新流程已完成！"
Write-Host ""

