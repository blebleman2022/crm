# 同步代码到所有远程仓库的PowerShell脚本

param(
    [string]$Message = "sync: 同步代码到所有远程仓库"
)

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  同步代码到所有远程仓库" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否有未提交的更改
$status = git status --porcelain
if ($status) {
    Write-Host "📝 检测到未提交的更改:" -ForegroundColor Yellow
    git status --short
    Write-Host ""
    
    $commit = Read-Host "是否提交这些更改? (y/N)"
    if ($commit -eq 'y' -or $commit -eq 'Y') {
        Write-Host ""
        Write-Host "📦 添加所有更改..." -ForegroundColor Yellow
        git add -A
        
        Write-Host "💾 提交更改..." -ForegroundColor Yellow
        git commit -m $Message
        Write-Host ""
    } else {
        Write-Host "⏭️  跳过提交，仅推送已有提交" -ForegroundColor Gray
        Write-Host ""
    }
}

# 获取当前分支
$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Host "📍 当前分支: $currentBranch" -ForegroundColor White
Write-Host ""

# 推送到GitHub
Write-Host "📤 推送到 GitHub..." -ForegroundColor Cyan
try {
    git push github $currentBranch
    Write-Host "  ✅ GitHub 推送成功" -ForegroundColor Green
} catch {
    Write-Host "  ❌ GitHub 推送失败: $_" -ForegroundColor Red
}
Write-Host ""

# 推送到Gitee
Write-Host "📤 推送到 Gitee..." -ForegroundColor Cyan
try {
    git push origin $currentBranch
    Write-Host "  ✅ Gitee 推送成功" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Gitee 推送失败: $_" -ForegroundColor Red
}
Write-Host ""

# 显示最新提交
Write-Host "📋 最新的3个提交:" -ForegroundColor White
git log --oneline -3
Write-Host ""

# 显示远程状态
Write-Host "🔍 远程仓库状态:" -ForegroundColor White
$localCommit = git rev-parse HEAD
$githubCommit = git rev-parse github/$currentBranch 2>$null
$giteeCommit = git rev-parse origin/$currentBranch 2>$null

Write-Host "  本地:   $($localCommit.Substring(0,12))" -ForegroundColor Gray
Write-Host "  GitHub: $($githubCommit.Substring(0,12))" -ForegroundColor Gray
Write-Host "  Gitee:  $($giteeCommit.Substring(0,12))" -ForegroundColor Gray
Write-Host ""

if ($localCommit -eq $githubCommit -and $localCommit -eq $giteeCommit) {
    Write-Host "✅ 所有远程仓库已同步" -ForegroundColor Green
} else {
    Write-Host "⚠️  部分远程仓库未同步" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  同步完成" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

