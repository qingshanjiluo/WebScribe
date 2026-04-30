@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 鈺斺晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晽
echo 鈺?       WebScribe 鍚姩绠＄悊鍣?             鈺?echo 鈺? 鏅鸿兘缃戦〉鎺㈢储涓庡鍒诲伐鍏?                  鈺?echo 鈺氣晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨暆
echo.

:menu
echo 璇烽€夋嫨鍚姩鏂瑰紡锛?echo.
echo  [1] Docker 閮ㄧ讲锛堟帹鑽愶級 鈥?涓€閿惎鍔ㄦ墍鏈夋湇鍔?echo  [2] 鏈湴寮€鍙戞ā寮?       鈥?鍒嗗埆鍚姩鍓嶅悗绔?echo  [3] 鍋滄鏈嶅姟            鈥?鍋滄 Docker 瀹瑰櫒
echo  [4] 鏌ョ湅鏈嶅姟鐘舵€?       鈥?Docker 瀹瑰櫒鐘舵€?echo  [0] 閫€鍑?echo.
set /p choice="璇疯緭鍏ユ暟瀛?(0-4): "

if "%choice%"=="1" goto docker_start
if "%choice%"=="2" goto local_start
if "%choice%"=="3" goto docker_stop
if "%choice%"=="4" goto docker_status
if "%choice%"=="0" exit /b 0
echo 鏃犳晥閫夋嫨锛岃閲嶆柊杈撳叆
pause
goto menu

:: ============================================
:: Docker 閮ㄧ讲妯″紡
:: ============================================
:docker_start
echo.
echo [*] 妫€鏌?Docker 鐜...
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [閿欒] 鏈壘鍒?Docker锛岃鍏堝畨瑁?Docker Desktop
    echo        涓嬭浇鍦板潃: https://www.docker.com/products/docker-desktop/
    pause
    goto menu
)

:: 鍒涘缓 .env 鏂囦欢锛堝鏋滀笉瀛樺湪锛?if not exist .env (
    echo [*] 棣栨杩愯锛屼粠 .env.example 鍒涘缓 .env 鏂囦欢...
    copy .env.example .env >nul
    echo [娉ㄦ剰] 璇风紪杈?.env 鏂囦欢锛屽～鍏ヤ綘鐨?DEEPSEEK_API_KEY 绛夐厤缃?)

:: 鍒涘缓蹇呰鐨勬暟鎹洰褰?if not exist data mkdir data
if not exist data\screenshots mkdir data\screenshots
if not exist data\reports mkdir data\reports

echo [*] 姝ｅ湪鍚姩 WebScribe 鏈嶅姟...
echo.

:: 灏濊瘯 docker compose锛堟柊鐗堬級
docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] 浣跨敤 docker compose 鍚姩...
    docker compose up -d
) else (
    :: 灏濊瘯 docker-compose锛堟棫鐗堬級
    where docker-compose >nul 2>&1
    if %errorlevel% equ 0 (
        echo [*] 浣跨敤 docker-compose 鍚姩...
        docker-compose up -d
    ) else (
        echo [閿欒] 鏈壘鍒?docker compose 鎴?docker-compose 鍛戒护
        pause
        goto menu
    )
)

if %errorlevel% neq 0 (
    echo [閿欒] 鍚姩澶辫触锛岃妫€鏌?Docker 鏃ュ織
    pause
    goto menu
)

echo.
echo 鈺斺晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晽
echo 鈺? WebScribe 鏈嶅姟宸叉垚鍔熷惎鍔紒              鈺?echo 鈺?                                         鈺?echo 鈺? 鍓嶇鎺у埗鍙? http://localhost:5173        鈺?echo 鈺? 鍚庣 API:   http://localhost:8000/docs   鈺?echo 鈺?                                         鈺?echo 鈺? 鏌ョ湅鐘舵€?   start.bat 閫?4              鈺?echo 鈺? 鍋滄鏈嶅姟:   start.bat 閫?3              鈺?echo 鈺氣晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨暆
echo.
pause
goto menu

