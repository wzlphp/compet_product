"""Amazon 爬虫采集器 (备用方案)"""
import httpx
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import random
import re
from .base import BaseCollector, ProductData, KeywordData, ReviewData
from ..config import settings

class AmazonScraper(BaseCollector):
    """Amazon 页面爬虫 (备用方案)"""
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    MARKETPLACES = {
        "US": "https://www.amazon.com",
        "UK": "https://www.amazon.co.uk",
        "DE": "https://www.amazon.de",
        "JP": "https://www.amazon.co.jp",
        "CA": "https://www.amazon.ca",
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers=self.HEADERS,
            timeout=30.0,
            follow_redirects=True
        )
        self.delay = settings.REQUEST_DELAY
    
    async def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """获取页面内容"""
        try:
            await asyncio.sleep(self.delay + random.uniform(0, 1))
            response = await self.client.get(url)
            
            if response.status_code == 200:
                return BeautifulSoup(response.text, "lxml")
            else:
                print(f"HTTP {response.status_code}: {url}")
                return None
        except Exception as e:
            print(f"Scraper error: {e}")
            return None
    
    async def fetch_product(self, asin: str, marketplace: str = "US") -> Optional[ProductData]:
        """抓取商品信息"""
        base_url = self.MARKETPLACES.get(marketplace, self.MARKETPLACES["US"])
        url = f"{base_url}/dp/{asin}"
        
        soup = await self._fetch_page(url)
        if not soup:
            return None
        
        # 解析标题
        title_elem = soup.select_one("#productTitle")
        title = title_elem.get_text(strip=True) if title_elem else ""
        
        # 解析品牌
        brand_elem = soup.select_one("#bylineInfo") or soup.select_one(".po-brand .po-break-word")
        brand = brand_elem.get_text(strip=True).replace("Brand: ", "").replace("Visit the ", "").replace(" Store", "") if brand_elem else ""
        
        # 解析价格 (尝试多个选择器)
        price = None
        price_selectors = [
            "#corePrice_feature_div .a-offscreen",
            "#apex_offerDisplay_desktop .a-offscreen",
            ".priceToPay .a-offscreen",
            ".a-price .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            ".a-price-whole",
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                if price_text:
                    # 提取数字 (处理各种货币符号和格式)
                    price_match = re.search(r"[\d,.]+", price_text.replace(",", ""))
                    if price_match:
                        try:
                            price = float(price_match.group().replace(",", ""))
                            if price > 0:
                                break
                        except:
                            continue
        
        # 解析评分
        rating = None
        rating_elem = soup.select_one("#acrPopover") or soup.select_one(".a-icon-star")
        if rating_elem:
            rating_text = rating_elem.get("title", "") or rating_elem.get_text()
            rating_match = re.search(r"([\d.]+)", rating_text)
            if rating_match:
                rating = float(rating_match.group(1))
        
        # 解析评论数
        review_count = None
        review_elem = soup.select_one("#acrCustomerReviewText")
        if review_elem:
            review_text = review_elem.get_text(strip=True)
            review_match = re.search(r"([\d,]+)", review_text.replace(",", ""))
            if review_match:
                review_count = int(review_match.group(1))
        
        # 解析BSR
        bsr = None
        bsr_category = ""
        bsr_elem = soup.select_one("#SalesRank") or soup.select_one("#detailBulletsWrapper_feature_div")
        if bsr_elem:
            bsr_text = bsr_elem.get_text()
            bsr_match = re.search(r"#([\d,]+)", bsr_text.replace(",", ""))
            if bsr_match:
                bsr = int(bsr_match.group(1))
            # 提取类目
            category_match = re.search(r"in ([^(]+)", bsr_text)
            if category_match:
                bsr_category = category_match.group(1).strip()
        
        # 解析图片
        image_url = None
        image_elem = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
        if image_elem:
            image_url = image_elem.get("src") or image_elem.get("data-old-hires")
        
        return ProductData(
            asin=asin,
            title=title,
            brand=brand,
            price=price,
            bsr=bsr,
            bsr_category=bsr_category,
            rating=rating,
            review_count=review_count,
            image_url=image_url
        )
    
    def _parse_review_card(self, card) -> Optional[ReviewData]:
        """解析单个评论卡片"""
        try:
            # 评论ID
            review_id = card.get("id", "")
            
            # 评分
            rating = 0
            rating_elem = card.select_one("[data-hook='review-star-rating']") or card.select_one(".a-icon-star")
            if rating_elem:
                rating_text = rating_elem.get("title", "") or rating_elem.get_text()
                rating_match = re.search(r"([\d.]+)", rating_text)
                if rating_match:
                    rating = int(float(rating_match.group(1)))
            
            # 标题
            title_elem = card.select_one("[data-hook='review-title']") or card.select_one(".review-title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            # 清理标题中的评分文字
            title = re.sub(r'^\d+\.\d+ out of \d+ stars?', '', title).strip()
            
            # 内容
            content_elem = card.select_one("[data-hook='review-body']") or card.select_one(".review-text")
            content = content_elem.get_text(strip=True) if content_elem else ""
            
            # 如果没有内容，跳过
            if not content and not title:
                return None
            
            # VP标识
            vp_elem = card.select_one("[data-hook='avp-badge']") or card.select_one(".a-color-success")
            is_vp = vp_elem is not None and "Verified" in (vp_elem.get_text() if vp_elem else "")
            
            # 有用数
            helpful = 0
            helpful_elem = card.select_one("[data-hook='helpful-vote-statement']")
            if helpful_elem:
                helpful_match = re.search(r"(\d+)", helpful_elem.get_text())
                if helpful_match:
                    helpful = int(helpful_match.group(1))
            
            return ReviewData(
                review_id=review_id,
                rating=rating,
                title=title,
                content=content,
                is_vp=is_vp,
                helpful_votes=helpful
            )
        except Exception as e:
            print(f"Parse review error: {e}")
            return None
    
    async def fetch_reviews(self, asin: str, pages: int = 5) -> List[ReviewData]:
        """抓取评论 - 从产品页获取"""
        reviews = []
        seen_ids = set()
        
        # 从产品页获取评论
        product_url = f"https://www.amazon.com/dp/{asin}"
        soup = await self._fetch_page(product_url)
        
        if soup:
            # 产品页上的评论选择器
            review_cards = soup.select("[data-hook='review']") or soup.select(".review")
            
            for card in review_cards:
                review = self._parse_review_card(card)
                if review and review.review_id not in seen_ids:
                    reviews.append(review)
                    seen_ids.add(review.review_id)
        
        # 尝试从评论页获取更多 (可能会被阻止)
        if len(reviews) < pages * 5:
            for page in range(1, min(pages, 3) + 1):
                url = f"https://www.amazon.com/product-reviews/{asin}?pageNumber={page}&sortBy=recent"
                soup = await self._fetch_page(url)
                
                if not soup:
                    continue
                
                # 检查是否被重定向到登录页
                if soup.title and "Sign-In" in (soup.title.string or ""):
                    break
                
                review_cards = soup.select("[data-hook='review']")
                
                for card in review_cards:
                    review = self._parse_review_card(card)
                    if review and review.review_id not in seen_ids:
                        reviews.append(review)
                        seen_ids.add(review.review_id)
        
        return reviews
    
    async def fetch_price_history(self, asin: str, days: int = 90) -> List[Dict]:
        """爬虫无法获取历史数据"""
        return []
    
    async def fetch_keywords(self, asin: str) -> List[KeywordData]:
        """爬虫无法获取关键词数据"""
        return []
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
