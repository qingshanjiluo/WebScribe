import pytest
from datetime import datetime
from models import Task, Log, Result
from sqlalchemy.orm import Session

def test_task_creation(db: Session):
    task = Task(
        url="https://example.com",
        status="pending",
        config={"max_depth": 3}
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    assert task.id is not None
    assert task.url == "https://example.com"
    assert task.status == "pending"
    assert task.config["max_depth"] == 3
    assert isinstance(task.created_at, datetime)

def test_log_creation(db: Session):
    task = Task(url="https://example.com", status="pending", config={})
    db.add(task)
    db.commit()
    
    log = Log(
        task_id=task.id,
        message="Test log message",
        level="info"
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    assert log.id is not None
    assert log.task_id == task.id
    assert log.message == "Test log message"
    assert log.level == "info"

def test_result_creation(db: Session):
    task = Task(url="https://example.com", status="completed", config={})
    db.add(task)
    db.commit()
    
    result = Result(
        task_id=task.id,
        page_url="https://example.com",
        screenshot_path="/path/to/screenshot.png",
        design_tokens={"colors": {"primary": "#007bff"}},
        requests=[{"url": "/api/data", "method": "GET"}],
        generated_code={"dir": "/path/to/code"},
        report_path="/path/to/report.html",
        openapi_path="/path/to/openapi.yaml",
        content_data={"text": ["Hello world"]}
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    
    assert result.id is not None
    assert result.task_id == task.id
    assert result.openapi_path == "/path/to/openapi.yaml"
    assert result.design_tokens["colors"]["primary"] == "#007bff"