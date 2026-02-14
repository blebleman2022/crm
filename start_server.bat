@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo 启动 EduConnect CRM 本地服务
echo ==========================================
echo.

set PORT=5002
set FLASK_ENV=development
set USE_RELOADER=1
set RELOADER_TYPE=stat

set "PYTHON_CMD="
call :try_python "%~dp0venv_win\Scripts\python.exe"
if not defined PYTHON_CMD call :try_python "%~dp0venv\Scripts\python.exe"
if not defined PYTHON_CMD call :try_python "python"

if not defined PYTHON_CMD (
    echo ❌ 未找到可用的 Python 解释器（需包含 flask 和 blinker）
    pause
    exit /b 1
)

echo 🚀 启动服务...
echo    - 端口: %PORT%
echo    - 环境: %FLASK_ENV%
echo    - 访问地址: http://127.0.0.1:%PORT%
echo    - Python: %PYTHON_CMD%
echo.
echo 按 Ctrl+C 停止服务
echo.

"%PYTHON_CMD%" run.py run
pause

goto :eof

:try_python
set "CANDIDATE=%~1"
if /I "%CANDIDATE%"=="python" (
    where python >nul 2>nul || goto :eof
    python -c "import flask, blinker" >nul 2>nul || goto :eof
    set "PYTHON_CMD=python"
    goto :eof
)

if exist "%CANDIDATE%" (
    "%CANDIDATE%" -c "import flask, blinker" >nul 2>nul || goto :eof
    set "PYTHON_CMD=%CANDIDATE%"
)
goto :eof
