# ============================================
# 推送到GitHub main分支 (PowerShell)
# ============================================

Write-Host "正在推送到GitHub main分支..." -ForegroundColor Cyan

# 推送master分支到GitHub的main分支
git push github master:main

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 成功推送到GitHub main分支" -ForegroundColor Green
} else {
    Write-Host "❌ 推送失败，请检查网络连接" -ForegroundColor Red
    exit 1
}

