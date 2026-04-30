@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ╔══════════════════════════════════════════╗
echo ║        WebScribe 启动管理器              ║
echo ║  智能网页探索与复刻工具                   ║
echo ╚══════════════════════════════════════════╝
echo.

:menu
echo 请选择启动方式：
echo.
echo  [1] Docker 部署（推荐） — 一键启动所有服务
echo  [2] 本地开发模式        — 分别启动前后端
echo  [3] 停止服务            — 停止 Docker 容器
echo  [4] 查看服务状态        — Docker 容器状态
echo  [0] 退出
echo.
set /p choice="请输入数字 (0-4): "

if "%choice%"=="1" goto docker_start
if "%choice%"=="2" goto local_start
if "%choice%"=="3" goto docker_stop
if "%choice%"=="4" goto docker_status
if "%choice%"=="0" exit /b 0
echo 无效选择，请重新输入
pause
goto menu

:: ============================================
:: Docker 部署模式
:: ============================================
:docker_start
echo.
echo [*] 检查 Docker 环境...
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Docker，请先安装 Docker Desktop
    echo        下载地址: https://www.docker.com/products/docker-desktop/
    pause
    goto menu
)

:: 创建 .env 文件（如果不存在）
if not exist .env (
    echo [*] 首次运行，从 .env.example 创建 .env 文件...
    copy .env.example .env >nul
    echo [注意] 请编辑 .env 文件，填入你的 DEEPSEEK_API_KEY 等配置
)

:: 创建必要的数据目录
if not exist data mkdir data
if not exist data\screenshots mkdir data\screenshots
if not exist data\reports mkdir data\reports

echo [*] 正在启动 WebScribe 服务...
echo.

:: 尝试 docker compose（新版）
docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] 使用 docker compose 启动...
    docker compose up -d
) else (
    :: 尝试 docker-compose（旧版）
    where docker-compose >nul 2>&1
    if %errorlevel% equ 0 (
        echo [*] 使用 docker-compose 启动...
        docker-compose up -d
    ) else (
        echo [错误] 未找到 docker compose 或 docker-compose 命令
        pause
        goto menu
    )
)

if %errorlevel% neq 0 (
    echo [错误] 启动失败，请检查 Docker 日志
    pause
    goto menu
)

echo.
echo ╔══════════════════════════════════════════╗
echo ║  WebScribe 服务已成功启动！              ║
echo ║                                          ║
echo ║  前端控制台: http://localhost:5173        ║
echo ║  后端 API:   http://localhost:8000/docs   ║
echo ║                                          ║
echo ║  查看状态:   start.bat 选 4              ║
echo ║  停止服务:   start.bat 选 3              ║
echo ╚══════════════════════════════════════════╝
echo.
pause
goto menu

:: ============================================
:: 本地开发模式
:: ============================================
:local_start
echo.
echo [*] 检查本地开发环境...

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请安装 Python 3.10+
    pause
    goto menu
)

:: 检查 Node.js
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 npm，请安装 Node.js 18+
    pause
    goto menu
)

:: 创建 .env 文件（如果不存在）
if not exist .env (
    echo [*] 首次运行，从 .env.example 创建 .env 文件...
    copy .env.example .env >nul
    echo [注意] 请编辑 .env 文件，填入你的 DEEPSEEK_API_KEY 等配置
)

:: 创建必要的数据目录
if not exist data mkdir data
if not exist data\screenshots mkdir data\screenshots
if not exist data\reports mkdir data\reports

:: 创建 Python 虚拟环境
if not exist .venv (
    echo [*] 创建 Python 虚拟环境...
    python -m venv .venv
)

:: 安装后端依赖
echo [*] 安装/更新 Python 依赖...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r backend\requirements.txt -q
python -m playwright install chromium 2>nul
echo [*] Python 依赖安装完成

:: 安装前端依赖
if not exist frontend\node_modules (
    echo [*] 安装前端依赖...
    pushd frontend
    call npm install
    popd
)

echo.
echo [*] 启动后端服务 (http://localhost:8000/docs)
start "WebScribe Backend" cmd /k "cd /d %cd% && call .venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo [*] 启动前端服务 (http://localhost:5173)
start "WebScribe Frontend" cmd /k "cd /d %cd%\frontend && npm run dev"

echo.
echo ╔══════════════════════════════════════════╗
echo ║  WebScribe 本地服务已启动！              ║
echo ║                                          ║
echo ║  前端控制台: http://localhost:5173        ║
echo ║  后端 API:   http://localhost:8000/docs   ║
echo ║                                          ║
echo ║  关闭窗口即可停止服务                     ║
echo ╚══════════════════════════════════════════╝
echo.
pause
goto menu

:: ============================================
:: Docker 停止服务
:: ============================================
:docker_stop
echo.
echo [*] 正在停止 WebScribe 服务...

docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    docker compose down
) else (
    where docker-compose >nul 2>&1
    if %errorlevel% equ 0 (
        docker-compose down
    ) else (
        echo [错误] 未找到 docker compose 命令
        pause
        goto menu
    )
)

if %errorlevel% equ 0 (
    echo [✓] 服务已成功停止
) else (
    echo [警告] 停止服务时出现问题
)
echo.
pause
goto menu

:: ============================================
:: Docker 查看状态
:: ============================================
:docker_status
echo.
echo [*] 当前服务状态：

docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    docker compose ps
) else (
    where docker-compose >nul 2>&1
    if %errorlevel% equ 0 (
        docker-compose ps
    ) else (
        echo [错误] 未找到 docker compose 命令
        pause
        goto menu
    )
)
echo.
pause
goto menu
