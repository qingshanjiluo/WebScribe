#!/bin/bash

echo "WebScribe 一键启动脚本"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装，请先安装 Docker"
    echo "下载地址: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo "错误: Docker 服务未运行，请启动 Docker"
    exit 1
fi

# 创建 .env 文件（如果不存在）
if [ ! -f .env ]; then
    echo "创建 .env 文件，请编辑填入你的 DeepSeek API Key"
    cp .env.example .env
    echo ""
    echo "注意：请编辑 .env 文件，设置你的 API Key 和其他配置"
    echo ""
fi

# 创建必要的目录
mkdir -p data/screenshots
mkdir -p data/reports

echo "正在启动 WebScribe 服务..."
echo ""

# 尝试使用 docker compose（新版本）
if docker compose version &> /dev/null; then
    echo "使用 docker compose 启动服务..."
    docker compose up -d
elif command -v docker-compose &> /dev/null; then
    echo "使用 docker-compose 启动服务..."
    docker-compose up -d
else
    echo "错误: 未找到 docker compose 或 docker-compose 命令"
    echo "请确保 Docker 已正确安装"
    exit 1
fi

if [ $? -ne 0 ]; then
    echo "错误: 启动服务失败，请检查 Docker 日志"
    exit 1
fi

echo ""
echo "========================================"
echo "WebScribe 服务已成功启动！"
echo ""
echo "访问前端控制台: http://localhost:5173"
echo "后端 API 文档: http://localhost:8000/docs"
echo ""
echo "查看服务状态: docker compose ps"
echo "查看服务日志: docker compose logs -f"
echo "停止服务: docker compose down"
echo "========================================"
echo ""

# 尝试打开浏览器（仅限 macOS 和 Linux）
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:5173
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:5173 2>/dev/null || echo "请手动访问: http://localhost:5173"
else
    echo "请手动访问: http://localhost:5173"
fi

echo ""
read -p "按回车键退出..."
