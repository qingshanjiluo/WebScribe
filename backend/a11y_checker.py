from playwright.async_api import Page

class A11yChecker:
    async def check(self, page: Page):
        await page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.2/axe.min.js")
        await page.wait_for_function('typeof window.axe !== "undefined"')
        results = await page.evaluate('''async () => await window.axe.run()''')
        violations = results.get('violations', [])
        summary = {
            'total_violations': len(violations),
            'violations': [],
            'impact_counts': {}
        }
        for v in violations:
            impact = v.get('impact', 'unknown')
            summary['impact_counts'][impact] = summary['impact_counts'].get(impact, 0) + 1
            summary['violations'].append({
                'id': v['id'],
                'impact': impact,
                'description': v['description'],
                'help': v['help'],
                'nodes': len(v['nodes']),
                'tags': v['tags']
            })
        return summary