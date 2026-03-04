"""Review 分析引擎"""
from typing import List, Dict, Tuple
from collections import Counter
import re
from dataclasses import dataclass

@dataclass
class ReviewAnalysis:
    """评论分析结果"""
    total_reviews: int
    avg_rating: float
    rating_distribution: Dict[int, float]
    vp_ratio: float
    sentiment_score: float
    positive_keywords: List[Tuple[str, int]]
    negative_keywords: List[Tuple[str, int]]
    pain_points: List[str]
    selling_points: List[str]

class ReviewAnalyzer:
    """Review 分析引擎"""
    
    # 常见停用词
    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "under", "again", "further", "then", "once", "here",
        "there", "when", "where", "why", "how", "all", "each", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "just", "and", "but", "if", "or",
        "because", "until", "while", "this", "that", "these", "those", "i",
        "me", "my", "myself", "we", "our", "ours", "you", "your", "he", "him",
        "she", "her", "it", "its", "they", "them", "their", "what", "which",
        "who", "whom", "am", "product", "item", "bought", "buy", "got", "get",
        "one", "two", "also", "really", "much", "well", "even", "still", "back"
    }
    
    # 正面情感词
    POSITIVE_WORDS = {
        "love", "great", "excellent", "amazing", "perfect", "best", "good",
        "comfortable", "soft", "quality", "recommend", "happy", "satisfied",
        "beautiful", "nice", "awesome", "fantastic", "wonderful", "super",
        "value", "worth", "sturdy", "durable", "flattering", "fit", "fits"
    }
    
    # 负面情感词
    NEGATIVE_WORDS = {
        "bad", "poor", "terrible", "horrible", "worst", "disappointed",
        "broken", "cheap", "flimsy", "small", "tight", "loose", "thin",
        "see-through", "transparent", "uncomfortable", "itchy", "rough",
        "returned", "return", "refund", "waste", "defective", "wrong",
        "ripped", "torn", "faded", "shrunk", "pilling", "pills"
    }
    
    def analyze(self, reviews: List[Dict]) -> ReviewAnalysis:
        """分析评论列表"""
        if not reviews:
            return ReviewAnalysis(
                total_reviews=0,
                avg_rating=0,
                rating_distribution={},
                vp_ratio=0,
                sentiment_score=0,
                positive_keywords=[],
                negative_keywords=[],
                pain_points=[],
                selling_points=[]
            )
        
        # 基础统计
        total = len(reviews)
        ratings = [r.get("rating", 0) for r in reviews]
        avg_rating = sum(ratings) / total if total else 0
        
        # 评分分布
        rating_dist = Counter(ratings)
        rating_distribution = {i: rating_dist.get(i, 0) / total * 100 for i in range(1, 6)}
        
        # VP占比
        vp_count = sum(1 for r in reviews if r.get("is_vp", False))
        vp_ratio = vp_count / total if total else 0
        
        # 分离正面和负面评论
        positive_reviews = [r for r in reviews if r.get("rating", 0) >= 4]
        negative_reviews = [r for r in reviews if r.get("rating", 0) <= 2]
        
        # 提取关键词
        positive_text = " ".join([r.get("content", "") + " " + r.get("title", "") for r in positive_reviews])
        negative_text = " ".join([r.get("content", "") + " " + r.get("title", "") for r in negative_reviews])
        
        positive_keywords = self._extract_keywords(positive_text, top_n=20)
        negative_keywords = self._extract_keywords(negative_text, top_n=20)
        
        # 情感得分
        sentiment_score = self._calculate_sentiment(reviews)
        
        # 痛点和卖点提取
        pain_points = self._extract_pain_points(negative_reviews)
        selling_points = self._extract_selling_points(positive_reviews)
        
        return ReviewAnalysis(
            total_reviews=total,
            avg_rating=round(avg_rating, 2),
            rating_distribution=rating_distribution,
            vp_ratio=round(vp_ratio, 2),
            sentiment_score=round(sentiment_score, 2),
            positive_keywords=positive_keywords,
            negative_keywords=negative_keywords,
            pain_points=pain_points,
            selling_points=selling_points
        )
    
    def _extract_keywords(self, text: str, top_n: int = 20) -> List[Tuple[str, int]]:
        """提取关键词"""
        # 清洗文本
        text = text.lower()
        text = re.sub(r"[^a-z\s]", " ", text)
        words = text.split()
        
        # 过滤停用词和短词
        words = [w for w in words if w not in self.STOP_WORDS and len(w) > 2]
        
        # 统计词频
        word_counts = Counter(words)
        
        return word_counts.most_common(top_n)
    
    def _calculate_sentiment(self, reviews: List[Dict]) -> float:
        """计算情感得分 (0-1, 1为最正面)"""
        if not reviews:
            return 0.5
        
        scores = []
        for review in reviews:
            text = (review.get("content", "") + " " + review.get("title", "")).lower()
            words = set(re.findall(r"\b[a-z]+\b", text))
            
            pos_count = len(words & self.POSITIVE_WORDS)
            neg_count = len(words & self.NEGATIVE_WORDS)
            
            if pos_count + neg_count > 0:
                score = pos_count / (pos_count + neg_count)
            else:
                # 使用评分作为备用
                rating = review.get("rating", 3)
                score = (rating - 1) / 4
            
            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _extract_pain_points(self, negative_reviews: List[Dict]) -> List[str]:
        """提取差评痛点"""
        pain_patterns = [
            (r"(too small|too tight|runs small|size.{0,20}small)", "尺码偏小"),
            (r"(see.?through|transparent|thin)", "透光/太薄"),
            (r"(pill|pilling|pills)", "容易起球"),
            (r"(fell apart|ripped|torn|broke)", "质量差/易损坏"),
            (r"(uncomfortable|itchy|scratchy)", "穿着不舒服"),
            (r"(faded|color.{0,10}fade)", "容易褪色"),
            (r"(shrunk|shrink)", "缩水"),
            (r"(cheap.{0,10}quality|poor quality)", "质量低劣"),
            (r"(waistband.{0,10}(roll|tight|loose))", "腰带问题"),
            (r"(thread|loose thread|stitching)", "线头/做工问题"),
        ]
        
        pain_counts = Counter()
        
        for review in negative_reviews:
            text = (review.get("content", "") + " " + review.get("title", "")).lower()
            for pattern, pain_point in pain_patterns:
                if re.search(pattern, text):
                    pain_counts[pain_point] += 1
        
        # 返回出现次数最多的痛点
        return [p for p, _ in pain_counts.most_common(5) if pain_counts[p] >= 2]
    
    def _extract_selling_points(self, positive_reviews: List[Dict]) -> List[str]:
        """提取好评卖点"""
        selling_patterns = [
            (r"(soft|buttery soft|super soft)", "材质柔软"),
            (r"(comfortable|comfy)", "穿着舒适"),
            (r"(flattering|slimming|tummy control)", "显瘦/收腹"),
            (r"(good quality|great quality|high quality)", "质量好"),
            (r"(great value|good price|worth)", "性价比高"),
            (r"(stay.{0,10}(up|place)|doesn't roll)", "不下滑/不卷边"),
            (r"(squat.?proof|not see.?through|opaque)", "不透光"),
            (r"(true to size|perfect fit|fits great)", "尺码准确"),
            (r"(love the color|beautiful color)", "颜色好看"),
            (r"(stretchy|flexible|4.?way stretch)", "弹力好"),
        ]
        
        selling_counts = Counter()
        
        for review in positive_reviews:
            text = (review.get("content", "") + " " + review.get("title", "")).lower()
            for pattern, selling_point in selling_patterns:
                if re.search(pattern, text):
                    selling_counts[selling_point] += 1
        
        return [p for p, _ in selling_counts.most_common(5) if selling_counts[p] >= 3]
    
    def generate_wordcloud_data(self, reviews: List[Dict], sentiment: str = "all") -> Dict[str, int]:
        """生成词云数据"""
        if sentiment == "positive":
            reviews = [r for r in reviews if r.get("rating", 0) >= 4]
        elif sentiment == "negative":
            reviews = [r for r in reviews if r.get("rating", 0) <= 2]
        
        text = " ".join([r.get("content", "") + " " + r.get("title", "") for r in reviews])
        keywords = self._extract_keywords(text, top_n=50)
        
        return dict(keywords)
