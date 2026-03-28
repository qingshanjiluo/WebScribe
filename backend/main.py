from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import asyncio
import json
from datetime import datetime

from . import models, schemas, tasks
from .database import SessionLocal, engine
from .config import Settings

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

task_queue = tasks.TaskQueue(max_concurrent=Settings.MAX_CONCURRENT_TASKS)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, task_id: int):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: int):
        if task_id in self.active_connections:
            del self.active_connections[task_id]

    async def send_log(self, task_id: int, message: str, level="info"):
        if task_id in self.active_connections:
            await self.active_connections[task_id].send_json({
                "type": "log",
                "level": level,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            })

manager = ConnectionManager()

@app.post("/tasks")
async def create_task(task_data: schemas.TaskCreate, db: Session = Depends(get_db)):
    task = models.Task(
        url=task_data.url,
        config=task_data.config.dict(),
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    await task_queue.add_task(task.id, task_data.config.dict())
    return task

@app.get("/tasks")
async def list_tasks(db: Session = Depends(get_db)):
    return db.query(models.Task).all()

@app.get("/tasks/{task_id}/logs")
async def get_logs(task_id: int, db: Session = Depends(get_db)):
    return db.query(models.Log).filter(models.Log.task_id == task_id).order_by(models.Log.timestamp).all()

@app.get("/tasks/{task_id}/report")
async def get_report(task_id: int, db: Session = Depends(get_db)):
    result = db.query(models.Result).filter(models.Result.task_id == task_id).first()
    if not result:
        raise HTTPException(404, "报告未生成")
    return {"report_path": result.report_path}

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: int):
    await manager.connect(websocket, task_id)
    try:
        while True:
            data = await websocket.receive_json()
            cmd = data.get("command")
            # 这里可以处理暂停、继续等命令，需要与 task_queue 交互
    except WebSocketDisconnect:
        manager.disconnect(task_id)