# WebScribe · 智能网页探索与复刻工具

WebScribe 是一个强大的网页分析工具，能够自动探索网站、捕获网络请求、提取设计系统、生成前端代码等。

## 🌟 核心功能

### 1. 自主探索——像人一样浏览网站
- 打开指定网址，自动识别所有按钮、链接、可点击区域
- 像真人一样点击、输入、滚动、悬停，触发隐藏菜单、弹出窗口、懒加载内容
- 深度遍历整个网站，不放过任何一个页面和状态
- 支持登录页面自动填写（账号密码、验证码识别）

### 2. 全量捕获——不放过任何细节
- **网络请求**：页面加载时发出的所有 API 调用（XHR、Fetch）
- **WebSocket 消息**：实时通信的内容（如聊天消息、股票行情）
- **页面变化**：DOM 结构如何动态增减
- **设计系统**：颜色、字体、字号、圆角、间距，整理成 CSS 变量
- **性能指标**：页面加载时间、资源大小、优化建议
- **无障碍问题**：检测图片 alt、颜色对比度等 WCAG 合规问题
- **媒体资源**：图片、视频、音频链接，自动提取并分析
- **文字内容**：主要段落、文章正文，用于内容摘要或 SEO 分析

### 3. 智能生成——直接给你可用的开发材料
- **前端代码**：自动生成 React / Vue / Svelte 项目，包含完整项目结构
- **API 文档**：整理成 OpenAPI 3.0 规范文件，可导入 Postman、Apifox
- **设计系统**：输出 CSS 变量文件（`design_tokens.css`）
- **移动端适配**：分析媒体查询，生成移动端适配 CSS
- **状态图谱**：用 Mermaid 流程图画出页面跳转关系
- **综合报告**：HTML 报告汇总所有探索数据

## 🚀 快速启动

### 前置要求
- Docker 和 Docker Compose
- Node.js 18+（仅用于开发）
- Python 3.10+（仅用于开发）

### 一键启动（推荐）
```bash
# 克隆仓库
git clone https://github.com/qingshanjiluo/WebScribe.git
cd WebScribe

# 复制环境变量文件
cp .env.example .env

# 启动所有服务
docker-compose up -d
```

访问 http://localhost:5173 使用控制台。

### 手动启动（开发模式）
```bash
# 启动后端
cd backend
pip install -r requirements.txt
python -m playwright install chromium
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动前端（新终端）
cd frontend
npm install
npm run dev
```

## 📋 使用指南

### 1. 创建探索任务
1. 打开 WebScribe 控制台（http://localhost:5173）
2. 输入目标网址
3. 配置探索参数：
   - **探索深度**：最多点击几层（默认 3）
   - **最大页面数**：最多探索多少页面（默认 20）
   - **反爬策略**：开发/标准/隐匿/激进模式
   - **AI 代码生成**：是否生成前端代码
   - **登录凭据**：如需登录，填写用户名密码
4. 点击"开始探索"

### 2. 实时监控
- 控制台实时显示探索日志
- 查看正在访问的页面、点击的元素、捕获的请求
- 支持暂停、继续、跳过当前元素、停止

### 3. 下载成果
任务完成后，点击"下载报告"按钮，获得 ZIP 压缩包，包含：
- 前端代码（可直接 `npm start` 运行）
- OpenAPI 文档（可导入 Postman）
- 设计系统 CSS 变量
- 状态图（展示页面跳转关系）
- 性能分析报告
- 无障碍检测报告

## 🛠️ 技术架构

### 后端（Python + FastAPI）
- **FastAPI**：高性能 Web 框架
- **Playwright**：浏览器自动化
- **SQLAlchemy**：数据库 ORM
- **Redis + RQ**：任务队列
- **OpenAI API**：AI 代码生成

### 前端（React + Vite + TailwindCSS）
- **React 18**：用户界面
- **Vite**：构建工具
- **TailwindCSS**：样式框架
- **WebSocket**：实时日志流

### 数据库
- **SQLite**：默认数据库（开发）
- **PostgreSQL**：生产环境推荐

## 🔧 配置说明

### 环境变量
复制 `.env.example` 为 `.env` 并修改：
```env
# 数据库配置
DATABASE_URL=sqlite:///./data/webscribe.db

# Redis 配置
REDIS_URL=redis://redis:6379/0

# AI 配置（可选）
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# 代理配置（可选）
USE_PROXY=false
PROXY_LIST=http://proxy1:8080,http://proxy2:8080
```

### 反爬策略
- **开发模式**：无伪装，快速测试
- **标准模式**：随机 User-Agent，基础延迟
- **隐匿模式**：代理轮换，指纹随机化
- **激进模式**：模拟人类点击轨迹，高级反检测

## 📁 项目结构
```
WebScribe/
├── backend/              # 后端服务
│   ├── main.py          # FastAPI 主应用
│   ├── explorer.py      # 核心探索引擎
│   ├── ai_generator.py  # AI 代码生成
│   ├── design_extractor.py # 设计系统提取
│   └── ...
├── frontend/            # 前端控制台
│   ├── src/
│   │   ├── App.jsx      # 主组件
│   │   ├── components/  # 组件库
│   │   └── api.js       # API 客户端
│   └── ...
├── data/                # 数据存储
│   ├── reports/         # 生成的报告
│   └── screenshots/     # 页面截图
├── docker-compose.yml   # Docker 编排
└── README.md            # 本文档
```

## 🐳 Docker 部署

### 生产环境部署
```bash
# 构建镜像
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose logs -f
```

### Kubernetes 部署
```bash
kubectl apply -f k8s/
```

## 🔍 示例场景

### 分析电商网站
```bash
# 探索商品详情页到结算流程
网址：https://shop.example.com/product/123
配置：深度=3，页面数=30，反爬=激进，开启AI代码生成

# 结果：
# 1. 生成 React 项目，包含商品页、购物车、结算页组件
# 2. OpenAPI 文档，包含 /cart/add、/checkout 等接口
# 3. 设计系统：提取品牌色、字体、间距
# 4. 状态图：商品详情→购物车→结算→登录→订单确认
```

### 学习竞品设计
```bash
# 提取设计系统
网址：https://design.example.com
配置：深度=1，页面数=5，反爬=标准，关闭AI

# 结果：
# 1. design_tokens.css：包含所有颜色、字体变量
# 2. 响应式断点分析
# 3. 无障碍问题报告
```

## 🚨 注意事项

1. **合法使用**：仅用于学习、测试、授权分析，请遵守目标网站的 robots.txt
2. **性能影响**：探索过程会占用较多 CPU/内存，建议在服务器运行
3. **网络要求**：需要稳定的网络连接，国外网站建议配置代理
4. **存储空间**：截图和报告会占用磁盘空间，定期清理 data/ 目录

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 📞 支持与反馈

- 问题反馈：[GitHub Issues](https://github.com/qingshanjiluo/WebScribe/issues)
- 功能建议：[Discussions](https://github.com/qingshanjiluo/WebScribe/discussions)
- 文档更新：欢迎提交 PR 完善文档

---

**WebScribe** - 让网页逆向工程变得简单高效！