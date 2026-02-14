# EduConnect CRM 启动脚本 (Windows PowerShell)
# 使用方法: .\start_server.ps1

Write-Host "=========================================="
Write-Host "启动 EduConnect CRM 本地服务"
Write-Host "=========================================="
Write-Host ""

# 切换到脚本所在目录
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

# 设置端口
$PORT = if ($env:PORT) { $env:PORT } else { "5002" }

# 检查端口是否被占用
Write-Host "🔍 检查端口 $PORT 是否被占用..."
$process = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue
if ($process) {
    Write-Host "⚠️  端口 $PORT 已被占用，正在停止旧进程..."
    $processId = $process.OwningProcess
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "✅ 旧进程已停止"
} else {
    Write-Host "✅ 端口 $PORT 可用"
}

Write-Host ""
Write-Host "🚀 启动服务..."
Write-Host "   - 端口: $PORT"
Write-Host "   - 环境: development"
Write-Host "   - 访问地址: http://127.0.0.1:$PORT"
Write-Host ""
Write-Host "按 Ctrl+C 停止服务"
Write-Host ""

# 设置环境变量并启动
$env:PORT = $PORT
$env:FLASK_ENV = "development"
$env:USE_RELOADER = if ($env:USE_RELOADER) { $env:USE_RELOADER } else { "1" }
$env:RELOADER_TYPE = if ($env:RELOADER_TYPE) { $env:RELOADER_TYPE } else { "stat" }

# 校验解释器是否具备核心依赖
function Test-PythonInterpreter {
    param([string]$Command)
    try {
        & $Command -c "import flask, blinker" *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

# 优先使用项目内虚拟环境 Python
$pythonCandidates = @(
    (Join-Path $SCRIPT_DIR "venv_win\Scripts\python.exe"),
    (Join-Path $SCRIPT_DIR "venv\Scripts\python.exe"),
    "python"
)

$pythonCmd = $null
foreach ($candidate in $pythonCandidates) {
    if ($candidate -eq "python") {
        if (Get-Command python -ErrorAction SilentlyContinue) {
            if (Test-PythonInterpreter "python") {
                $pythonCmd = "python"
                break
            }
        }
    } elseif (Test-Path $candidate) {
        if (Test-PythonInterpreter $candidate) {
            $pythonCmd = $candidate
            break
        }
    }
}

if (-not $pythonCmd) {
    Write-Host "❌ 未找到可用的 Python 解释器（需包含 flask 与 blinker）"
    exit 1
}

Write-Host "🐍 Python: $pythonCmd"

# 运行服务
& $pythonCmd run.py run
