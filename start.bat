@echo off
echo ========================================
echo  自动化测试后端服务 - 启动脚本
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未检测到Python环境，请先安装Python 3.9+
    pause
    exit /b 1
)

echo.
echo [2/3] 安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo 警告: 依赖安装可能存在问题，尝试继续启动...
)

echo.
echo [3/3] 启动服务...
echo 服务将在 http://localhost:8000 启动
echo API文档: http://localhost:8000/docs
echo 按 Ctrl+C 停止服务
echo.

python run.py

pause
