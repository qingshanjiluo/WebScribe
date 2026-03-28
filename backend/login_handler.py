import asyncio
import base64
from typing import Optional, Callable
import ddddocr
from playwright.async_api import Page

class LoginHandler:
    def __init__(self, task_id: int, on_captcha_callback: Optional[Callable] = None):
        self.task_id = task_id
        self.on_captcha = on_captcha_callback
        self.ocr = ddddocr.DdddOcr()

    async def try_login(self, page: Page, username: str, password: str) -> bool:
        form = await self._find_login_form(page)
        if not form:
            return False
        await self._fill_credentials(page, username, password)
        captcha_ok = await self._solve_captcha(page)
        if not captcha_ok:
            return False
        submit_btn = await form.query_selector('button[type="submit"], input[type="submit"], button:has-text("登录")')
        if submit_btn:
            await submit_btn.click()
            await page.wait_for_load_state('networkidle')
            return await self._check_login_success(page)
        return False

    async def _find_login_form(self, page: Page):
        forms = await page.query_selector_all('form')
        for form in forms:
            has_password = await form.query_selector('input[type="password"]') is not None
            if has_password:
                return form
        return None

    async def _fill_credentials(self, page: Page, username: str, password: str):
        user_input = await page.query_selector('input[type="text"], input[name*="user"], input[name*="email"]')
        if user_input:
            await user_input.fill(username)
        pass_input = await page.query_selector('input[type="password"]')
        if pass_input:
            await pass_input.fill(password)

    async def _solve_captcha(self, page: Page) -> bool:
        captcha_img = await page.query_selector('img[src*="captcha"], img[alt*="captcha"]')
        if not captcha_img:
            return True
        screenshot = await captcha_img.screenshot()
        if self.on_captcha:
            img_base64 = base64.b64encode(screenshot).decode()
            captcha_text = await self.on_captcha(self.task_id, img_base64)
        else:
            captcha_text = self.ocr.classification(screenshot)
        if not captcha_text:
            return False
        captcha_input = await page.query_selector('input[name*="captcha"], input[name*="code"]')
        if captcha_input:
            await captcha_input.fill(captcha_text)
            return True
        return False

    async def _check_login_success(self, page: Page) -> bool:
        avatar = await page.query_selector('img[alt*="avatar"], .avatar')
        if avatar:
            return True
        if 'login' not in page.url.lower():
            return True
        return False