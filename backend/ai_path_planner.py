import json
import openai
from typing import List, Dict, Any
from .config import Settings

class AIPathPlanner:
    def __init__(self):
        self.client = openai.OpenAI(api_key=Settings.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    async def rank_elements(self, page_url: str, page_title: str, elements: List[Dict]) -> List[Dict]:
        if not Settings.DEEPSEEK_API_KEY:
            return elements
        element_desc = []
        for idx, el in enumerate(elements[:30]):
            desc = f"{idx}: {el['tagName']} '{el.get('text', '')[:50]}' selector={el['selector']}"
            element_desc.append(desc)
        prompt = f"""你是一个智能网页探索助手。当前页面 URL: {page_url}，标题: {page_title}。
你需要根据以下元素列表，判断哪些元素最值得点击，以便深入探索网站功能。
请按优先级从高到低排序，返回元素索引列表（例如 [0,3,1,...]）。

元素列表：
{chr(10).join(element_desc)}

只返回 JSON 数组，不要有其他文字。"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            ranking = result.get('ranking', [])
            sorted_elements = []
            for idx in ranking:
                if 0 <= idx < len(elements):
                    sorted_elements.append(elements[idx])
            for i, el in enumerate(elements):
                if i not in ranking:
                    sorted_elements.append(el)
            return sorted_elements
        except Exception as e:
            print(f"AI 路径规划失败: {e}")
            return elements