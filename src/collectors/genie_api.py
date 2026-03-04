"""Genie API 采集器"""
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseCollector, ProductData, KeywordData, ReviewData
from ..config import settings

class GenieCollector(BaseCollector):
    """Genie Data API 采集器"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "https://genie-data.hbo-erp.com/main/api/v1"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_product(self, asin: str, marketplace: str = "US") -> Optional[ProductData]:
        """获取商品信息"""
        url = f"{self.base_url}/asin/{asin}"
        params = {
            "marketplace": marketplace,
            "force_refresh": "false"
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 解析返回数据
            if not data or data.get("code") != 0:
                print(f"Genie API error: {data.get('message', 'Unknown error')}")
                return None
            
            product_data = data.get("data", {})
            
            # 提取基础信息
            return ProductData(
                asin=asin,
                title=product_data.get("title", ""),
                brand=product_data.get("brand", ""),
                price=self._parse_price(product_data.get("price")),
                bsr=product_data.get("bsr") or product_data.get("salesRank"),
                bsr_category=product_data.get("bsrCategory", ""),
                rating=product_data.get("rating") or product_data.get("stars"),
                review_count=product_data.get("reviewCount") or product_data.get("ratings"),
                monthly_sales=product_data.get("monthlySales") or product_data.get("estimatedSales"),
                category=product_data.get("category", ""),
                image_url=product_data.get("imageUrl") or product_data.get("mainImage"),
                parent_asin=product_data.get("parentAsin"),
                variants=product_data.get("variants", [])
            )
            
        except httpx.HTTPError as e:
            print(f"Genie API HTTP error: {e}")
            return None
        except Exception as e:
            print(f"Genie API error: {e}")
            return None
    
    def _parse_price(self, price_value: Any) -> Optional[float]:
        """解析价格"""
        if price_value is None:
            return None
        if isinstance(price_value, (int, float)):
            return float(price_value)
        if isinstance(price_value, str):
            # 去除货币符号
            import re
            match = re.search(r"[\d.]+", price_value.replace(",", ""))
            if match:
                return float(match.group())
        return None
    
    async def fetch_price_history(self, asin: str, days: int = 90) -> List[Dict]:
        """获取价格历史"""
        url = f"{self.base_url}/asin/{asin}/history"
        params = {
            "marketplace": "US",
            "days": days
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0 and data.get("data"):
                return data.get("data", [])
            return []
            
        except Exception as e:
            print(f"Genie API history error: {e}")
            return []
    
    async def fetch_keywords(self, asin: str) -> List[KeywordData]:
        """获取关键词数据"""
        url = f"{self.base_url}/asin/{asin}/keywords"
        params = {"marketplace": "US"}
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0 and data.get("data"):
                keywords = []
                for kw in data.get("data", []):
                    keywords.append(KeywordData(
                        keyword=kw.get("keyword", ""),
                        search_volume=kw.get("searchVolume", 0),
                        keyword_type=kw.get("type", "organic"),
                        organic_rank=kw.get("organicRank"),
                        sponsored_rank=kw.get("sponsoredRank"),
                        click_share=kw.get("clickShare", 0),
                        competition_level=kw.get("competition", "medium")
                    ))
                return keywords
            return []
            
        except Exception as e:
            print(f"Genie API keywords error: {e}")
            return []
    
    async def fetch_reviews(self, asin: str, pages: int = 10) -> List[ReviewData]:
        """获取评论数据"""
        url = f"{self.base_url}/asin/{asin}/reviews"
        params = {
            "marketplace": "US",
            "limit": pages * 10
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0 and data.get("data"):
                reviews = []
                for r in data.get("data", []):
                    reviews.append(ReviewData(
                        review_id=r.get("reviewId", ""),
                        rating=r.get("rating", 0),
                        title=r.get("title", ""),
                        content=r.get("content", ""),
                        is_vp=r.get("isVp", False),
                        helpful_votes=r.get("helpfulVotes", 0),
                        review_date=datetime.fromisoformat(r["reviewDate"]) if r.get("reviewDate") else None
                    ))
                return reviews
            return []
            
        except Exception as e:
            print(f"Genie API reviews error: {e}")
            return []
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
