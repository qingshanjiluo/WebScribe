import re
from collections import Counter
from playwright.async_api import Page

class DesignExtractor:
    def __init__(self):
        self.colors = Counter()
        self.fonts = Counter()
        self.font_sizes = Counter()
        self.border_radius = Counter()
        self.spacings = Counter()

    async def extract(self, page: Page):
        styles = await page.evaluate('''
            () => {
                const elements = document.querySelectorAll('*');
                const result = {
                    colors: [], fonts: [], fontSizes: [], borderRadius: [], spacing: []
                };
                elements.forEach(el => {
                    const style = getComputedStyle(el);
                    if (style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)') {
                        result.colors.push(style.backgroundColor);
                    }
                    if (style.color) result.colors.push(style.color);
                    if (style.fontFamily) result.fonts.push(style.fontFamily);
                    if (style.fontSize) result.fontSizes.push(style.fontSize);
                    if (style.borderRadius && style.borderRadius !== '0px') {
                        result.borderRadius.push(style.borderRadius);
                    }
                    ['marginTop','marginRight','marginBottom','marginLeft',
                     'paddingTop','paddingRight','paddingBottom','paddingLeft'].forEach(prop => {
                        const val = style[prop];
                        if (val && val !== '0px') result.spacing.push(val);
                    });
                });
                return result;
            }
        ''')
        for color in styles['colors']:
            hex_color = self._rgb_to_hex(color)
            if hex_color:
                self.colors[hex_color] += 1
        for font in styles['fonts']:
            font_family = font.split(',')[0].strip().strip("'\"")
            self.fonts[font_family] += 1
        for size in styles['fontSizes']:
            self.font_sizes[size] += 1
        for radius in styles['borderRadius']:
            self.border_radius[radius] += 1
        for spacing in styles['spacing']:
            self.spacings[spacing] += 1
        return {
            'colors': self._top_items(self.colors, 10),
            'fonts': self._top_items(self.fonts, 5),
            'font_sizes': self._top_items(self.font_sizes, 8),
            'border_radius': self._top_items(self.border_radius, 5),
            'spacing_values': sorted(set(self.spacings.keys()))[:10]
        }

    def _rgb_to_hex(self, rgb_str):
        match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', rgb_str)
        if match:
            r, g, b = map(int, match.groups())
            return f'#{r:02x}{g:02x}{b:02x}'
        return None

    def _top_items(self, counter, n):
        return [{'value': k, 'count': v} for k, v in counter.most_common(n)]

    def to_css_variables(self):
        lines = [":root {"]
        for i, (color, count) in enumerate(self.colors.most_common(10)):
            lines.append(f"    --color-{i+1}: {color}; /* {count}次 */")
        for i, (font, count) in enumerate(self.fonts.most_common(5)):
            lines.append(f"    --font-family-{i+1}: \"{font}\", sans-serif;")
        for size, count in self.font_sizes.most_common(5):
            lines.append(f"    --font-size-{size.replace('px', '')}: {size};")
        for radius, count in self.border_radius.most_common(3):
            lines.append(f"    --border-radius-{radius.replace('px', '')}: {radius};")
        lines.append("}")
        return "\n".join(lines)