@echo off
REM 运行后端 API 测试脚本
REM 使用 test/patterns/test.json 和 test/test_fuction/get_daily_stats.py

echo ========================================
echo 后端 API 测试
echo ========================================
echo.

REM 检查是否设置了 API Key
if "%DASHSCOPE_API_KEY%"=="" (
    if "%OPENAI_API_KEY%"=="" (
        echo [警告] 未设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY
        echo 某些测试可能会失败
        echo.
        echo 设置方法:
        echo   set DASHSCOPE_API_KEY=your-api-key
        echo 或
        echo   set OPENAI_API_KEY=your-api-key
        echo.
        pause
    )
)

REM 安装依赖（如果需要）
echo 检查依赖...
pip show pytest >nul 2>&1
if errorlevel 1 (
    echo 安装 pytest...
    pip install pytest pytest-asyncio httpx
)

echo.
echo 开始运行测试...
echo.

REM 运行测试
python -m pytest test\test_backend_api.py -v -s --tb=short

echo.
echo ========================================
echo 测试完成
echo ========================================
pause
