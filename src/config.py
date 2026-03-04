"""配置管理"""
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """应用配置"""
    
    # 数据库
    DATABASE_URL: str = "sqlite:///./data/compet.db"
    
    # Genie API (优先)
    GENIE_API_URL: str = "https://genie-data.hbo-erp.com/main/api/v1"
    
    # Keepa API
    KEEPA_API_KEY: Optional[str] = None
    
    # Amazon PA-API
    AMAZON_ACCESS_KEY: Optional[str] = None
    AMAZON_SECRET_KEY: Optional[str] = None
    AMAZON_PARTNER_TAG: Optional[str] = None
    
    # 爬虫配置
    REQUEST_DELAY: float = 3.0  # 请求间隔(秒)
    MAX_RETRIES: int = 3
    
    # 监控配置
    PRICE_ALERT_THRESHOLD: float = 0.05  # 5%价格变动报警
    BSR_ALERT_THRESHOLD: float = 0.20    # 20%BSR变动报警
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
