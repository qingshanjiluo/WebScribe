import os
from config import Settings

def test_settings_defaults():
    # 测试默认值
    assert Settings.MAX_CONCURRENT_TASKS == 3
    assert Settings.MAX_PAGES_PER_TASK == 50
    assert Settings.DEFAULT_TIMEOUT == 30000
    assert Settings.SCREENSHOT_DIR == "./data/screenshots"
    assert Settings.REPORT_DIR == "./data/reports"
    assert Settings.DATABASE_URL == "sqlite:///./webscribe.db"

def test_settings_env(monkeypatch):
    monkeypatch.setenv("MAX_CONCURRENT_TASKS", "5")
    monkeypatch.setenv("MAX_PAGES_PER_TASK", "100")
    monkeypatch.setenv("USE_PROXY", "True")
    
    # 重新导入以应用环境变量
    import importlib
    import config
    importlib.reload(config)
    
    assert config.Settings.MAX_CONCURRENT_TASKS == 5
    assert config.Settings.MAX_PAGES_PER_TASK == 100
    assert config.Settings.USE_PROXY == True
    
    # 恢复默认
    importlib.reload(config)