import asyncio
import urllib.parse
from urllib.robotparser import RobotFileParser

class RobotsChecker:
    def __init__(self, user_agent="WebScribeBot"):
        self.user_agent = user_agent
        self.cache = {}

    async def can_fetch(self, url):
        parsed = urllib.parse.urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{base}/robots.txt"
        if base not in self.cache:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, rp.read)
                self.cache[base] = rp
            except Exception:
                self.cache[base] = None
        rp = self.cache[base]
        if rp is None:
            return True
        return rp.can_fetch(self.user_agent, url)