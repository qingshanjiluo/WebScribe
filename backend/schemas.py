from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class AntiSpiderLevel(str, Enum):
    DEV = "dev"
    STANDARD = "standard"
    STEALTH = "stealth"
    AGGRESSIVE = "aggressive"

class TaskConfig(BaseModel):
    start_url: str
    max_depth: int = 3
    max_pages: int = 20
    headless: bool = False
    enable_ai: bool = False
    enable_screenshot: bool = True
    anti_spider_level: AntiSpiderLevel = AntiSpiderLevel.STANDARD
    enable_ai_path: bool = False
    login_username: Optional[str] = None
    login_password: Optional[str] = None
    extract_content: bool = False

class TaskCreate(BaseModel):
    url: str
    config: TaskConfig

class TaskOut(BaseModel):
    id: int
    url: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    config: Dict[str, Any]

class LogOut(BaseModel):
    id: int
    task_id: int
    message: str
    level: str
    timestamp: datetime

class ResultOut(BaseModel):
    id: int
    task_id: int
    page_url: str
    screenshot_path: Optional[str]
    design_tokens: Optional[Dict]
    requests: Optional[List]
    generated_code: Optional[Dict]
    report_path: Optional[str]