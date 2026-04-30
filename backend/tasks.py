import asyncio
import traceback

try:
    import redis
    from rq import Queue
except ImportError:
    redis = None
    Queue = None

try:
    from .explorer import Explorer
    from .database import SessionLocal
    from .models import Log, Task as TaskModel
    from .config import Settings
except ImportError:
    from explorer import Explorer
    from database import SessionLocal
    from models import Log, Task as TaskModel
    from config import Settings

redis_conn = redis.from_url(Settings.REDIS_URL) if redis and Settings.USE_REDIS and Settings.REDIS_URL else None
rq_queue = Queue("webscribe", connection=redis_conn) if redis_conn else None

class TaskQueue:
    def __init__(self, max_concurrent=3):
        self.max_concurrent = max_concurrent
        self.running = {}
        self.explorers = {}
        self.queue = asyncio.Queue()
        self._redis_enabled = rq_queue is not None

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
                db.add(Log(task_id=task_id, level="info", message="任务进入运行队列，初始化脚本爬虫"))
                db.commit()
            explorer = Explorer(task_id, db, anti_level=config.get("anti_spider_level", "standard"))
            self.explorers[task_id] = explorer
            await explorer.run(config)
        except BaseException as e:
            tb = traceback.format_exc()
            err_msg = str(e) or type(e).__name__
            task = db.query(TaskModel).get(task_id)
            if task:
                task.status = "failed"
                db.add(Log(task_id=task_id, level="error", message=f"任务执行异常: {err_msg}"))
                db.commit()
            print(f"Task {task_id} failed: {err_msg}\n{tb}")
        finally:
            db.close()
            self.explorers.pop(task_id, None)
            del self.running[task_id]
            await self._process()

    def control_task(self, task_id, command):
        explorer = self.explorers.get(task_id)
        if not explorer:
            return False
        if command == "pause":
            explorer.paused = True
        elif command == "resume":
            explorer.paused = False
        elif command == "skip":
            explorer.skip_current = True
        elif command == "stop":
            explorer.stop_requested = True
            explorer.paused = False
        else:
            return False
        return True

def run_explorer_task(task_id, config):
    """供 RQ 调用的函数"""
    import asyncio
    db = SessionLocal()
    try:
        explorer = Explorer(task_id, db, anti_level=config.get("anti_spider_level", "standard"))
        asyncio.run(explorer.run(config))
    finally:
        db.close()
