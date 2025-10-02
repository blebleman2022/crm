# 检查本地代码是否与远程同步的PowerShell脚本

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  检查代码同步状态" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 获取远程最新信息
Write-Host "📡 获取远程最新信息..." -ForegroundColor Yellow
git fetch github 2>&1 | Out-Null
Write-Host ""

# 获取当前分支
$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Host "📍 当前分支: $currentBranch" -ForegroundColor White
Write-Host ""

# 获取本地和远程的commit hash
$localCommit = git rev-parse HEAD
$remoteCommit = git rev-parse github/master 2>$null

Write-Host "🔍 Commit对比:" -ForegroundColor White
Write-Host "  本地 HEAD:          $($localCommit.Substring(0,12))" -ForegroundColor Gray
Write-Host "  远程 github/master: $($remoteCommit.Substring(0,12))" -ForegroundColor Gray
Write-Host ""

# 检查是否同步
if ($localCommit -eq $remoteCommit) {
    Write-Host "✅ 状态: 本地代码与远程完全同步" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 最新的5个提交:" -ForegroundColor White
    git log --oneline -5
} else {
    Write-Host "⚠️  状态: 本地代码与远程不同步" -ForegroundColor Yellow
    Write-Host ""
    
    # 检查本地是否领先
    $ahead = (git rev-list --count github/master..HEAD 2>$null)
    # 检查本地是否落后
    $behind = (git rev-list --count HEAD..github/master 2>$null)
    
    if ([int]$ahead -gt 0) {
        Write-Host "📤 本地领先远程 $ahead 个提交" -ForegroundColor Cyan
        Write-Host "   建议执行: git push github master" -ForegroundColor Gray
        Write-Host ""
        Write-Host "📋 本地独有的提交:" -ForegroundColor White
        git log github/master..HEAD --oneline
    }
    
    if ([int]$behind -gt 0) {
        Write-Host "📥 本地落后远程 $behind 个提交" -ForegroundColor Magenta
        Write-Host "   建议执行: git pull github master" -ForegroundColor Gray
        Write-Host ""
        Write-Host "📋 远程新增的提交:" -ForegroundColor White
        git log HEAD..github/master --oneline
    }
}

Write-Host ""

# 检查requirements.txt中的Pillow
Write-Host "🔍 检查关键文件:" -ForegroundColor White
if (Select-String -Path "requirements.txt" -Pattern "^Pillow" -Quiet) {
    Write-Host "  ✅ requirements.txt 包含 Pillow" -ForegroundColor Green
} else {
    Write-Host "  ❌ requirements.txt 不包含 Pillow" -ForegroundColor Red
}

# 检查admin.py中的PIL导入
if (Select-String -Path "routes/admin.py" -Pattern "HAS_PIL" -Quiet) {
    Write-Host "  ✅ routes/admin.py 使用可选PIL导入" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  routes/admin.py 未使用可选PIL导入" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  检查完成" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

