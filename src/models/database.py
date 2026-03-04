"""数据库模型"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from ..config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    """商品表"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(10), unique=True, index=True, nullable=False)
    title = Column(Text)
    brand = Column(String(255))
    category = Column(String(500))
    parent_asin = Column(String(10))
    image_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    price_history = relationship("PriceHistory", back_populates="product")
    keywords = relationship("Keyword", back_populates="product")
    reviews = relationship("Review", back_populates="product")

class PriceHistory(Base):
    """价格历史表"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(10), ForeignKey("products.asin"), index=True)
    price = Column(Float)
    bsr = Column(Integer)
    bsr_category = Column(String(255))
    review_count = Column(Integer)
    rating = Column(Float)
    monthly_sales = Column(Integer)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="price_history")

class Keyword(Base):
    """关键词表"""
    __tablename__ = "keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(10), ForeignKey("products.asin"), index=True)
    keyword = Column(String(500), index=True)
    search_volume = Column(Integer)
    keyword_type = Column(String(20))  # organic/sponsored/brand
    organic_rank = Column(Integer)
    sponsored_rank = Column(Integer)
    click_share = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="keywords")

class Review(Base):
    """评论表"""
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(10), ForeignKey("products.asin"), index=True)
    review_id = Column(String(50), unique=True)
    rating = Column(Integer)
    title = Column(Text)
    content = Column(Text)
    is_vp = Column(Boolean, default=False)
    helpful_votes = Column(Integer, default=0)
    sentiment = Column(String(20))  # positive/negative/neutral
    sentiment_score = Column(Float)
    review_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="reviews")

class MonitorConfig(Base):
    """监控配置表"""
    __tablename__ = "monitor_config"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(10), index=True)
    monitor_type = Column(String(50))  # price/bsr/inventory/reviews
    frequency = Column(String(20))  # daily/weekly
    alert_threshold = Column(Float)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    """报警记录表"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String(10), index=True)
    alert_type = Column(String(50))
    old_value = Column(String(100))
    new_value = Column(String(100))
    change_percent = Column(Float)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
