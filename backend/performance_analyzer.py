from datetime import datetime
from typing import Dict
from playwright.async_api import Page

class PerformanceAnalyzer:
    async def analyze(self, page: Page) -> Dict:
        perf_data = await page.evaluate('''() => {
            const perf = performance.getEntriesByType('navigation')[0];
            const resources = performance.getEntriesByType('resource');
            return {
                navigation: {
                    dns: perf.domainLookupEnd - perf.domainLookupStart,
                    tcp: perf.connectEnd - perf.connectStart,
                    request: perf.responseStart - perf.requestStart,
                    response: perf.responseEnd - perf.responseStart,
                    dom: perf.domContentLoadedEventEnd - perf.domContentLoadedEventStart,
                    load: perf.loadEventEnd - perf.loadEventStart,
                    total: perf.loadEventEnd - perf.fetchStart
                },
                resources: resources.map(r => ({
                    name: r.name,
                    duration: r.duration,
                    size: r.transferSize || 0,
                    type: r.initiatorType
                }))
            };
        }''')
        scores = self._calculate_scores(perf_data['navigation'])
        suggestions = self._generate_suggestions(perf_data['navigation'], perf_data['resources'])
        return {
            'metrics': perf_data,
            'scores': scores,
            'suggestions': suggestions,
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_scores(self, nav):
        total = nav.get('total', 3000)
        if total < 1000:
            score = 90
        elif total < 2000:
            score = 70
        elif total < 3000:
            score = 50
        else:
            score = 30
        return {'overall': score, 'total_time': total}

    def _generate_suggestions(self, nav, resources):
        suggestions = []
        if nav.get('dns', 0) > 100:
            suggestions.append("DNS 解析耗时较长，考虑使用 CDN 或预解析")
        if nav.get('request', 0) > 200:
            suggestions.append("请求等待时间长，检查服务器响应速度")
        large_resources = [r for r in resources if r.get('size', 0) > 500000]
        if large_resources:
            suggestions.append(f"发现 {len(large_resources)} 个大资源，建议压缩或懒加载")
        return suggestions