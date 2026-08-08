@echo off
echo ====================================================
echo   体育产业分析 - 全流程一键运行
echo ====================================================
echo.

cd /d "%~dp0backend"

if not exist "venv\Scripts\python.exe" (
    echo [SETUP] 创建虚拟环境...
    python -m venv venv
    echo [SETUP] 安装依赖...
    venv\Scripts\pip install -r requirements.txt -q
)

echo [1/4] 数据预处理（清洗+分词+体育标签标注）...
venv\Scripts\python run_preprocess.py --output ../data/processed
if %ERRORLEVEL% neq 0 (
    echo [FAIL] 数据预处理失败
    pause
    exit /b 1
)

echo.
echo [2/4] 体育业务识别+比重测算...
venv\Scripts\python run_recognition.py --output ../data/processed
if %ERRORLEVEL% neq 0 (
    echo [FAIL] 业务识别失败
    pause
    exit /b 1
)

echo.
echo [3/4] 产业规模测算+空间分析...
venv\Scripts\python run_analysis.py --region-detail --category-detail --output ../data/processed
if %ERRORLEVEL% neq 0 (
    echo [FAIL] 产业分析失败
    pause
    exit /b 1
)

echo.
echo [4/4] 综合报告+政策建议生成...
venv\Scripts\python run_final_report.py --output-dir ../data/processed
if %ERRORLEVEL% neq 0 (
    echo [FAIL] 报告生成失败
    pause
    exit /b 1
)

echo.
echo ====================================================
echo   全流程完成！
echo   产出文件: data\processed
echo ====================================================
echo.
echo   正在启动前后端服务...
echo.

start "Backend" cmd /k ""%~dp0start_backend.bat""
start "Frontend" cmd /k ""%~dp0start_frontend.bat""

echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo.

pause
