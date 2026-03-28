import os
import json
import hashlib
from datetime import datetime
from playwright.async_api import Page
from .config import Settings

async def save_screenshot(page: Page, task_id: int, url: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_url = url.replace("https://", "").replace("http://", "").replace("/", "_")[:50]
    filename = f"{task_id}_{safe_url}_{timestamp}.png"
    filepath = os.path.join(Settings.SCREENSHOT_DIR, filename)
    await page.screenshot(path=filepath, full_page=True)
    return filepath

def generate_mermaid(state_graph: list) -> str:
    if not state_graph:
        return "graph TD; 开始 --> 结束;"
    nodes = set()
    edges = []
    for from_url, to_url, action in state_graph:
        nodes.add(from_url)
        nodes.add(to_url)
        edges.append(f'    "{from_url}" -->|{action}| "{to_url}"')
    mermaid = "graph TD;\n"
    for node in nodes:
        mermaid += f'    "{node}";\n'
    for edge in edges:
        mermaid += edge + "\n"
    return mermaid

def compute_content_hash(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()