import asyncio
import hashlib
import json
import random
import string
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from . import models
from .anti_antispider import AntiAntiSpider
from .config import Settings
from .utils import save_screenshot, generate_mermaid
from .robots_checker import RobotsChecker
from .performance_analyzer import PerformanceAnalyzer
from .a11y_checker import A11yChecker
from .responsive_generator import ResponsiveGenerator
from .design_extractor import DesignExtractor
from .ai_generator import AIGenerator
from .ai_path_planner import AIPathPlanner
from .login_handler import LoginHandler
from .content_extractor import ContentExtractor

class Explorer:
    def __init__(self, task_id: int, db: Session, anti_level="standard"):
        self.task_id = task_id
        self.db = db
        self.anti_level = anti_level
        self.anti = AntiAntiSpider(level=anti_level, use_proxy=Settings.USE_PROXY, proxy_list=Settings.PROXY_LIST)
        self.robots = RobotsChecker()
        self.performance = PerformanceAnalyzer()
        self.a11y = A11yChecker()
        self.responsive = ResponsiveGenerator()
        self.visited_urls = set()
        self.requests = []
        self.screenshots = []
        self.state_graph = []
        self.last_state = None
        self.ws_connections = []
        self.dom_changes = []
        self.paused = False
        self.skip_current = False
        self.stop_requested = False
        self.current_depth = 0
        self.config = None
        self.design_tokens = None
        self.content_extractor = None
        self.login_handler = None
        self.ai_planner = None
        self.user_credentials = None

    async def run(self, config: dict):
        self.config = config
        await self._add_log("启动探索任务")
        if not await self.robots.can_fetch(config["start_url"]):
            await self._add_log("robots.txt 禁止抓取该网站", "error")
            self._update_task_status("failed")
            return

        # 初始化模块
        self.user_credentials = config.get('login_username') and config.get('login_password')
        if self.user_credentials:
            self.login_handler = LoginHandler(self.task_id, on_captcha_callback=self._request_captcha_input)
        if config.get('extract_content', False):
            self.content_extractor = ContentExtractor(self.task_id)
        if config.get('enable_ai_path', False) and Settings.DEEPSEEK_API_KEY:
            self.ai_planner = AIPathPlanner()

        try:
            async with async_playwright() as p:
                await self._launch_browser(p, config)
                page = await self.context.new_page()

                # 设置网络捕获
                page.on('response', self._on_response)

                await self.anti.apply_stealth(page)
                await self._setup_websocket_capture(page)
                await self._inject_mutation_observer(page)

                await self._explore_page(page, config["start_url"], depth=0)

                await self._add_log(f"探索完成，共访问 {len(self.visited_urls)} 个页面，捕获 {len(self.requests)} 个请求")
                await self._generate_final_artifacts(page)
                self._update_task_status("completed")

        except Exception as e:
            await self._add_log(f"探索失败: {str(e)}", "error")
            self._update_task_status("failed")
            raise
        finally:
            if self.browser:
                await self.browser.close()

    async def _launch_browser(self, playwright, config):
        launch_options = {
            "headless": config.get("headless", False),
            "args": self.anti.get_browser_args(),
        }
        if Settings.USE_PROXY and Settings.PROXY_LIST:
            proxy = self.anti.get_random_proxy()
            if proxy:
                launch_options["proxy"] = {"server": proxy}
        self.browser = await playwright.chromium.launch(**launch_options)
        self.context = await self.browser.new_context(
            user_agent=self.anti.get_random_ua(),
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )
        self.context.set_default_timeout(Settings.DEFAULT_TIMEOUT)

    def _on_response(self, response):
        request = response.request
        self.requests.append({
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "post_data": request.post_data,
            "status": response.status,
            "status_text": response.status_text,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def _setup_websocket_capture(self, page):
        def on_websocket(ws):
            conn = {"url": ws.url, "messages": []}
            self.ws_connections.append(conn)
            ws.on("framereceived", lambda data: conn["messages"].append(("receive", data)))
            ws.on("framesent", lambda data: conn["messages"].append(("send", data)))
        page.on("websocket", on_websocket)

    async def _inject_mutation_observer(self, page):
        await page.evaluate('''
            const observer = new MutationObserver(mutations => {
                const changes = mutations.map(m => ({
                    type: m.type,
                    target: m.target.nodeName,
                    addedNodes: m.addedNodes.length,
                    removedNodes: m.removedNodes.length,
                    attributeName: m.attributeName
                }));
                console.log('DOMChanges', changes);
            });
            observer.observe(document.body, { childList: true, subtree: true, attributes: true });
        ''')

    async def _explore_page(self, page, url, depth):
        while self.paused:
            await asyncio.sleep(0.5)
            if self.stop_requested:
                return
        if self.stop_requested:
            return
        if depth > self.config.get("max_depth", 5):
            return
        if url in self.visited_urls:
            return
        if len(self.visited_urls) >= Settings.MAX_PAGES_PER_TASK:
            return

        self.current_depth = depth
        await self._add_log(f"访问: {url} (深度 {depth})")
        self.visited_urls.add(url)

        try:
            await page.goto(url, wait_until="networkidle", timeout=Settings.DEFAULT_TIMEOUT)
        except Exception as e:
            await self._add_log(f"导航失败 {url}: {e}", "error")
            return

        await self.anti.random_delay(1000, 3000)

        if self.config.get("enable_screenshot", True):
            screenshot_path = await save_screenshot(page, self.task_id, url)
            self.screenshots.append(screenshot_path)

        state = await self._capture_state(page)
        self.last_state = state

        if depth == 0:
            perf_data = await self.performance.analyze(page)
            await self._add_log(f"性能评分: {perf_data['scores']['overall']}/100")
            a11y_data = await self.a11y.check(page)
            await self._add_log(f"无障碍违规项: {a11y_data['total_violations']}")
            extractor = DesignExtractor()
            self.design_tokens = await extractor.extract(page)

        # 登录处理
        if self.user_credentials and not await self._is_logged_in(page):
            await self._add_log("尝试自动登录...")
            success = await self.login_handler.try_login(page, self.user_credentials[0], self.user_credentials[1])
            if success:
                await self._add_log("登录成功")
            else:
                await self._add_log("登录失败", "warning")

        # 内容提取
        if self.content_extractor:
            content_data = await self.content_extractor.extract(page, url)
            await self._add_log(f"提取文本: {len(content_data['text_paragraphs'])} 段, 图片: {len(content_data['images'])} 张")

        await self._scroll_and_hover(page)
        await self._fill_and_submit_forms(page)

        elements = await self._get_clickable_elements(page)
        await self._add_log(f"发现 {len(elements)} 个可交互元素")

        # AI 路径规划
        if self.ai_planner and elements:
            elements = await self.ai_planner.rank_elements(page.url, await page.title(), elements)
            await self._add_log(f"AI 规划后优先点击: {[e.get('text','')[:20] for e in elements[:5]]}")

        for idx, el in enumerate(elements):
            if self.skip_current:
                self.skip_current = False
                continue
            if self.stop_requested:
                break
            if idx >= 20:
                break
            await self._try_click(page, el, depth)

        self.state_graph.append((url, url, "start"))

    async def _try_click(self, page, element, depth):
        try:
            await page.evaluate(f"document.querySelector('{element['selector']}').scrollIntoView()")
            await self.anti.random_delay(200, 500)
            if self.anti_level != "dev":
                success = await self.anti.human_like_click(page, element['selector'])
                if not success:
                    await page.click(element["selector"], timeout=3000)
            else:
                await page.click(element["selector"], timeout=3000)
            await self.anti.random_delay(500, 1000)

            if page.url != element.get("_original_url", page.url):
                self.state_graph.append((element.get("_original_url", page.url), page.url, "click"))
                await self._explore_page(page, page.url, depth+1)
                await page.go_back()
            else:
                new_state = await self._capture_state(page)
                if new_state["content_hash"] != element.get("_state_hash"):
                    await self._explore_page(page, page.url, depth+1)
        except Exception as e:
            await self._add_log(f"点击 {element['selector']} 失败: {e}", "warning")

    async def _capture_state(self, page):
        content = await page.content()
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return {"url": page.url, "content_hash": content_hash}

    async def _get_clickable_elements(self, page):
        return await page.evaluate('''
            () => {
                const selectors = ['a', 'button', '[role="button"]', '[onclick]'];
                const elements = document.querySelectorAll(selectors.join(','));
                const results = [];
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return;
                    let selector = '';
                    if (el.id) selector = `#${el.id}`;
                    else if (el.className && typeof el.className === 'string') {
                        const classes = el.className.split(/\\s+/).filter(c => c && !/^\\d/.test(c));
                        if (classes.length) selector = `.${classes[0]}`;
                    } else {
                        selector = el.tagName.toLowerCase();
                    }
                    results.push({
                        selector: selector,
                        tagName: el.tagName.toLowerCase(),
                        text: (el.textContent || '').trim().slice(0, 100),
                        href: el.href || null,
                    });
                });
                return results;
            }
        ''')

    async def _fill_and_submit_forms(self, page):
        forms = await page.query_selector_all('form')
        for form in forms:
            inputs = await form.query_selector_all('input, textarea, select')
            for inp in inputs:
                await self._fill_input(page, inp)
            submit_btns = await form.query_selector_all('button[type="submit"], input[type="submit"], button:has-text("提交"), button:has-text("登录")')
            if submit_btns:
                await submit_btns[0].click()
                await page.wait_for_load_state('networkidle')
                await self._add_log("提交表单，页面可能发生变化")

    async def _fill_input(self, page, element):
        type_ = await element.get_attribute('type')
        name = await element.get_attribute('name') or ''
        placeholder = await element.get_attribute('placeholder') or ''
        value = self._generate_fake_value(type_, name, placeholder)
        if value:
            await element.fill(value)
            await self._add_log(f"填充输入框 {name or placeholder} 值为 {value}")

    def _generate_fake_value(self, input_type, name, placeholder):
        input_type = input_type or ''
        if 'email' in input_type or 'email' in name or 'email' in placeholder:
            return f"test_{random.randint(1,1000)}@example.com"
        if 'password' in input_type or 'password' in name:
            return "Test@123456"
        if 'phone' in input_type or 'phone' in name:
            return f"138{random.randint(10000000,99999999)}"
        if 'search' in input_type:
            return "test search"
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    async def _scroll_and_hover(self, page):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * Math.random())")
        await self.anti.random_delay(500, 1500)
        elements = await page.query_selector_all('a, button, div[onclick], [role="button"]')
        visible = [el for el in elements if await el.is_visible()]
        if visible:
            target = random.choice(visible)
            await target.hover()
            await self.anti.random_delay(300, 1000)

    async def _is_logged_in(self, page):
        avatar = await page.query_selector('img[alt*="avatar"], .avatar')
        return avatar is not None

    async def _request_captcha_input(self, task_id, img_base64):
        # 这里需要与前端通信，通过 WebSocket 发送验证码图片并等待用户输入
        # 实现略，返回模拟
        return ""

    async def _generate_final_artifacts(self, page):
        report_dir = Path(Settings.REPORT_DIR) / f"task_{self.task_id}"
        report_dir.mkdir(parents=True, exist_ok=True)

        # 1. 响应式CSS
        responsive_css = await self.responsive.generate(page)
        (report_dir / "responsive.css").write_text(responsive_css)

        # 2. 设计系统CSS变量
        if self.design_tokens:
            extractor = DesignExtractor()
            extractor.colors = self.design_tokens.get('colors', {})
            extractor.fonts = self.design_tokens.get('fonts', {})
            extractor.font_sizes = self.design_tokens.get('font_sizes', {})
            extractor.border_radius = self.design_tokens.get('border_radius', {})
            css_vars = extractor.to_css_variables()
            (report_dir / "design_tokens.css").write_text(css_vars)

        # 3. 状态图
        mermaid = generate_mermaid(self.state_graph)
        (report_dir / "state_graph.mmd").write_text(mermaid)

        # 4. 请求数据
        with open(report_dir / "requests.json", "w") as f:
            json.dump(self.requests, f, indent=2)
        with open(report_dir / "screenshots.json", "w") as f:
            json.dump(self.screenshots, f, indent=2)

        # 5. OpenAPI 文档
        try:
            ai = AIGenerator()
            openapi_spec = await ai.generate_openapi_spec(self.requests)
            with open(report_dir / "openapi.yaml", "w", encoding="utf-8") as f:
                import yaml
                yaml.dump(openapi_spec, f, allow_unicode=True, default_flow_style=False)
            with open(report_dir / "openapi.json", "w", encoding="utf-8") as f:
                json.dump(openapi_spec, f, indent=2, ensure_ascii=False)
        except Exception as e:
            await self._add_log(f"生成OpenAPI文档失败: {e}", "warning")

        # 6. AI生成代码（如果启用）
        if self.config.get("enable_ai", False) and Settings.DEEPSEEK_API_KEY:
            try:
                ai = AIGenerator()
                project_files = await ai.generate_full_project(
                    self.requests[:20],
                    self.design_tokens or {},
                    framework="react"
                )
                project_dir = report_dir / "generated_code"
                project_dir.mkdir(exist_ok=True)
                for path, content in project_files.items():
                    full_path = project_dir / path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
            except Exception as e:
                await self._add_log(f"AI生成代码失败: {e}", "warning")

        # 7. 改进的HTML报告
        stats = {
            "pages_visited": len(self.visited_urls),
            "requests_captured": len(self.requests),
            "screenshots": len(self.screenshots),
            "performance_score": "N/A",
            "timestamp": datetime.now().isoformat()
        }
        try:
            ai = AIGenerator()
            report_html = await ai.generate_html_report(self.task_id, self.config, stats)
        except Exception as e:
            await self._add_log(f"生成HTML报告失败，使用默认报告: {e}", "warning")
            report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebScribe Report - Task {self.task_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 2rem; background: #f9f9f9; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 0.5rem; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 2rem 0; }}
        .stat-card {{ background: #f8f9fa; padding: 1.5rem; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2rem; font-weight: bold; color: #3498db; }}
        .section {{ margin: 2rem 0; }}
        pre {{ background: #2c3e50; color: #ecf0f1; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>WebScribe Exploration Report</h1>
        <p><strong>Task ID:</strong> {self.task_id}</p>
        <p><strong>Start URL:</strong> {self.config.get('start_url', 'N/A')}</p>
        <p><strong>Exploration Time:</strong> {stats['timestamp']}</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{stats['pages_visited']}</div>
                <div class="stat-label">Pages Visited</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['requests_captured']}</div>
                <div class="stat-label">Requests Captured</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['screenshots']}</div>
                <div class="stat-label">Screenshots</div>
            </div>
        </div>

        <div class="section">
            <h2>Generated Artifacts</h2>
            <ul>
                <li><strong>Frontend Code:</strong> React project with mock API</li>
                <li><strong>OpenAPI Specification:</strong> API documentation in OpenAPI 3.0 format</li>
                <li><strong>Design System:</strong> CSS variables extracted from the site</li>
                <li><strong>Responsive CSS:</strong> Media queries for mobile adaptation</li>
                <li><strong>State Graph:</strong> Mermaid diagram of page transitions</li>
            </ul>
        </div>

        <div class="section">
            <h2>Next Steps</h2>
            <p>Download the generated ZIP file and extract it. Run the following commands to start the generated application:</p>
            <pre>cd generated_code
npm install
npm start</pre>
        </div>
    </div>
</body>
</html>"""
        (report_dir / "report.html").write_text(report_html)

        # 8. 保存结果到数据库
        result = models.Result(
            task_id=self.task_id,
            page_url=self.config['start_url'],
            screenshot_path=str(report_dir / "screenshots.json"),
            design_tokens=json.dumps(self.design_tokens) if self.design_tokens else None,
            requests=json.dumps(self.requests),
            generated_code=json.dumps({"dir": str(report_dir / "generated_code")}) if self.config.get("enable_ai") else None,
            report_path=str(report_dir / "report.html"),
            openapi_path=str(report_dir / "openapi.yaml")
        )
        self.db.add(result)
        self.db.commit()

    async def _add_log(self, message, level="info"):
        log = models.Log(task_id=self.task_id, message=message, level=level)
        self.db.add(log)
        self.db.commit()
        # 可以在这里添加 WebSocket 广播

    def _update_task_status(self, status):
        task = self.db.query(models.Task).get(self.task_id)
        if task:
            task.status = status
            if status == "completed":
                task.completed_at = datetime.utcnow()
            self.db.commit()