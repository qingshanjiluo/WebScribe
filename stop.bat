@echo off
echo WebScribe 停止服务脚本
echo.

REM 检查 Docker 是否安装
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Docker 未安装
    pause
    exit /b 1
)

echo 正在停止 WebScribe 服务...
echo.

REM 尝试使用 docker compose（新版本）
docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    echo 使用 docker compose 停止服务...
    docker compose down
) else (
    REM 尝试使用 docker-compose（旧版本）
    where docker-compose >nul 2>&1
    if %errorlevel% equ 0 (
        echo 使用 docker-compose 停止服务...
        docker-compose down
    ) else (
        echo 错误: 未找到 docker compose 或 docker-compose 命令
        pause
        exit /b 1
    )
)

if %errorlevel% neq 0 (
    echo 警告: 停止服务时出现问题
) else (
    echo 服务已成功停止
)

echo.
echo 按任意键退出...
pause >nul