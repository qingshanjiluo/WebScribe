import asyncio
import aiohttp
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import Page
from .config import Settings

class ContentExtractor:
    def __init__(self, task_id: int):
        self.task_id = task_id
        self.images = []
        self.videos = []
        self.audios = []
        self.text_paragraphs = []

    async def extract(self, page: Page, base_url: str) -> dict:
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        self.text_paragraphs = self._extract_text_paragraphs(soup)
        self.images = await self._extract_images(page, base_url)
        self.videos = self._extract_media(soup, base_url, ['video', 'iframe[src*="youtube"]', 'iframe[src*="vimeo"]'])
        self.audios = self._extract_media(soup, base_url, ['audio', 'source[type*="audio"]'])
        return {
            'text_paragraphs': self.text_paragraphs[:20],
            'images': self.images,
            'videos': self.videos,
            'audios': self.audios,
        }

    def _extract_text_paragraphs(self, soup):
        paragraphs = []
        for tag in soup.find_all(['p', 'article', 'section', 'div']):
            text = tag.get_text(strip=True)
            if len(text) > 50 and not tag.find_parent('script'):
                paragraphs.append(text[:500])
        return paragraphs

    async def _extract_images(self, page: Page, base_url: str):
        img_urls = await page.evaluate('''
            () => {
                const imgs = Array.from(document.querySelectorAll('img'));
                return imgs.map(img => ({
                    url: img.src,
                    alt: img.alt,
                    width: img.width,
                    height: img.height,
                    naturalWidth: img.naturalWidth,
                    naturalHeight: img.naturalHeight
                }));
            }
        ''')
        bg_urls = await page.evaluate('''
            () => {
                const elements = document.querySelectorAll('*');
                const urls = [];
                elements.forEach(el => {
                    const bg = window.getComputedStyle(el).backgroundImage;
                    if (bg && bg !== 'none') {
                        const match = bg.match(/url\\(["']?([^"'\\)]+)["']?\\)/);
                        if (match) urls.push(match[1]);
                    }
                });
                return urls;
            }
        ''')
        all_urls = []
        seen = set()
        for img in img_urls:
            if img['url'] and img['url'] not in seen:
                seen.add(img['url'])
                all_urls.append(img)
        for url in bg_urls:
            if url and url not in seen:
                seen.add(url)
                all_urls.append({'url': url, 'alt': '', 'width': 0, 'height': 0})
        for img in all_urls[:20]:
            await self._download_and_analyze(img['url'], img)
        return all_urls

    async def _download_and_analyze(self, url, img_info):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        if content.startswith(b'\x89PNG'):
                            fmt = 'png'
                        elif content.startswith(b'\xff\xd8'):
                            fmt = 'jpeg'
                        elif content.startswith(b'GIF'):
                            fmt = 'gif'
                        else:
                            fmt = 'unknown'
                        img_info['format'] = fmt
                        img_info['size'] = len(content)
        except Exception:
            pass

    def _extract_media(self, soup, base_url, selectors):
        results = []
        for selector in selectors:
            for tag in soup.select(selector):
                if tag.name in ('video', 'audio'):
                    src = tag.get('src')
                    if src:
                        results.append({'url': urljoin(base_url, src), 'type': tag.name})
                elif tag.name == 'source':
                    src = tag.get('src')
                    if src:
                        parent = tag.parent
                        results.append({'url': urljoin(base_url, src), 'type': parent.name if parent else 'unknown'})
                elif tag.name == 'iframe':
                    src = tag.get('src')
                    if src and ('youtube' in src or 'vimeo' in src):
                        results.append({'url': src, 'type': 'video_embed'})
        return results