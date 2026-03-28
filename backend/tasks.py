import asyncio
from .explorer import Explorer
from .models import SessionLocal, Task as TaskModel
from .config import Settings
import redis
from rq import Queue

redis_conn = redis.from_url(Settings.REDIS_URL) if Settings.REDIS_URL else None
rq_queue = Queue('webscribe', connection=redis_conn) if redis_conn else None

class TaskQueue:
    def __init__(self, max_concurrent=3):
        self.max_concurrent = max_concurrent
        self.running = {}
        self.queue = asyncio.Queue()
        self._redis_enabled = redis_conn is not None

    async def add_task(self, task_id, config):
        if self._redis_enabled:
            rq_queue.enqueue('backend.tasks.run_explorer_task', task_id, config)
        else:
            await self.queue.put((task_id, config))
            await self._process()

    async def _process(self):
        while len(self.running) < self.max_concurrent and not self.queue.empty():
            task_id, config = await self.queue.get()
            asyncio.create_task(self._run_task(task_id, config))

    async def _run_task(self, task_id, config):
        self.running[task_id] = True
        db = SessionLocal()
        try:
            task = db.query(TaskModel).get(task_id)
            if task:
                task.status = "running"
                db.commit()
            explorer = Explorer(task_id, db, anti_level=config.get("anti_spider_level", "standard"))
            await explorer.run(config)
        except Exception as e:
            print(f"Task {task_id} failed: {e}")
        finally:
            db.close()
            del self.running[task_id]
            await self._process()

def run_explorer_task(task_id, config):
    """供 RQ 调用的函数"""
    import asyncio
    from .database import SessionLocal
    db = SessionLocal()
    try:
        explorer = Explorer(task_id, db, anti_level=config.get("anti_spider_level", "standard"))
        asyncio.run(explorer.run(config))
    finally:
        db.close()