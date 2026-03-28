import random
import asyncio
from fake_useragent import UserAgent
from playwright.async_api import Page

class AntiAntiSpider:
    def __init__(self, level="standard", use_proxy=False, proxy_list=None):
        self.level = level
        self.ua = UserAgent()
        self.use_proxy = use_proxy
        self.proxy_list = proxy_list or []
        self.current_proxy = None

    def get_random_ua(self):
        return self.ua.random

    def get_random_proxy(self):
        if self.proxy_list and self.use_proxy:
            return random.choice(self.proxy_list)
        return None

    async def apply_stealth(self, page: Page):
        if self.level == "dev":
            return
        await self._inject_stealth_js(page)
        if self.level == "standard":
            pass
        elif self.level == "stealth":
            await self._disable_devtools(page)
            await self._inject_fingerprint_randomizer(page)
        elif self.level == "aggressive":
            await self._disable_devtools(page)
            await self._inject_fingerprint_randomizer(page)

    async def _disable_devtools(self, page: Page):
        await page.add_init_script("""
            document.addEventListener('keydown', function(e) {
                if (e.key === 'F12' || 
                    (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'J')) ||
                    (e.ctrlKey && e.key === 'U')) {
                    e.preventDefault();
                    return false;
                }
            });
            document.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                return false;
            });
        """)

    async def _inject_fingerprint_randomizer(self, page: Page):
        await page.add_init_script("""
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
                const original = originalToDataURL.call(this, type, quality);
                if (this.width > 10 && this.height > 10) {
                    return original.slice(0, -2) + '00';
                }
                return original;
            };
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    const vendors = ['Intel Inc.', 'NVIDIA Corporation', 'AMD', 'Apple Inc.'];
                    return vendors[Math.floor(Math.random() * vendors.length)];
                }
                if (parameter === 37446) {
                    const renderers = ['Intel Iris OpenGL Engine', 'NVIDIA GeForce GTX 1080', 'AMD Radeon Pro 580', 'Apple M1'];
                    return renderers[Math.floor(Math.random() * renderers.length)];
                }
                return getParameter.call(this, parameter);
            };
        """)

    async def _inject_stealth_js(self, page: Page):
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
        """)

    async def random_mouse_move(self, page: Page):
        steps = 10 if self.level == "aggressive" else 5
        viewport = page.viewport_size
        if viewport:
            x = random.randint(0, viewport['width'])
            y = random.randint(0, viewport['height'])
            await page.mouse.move(x, y, steps=steps)

    async def random_delay(self, min_ms=500, max_ms=2000):
        if self.level == "aggressive":
            min_ms, max_ms = 800, 3000
        await asyncio.sleep(random.uniform(min_ms/1000, max_ms/1000))

    async def human_like_click(self, page: Page, selector: str):
        element = await page.query_selector(selector)
        if not element:
            return False
        box = await element.bounding_box()
        if not box:
            return False
        x = box['x'] + box['width'] * random.uniform(0.2, 0.8)
        y = box['y'] + box['height'] * random.uniform(0.2, 0.8)
        if self.level == "aggressive":
            x += random.randint(-5, 5)
            y += random.randint(-5, 5)
        await page.mouse.move(x - random.randint(5, 20), y - random.randint(5, 20), steps=5)
        await self.random_delay(50, 150)
        await page.mouse.move(x, y, steps=5)
        await self.random_delay(50, 100)
        await page.mouse.click(x, y)
        return True

    def get_browser_args(self):
        common = [
            "--disable-blink-features=AutomationControlled",
            "--disable-extensions",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-breakpad",
        ]
        if self.level == "dev":
            return common
        elif self.level == "standard":
            return common + [
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-default-apps",
            ]
        elif self.level in ("stealth", "aggressive"):
            return common + [
                "--disable-dev-shm-usage",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-default-apps",
                "--disable-devtools",
                "--disable-component-update",
                "--disable-crash-reporter",
                "--disable-domain-reliability",
                "--disable-features=ChromeWhatsNewUI,PrivacySandboxAdsAPIs,TranslateUI",
                "--disable-component-extensions-with-background-pages",
                "--disable-field-trial-config",
                "--disable-ipc-flooding-protection",
                "--disable-renderer-backgrounding",
            ]
        return common