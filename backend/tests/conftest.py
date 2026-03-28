import pytest
import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, engine
from models import Base

@pytest.fixture(scope="session")
def db():
    # 创建测试数据库表
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    # 清理表
    Base.metadata.drop_all(bind=engine)