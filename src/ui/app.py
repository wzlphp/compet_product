"""Streamlit 主应用 - 完整版"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import asyncio
import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.collectors.keepa import KeepaCollector
from src.collectors.amazon_scraper import AmazonScraper
from src.collectors.genie_api import GenieCollector
from src.engines.review_analyzer import ReviewAnalyzer
from src.models.database import init_db, get_db, Product, PriceHistory, Keyword, Review, MonitorConfig, Alert
from src.config import settings

# 页面配置
st.set_page_config(
    page_title="亚马逊竞品分析工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化数据库
init_db()

# 数据存储路径
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
COMPARE_FILE = DATA_DIR / "compare_list.json"
MONITOR_FILE = DATA_DIR / "monitor_list.json"
ALERTS_FILE = DATA_DIR / "alerts.json"

# 辅助函数: 加载/保存JSON
def load_json(file_path, default=None):
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default or []

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 侧边栏导航
st.sidebar.title("🔍 竞品分析工具")
page = st.sidebar.radio(
    "功能导航",
    ["🏠 ASIN查询", "📊 竞品对比", "🔑 关键词分析", "💬 Review分析", "🔔 监控中心"]
)

# 初始化采集器
@st.cache_resource
def get_collectors():
    genie = GenieCollector()
    keepa = KeepaCollector() if settings.KEEPA_API_KEY else None
    scraper = AmazonScraper()
    return genie, keepa, scraper

genie_collector, keepa_collector, scraper = get_collectors()

# 异步运行辅助函数
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# 获取商品数据 (统一接口)
def fetch_product_data(asin, marketplace="US"):
    """按优先级获取商品数据"""
    product = run_async(scraper.fetch_product(asin, marketplace))
    if not product:
        product = run_async(genie_collector.fetch_product(asin, marketplace))
    if not product and keepa_collector:
        product = run_async(keepa_collector.fetch_product(asin, marketplace))
    return product

# ==================== 页面: ASIN查询 ====================
if page == "🏠 ASIN查询":
    st.title("📦 ASIN 商品查询")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        asin_input = st.text_input(
            "输入 ASIN",
            placeholder="例如: B0D6VW8ZZK",
            help="支持单个ASIN查询"
        )
    with col2:
        marketplace = st.selectbox("站点", ["US", "UK", "DE", "JP", "CA"])
    
    if st.button("🔍 查询", type="primary"):
        if asin_input:
            asin_input = asin_input.strip().upper()
            with st.spinner("正在获取数据..."):
                product = fetch_product_data(asin_input, marketplace)
                
                if product:
                    # 保存到session用于后续操作
                    st.session_state['current_product'] = {
                        'asin': asin_input,
                        'marketplace': marketplace,
                        'data': product
                    }
                    
                    # 显示商品信息
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        if product.image_url:
                            st.image(product.image_url, width=250)
                    
                    with col2:
                        st.subheader(product.title[:100] + "..." if len(product.title) > 100 else product.title)
                        
                        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                        
                        with metrics_col1:
                            st.metric("💰 价格", f"${product.price:.2f}" if product.price else "N/A")
                        with metrics_col2:
                            st.metric("🏆 BSR", f"#{product.bsr:,}" if product.bsr else "N/A")
                        with metrics_col3:
                            st.metric("⭐ 评分", f"{product.rating}" if product.rating else "N/A")
                        with metrics_col4:
                            st.metric("💬 评价数", f"{product.review_count:,}" if product.review_count else "N/A")
                        
                        st.divider()
                        
                        info_col1, info_col2 = st.columns(2)
                        with info_col1:
                            st.write(f"**品牌:** {product.brand or 'N/A'}")
                            st.write(f"**类目:** {product.bsr_category or 'N/A'}")
                        with info_col2:
                            st.write(f"**月销量:** ~{product.monthly_sales:,}" if product.monthly_sales else "**月销量:** N/A")
                            st.write(f"**父ASIN:** {product.parent_asin or 'N/A'}")
                    
                    # 历史数据图表
                    st.divider()
                    st.subheader("📈 价格 & BSR 趋势")
                    
                    history = run_async(genie_collector.fetch_price_history(asin_input, days=90))
                    if not history and keepa_collector:
                        history = run_async(keepa_collector.fetch_price_history(asin_input, days=90))
                        
                    if history:
                        df = pd.DataFrame(history)
                        df['date'] = pd.to_datetime(df['date'])
                        
                        fig = make_subplots(specs=[[{"secondary_y": True}]])
                        fig.add_trace(
                            go.Scatter(x=df['date'], y=df['price'], name="价格", line=dict(color='#1890FF')),
                            secondary_y=False
                        )
                        fig.add_trace(
                            go.Scatter(x=df['date'], y=df['bsr'], name="BSR", line=dict(color='#FF7A45')),
                            secondary_y=True
                        )
                        fig.update_yaxes(title_text="价格 ($)", secondary_y=False)
                        fig.update_yaxes(title_text="BSR 排名", secondary_y=True, autorange="reversed")
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("暂无历史数据")
                    
                    # 操作按钮
                    st.divider()
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if st.button("➕ 添加到对比"):
                            compare_list = load_json(COMPARE_FILE, [])
                            if not any(c['asin'] == asin_input for c in compare_list):
                                compare_list.append({
                                    'asin': asin_input,
                                    'title': product.title[:50],
                                    'price': product.price,
                                    'bsr': product.bsr,
                                    'rating': product.rating,
                                    'review_count': product.review_count,
                                    'monthly_sales': product.monthly_sales,
                                    'brand': product.brand,
                                    'image_url': product.image_url,
                                    'added_at': datetime.now().isoformat()
                                })
                                save_json(COMPARE_FILE, compare_list)
                                st.success(f"已添加 {asin_input} 到对比列表")
                            else:
                                st.warning("该ASIN已在对比列表中")
                    with btn_col2:
                        if st.button("👁 添加到监控"):
                            monitor_list = load_json(MONITOR_FILE, [])
                            if not any(m['asin'] == asin_input for m in monitor_list):
                                monitor_list.append({
                                    'asin': asin_input,
                                    'title': product.title[:50],
                                    'marketplace': marketplace,
                                    'base_price': product.price,
                                    'base_bsr': product.bsr,
                                    'price_alert': True,
                                    'bsr_alert': True,
                                    'review_alert': True,
                                    'added_at': datetime.now().isoformat()
                                })
                                save_json(MONITOR_FILE, monitor_list)
                                st.success(f"已添加 {asin_input} 到监控列表")
                            else:
                                st.warning("该ASIN已在监控列表中")
                    with btn_col3:
                        if st.button("📄 导出报告"):
                            report = f"""# 竞品分析报告
