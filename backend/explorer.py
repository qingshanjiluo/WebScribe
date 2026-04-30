import asyncio
import hashlib
import html
import json
import random
import string
import traceback
from urllib.parse import urldefrag, urljoin, urlparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import aiohttp
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
        self.page_snapshots = []
        self.interactive_elements = []
        self.discovered_urls = set()
        self.asset_manifest = []
        self.attempted_actions = set()
        self.total_interactions = 0
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
        self.browser = None
        self.context = None

    async def run(self, config: dict):
        self.config = config
        safe_config = {k: ("***" if "key" in k.lower() or "password" in k.lower() else v) for k, v in config.items()}
        await self._add_log(f"启动探索任务，配置: {json.dumps(safe_config, ensure_ascii=False)}")
        if not await self.robots.can_fetch(config["start_url"]):
            await self._add_log("robots.txt 禁止抓取该网站", "error")
            self._update_task_status("failed")
            return

        # 初始化模块
        username = config.get("login_username")
        password = config.get("login_password")
        self.user_credentials = (username, password) if username and password else None
        if self.user_credentials:
            self.login_handler = LoginHandler(self.task_id, on_captcha_callback=self._request_captcha_input)
        if config.get('extract_content', False):
            self.content_extractor = ContentExtractor(self.task_id)
        ai_config = Settings.ai_config(config)
        if config.get('enable_ai_path', False) and ai_config["api_key"]:
            self.ai_planner = AIPathPlanner(config)

        try:
            async with async_playwright() as p:
                await self._launch_browser(p, config)
                page = await self.context.new_page()
                page.on("console", lambda msg: self.dom_changes.append({"type": "console", "text": msg.text, "timestamp": datetime.utcnow().isoformat()}))

                # 设置网络捕获
                page.on('response', self._on_response)

                await self.anti.apply_stealth(page)
                await self._setup_websocket_capture(page)
                await self._inject_mutation_observer(page)

                await self._explore_page(page, config["start_url"], depth=0)

                await self._add_log(f"探索完成，共访问 {len(self.visited_urls)} 个页面，捕获 {len(self.requests)} 个请求")
                await self._generate_final_artifacts(page)
                self._update_task_status("completed")

        except BaseException as e:
            tb = traceback.format_exc()
            err_msg = str(e) or type(e).__name__
            await self._add_log(f"探索失败: {err_msg}", "error")
            print(f"[Explorer] Task {self.task_id} failed:\n{tb}")
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
        await self._add_log(f"启动 Chromium，headless={launch_options['headless']}，反爬策略={self.anti_level}")
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
        await self._add_log(f"浏览器上下文已创建，超时={Settings.DEFAULT_TIMEOUT}ms，viewport=1280x720")

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
        if response.status >= 400:
            try:
                self.db.add(models.Log(
                    task_id=self.task_id,
                    message=f"请求异常 {response.status}: {request.method} {request.url}",
                    level="warning",
                ))
                self.db.commit()
            except Exception:
                self.db.rollback()

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
        max_pages = min(self.config.get("max_pages", Settings.MAX_PAGES_PER_TASK), Settings.MAX_PAGES_PER_TASK)
        if len(self.visited_urls) >= max_pages:
            return

        self.current_depth = depth
        url = self._normalize_url(url)
        if not self._is_allowed_url(url):
            await self._add_log(f"跳过非允许范围 URL: {url}", "warning")
            return
        await self._add_log(f"访问: {url} (深度 {depth})")
        self.visited_urls.add(url)

        try:
            await self._add_log(f"开始导航: {url}")
            await page.goto(url, wait_until="networkidle", timeout=Settings.DEFAULT_TIMEOUT)
            await self._add_log(f"导航完成: {page.url}，标题: {await page.title()}")
            await self._save_live_html(page)
        except Exception as e:
            await self._add_log(f"导航失败 {url}: {e}", "error")
            return

        await self.anti.random_delay(1000, 3000)

        if self.config.get("enable_screenshot", True):
            screenshot_path = await save_screenshot(page, self.task_id, url)
            self.screenshots.append(screenshot_path)
            await self._add_log(f"已保存页面截图: {screenshot_path}")

        state = await self._capture_state(page)
        self.last_state = state

        if depth == 0:
            perf_data = await self.performance.analyze(page)
            await self._add_log(f"性能评分: {perf_data['scores']['overall']}/100")
            a11y_data = await self.a11y.check(page)
            await self._add_log(f"无障碍违规项: {a11y_data['total_violations']}")
            extractor = DesignExtractor()
            self.design_tokens = await extractor.extract(page)
            await self._add_log(
                f"设计信息: 颜色 {len(self.design_tokens.get('colors', {}))} 个，字体 {len(self.design_tokens.get('fonts', {}))} 个，字号 {len(self.design_tokens.get('font_sizes', {}))} 个"
            )

        # 登录处理
        if self.user_credentials and await self._has_login_form(page):
            await self._add_log("尝试自动登录...")
            success = await self.login_handler.try_login(page, self.user_credentials[0], self.user_credentials[1])
            if success:
                await self._add_log("登录成功")
            else:
                await self._add_log("登录失败", "warning")

        # 内容提取：优先通过脚本从 DOM 读取网页内容，后续再交给 AI 生成/完善。
        if self.content_extractor:
            content_data = await self.content_extractor.extract(page, url)
            await self._add_log(f"提取文本: {len(content_data['text_paragraphs'])} 段, 图片: {len(content_data['images'])} 张")

        await self._scroll_and_hover(page)
        await self._handle_forms(page)

        elements = await self._get_clickable_elements(page)
        self.interactive_elements = elements
        await self._add_log(f"发现 {len(elements)} 个可交互元素")
        for el in elements[:8]:
            await self._add_log(f"候选元素: {el.get('tagName')} selector={el.get('selector')} text={el.get('text', '')[:40]}")

        # AI 路径规划
        if self.ai_planner and elements:
            elements = await self.ai_planner.rank_elements(page.url, await page.title(), elements)
            await self._add_log(f"AI 规划后优先点击: {[e.get('text','')[:20] for e in elements[:5]]}")

        links = await self._discover_links(page)
        await self._add_log(f"发现 {len(links)} 个同域可递归链接")
        for link in links[: self.config.get("max_pages", 20)]:
            if self.stop_requested:
                break
            while self.paused:
                await asyncio.sleep(0.5)
            if len(self.visited_urls) >= max_pages:
                break
            if depth < self.config.get("max_depth", 5) and link not in self.visited_urls:
                await self._explore_page(page, link, depth + 1)
                try:
                    await page.goto(url, wait_until="networkidle", timeout=Settings.DEFAULT_TIMEOUT)
                except Exception as exc:
                    await self._add_log(f"返回父页面失败: {exc}", "warning")
                    break

        for idx, el in enumerate(elements):
            if self.stop_requested:
                break
            while self.paused:
                await asyncio.sleep(0.5)
            if self.skip_current:
                self.skip_current = False
                continue
            if self.stop_requested:
                break
            if idx >= self.config.get("max_interactions_per_page", 20):
                break
            if self.total_interactions >= self.config.get("max_total_interactions", 80):
                await self._add_log("达到全局交互次数上限，停止继续模拟点击", "warning")
                break
            await self._try_click(page, el, depth)

        self.state_graph.append((url, url, "start"))

    def _normalize_url(self, url: str) -> str:
        normalized, _fragment = urldefrag(url)
        return normalized.rstrip("/")

    def _is_allowed_url(self, url: str) -> bool:
        start = urlparse(self.config.get("start_url", url))
        current = urlparse(url)
        if current.scheme not in ("http", "https"):
            return False
        if self.config.get("same_origin_only", True):
            return current.netloc == start.netloc
        return True

    async def _discover_links(self, page):
        hrefs = await page.evaluate("""() => [...document.querySelectorAll('a[href], area[href]')]
            .map(a => a.href)
            .filter(Boolean)
        """)
        links = []
        for href in hrefs:
            url = self._normalize_url(urljoin(page.url, href))
            if url not in self.visited_urls and self._is_allowed_url(url):
                self.discovered_urls.add(url)
                links.append(url)
        return list(dict.fromkeys(links))

    async def _try_click(self, page, element, depth):
        selector = element.get("selector")
        action_key = (
            self._normalize_url(page.url),
            selector,
            element.get("text", "")[:80],
            element.get("action", "click"),
        )
        if action_key in self.attempted_actions:
            await self._add_log(f"跳过重复交互: {selector}", "warning")
            return
        self.attempted_actions.add(action_key)
        self.total_interactions += 1
        try:
            await self._add_log(f"尝试交互: action={element.get('action')} selector={selector} text={element.get('text', '')[:50]}")
            before = await self._save_named_screenshot(page, f"before_{len(self.page_snapshots)}")
            await self._perform_element_action(page, element)
            await self.anti.random_delay(600, 1200)
            after = await self._save_named_screenshot(page, f"after_{len(self.page_snapshots)}")
            await self._add_log(f"交互截图: before={before}, after={after}")
            await self._save_live_html(page)

            if page.url != element.get("_original_url", page.url):
                self.state_graph.append((element.get("_original_url", page.url), page.url, "click"))
                await self._explore_page(page, page.url, depth+1)
                await page.go_back()
            else:
                new_state = await self._capture_state(page)
                if new_state["content_hash"] != element.get("_state_hash"):
                    await self._add_log(f"点击后页面状态变化: {element.get('selector')}")
                    await self._explore_page(page, page.url, depth+1)
        except Exception as e:
            await self._add_log(f"交互 {selector} 失败: {e}", "warning")

    async def _perform_element_action(self, page, element):
        selector = element.get("selector")
        action = element.get("action", "click")
        box = element.get("box") or {}
        if action == "input":
            locator = page.locator(selector).first
            if callable(locator):
                locator = locator()
            await locator.scroll_into_view_if_needed()
            type_ = element.get("type", "")
            if type_ in ("password",):
                await self._add_log(f"输入框需要真实敏感数据，跳过自动填充: {selector}", "warning")
                return
            value = self._generate_fake_value(type_, "", element.get("text", ""))
            await locator.fill(value, timeout=3000)
            await self._add_log(f"已填充输入框 {selector}: {value}")
            return

        errors = []
        for strategy in ("selector-human", "selector-click", "coordinate", "js-click"):
            try:
                if strategy == "selector-human":
                    await page.locator(selector).first.scroll_into_view_if_needed()
                    if self.anti_level != "dev":
                        ok = await self.anti.human_like_click(page, selector)
                        if not ok:
                            raise RuntimeError("human_like_click returned false")
                    else:
                        raise RuntimeError("dev 模式跳过 human_like_click")
                elif strategy == "selector-click":
                    await page.locator(selector).first.click(timeout=3000)
                elif strategy == "coordinate":
                    if not box:
                        raise RuntimeError("缺少坐标")
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2
                    await page.mouse.click(x, y)
                else:
                    await page.evaluate(
                        """selector => {
                            const el = document.querySelector(selector);
                            if (!el) throw new Error('element not found');
                            el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
                            el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                            el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                            el.click();
                        }""",
                        selector,
                    )
                await self._add_log(f"交互成功: {strategy} -> {selector}")
                return
            except Exception as exc:
                errors.append(f"{strategy}: {exc}")
        raise RuntimeError("; ".join(errors))

    async def _save_named_screenshot(self, page, name):
        report_dir = Path(Settings.REPORT_DIR) / f"task_{self.task_id}" / "interaction_screenshots"
        report_dir.mkdir(parents=True, exist_ok=True)
        path = report_dir / f"{name}_{datetime.now().strftime('%H%M%S_%f')}.png"
        await page.screenshot(path=str(path), full_page=True)
        self.page_snapshots.append(str(path))
        return str(path)

    async def _save_live_html(self, page):
        report_dir = Path(Settings.REPORT_DIR) / f"task_{self.task_id}"
        report_dir.mkdir(parents=True, exist_ok=True)
        html = await page.content()
        inject = f"""
  <base href="{page.url}">
  <style>
    body::before {{
      content: "WebScribe live snapshot: {page.url}";
      position: fixed;
      left: 0;
      right: 0;
      top: 0;
      z-index: 2147483647;
      padding: 6px 10px;
      background: rgba(17, 24, 39, .92);
      color: #fff;
      font: 12px/1.4 system-ui, sans-serif;
    }}
    body {{ padding-top: 28px !important; }}
  </style>
"""
        if "</head>" in html.lower():
            head_index = html.lower().find("</head>")
            html = html[:head_index] + inject + html[head_index:]
        else:
            html = f"<!doctype html><html><head>{inject}</head><body>{html}</body></html>"
        (report_dir / "live.html").write_text(html, encoding="utf-8")
        await self._add_log(f"实时 HTML 快照已更新: {report_dir / 'live.html'}")

    async def _capture_state(self, page):
        content = await page.content()
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return {"url": page.url, "content_hash": content_hash}

    async def _get_clickable_elements(self, page):
        return await page.evaluate('''
            () => {
                const stateHash = document.documentElement.innerText.length + ':' + document.querySelectorAll('*').length;
                const cssEscape = window.CSS && CSS.escape ? CSS.escape : (v) => String(v).replace(/["\\\\#.;?+*~':!^$[\\]()=>|/@]/g, '\\\\$&');
                const uniqueSelector = (el) => {
                    if (el.id) return `#${cssEscape(el.id)}`;
                    const parts = [];
                    let node = el;
                    while (node && node.nodeType === 1 && parts.length < 5) {
                        let part = node.tagName.toLowerCase();
                        const testId = node.getAttribute('data-testid') || node.getAttribute('data-test') || node.getAttribute('data-v');
                        if (testId) {
                            part += `[${node.hasAttribute('data-testid') ? 'data-testid' : node.hasAttribute('data-test') ? 'data-test' : 'data-v'}="${testId}"]`;
                            parts.unshift(part);
                            break;
                        }
                        const cls = [...node.classList].filter(c => c && !/^\\d/.test(c)).slice(0, 2);
                        if (cls.length) part += '.' + cls.map(cssEscape).join('.');
                        const parent = node.parentElement;
                        if (parent) {
                            const same = [...parent.children].filter(child => child.tagName === node.tagName);
                            if (same.length > 1) part += `:nth-of-type(${same.indexOf(node) + 1})`;
                        }
                        parts.unshift(part);
                        node = parent;
                    }
                    return parts.join(' > ');
                };
                const selectors = [
                    'a[href]', 'button', 'input', 'textarea', 'select', 'summary',
                    '[role="button"]', '[role="link"]', '[role="menuitem"]', '[role="tab"]',
                    '[onclick]', '[tabindex]:not([tabindex="-1"])',
                    '[class*="btn" i]', '[class*="button" i]', '[class*="login" i]',
                    '[class*="submit" i]', '[class*="nav" i]', '[class*="menu" i]',
                    '[style*="cursor: pointer"]'
                ];
                const elements = [...document.querySelectorAll(selectors.join(','))];
                const results = [];
                const seen = new Set();
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    if (rect.width === 0 || rect.height === 0 || style.visibility === 'hidden' || style.display === 'none') return;
                    const selector = uniqueSelector(el);
                    if (!selector || seen.has(selector)) return;
                    seen.add(selector);
                    const tag = el.tagName.toLowerCase();
                    const type = el.getAttribute('type') || '';
                    const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.value || '').trim().slice(0, 120);
                    const action = ['input', 'textarea', 'select'].includes(tag) ? 'input' : 'click';
                    results.push({
                        selector: selector,
                        tagName: tag,
                        type,
                        action,
                        text,
                        href: el.href || null,
                        _original_url: location.href,
                        _state_hash: stateHash,
                        box: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) }
                    });
                });
                return results.slice(0, 120);
            }
        ''')

    async def _handle_forms(self, page):
        forms = await page.query_selector_all('form')
        if not forms:
            inputs = await page.query_selector_all('input, textarea, select')
            visible_inputs = [inp for inp in inputs if await inp.is_visible()]
            if visible_inputs:
                fields = []
                for inp in visible_inputs:
                    name = await inp.get_attribute('name') or ''
                    placeholder = await inp.get_attribute('placeholder') or ''
                    type_ = await inp.get_attribute('type') or ''
                    fields.append(placeholder or name or type_ or 'input')
                if self.config.get("ask_user_for_inputs", True):
                    shot = await save_screenshot(page, self.task_id, page.url)
                    await self._add_log(f"发现页面输入框但没有 form，已保存截图 {shot}，字段: {', '.join(fields)}。请提供真实数据或登录信息后继续。", "warning")
                    return
        for form in forms:
            if await form.query_selector('input[type="password"]'):
                continue
            if self.config.get("ask_user_for_inputs", True):
                fields = await self._describe_form_fields(form)
                if fields:
                    shot = await save_screenshot(page, self.task_id, page.url)
                    await self._add_log(f"发现需要填写的表单，已保存截图 {shot}，字段: {', '.join(fields)}。请根据页面手动提供数据后重新创建任务。", "warning")
                    continue
            inputs = await form.query_selector_all('input, textarea, select')
            for inp in inputs:
                await self._fill_input(page, inp)
            submit_btns = await form.query_selector_all('button[type="submit"], input[type="submit"], button:has-text("提交"), button:has-text("登录")')
            if submit_btns:
                await submit_btns[0].click()
                await page.wait_for_load_state('networkidle')
                await self._add_log("提交表单，页面可能发生变化")

    async def _describe_form_fields(self, form):
        fields = []
        inputs = await form.query_selector_all('input, textarea, select')
        for inp in inputs:
            type_ = await inp.get_attribute('type') or inp.__class__.__name__
            if type_ in ("hidden", "submit", "button"):
                continue
            name = await inp.get_attribute('name') or ''
            placeholder = await inp.get_attribute('placeholder') or ''
            label = await inp.get_attribute('aria-label') or ''
            fields.append(label or placeholder or name or type_)
        return fields

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
        try:
            await page.evaluate("window.scrollTo(0, Math.min(document.body.scrollHeight, window.innerHeight * 1.2))")
            await self.anti.random_delay(300, 800)
        except Exception as exc:
            await self._add_log(f"滚动探测失败，继续后续抓取: {exc}", "warning")
            return

        try:
            elements = await page.query_selector_all('a, button, div[onclick], [role="button"]')
            visible = [el for el in elements[:80] if await el.is_visible()]
            if not visible:
                return
            target = random.choice(visible)
            try:
                await target.hover(timeout=1500)
            except Exception as exc:
                await self._add_log(f"hover 被遮罩或浮层阻止，已跳过: {str(exc).splitlines()[0]}", "warning")
                return
            await self.anti.random_delay(200, 500)
        except Exception as exc:
            await self._add_log(f"hover 探测失败，继续后续抓取: {exc}", "warning")

    async def _has_login_form(self, page):
        return await page.query_selector('input[type="password"]') is not None

    async def _request_captcha_input(self, task_id, img_base64):
        # 这里需要与前端通信，通过 WebSocket 发送验证码图片并等待用户输入
        # 实现略，返回模拟
        return ""

    async def _generate_final_artifacts(self, page):
        report_dir = Path(Settings.REPORT_DIR) / f"task_{self.task_id}"
        report_dir.mkdir(parents=True, exist_ok=True)

        # 1. 响应式CSS
        responsive_css = await self.responsive.generate(page)
        (report_dir / "responsive.css").write_text(responsive_css, encoding="utf-8")

        # 2. 设计系统CSS变量
        if self.design_tokens:
            extractor = DesignExtractor()
            extractor.colors = self.design_tokens.get('colors', {})
            extractor.fonts = self.design_tokens.get('fonts', {})
            extractor.font_sizes = self.design_tokens.get('font_sizes', {})
            extractor.border_radius = self.design_tokens.get('border_radius', {})
            css_vars = extractor.to_css_variables()
            (report_dir / "design_tokens.css").write_text(css_vars, encoding="utf-8")

        # 3. 状态图
        mermaid = generate_mermaid(self.state_graph)
        (report_dir / "state_graph.mmd").write_text(mermaid, encoding="utf-8")

        # 4. 请求数据
        with open(report_dir / "requests.json", "w", encoding="utf-8") as f:
            json.dump(self.requests, f, indent=2)
        with open(report_dir / "screenshots.json", "w", encoding="utf-8") as f:
            json.dump(self.screenshots, f, indent=2)

        # 5. 静态复刻版网页：无论 AI 是否可用，都输出一个可直接打开的 replica_site。
        replica_dir = await self._generate_replica_site(page, report_dir)
        if self.config.get("mirror_assets", True):
            await self._download_assets(page, replica_dir)

        # 6. OpenAPI 文档
        try:
            ai = AIGenerator(self.config)
            openapi_spec = ai.generate_openapi_spec(self.requests)
            with open(report_dir / "openapi.yaml", "w", encoding="utf-8") as f:
                import yaml
                yaml.dump(openapi_spec, f, allow_unicode=True, default_flow_style=False)
            with open(report_dir / "openapi.json", "w", encoding="utf-8") as f:
                json.dump(openapi_spec, f, indent=2, ensure_ascii=False)
        except Exception as e:
            await self._add_log(f"生成OpenAPI文档失败: {e}", "warning")

        # 7. AI生成可运行前端项目（如果启用）
        ai_config = Settings.ai_config(self.config)
        if self.config.get("enable_ai", False) and ai_config["api_key"]:
            try:
                ai = AIGenerator(self.config)
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
                    full_path.write_text(content, encoding="utf-8")
            except Exception as e:
                await self._add_log(f"AI生成代码失败: {e}", "warning")

        # 8. 改进的HTML报告
        stats = {
            "pages_visited": len(self.visited_urls),
            "requests_captured": len(self.requests),
            "screenshots": len(self.screenshots),
            "performance_score": "N/A",
            "timestamp": datetime.now().isoformat()
        }
        try:
            ai = AIGenerator(self.config)
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
        report_html = report_html.replace(
            "<h2>Generated Artifacts</h2>",
            f"""<h2>Generated Artifacts</h2>
            <p><strong>完整静态复刻网页:</strong> <a href="./replica_site/index.html">replica_site/index.html</a></p>
            <p><strong>复刻说明:</strong> <a href="./replica_site/README.md">replica_site/README.md</a></p>
            <p><strong>爬虫脚本:</strong> <a href="./custom_crawler.py">custom_crawler.py</a>（可在“生成针对性爬虫”后创建/更新）</p>"""
        )
        (report_dir / "report.html").write_text(report_html, encoding="utf-8")

        manifest = {
            "task_id": self.task_id,
            "target_url": self.config.get("start_url"),
            "report": str(report_dir / "report.html"),
            "replica_site": str(replica_dir / "index.html"),
            "replica_readme": str(replica_dir / "README.md"),
            "crawler_script": str(report_dir / "custom_crawler.py"),
            "requests": str(report_dir / "requests.json"),
            "screenshots": self.screenshots,
            "interaction_screenshots": self.page_snapshots,
            "interactive_elements": str(report_dir / "interactive_elements.json"),
            "asset_manifest": str(replica_dir / "data" / "assets.json"),
            "openapi": str(report_dir / "openapi.yaml"),
            "generated_code": str(report_dir / "generated_code"),
        }
        (report_dir / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (report_dir / "interactive_elements.json").write_text(json.dumps(self.interactive_elements, ensure_ascii=False, indent=2), encoding="utf-8")
        (report_dir / "page_snapshots.json").write_text(json.dumps(self.page_snapshots, ensure_ascii=False, indent=2), encoding="utf-8")

        # 8. 保存结果到数据库
        result = models.Result(
            task_id=self.task_id,
            page_url=self.config['start_url'],
            screenshot_path=str(report_dir / "screenshots.json"),
            design_tokens=self.design_tokens if self.design_tokens else None,
            requests=self.requests,
            generated_code={"dir": str(report_dir / "generated_code")} if self.config.get("enable_ai") else None,
            report_path=str(report_dir / "report.html"),
            openapi_path=str(report_dir / "openapi.yaml")
        )
        self.db.add(result)
        self.db.commit()
        await self._add_log(f"报告已生成: {report_dir / 'report.html'}")
        await self._add_log(f"完整静态复刻网页已生成: {replica_dir / 'index.html'}")

    async def _generate_replica_site(self, page, report_dir: Path) -> Path:
        replica_dir = report_dir / "replica_site"
        assets_dir = replica_dir / "assets"
        data_dir = replica_dir / "data"
        replica_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(exist_ok=True)
        data_dir.mkdir(exist_ok=True)

        current_url = page.url
        title = await page.title()
        body_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
        dom_html = await page.content()
        controls = await page.evaluate("""
        () => [...document.querySelectorAll('a[href], button, input, textarea, select, [role="button"], [onclick]')].slice(0, 200).map((el, index) => {
          const rect = el.getBoundingClientRect();
          return {
            index,
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute('type') || '',
            text: (el.innerText || el.textContent || el.getAttribute('placeholder') || el.getAttribute('aria-label') || el.value || '').trim().slice(0, 160),
            href: el.href || '',
            name: el.getAttribute('name') || '',
            role: el.getAttribute('role') || '',
            box: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) }
          };
        })
        """)
        screenshot_rel = ""
        if self.screenshots:
            source = Path(self.screenshots[-1])
            if source.exists():
                target = assets_dir / "snapshot.png"
                target.write_bytes(source.read_bytes())
                screenshot_rel = "assets/snapshot.png"

        styles = """:root {
  --replica-bg: #f7f8fb;
  --replica-panel: #ffffff;
  --replica-text: #111827;
  --replica-muted: #6b7280;
  --replica-border: #d8dee9;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--replica-bg); color: var(--replica-text); }
.webscribe-toolbar { position: sticky; top: 0; z-index: 9999; display: flex; gap: 12px; align-items: center; justify-content: space-between; padding: 10px 16px; background: #111827; color: white; font-size: 13px; }
.webscribe-toolbar a { color: #93c5fd; }
.webscribe-shell { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 16px; padding: 16px; }
.webscribe-page { min-height: 80vh; overflow: auto; border: 1px solid var(--replica-border); background: white; }
.webscribe-side { border: 1px solid var(--replica-border); background: var(--replica-panel); padding: 16px; }
.webscribe-side h2 { margin: 0 0 12px; font-size: 18px; }
.webscribe-side pre { max-height: 360px; overflow: auto; white-space: pre-wrap; background: #0f172a; color: #e5e7eb; padding: 12px; border-radius: 6px; font-size: 12px; }
.webscribe-snapshot { width: 100%; border: 1px solid var(--replica-border); border-radius: 6px; margin: 10px 0; }
.replica-controls { display: grid; gap: 8px; max-height: 320px; overflow: auto; margin-bottom: 14px; }
.replica-control { display: grid; gap: 3px; width: 100%; padding: 8px 10px; border: 1px solid var(--replica-border); border-radius: 6px; background: #f9fafb; color: #111827; text-align: left; cursor: pointer; }
.replica-control:hover { border-color: #2563eb; background: #eff6ff; }
.replica-control span { color: var(--replica-muted); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 960px) { .webscribe-shell { grid-template-columns: 1fr; } }
"""

        replay_script = """document.addEventListener('click', (event) => {
  const link = event.target.closest('a[href]');
  if (link) {
    event.preventDefault();
    const url = link.getAttribute('href');
    const log = document.querySelector('[data-replica-log]');
    if (log) log.textContent = `静态复刻模式：拦截跳转 ${url}`;
  }
});

const controls = window.WEBSCRIBE_CONTROLS || [];
const controlList = document.querySelector('[data-control-list]');
const log = document.querySelector('[data-replica-log]');
if (controlList) {
  controlList.innerHTML = controls.map(item => `
    <button class="replica-control" data-index="${item.index}">
      <strong>${item.tag}${item.type ? ':' + item.type : ''}</strong>
      <span>${(item.text || item.href || item.name || '未命名控件').replace(/[<>&]/g, '')}</span>
    </button>
  `).join('');
  controlList.addEventListener('click', (event) => {
    const button = event.target.closest('[data-index]');
    if (!button) return;
    const item = controls.find(control => String(control.index) === button.dataset.index);
    if (log && item) {
      log.textContent = `复刻交互：${item.tag} ${item.text || item.href || item.name || ''}`;
    }
  });
}

document.querySelectorAll('input, textarea, select').forEach((el) => {
  el.addEventListener('input', () => {
    if (log) log.textContent = `复刻输入：${el.name || el.placeholder || el.type || el.tagName}`;
  });
  el.addEventListener('change', () => {
    if (log) log.textContent = `复刻变更：${el.name || el.placeholder || el.type || el.tagName}`;
  });
});

document.querySelectorAll('button, [role="button"], [onclick], [tabindex]').forEach((el) => {
  el.addEventListener('click', () => {
    if (log) log.textContent = `复刻点击：${(el.innerText || el.textContent || el.getAttribute('aria-label') || el.className || el.tagName).toString().slice(0, 80)}`;
    const target = el.getAttribute('data-target') || el.getAttribute('aria-controls');
    if (target) {
      const panel = document.getElementById(target) || document.querySelector(target);
      if (panel) panel.hidden = !panel.hidden;
    }
  });
});"""

        escaped_dom = dom_html
        original_panel = f"""
<aside class="webscribe-side">
  <h2>复刻说明</h2>
  <p><strong>目标:</strong> <a href="{html.escape(current_url)}" target="_blank">{html.escape(current_url)}</a></p>
  <p><strong>标题:</strong> {html.escape(title)}</p>
  <p><strong>状态:</strong> 这是基于脚本爬虫抓取结果生成的静态复刻版，保留页面 DOM、可视截图、请求数据和文本摘要。</p>
  {'<img class="webscribe-snapshot" src="' + screenshot_rel + '" alt="页面截图">' if screenshot_rel else ''}
  <h2>控件清单</h2>
  <div class="replica-controls" data-control-list></div>
  <h2>文本摘要</h2>
  <pre>{html.escape(body_text[:5000])}</pre>
  <p data-replica-log>交互日志：等待操作</p>
</aside>
"""
        index_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Replica - {html.escape(title or current_url)}</title>
  <base href="{html.escape(current_url)}">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="webscribe-toolbar">
    <span>WebScribe 静态复刻版</span>
    <span><a href="../report.html">报告</a> · <a href="../requests.json">请求数据</a> · <a href="../artifact_manifest.json">产物清单</a></span>
  </div>
  <main class="webscribe-shell">
    <section class="webscribe-page">
      {escaped_dom}
    </section>
    {original_panel}
  </main>
  <script>window.WEBSCRIBE_CONTROLS = {json.dumps(controls, ensure_ascii=False)};</script>
  <script src="replay.js"></script>
</body>
</html>"""

        (replica_dir / "index.html").write_text(index_html, encoding="utf-8")
        (replica_dir / "styles.css").write_text(styles, encoding="utf-8")
        (replica_dir / "replay.js").write_text(replay_script, encoding="utf-8")
        (data_dir / "requests.json").write_text(json.dumps(self.requests, ensure_ascii=False, indent=2), encoding="utf-8")
        (data_dir / "design_tokens.json").write_text(json.dumps(self.design_tokens or {}, ensure_ascii=False, indent=2), encoding="utf-8")
        (data_dir / "controls.json").write_text(json.dumps(controls, ensure_ascii=False, indent=2), encoding="utf-8")
        (data_dir / "interaction_screenshots.json").write_text(json.dumps(self.page_snapshots, ensure_ascii=False, indent=2), encoding="utf-8")
        (data_dir / "discovered_urls.json").write_text(json.dumps(sorted(self.discovered_urls), ensure_ascii=False, indent=2), encoding="utf-8")
        (replica_dir / "README.md").write_text(
            f"""# WebScribe 复刻网页

目标地址：{current_url}

## 文件

- `index.html`：完整静态复刻入口
- `styles.css`：复刻外壳样式
- `replay.js`：静态交互拦截脚本
- `assets/snapshot.png`：抓取截图
- `data/requests.json`：网络请求数据
- `data/design_tokens.json`：设计 token

## 运行

直接用浏览器打开 `index.html`，或在本目录运行静态服务器。
""",
            encoding="utf-8",
        )
        return replica_dir

    async def _download_assets(self, page, replica_dir: Path):
        data_dir = replica_dir / "data"
        assets_dir = replica_dir / "assets" / "downloaded"
        assets_dir.mkdir(parents=True, exist_ok=True)
        assets = await page.evaluate("""
        () => {
          const urls = [];
          document.querySelectorAll('img[src], script[src], link[href], video[src], audio[src], source[src]').forEach(el => {
            urls.push({ tag: el.tagName.toLowerCase(), attr: el.src ? 'src' : 'href', url: el.src || el.href || '' });
          });
          document.querySelectorAll('*').forEach(el => {
            const bg = getComputedStyle(el).backgroundImage;
            const match = bg && bg.match(/url\\(["']?([^"')]+)["']?\\)/);
            if (match) urls.push({ tag: 'background', attr: 'background-image', url: match[1] });
          });
          return urls.filter(item => item.url);
        }
        """)
        seen = set()
        manifest = []
        async with aiohttp.ClientSession() as session:
            for index, item in enumerate(assets[:120]):
                source_url = urljoin(page.url, item["url"])
                if source_url in seen or not source_url.startswith(("http://", "https://")):
                    continue
                seen.add(source_url)
                suffix = Path(urlparse(source_url).path).suffix[:12] or ".bin"
                target = assets_dir / f"asset_{index}{suffix}"
                record = {**item, "source_url": source_url, "local_path": str(target), "ok": False}
                try:
                    async with session.get(source_url, timeout=10) as resp:
                        if resp.status == 200:
                            target.write_bytes(await resp.read())
                            record["ok"] = True
                            record["status"] = resp.status
                        else:
                            record["status"] = resp.status
                except Exception as exc:
                    record["error"] = str(exc)
                manifest.append(record)
        self.asset_manifest = manifest
        (data_dir / "assets.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        await self._add_log(f"资源镜像完成: {sum(1 for item in manifest if item.get('ok'))}/{len(manifest)} 个资源已下载")

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
