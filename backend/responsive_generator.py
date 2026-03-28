from playwright.async_api import Page

class ResponsiveGenerator:
    async def generate(self, page: Page) -> str:
        breakpoints = await page.evaluate('''
            () => {
                const styles = [...document.styleSheets];
                let queries = new Set();
                styles.forEach(sheet => {
                    try {
                        const rules = sheet.cssRules || sheet.rules;
                        for (let rule of rules) {
                            if (rule.type === CSSRule.MEDIA_RULE) {
                                queries.add(rule.conditionText);
                            }
                        }
                    } catch(e) {}
                });
                return Array.from(queries);
            }
        ''')
        css = """
/* 移动端适配 - 自动生成 */
@media (max-width: 768px) {
    .container {
        padding: 0 16px;
        width: 100%;
    }
    body {
        font-size: 14px;
    }
    .sidebar {
        display: none;
    }
    nav {
        flex-direction: column;
    }
}
@media (max-width: 480px) {
    h1 {
        font-size: 1.5rem;
    }
}
"""
        if breakpoints:
            css += f"\n/* 原始页面媒体查询参考: {', '.join(breakpoints)} */"
        return css