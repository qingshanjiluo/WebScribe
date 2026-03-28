@echo off
chcp 65001 >nul
echo WebScribe 服务管理脚本
echo.

REM 检查 Docker 是否安装
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Docker 未安装
    pause
    exit /b 1
)

:menu
cls
echo ========================================
echo        WebScribe 服务管理菜单
echo ========================================
echo.
echo  1. 查看服务状态
echo  2. 查看服务日志
echo  3. 重启服务
echo  4. 查看容器日志（实时）
echo  5. 清理所有容器和镜像
echo  6. 打开前端控制台
echo  7. 打开后端API文档
echo  0. 退出
echo.
set /p choice="请选择操作 (0-7): "

if "%choice%"=="1" goto status
if "%choice%"=="2" goto logs
if "%choice%"=="3" goto restart
if "%choice%"=="4" goto logs_follow
if "%choice%"=="5" goto cleanup
if "%choice%"=="6" goto open_frontend
if "%choice%"=="7" goto open_backend
if "%choice%"=="0" goto exit
echo 无效的选择，请重新输入
pause
goto menu

:status
echo.
echo 服务状态：
call :run_compose ps
pause
goto menu

:logs
echo.
echo 服务日志：
call :run_compose logs
pause
goto menu

:logs_follow
echo.
echo 实时日志（按 Ctrl+C 退出）：
call :run_compose logs -f
pause
goto menu

:restart
echo.
echo 重启服务...
call :run_compose restart
echo 服务已重启
pause
goto menu

:cleanup
echo.
set /p confirm="警告：这将删除所有容器和镜像，确定吗？(y/N): "
if /i "%confirm%" neq "y" goto menu
echo 停止并删除所有容器...
call :run_compose down
echo 清理未使用的镜像...
docker system prune -f
echo 清理完成
pause
goto menu

:open_frontend
echo.
echo 正在打开前端控制台...
start http://localhost:5173 2>nul
echo 如果浏览器未自动打开，请手动访问: http://localhost:5173
pause
goto menu

:open_backend
echo.
echo 正在打开后端API文档...
start http://localhost:8000/docs 2>nul
echo 如果浏览器未自动打开，请手动访问: http://localhost:8000/docs
pause
goto menu

:exit
echo 退出管理脚本
exit /b 0

:run_compose
REM 尝试使用 docker compose（新版本）
docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    docker compose %*
    exit /b
)

REM 尝试使用 docker-compose（旧版本）
where docker-compose >nul 2>&1
if %errorlevel% equ 0 (
    docker-compose %*
    exit /b
)

echo 错误: 未找到 docker compose 或 docker-compose 命令
exit /b 1