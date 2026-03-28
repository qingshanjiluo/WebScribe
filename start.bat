@echo off
echo WebScribe 一键启动脚本

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Docker 未安装，请先安装 Docker Desktop
    pause
    exit /b 1
)

if not exist .env (
    echo 创建 .env 文件，请编辑填入你的 DeepSeek API Key
    copy .env.example .env
)

if not exist data\screenshots mkdir data\screenshots
if not exist data\reports mkdir data\reports

docker-compose up -d

echo 服务已启动！
echo 访问前端: http://localhost:5173
echo 后端 API: http://localhost:8000
pause