:: ============================================
:: 鏈湴寮€鍙戞ā寮?:: ============================================
:local_start
echo.
echo [*] 妫€鏌ユ湰鍦板紑鍙戠幆澧?..

:: 妫€鏌?Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [閿欒] 鏈壘鍒?Python锛岃瀹夎 Python 3.10+
    pause
    goto menu
)

:: 妫€鏌?Node.js
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [閿欒] 鏈壘鍒?npm锛岃瀹夎 Node.js 18+
    pause
    goto menu
)

:: 鍒涘缓 .env 鏂囦欢锛堝鏋滀笉瀛樺湪锛?if not exist .env (
    echo [*] 棣栨杩愯锛屼粠 .env.example 鍒涘缓 .env 鏂囦欢...
    copy .env.example .env >nul
    echo [娉ㄦ剰] 璇风紪杈?.env 鏂囦欢锛屽～鍏ヤ綘鐨?DEEPSEEK_API_KEY 绛夐厤缃?)

:: 鍒涘缓蹇呰鐨勬暟鎹洰褰?if not exist data mkdir data
if not exist data\screenshots mkdir data\screenshots
if not exist data\reports mkdir data\reports

:: 鍒涘缓 Python 铏氭嫙鐜
if not exist .venv (
    echo [*] 鍒涘缓 Python 铏氭嫙鐜...
    python -m venv .venv
)

:: 瀹夎鍚庣渚濊禆
echo [*] 瀹夎/鏇存柊 Python 渚濊禆...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r backend\requirements.txt -q
python -m playwright install chromium 2>nul
echo [*] Python 渚濊禆瀹夎瀹屾垚

:: 瀹夎鍓嶇渚濊禆
if not exist frontend\node_modules (
    echo [*] 瀹夎鍓嶇渚濊禆...
    pushd frontend
    call npm install
    popd
)

echo.
echo [*] 鍚姩鍚庣鏈嶅姟 (http://localhost:8000/docs)
start "WebScribe Backend" cmd /k "cd /d %cd% && call .venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo [*] 鍚姩鍓嶇鏈嶅姟 (http://localhost:5173)
start "WebScribe Frontend" cmd /k "cd /d %cd%\frontend && npm run dev"

echo.
echo 鈺斺晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晽
echo 鈺? WebScribe 鏈湴鏈嶅姟宸插惎鍔紒              鈺?echo 鈺?                                         鈺?echo 鈺? 鍓嶇鎺у埗鍙? http://localhost:5173        鈺?echo 鈺? 鍚庣 API:   http://localhost:8000/docs   鈺?echo 鈺?                                         鈺?echo 鈺? 鍏抽棴绐楀彛鍗冲彲鍋滄鏈嶅姟                     鈺?echo 鈺氣晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨晲鈺愨暆
echo.
pause
goto menu

:: ============================================
:: Docker 鍋滄鏈嶅姟
:: ============================================
:docker_stop
echo.
echo [*] 姝ｅ湪鍋滄 WebScribe 鏈嶅姟...

docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    docker compose down
) else (
    where docker-compose >nul 2>&1
    if %errorlevel% equ 0 (
        docker-compose down
    ) else (
        echo [閿欒] 鏈壘鍒?docker compose 鍛戒护
        pause
        goto menu
    )
)

if %errorlevel% equ 0 (
    echo [鉁揮 鏈嶅姟宸叉垚鍔熷仠姝?) else (
    echo [璀﹀憡] 鍋滄鏈嶅姟鏃跺嚭鐜伴棶棰?)
echo.
pause
goto menu

:: ============================================
:: Docker 鏌ョ湅鐘舵€?:: ============================================
:docker_status
echo.
echo [*] 褰撳墠鏈嶅姟鐘舵€侊細

docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    docker compose ps
) else (
    where docker-compose >nul 2>&1
    if %errorlevel% equ 0 (
        docker-compose ps
    ) else (
        echo [閿欒] 鏈壘鍒?docker compose 鍛戒护
        pause
        goto menu
    )
)
echo.
pause
goto menu
