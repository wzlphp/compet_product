"""采集器基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ProductData:
    """商品数据"""
    asin: str
    title: str
    brand: Optional[str] = None
    price: Optional[float] = None
    bsr: Optional[int] = None
    bsr_category: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    monthly_sales: Optional[int] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    parent_asin: Optional[str] = None
    variants: Optional[List[str]] = None

@dataclass
class KeywordData:
    """关键词数据"""
    keyword: str
    search_volume: int = 0
    keyword_type: str = "organic"  # organic/sponsored/brand
    organic_rank: Optional[int] = None
    sponsored_rank: Optional[int] = None
    click_share: float = 0.0
    conversion_rate: float = 0.0
    competition_level: str = "medium"  # low/medium/high

@dataclass
class ReviewData:
    """评论数据"""
    review_id: str
    rating: int
    title: str
    content: str
    is_vp: bool = False
    helpful_votes: int = 0
    review_date: Optional[datetime] = None

class BaseCollector(ABC):
    """采集器基类"""
    
    @abstractmethod
    async def fetch_product(self, asin: str, marketplace: str = "US") -> Optional[ProductData]:
        """获取商品基础信息"""
        pass
    
    @abstractmethod
    async def fetch_price_history(self, asin: str, days: int = 90) -> List[Dict]:
        """获取价格历史"""
        pass
    
    @abstractmethod
    async def fetch_keywords(self, asin: str) -> List[KeywordData]:
        """获取关键词数据"""
        pass
    
    @abstractmethod
    async def fetch_reviews(self, asin: str, pages: int = 10) -> List[ReviewData]:
        """获取评论数据"""
        pass
