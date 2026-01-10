@echo off
setlocal

:: 设置基础目录为当前批处理文件所在目录
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

echo [INFO] Init
echo [INFO] Running main.py...
python main.py


echo [INFO] Starting Backend API...
:: 在新窗口运行后端 API
start "Simple-LLM-Backend" cmd /k "python -m simple_llm_playground.backend_api"

echo [INFO] Starting Debugger UI...
:: 在新窗口运行前端 UI
start "Simple-LLM-UI" cmd /k "python -m simple_llm_playground.debugger_ui"

echo.
echo ======================================================
echo  Simple LLM Playground Running
echo ======================================================
echo  [backend] Backend API (port 8001)
echo  [frontend] Debugger UI (PyQt5)
echo.
echo  Please keep the backend window open, otherwise the UI will not work.
echo ======================================================
echo.
pause