## {product.title}

**ASIN:** {asin_input}
**站点:** Amazon {marketplace}
**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

### 基础信息
- 品牌: {product.brand or 'N/A'}
- 价格: ${product.price:.2f if product.price else 'N/A'}
- BSR: #{product.bsr:,} if product.bsr else 'N/A'
- 评分: {product.rating or 'N/A'}
- 评价数: {product.review_count:,} if product.review_count else 'N/A'
- 月销量: ~{product.monthly_sales:,} if product.monthly_sales else 'N/A'
"""
                            st.download_button("📥 下载报告", report, f"report_{asin_input}.md", "text/markdown")
                else:
                    st.error("未找到商品信息，请检查ASIN是否正确")
        else:
            st.warning("请输入ASIN")

# ==================== 页面: 竞品对比 ====================
elif page == "📊 竞品对比":
    st.title("📊 竞品对比看板")
    
    # 加载对比列表
    compare_list = load_json(COMPARE_FILE, [])
    
    # 添加新ASIN
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        new_asin = st.text_input("添加ASIN到对比", placeholder="输入ASIN")
    with col2:
        mp = st.selectbox("站点", ["US", "UK", "DE", "JP", "CA"], key="compare_mp")
    with col3:
        st.write("")
        st.write("")
        if st.button("➕ 添加", type="primary"):
            if new_asin:
                new_asin = new_asin.strip().upper()
                if not any(c['asin'] == new_asin for c in compare_list):
                    with st.spinner(f"正在获取 {new_asin} 数据..."):
                        product = fetch_product_data(new_asin, mp)
                        if product:
                            compare_list.append({
                                'asin': new_asin,
                                'title': product.title[:50],
                                'price': product.price,
                                'bsr': product.bsr,
                                'rating': product.rating,
                                'review_count': product.review_count,
                                'monthly_sales': product.monthly_sales,
                                'brand': product.brand,
                                'image_url': product.image_url,
                                'added_at': datetime.now().isoformat()
                            })
                            save_json(COMPARE_FILE, compare_list)
                            st.rerun()
                        else:
                            st.error("未找到商品")
                else:
                    st.warning("已存在")
    
    if not compare_list:
        st.info("📋 对比列表为空，请先添加商品")
    else:
        # 显示对比表格
        st.subheader(f"📋 对比列表 ({len(compare_list)}个商品)")
        
        # 构建对比数据
        compare_df = pd.DataFrame(compare_list)
        compare_df['价格'] = compare_df['price'].apply(lambda x: f"${x:.2f}" if x else "N/A")
        compare_df['BSR'] = compare_df['bsr'].apply(lambda x: f"#{x:,}" if x else "N/A")
        compare_df['评分'] = compare_df['rating'].apply(lambda x: f"⭐{x}" if x else "N/A")
        compare_df['评价数'] = compare_df['review_count'].apply(lambda x: f"{x:,}" if x else "N/A")
        compare_df['月销量'] = compare_df['monthly_sales'].apply(lambda x: f"~{x:,}" if x else "N/A")
        
        display_df = compare_df[['asin', 'title', '价格', 'BSR', '评分', '评价数', '月销量', 'brand']]
        display_df.columns = ['ASIN', '标题', '价格', 'BSR', '评分', '评价数', '月销量', '品牌']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # 删除按钮
        col1, col2 = st.columns([3, 1])
        with col1:
            del_asin = st.selectbox("选择要删除的商品", [c['asin'] for c in compare_list])
        with col2:
            st.write("")
            st.write("")
            if st.button("🗑️ 删除"):
                compare_list = [c for c in compare_list if c['asin'] != del_asin]
                save_json(COMPARE_FILE, compare_list)
                st.rerun()
        
        st.divider()
        
        # 可视化对比
        if len(compare_list) >= 2:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 价格对比")
                prices = [c['price'] or 0 for c in compare_list]
                asins = [c['asin'] for c in compare_list]
                fig = px.bar(x=asins, y=prices, labels={'x': 'ASIN', 'y': '价格 ($)'})
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("🏆 BSR对比")
                bsrs = [c['bsr'] or 0 for c in compare_list]
                fig = px.bar(x=asins, y=bsrs, labels={'x': 'ASIN', 'y': 'BSR排名'})
                fig.update_layout(height=300, yaxis={'autorange': 'reversed'})
                st.plotly_chart(fig, use_container_width=True)
            
            # 雷达图
            st.subheader("🎯 综合能力雷达图")
            
            # 归一化数据
            def normalize(values, reverse=False):
                if not values or all(v is None or v == 0 for v in values):
                    return [0] * len(values)
                valid = [v for v in values if v and v > 0]
                if not valid:
                    return [0] * len(values)
                min_v, max_v = min(valid), max(valid)
                if min_v == max_v:
                    return [5] * len(values)
                result = []
                for v in values:
                    if v and v > 0:
                        score = (v - min_v) / (max_v - min_v) * 5
                        result.append(5 - score if reverse else score)
                    else:
                        result.append(0)
                return result
            
            categories = ['价格竞争力', '销量排名', '评分', '评价数', '月销量']
            
            fig = go.Figure()
            for i, c in enumerate(compare_list[:5]):  # 最多5个
                r = [
                    5 - normalize([x['price'] for x in compare_list])[i] if compare_list[i]['price'] else 0,
                    5 - normalize([x['bsr'] for x in compare_list])[i] if compare_list[i]['bsr'] else 0,
                    (c['rating'] or 0),
                    normalize([x['review_count'] for x in compare_list])[i],
                    normalize([x['monthly_sales'] for x in compare_list])[i]
                ]
                fig.add_trace(go.Scatterpolar(
                    r=r,
                    theta=categories,
                    fill='toself',
                    name=c['asin']
                ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                height=450
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # 导出对比报告
        st.divider()
        if st.button("📥 导出对比报告"):
            report = "# 竞品对比报告\n\n"
            report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            report += "| ASIN | 标题 | 价格 | BSR | 评分 | 评价数 |\n"
            report += "|------|------|------|-----|------|--------|\n"
            for c in compare_list:
                report += f"| {c['asin']} | {c['title'][:30]} | ${c['price']:.2f if c['price'] else 'N/A'} | #{c['bsr']:,} if c['bsr'] else 'N/A' | {c['rating'] or 'N/A'} | {c['review_count'] or 'N/A'} |\n"
            st.download_button("📥 下载", report, "compare_report.md", "text/markdown")

# ==================== 页面: 关键词分析 ====================
elif page == "🔑 关键词分析":
    st.title("🔑 关键词分析")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        kw_asin = st.text_input("输入ASIN进行关键词分析", placeholder="B0D6VW8ZZK")
    with col2:
        kw_mp = st.selectbox("站点", ["US", "UK", "DE", "JP", "CA"], key="kw_mp")
    
    if st.button("🔍 分析关键词", type="primary"):
        if kw_asin:
            kw_asin = kw_asin.strip().upper()
            with st.spinner("正在分析关键词..."):
                # 获取商品信息
                product = fetch_product_data(kw_asin, kw_mp)
                
                if product:
                    st.success(f"✅ 商品: {product.title[:60]}...")
                    
                    # 从标题提取关键词
                    st.subheader("📝 标题关键词分析")
                    
                    import re
                    title_words = re.findall(r'\b[a-zA-Z]{3,}\b', product.title.lower())
                    stop_words = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'are', 'was', 'were', 'been', 'being', 'have', 'has', 'had', 'will', 'would', 'could', 'should'}
                    title_words = [w for w in title_words if w not in stop_words]
                    
                    from collections import Counter
                    word_freq = Counter(title_words)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**核心关键词:**")
                        for word, count in word_freq.most_common(10):
                            st.write(f"• {word}")
                    
                    with col2:
                        st.write("**关键词组合建议:**")
                        if len(title_words) >= 2:
                            bigrams = [f"{title_words[i]} {title_words[i+1]}" for i in range(len(title_words)-1)]
                            for bg in list(set(bigrams))[:5]:
                                st.write(f"• {bg}")
                    
                    st.divider()
                    
                    # 尝试从API获取关键词
                    st.subheader("🔗 关联关键词")
                    keywords = run_async(genie_collector.fetch_keywords(kw_asin))
                    
                    if keywords:
                        kw_data = []
                        for kw in keywords[:20]:
                            kw_data.append({
                                '关键词': kw.keyword,
                                '搜索量': kw.search_volume,
                                '自然排名': kw.organic_rank or '-',
                                '广告排名': kw.sponsored_rank or '-',
                                '竞争度': kw.competition_level
                            })
                        st.dataframe(pd.DataFrame(kw_data), use_container_width=True, hide_index=True)
                        
                        # 关键词矩阵图
                        st.subheader("📊 关键词矩阵")
                        fig = px.scatter(
                            x=[kw.search_volume for kw in keywords[:15]],
                            y=[0.3 if kw.competition_level == 'low' else 0.6 if kw.competition_level == 'medium' else 0.9 for kw in keywords[:15]],
                            size=[max(20, kw.search_volume/1000) for kw in keywords[:15]],
                            text=[kw.keyword[:15] for kw in keywords[:15]],
                            labels={'x': '搜索量', 'y': '竞争度'}
                        )
                        fig.update_traces(textposition='top center')
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("💡 暂无API关键词数据，以下为基于标题的分析")
                        
                        # 模拟关键词数据
                        sim_keywords = [
                            {'关键词': w, '搜索量估算': len(w) * 1000, '类型': '🎯 核心词' if i < 3 else '🔍 长尾词'}
                            for i, (w, _) in enumerate(word_freq.most_common(10))
                        ]
                        st.dataframe(pd.DataFrame(sim_keywords), use_container_width=True, hide_index=True)
                    
                    # 词云图
                    st.divider()
                    st.subheader("☁️ 关键词词云")
                    
                    if title_words:
                        wordcloud = WordCloud(
                            width=800, height=400,
                            background_color='white',
                            colormap='viridis'
                        ).generate(' '.join(title_words * 3))
                        
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.imshow(wordcloud, interpolation='bilinear')
                        ax.axis('off')
                        st.pyplot(fig)
                else:
                    st.error("未找到商品信息")
        else:
            st.warning("请输入ASIN")

# ==================== 页面: Review分析 ====================
elif page == "💬 Review分析":
    st.title("💬 Review 深度分析")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        review_asin = st.text_input("输入要分析的 ASIN", placeholder="B0D6VW8ZZK")
    with col2:
        review_pages = st.number_input("抓取页数", min_value=1, max_value=10, value=3)
    
    if st.button("📊 分析评论", type="primary"):
        if review_asin:
            review_asin = review_asin.strip().upper()
            with st.spinner(f"正在抓取和分析 {review_pages} 页评论..."):
                # 获取评论
                reviews = run_async(scraper.fetch_reviews(review_asin, pages=review_pages))
                
                if not reviews:
                    reviews = run_async(genie_collector.fetch_reviews(review_asin, pages=review_pages))
                
                if reviews:
                    # 转换为字典列表
                    review_dicts = [
                        {
                            "rating": r.rating,
                            "title": r.title,
                            "content": r.content,
                            "is_vp": r.is_vp,
                            "helpful_votes": r.helpful_votes
                        }
                        for r in reviews
                    ]
                    
                    # 分析
                    analyzer = ReviewAnalyzer()
                    analysis = analyzer.analyze(review_dicts)
                    
                    # 概览指标
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("📝 总评价", analysis.total_reviews)
                    col2.metric("⭐ 平均评分", analysis.avg_rating)
                    col3.metric("✅ VP占比", f"{analysis.vp_ratio:.0%}")
                    col4.metric("😊 情感得分", f"{analysis.sentiment_score:.2f}")
                    good_rate = analysis.rating_distribution.get(5, 0) + analysis.rating_distribution.get(4, 0)
                    col5.metric("👍 好评率", f"{good_rate:.0f}%")
                    
                    st.divider()
                    
                    # 评分分布 & 关键词
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("⭐ 评分分布")
                        ratings = [5, 4, 3, 2, 1]
                        percentages = [analysis.rating_distribution.get(i, 0) for i in ratings]
                        colors = ['#52C41A', '#95DE64', '#FADB14', '#FFA940', '#FF4D4F']
                        
                        fig = go.Figure(go.Bar(
                            x=ratings,
                            y=percentages,
                            marker_color=colors,
                            text=[f"{p:.1f}%" for p in percentages],
                            textposition='outside'
                        ))
                        fig.update_layout(
                            height=300,
                            xaxis_title="星级",
                            yaxis_title="占比 (%)"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 高频关键词")
                        if analysis.positive_keywords:
                            kw_df = pd.DataFrame(analysis.positive_keywords[:10], columns=["关键词", "出现次数"])
                            fig = px.bar(kw_df, x='出现次数', y='关键词', orientation='h')
                            fig.update_layout(height=300, yaxis={'categoryorder': 'total ascending'})
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("暂无关键词数据")
                    
                    st.divider()
                    
                    # 卖点和痛点
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("✅ 好评卖点")
                        st.caption("可直接复用到Listing的卖点")
                        if analysis.selling_points:
                            for point in analysis.selling_points:
                                st.success(f"✓ {point}")
                        else:
                            st.info("暂未提取到明显卖点")
                    
                    with col2:
                        st.subheader("❌ 差评痛点")
                        st.caption("差异化改进机会")
                        if analysis.pain_points:
                            for point in analysis.pain_points:
                                st.error(f"✗ {point}")
                        else:
                            st.info("暂未提取到明显痛点")
                    
                    st.divider()
                    
                    # 词云
                    st.subheader("☁️ 评论词云")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**😊 好评词云**")
                        pos_words = analyzer.generate_wordcloud_data(review_dicts, "positive")
                        if pos_words:
                            wc = WordCloud(width=400, height=300, background_color='white', colormap='Greens').generate_from_frequencies(pos_words)
                            fig, ax = plt.subplots()
                            ax.imshow(wc, interpolation='bilinear')
                            ax.axis('off')
                            st.pyplot(fig)
                    
                    with col2:
                        st.write("**😞 差评词云**")
                        neg_words = analyzer.generate_wordcloud_data(review_dicts, "negative")
                        if neg_words:
                            wc = WordCloud(width=400, height=300, background_color='white', colormap='Reds').generate_from_frequencies(neg_words)
                            fig, ax = plt.subplots()
                            ax.imshow(wc, interpolation='bilinear')
                            ax.axis('off')
                            st.pyplot(fig)
                    
                    st.divider()
                    
                    # 评论详情
                    st.subheader("📜 评论详情")
                    
                    review_tab1, review_tab2, review_tab3 = st.tabs(["全部", "好评 (4-5星)", "差评 (1-2星)"])
                    
                    with review_tab1:
                        for r in review_dicts[:20]:
                            with st.expander(f"{'⭐' * r['rating']} {r['title'][:50]}"):
                                st.write(r['content'])
                                st.caption(f"VP: {'✅' if r['is_vp'] else '❌'} | 有用: {r['helpful_votes']}")
                    
                    with review_tab2:
                        pos_reviews = [r for r in review_dicts if r['rating'] >= 4]
                        for r in pos_reviews[:15]:
                            with st.expander(f"{'⭐' * r['rating']} {r['title'][:50]}"):
                                st.write(r['content'])
                    
                    with review_tab3:
                        neg_reviews = [r for r in review_dicts if r['rating'] <= 2]
                        for r in neg_reviews[:15]:
                            with st.expander(f"{'⭐' * r['rating']} {r['title'][:50]}"):
                                st.write(r['content'])
                    
                    # 导出
                    if st.button("📥 导出分析报告"):
                        report = f"""# Review分析报告 - {review_asin}

