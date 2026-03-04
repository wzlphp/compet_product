"""Keepa API 采集器"""
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .base import BaseCollector, ProductData, KeywordData, ReviewData
from ..config import settings
import asyncio

# Keepa 域名映射
KEEPA_DOMAINS = {
    "US": 1, "UK": 2, "DE": 3, "FR": 4, "JP": 5,
    "CA": 6, "IT": 8, "ES": 9, "IN": 10, "MX": 11
}

class KeepaCollector(BaseCollector):
    """Keepa API 采集器"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.KEEPA_API_KEY
        self.base_url = "https://api.keepa.com"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _request(self, endpoint: str, params: Dict) -> Dict:
        """发送API请求"""
        params["key"] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Keepa API error: {e}")
            return {}
    
    async def fetch_product(self, asin: str, marketplace: str = "US") -> Optional[ProductData]:
        """获取商品信息"""
        domain = KEEPA_DOMAINS.get(marketplace, 1)
        
        params = {
            "domain": domain,
            "asin": asin,
            "history": 1,
            "buybox": 1,
            "stats": 90
        }
        
        data = await self._request("product", params)
        
        if not data or "products" not in data or not data["products"]:
            return None
        
        product = data["products"][0]
        
        # 解析价格 (Keepa价格需要除以100)
        current_price = None
        if "csv" in product and product["csv"][0]:
            prices = product["csv"][0]
            if prices and len(prices) >= 2:
                current_price = prices[-1] / 100 if prices[-1] > 0 else None
        
        # 解析BSR
        current_bsr = None
        if "csv" in product and product["csv"][3]:
            bsr_history = product["csv"][3]
            if bsr_history and len(bsr_history) >= 2:
                current_bsr = bsr_history[-1] if bsr_history[-1] > 0 else None
        
        # 解析统计数据
        stats = product.get("stats", {})
        
        return ProductData(
            asin=asin,
            title=product.get("title", ""),
            brand=product.get("brand", ""),
            price=current_price,
            bsr=current_bsr,
            bsr_category=product.get("categoryTree", [{}])[0].get("name", "") if product.get("categoryTree") else "",
            rating=stats.get("avg", [0, 0])[0] / 10 if stats.get("avg") else None,
            review_count=stats.get("avg", [0, 0])[1] if stats.get("avg") else None,
            monthly_sales=self._estimate_sales(current_bsr),
            category=product.get("categoryTree", [{}])[-1].get("name", "") if product.get("categoryTree") else "",
            image_url=f"https://images-na.ssl-images-amazon.com/images/I/{product.get('imagesCSV', '').split(',')[0]}" if product.get("imagesCSV") else None,
            parent_asin=product.get("parentAsin"),
            variants=product.get("variations", [])
        )
    
    async def fetch_price_history(self, asin: str, days: int = 90) -> List[Dict]:
        """获取价格历史"""
        params = {
            "domain": 1,
            "asin": asin,
            "history": 1
        }
        
        data = await self._request("product", params)
        
        if not data or "products" not in data:
            return []
        
        product = data["products"][0]
        history = []
        
        # 解析价格历史 (csv[0] = Amazon价格)
        if "csv" in product and product["csv"][0]:
            prices = product["csv"][0]
            bsr_data = product["csv"][3] if len(product["csv"]) > 3 else []
            
            # Keepa时间戳转换
            for i in range(0, len(prices), 2):
                if i + 1 < len(prices):
                    keepa_time = prices[i]
                    price_value = prices[i + 1]
                    
                    if price_value > 0:
                        # Keepa时间: (keepa_time + 21564000) * 60000 = Unix毫秒
                        unix_ms = (keepa_time + 21564000) * 60000
                        date = datetime.fromtimestamp(unix_ms / 1000)
                        
                        # 只取最近N天
                        if date > datetime.now() - timedelta(days=days):
                            history.append({
                                "date": date.isoformat(),
                                "price": price_value / 100,
                                "bsr": self._get_bsr_at_time(bsr_data, keepa_time)
                            })
        
        return history
    
    def _get_bsr_at_time(self, bsr_data: List, target_time: int) -> Optional[int]:
        """获取指定时间的BSR"""
        if not bsr_data:
            return None
        
        for i in range(0, len(bsr_data), 2):
            if i + 1 < len(bsr_data) and bsr_data[i] >= target_time:
                return bsr_data[i + 1] if bsr_data[i + 1] > 0 else None
        
        return bsr_data[-1] if bsr_data and bsr_data[-1] > 0 else None
    
    def _estimate_sales(self, bsr: Optional[int]) -> Optional[int]:
        """根据BSR估算月销量 (简化公式)"""
        if not bsr or bsr <= 0:
            return None
        
        # 简化的销量估算公式 (实际需要更复杂的模型)
        if bsr <= 100:
            return int(30000 / (bsr ** 0.5))
        elif bsr <= 1000:
            return int(10000 / (bsr ** 0.5))
        elif bsr <= 10000:
            return int(5000 / (bsr ** 0.5))
        else:
            return int(2000 / (bsr ** 0.5))
    
    async def fetch_keywords(self, asin: str) -> List[KeywordData]:
        """获取关键词 (Keepa需要额外订阅)"""
        # Keepa基础版不支持关键词,返回空列表
        # 实际项目中可以集成卖家精灵或Helium10 API
        return []
    
    async def fetch_reviews(self, asin: str, pages: int = 10) -> List[ReviewData]:
        """获取评论 (Keepa不提供评论内容)"""
        # Keepa不提供评论全文,需要爬虫或其他API
        return []
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
