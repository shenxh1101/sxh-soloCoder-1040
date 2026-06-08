from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "自动化测试后端服务"
    
    DATABASE_URL: str = "sqlite:///./test_automation.db"
    
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"
    
    MAX_RETRY_COUNT: int = 3
    RETRY_INTERVAL: int = 5
    
    REQUEST_TIMEOUT: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