## 概览
- 总评价数: {analysis.total_reviews}
- 平均评分: {analysis.avg_rating}
- VP占比: {analysis.vp_ratio:.0%}
- 情感得分: {analysis.sentiment_score:.2f}

## 评分分布
- 5星: {analysis.rating_distribution.get(5, 0):.1f}%
- 4星: {analysis.rating_distribution.get(4, 0):.1f}%
- 3星: {analysis.rating_distribution.get(3, 0):.1f}%
- 2星: {analysis.rating_distribution.get(2, 0):.1f}%
- 1星: {analysis.rating_distribution.get(1, 0):.1f}%

## 好评卖点
{chr(10).join(['- ' + p for p in analysis.selling_points]) or '暂无'}

## 差评痛点
{chr(10).join(['- ' + p for p in analysis.pain_points]) or '暂无'}

## 高频关键词
{chr(10).join([f'- {kw}: {cnt}' for kw, cnt in analysis.positive_keywords[:10]])}
"""
                        st.download_button("📥 下载", report, f"review_analysis_{review_asin}.md", "text/markdown")
                else:
                    st.warning("未能获取评论数据，请稍后重试")
        else:
            st.warning("请输入ASIN")

# ==================== 页面: 监控中心 ====================
elif page == "🔔 监控中心":
    st.title("🔔 竞品监控中心")
    
    # 加载监控列表和报警
    monitor_list = load_json(MONITOR_FILE, [])
    alerts = load_json(ALERTS_FILE, [])
    
    # 监控概览
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 监控中", len(monitor_list))
    today_alerts = [a for a in alerts if a.get('time', '').startswith(datetime.now().strftime('%Y-%m-%d'))]
    col2.metric("🚨 今日报警", len(today_alerts))
    unread = [a for a in alerts if not a.get('read', False)]
    col3.metric("📬 未读报警", len(unread))
    week_alerts = [a for a in alerts if datetime.fromisoformat(a.get('time', '2000-01-01')) > datetime.now() - timedelta(days=7)]
    col4.metric("📈 本周变动", len(week_alerts))
    
    st.divider()
    
    # 添加监控
    st.subheader("➕ 添加监控")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        new_monitor_asin = st.text_input("ASIN", placeholder="输入要监控的ASIN", key="new_monitor")
    with col2:
        monitor_mp = st.selectbox("站点", ["US", "UK", "DE", "JP", "CA"], key="monitor_mp")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        price_alert = st.checkbox("💰 价格变动 >5% 报警", value=True)
        bsr_alert = st.checkbox("🏆 BSR变动 >20% 报警", value=True)
    with col2:
        review_alert = st.checkbox("💬 新增评论 >10 报警", value=True)
        stock_alert = st.checkbox("📦 库存状态变化报警", value=False)
    with col3:
        keyword_alert = st.checkbox("🔑 关键词排名变化报警", value=False)
        listing_alert = st.checkbox("📝 Listing内容变更报警", value=False)
    
    if st.button("➕ 添加监控", type="primary"):
        if new_monitor_asin:
            new_monitor_asin = new_monitor_asin.strip().upper()
            if not any(m['asin'] == new_monitor_asin for m in monitor_list):
                with st.spinner("正在获取商品信息..."):
                    product = fetch_product_data(new_monitor_asin, monitor_mp)
                    if product:
                        monitor_list.append({
                            'asin': new_monitor_asin,
                            'title': product.title[:50],
                            'marketplace': monitor_mp,
                            'base_price': product.price,
                            'base_bsr': product.bsr,
                            'base_reviews': product.review_count,
                            'price_alert': price_alert,
                            'bsr_alert': bsr_alert,
                            'review_alert': review_alert,
                            'stock_alert': stock_alert,
                            'keyword_alert': keyword_alert,
                            'listing_alert': listing_alert,
                            'last_check': datetime.now().isoformat(),
                            'added_at': datetime.now().isoformat()
                        })
                        save_json(MONITOR_FILE, monitor_list)
                        st.success(f"✅ 已添加 {new_monitor_asin} 到监控列表")
                        st.rerun()
                    else:
                        st.error("未找到商品信息")
            else:
                st.warning("该ASIN已在监控列表中")
        else:
            st.warning("请输入ASIN")
    
    st.divider()
    
    # 监控列表
    st.subheader("📋 监控列表")
    
    if not monitor_list:
        st.info("监控列表为空，请添加商品")
    else:
        for i, item in enumerate(monitor_list):
            with st.expander(f"📦 {item['asin']} - {item.get('title', 'N/A')[:40]}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**站点:** {item.get('marketplace', 'US')}")
                    st.write(f"**基准价格:** ${item.get('base_price', 0):.2f}" if item.get('base_price') else "**基准价格:** N/A")
                with col2:
                    st.write(f"**基准BSR:** #{item.get('base_bsr', 0):,}" if item.get('base_bsr') else "**基准BSR:** N/A")
                    st.write(f"**基准评论:** {item.get('base_reviews', 0):,}" if item.get('base_reviews') else "**基准评论:** N/A")
                with col3:
                    st.write(f"**添加时间:** {item.get('added_at', 'N/A')[:10]}")
                    st.write(f"**最后检查:** {item.get('last_check', 'N/A')[:10]}")
                
                # 报警设置
                st.write("**报警设置:**")
                alerts_text = []
                if item.get('price_alert'): alerts_text.append("💰价格")
                if item.get('bsr_alert'): alerts_text.append("🏆BSR")
                if item.get('review_alert'): alerts_text.append("💬评论")
                if item.get('stock_alert'): alerts_text.append("📦库存")
                st.write(" | ".join(alerts_text) if alerts_text else "无")
                
                # 操作按钮
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🔄 立即检查", key=f"check_{i}"):
                        with st.spinner("正在检查..."):
                            product = fetch_product_data(item['asin'], item.get('marketplace', 'US'))
                            if product:
                                # 检查变动
                                changes = []
                                if item.get('price_alert') and item.get('base_price') and product.price:
                                    price_change = (product.price - item['base_price']) / item['base_price']
                                    if abs(price_change) > 0.05:
                                        changes.append(f"💰 价格: ${item['base_price']:.2f} → ${product.price:.2f} ({price_change:+.1%})")
                                
                                if item.get('bsr_alert') and item.get('base_bsr') and product.bsr:
                                    bsr_change = (product.bsr - item['base_bsr']) / item['base_bsr']
                                    if abs(bsr_change) > 0.20:
                                        changes.append(f"🏆 BSR: #{item['base_bsr']:,} → #{product.bsr:,} ({bsr_change:+.1%})")
                                
                                if changes:
                                    for change in changes:
                                        st.warning(change)
                                        alerts.append({
                                            'asin': item['asin'],
                                            'type': change.split()[0],
                                            'message': change,
                                            'time': datetime.now().isoformat(),
                                            'read': False
                                        })
                                    save_json(ALERTS_FILE, alerts)
                                else:
                                    st.success("✅ 无异常变动")
                                
                                # 更新最后检查时间
                                monitor_list[i]['last_check'] = datetime.now().isoformat()
                                save_json(MONITOR_FILE, monitor_list)
                            else:
                                st.error("检查失败")
                with col2:
                    if st.button("📊 更新基准", key=f"update_{i}"):
                        with st.spinner("正在更新..."):
                            product = fetch_product_data(item['asin'], item.get('marketplace', 'US'))
                            if product:
                                monitor_list[i]['base_price'] = product.price
                                monitor_list[i]['base_bsr'] = product.bsr
                                monitor_list[i]['base_reviews'] = product.review_count
                                monitor_list[i]['last_check'] = datetime.now().isoformat()
                                save_json(MONITOR_FILE, monitor_list)
                                st.success("✅ 基准已更新")
                                st.rerun()
                with col3:
                    if st.button("🗑️ 删除", key=f"del_{i}"):
                        monitor_list.pop(i)
                        save_json(MONITOR_FILE, monitor_list)
                        st.rerun()
    
    st.divider()
    
    # 报警历史
    st.subheader("🚨 报警历史")
    
    if not alerts:
        st.info("暂无报警记录")
    else:
        # 标记全部已读
        if st.button("✅ 全部标为已读"):
            for a in alerts:
                a['read'] = True
            save_json(ALERTS_FILE, alerts)
            st.rerun()
        
        # 显示报警
        for i, alert in enumerate(reversed(alerts[-20:])):  # 最近20条
            status = "📬" if not alert.get('read') else "📭"
            time_str = alert.get('time', '')[:16].replace('T', ' ')
            
            col1, col2, col3 = st.columns([1, 4, 1])
            with col1:
                st.write(f"{status} {alert.get('type', '📢')}")
            with col2:
                st.write(f"**{alert.get('asin', 'N/A')}** - {alert.get('message', '')}")
            with col3:
                st.caption(time_str)
        
        # 清除报警
        if st.button("🗑️ 清除所有报警"):
            save_json(ALERTS_FILE, [])
            st.rerun()

# 页脚
st.sidebar.divider()
st.sidebar.caption("亚马逊竞品分析工具 v2.0")
st.sidebar.caption(f"© 2026 CompetProduct")
st.sidebar.caption(f"数据更新: {datetime.now().strftime('%H:%M')}")
