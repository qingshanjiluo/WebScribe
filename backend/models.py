from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, nullable=True)  # 可选，用于多用户
    logs = relationship("Log", back_populates="task", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="task", cascade="all, delete-orphan")

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    message = Column(Text)
    level = Column(String(10))
    timestamp = Column(DateTime, default=datetime.utcnow)
    task = relationship("Task", back_populates="logs")

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    page_url = Column(String(500))
    screenshot_path = Column(String(500))
    design_tokens = Column(JSON)
    requests = Column(JSON)
    generated_code = Column(JSON)
    report_path = Column(String(500))
    openapi_path = Column(String(500))  # OpenAPI文档路径
    content_data = Column(JSON)  # 存储文本、图片、媒体等提取内容
    task = relationship("Task", back_populates="results")