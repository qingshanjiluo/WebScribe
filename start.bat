@echo off
chcp 65001 >nul
echo WebScribe 一键启动脚本
echo.

REM 检查 Docker 是否安装
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Docker 未安装，请先安装 Docker Desktop
    echo 下载地址: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

REM 检查 Docker 是否运行
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Docker 服务未运行，请启动 Docker Desktop
    pause
    exit /b 1
)

REM 创建 .env 文件（如果不存在）
if not exist .env (
    echo 创建 .env 文件，请编辑填入你的 DeepSeek API Key
    copy .env.example .env
    echo.
    echo 注意：请编辑 .env 文件，设置你的 API Key 和其他配置
    echo.
)

REM 创建必要的目录
if not exist data\screenshots mkdir data\screenshots
if not exist data\reports mkdir data\reports

echo 正在启动 WebScribe 服务...
echo.

REM 尝试使用 docker compose（新版本）
docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    echo 使用 docker compose 启动服务...
    docker compose up -d
) else (
    REM 尝试使用 docker-compose（旧版本）
    where docker-compose >nul 2>&1
    if %errorlevel% equ 0 (
        echo 使用 docker-compose 启动服务...
        docker-compose up -d
    ) else (
        echo 错误: 未找到 docker compose 或 docker-compose 命令
        echo 请确保 Docker 已正确安装
        pause
        exit /b 1
    )
)

if %errorlevel% neq 0 (
    echo 错误: 启动服务失败，请检查 Docker 日志
    pause
    exit /b 1
)

echo.
echo ========================================
echo WebScribe 服务已成功启动！
echo.
echo 访问前端控制台: http://localhost:5173
echo 后端 API 文档: http://localhost:8000/docs
echo.
echo 查看服务状态: docker compose ps
echo 查看服务日志: docker compose logs -f
echo 停止服务: docker compose down
echo ========================================
echo.
echo 按任意键打开浏览器访问控制台...
pause >nul

REM 尝试打开浏览器
start http://localhost:5173 2>nul

echo.
echo 如果浏览器未自动打开，请手动访问: http://localhost:5173
echo 按任意键退出...
pause >nul