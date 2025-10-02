# 验证代码同步状态的简单脚本

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  验证代码同步状态" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 获取当前分支和提交
$currentBranch = git rev-parse --abbrev-ref HEAD
$localCommit = git rev-parse HEAD

Write-Host "📍 当前分支: $currentBranch" -ForegroundColor White
Write-Host "📌 本地提交: $($localCommit.Substring(0,12))" -ForegroundColor White
Write-Host ""

# 显示最新提交
Write-Host "📋 最新的5个提交:" -ForegroundColor Yellow
git log --oneline -5
Write-Host ""

# 显示远程仓库
Write-Host "🌐 远程仓库配置:" -ForegroundColor Yellow
git remote -v | Select-String "(fetch)"
Write-Host ""

# 检查关键文件
Write-Host "🔍 关键文件检查:" -ForegroundColor Yellow

# 检查requirements.txt
if (Select-String -Path "requirements.txt" -Pattern "^Pillow==10.1.0" -Quiet) {
    Write-Host "  ✅ requirements.txt 包含 Pillow==10.1.0" -ForegroundColor Green
} else {
    Write-Host "  ❌ requirements.txt 不包含 Pillow==10.1.0" -ForegroundColor Red
}

# 检查admin.py
if (Select-String -Path "routes/admin.py" -Pattern "HAS_PIL = True" -Quiet) {
    Write-Host "  ✅ routes/admin.py 使用可选PIL导入" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  routes/admin.py 可能未使用可选PIL导入" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  验证完成" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "💡 提示:" -ForegroundColor Cyan
Write-Host "  - 使用 'git push github master' 推送到GitHub" -ForegroundColor Gray
Write-Host "  - 使用 'git push origin master' 推送到Gitee" -ForegroundColor Gray
Write-Host "  - 使用 '.\sync-all.ps1' 同时推送到所有远程仓库" -ForegroundColor Gray
Write-Host ""

