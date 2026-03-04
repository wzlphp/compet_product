"""Streamlit 主应用"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.collectors.keepa import KeepaCollector
from src.collectors.amazon_scraper import AmazonScraper
from src.engines.review_analyzer import ReviewAnalyzer
from src.models.database import init_db, get_db, Product, PriceHistory
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

# 侧边栏导航
st.sidebar.title("🔍 竞品分析工具")
page = st.sidebar.radio(
    "功能导航",
    ["🏠 ASIN查询", "📊 竞品对比", "🔑 关键词分析", "💬 Review分析", "🔔 监控中心"]
)

# 初始化采集器
@st.cache_resource
def get_collectors():
    keepa = KeepaCollector() if settings.KEEPA_API_KEY else None
    scraper = AmazonScraper()
    return keepa, scraper

keepa_collector, scraper = get_collectors()

# 异步运行辅助函数
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

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
            with st.spinner("正在获取数据..."):
                # 优先使用Keepa, 否则用爬虫
                if keepa_collector:
                    product = run_async(keepa_collector.fetch_product(asin_input, marketplace))
                else:
                    product = run_async(scraper.fetch_product(asin_input, marketplace))
                
                if product:
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
                    if keepa_collector:
                        st.divider()
                        st.subheader("📈 价格 & BSR 趋势")
                        
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
                        st.button("➕ 添加到对比")
                    with btn_col2:
                        st.button("👁 添加到监控")
                    with btn_col3:
                        st.button("📄 导出报告")
                else:
                    st.error("未找到商品信息，请检查ASIN是否正确")
        else:
            st.warning("请输入ASIN")

# ==================== 页面: 竞品对比 ====================
elif page == "📊 竞品对比":
    st.title("📊 竞品对比看板")
    
    st.info("🚧 此功能开发中...")
    
    # 示例对比数据
    compare_data = {
        "指标": ["价格", "BSR", "评分", "评价数", "月销量"],
        "竞品A": ["$52.96", "#158", "4.4", "2,341", "3,200"],
        "竞品B": ["$89.99", "#342", "4.3", "892", "1,500"],
        "竞品C": ["$45.00", "#89", "4.6", "5,672", "6,800"],
        "自身": ["$55.00", "#521", "4.2", "156", "420"]
    }
    
    st.dataframe(pd.DataFrame(compare_data), use_container_width=True)
    
    # 雷达图
    categories = ['价格竞争力', '评分', '评价数', '销量', '品牌力']
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[4, 4.4, 3, 4, 3],
        theta=categories,
        fill='toself',
        name='竞品A'
    ))
    fig.add_trace(go.Scatterpolar(
        r=[3, 4.2, 2, 2, 3],
        theta=categories,
        fill='toself',
        name='自身'
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])))
    
    st.plotly_chart(fig, use_container_width=True)

# ==================== 页面: 关键词分析 ====================
elif page == "🔑 关键词分析":
    st.title("🔑 关键词分析")
    
    st.info("🚧 此功能需要集成关键词数据源 (卖家精灵/Helium10 API)")
    
    # 示例关键词矩阵
    st.subheader("关键词矩阵")
    
    keyword_data = {
        "关键词": ["yoga pants", "high waist leggings", "buttery soft leggings", "workout pants", "squat proof"],
        "搜索量": [89000, 56000, 34000, 28000, 8500],
        "自然排名": [3, 8, 2, 15, 1],
        "广告排名": [1, 4, "-", 6, "-"],
        "类型": ["🎯 机会", "⚔️ 战场", "🎯 机会", "⚔️ 战场", "🔍 长尾"]
    }
    
    st.dataframe(pd.DataFrame(keyword_data), use_container_width=True)
    
    # 关键词矩阵散点图
    fig = px.scatter(
        x=[89000, 56000, 34000, 28000, 8500],
        y=[0.3, 0.8, 0.2, 0.7, 0.1],
        size=[50, 40, 35, 30, 20],
        color=["机会词", "战场词", "机会词", "战场词", "长尾词"],
        text=["yoga pants", "high waist", "buttery soft", "workout", "squat proof"],
        labels={"x": "搜索量", "y": "竞争度"}
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(height=400)
    
    st.plotly_chart(fig, use_container_width=True)

# ==================== 页面: Review分析 ====================
elif page == "💬 Review分析":
    st.title("💬 Review 深度分析")
    
    asin = st.text_input("输入要分析的 ASIN", placeholder="B0D6VW8ZZK")
    
    if st.button("📊 分析评论"):
        if asin:
            with st.spinner("正在抓取和分析评论..."):
                # 抓取评论
                reviews = run_async(scraper.fetch_reviews(asin, pages=3))
                
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
                    
                    # 显示结果
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("总评价", analysis.total_reviews)
                    col2.metric("平均评分", analysis.avg_rating)
                    col3.metric("VP占比", f"{analysis.vp_ratio:.0%}")
                    col4.metric("情感得分", f"{analysis.sentiment_score:.2f}")
                    col5.metric("好评率", f"{analysis.rating_distribution.get(5, 0) + analysis.rating_distribution.get(4, 0):.0f}%")
                    
                    st.divider()
                    
                    # 评分分布
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("⭐ 评分分布")
                        fig = px.bar(
                            x=[5, 4, 3, 2, 1],
                            y=[analysis.rating_distribution.get(i, 0) for i in [5, 4, 3, 2, 1]],
                            labels={"x": "星级", "y": "占比 (%)"},
                            color_discrete_sequence=["#52C41A"]
                        )
                        fig.update_layout(height=300)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 关键词")
                        if analysis.positive_keywords:
                            keywords_df = pd.DataFrame(analysis.positive_keywords[:10], columns=["关键词", "出现次数"])
                            st.dataframe(keywords_df, use_container_width=True)
                    
                    st.divider()
                    
                    # 卖点和痛点
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("✅ 好评卖点 (可复制)")
                        for point in analysis.selling_points:
                            st.success(f"• {point}")
                        if not analysis.selling_points:
                            st.info("暂未提取到明显卖点")
                    
                    with col2:
                        st.subheader("❌ 差评痛点 (差异化机会)")
                        for point in analysis.pain_points:
                            st.error(f"• {point}")
                        if not analysis.pain_points:
                            st.info("暂未提取到明显痛点")
                else:
                    st.warning("未能获取评论数据")
        else:
            st.warning("请输入ASIN")

# ==================== 页面: 监控中心 ====================
elif page == "🔔 监控中心":
    st.title("🔔 竞品监控中心")
    
    st.info("🚧 监控功能开发中...")
    
    # 监控概览
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("监控中", "8")
    col2.metric("今日报警", "3", delta="2")
    col3.metric("未读报警", "5")
    col4.metric("本周变动", "12")
    
    st.divider()
    
    # 最新报警
    st.subheader("🚨 最新报警")
    
    alerts = [
        {"类型": "🔴 价格下降", "ASIN": "B0D6VW8ZZK", "变动": "$62.50 → $52.96 (-15%)", "时间": "2小时前"},
        {"类型": "🟡 BSR上升", "ASIN": "B09XYZ1234", "变动": "#521 → #342 (+34%)", "时间": "5小时前"},
        {"类型": "🔵 新增评论", "ASIN": "B08ABC5678", "变动": "+15条评论", "时间": "今天"},
    ]
    
    st.dataframe(pd.DataFrame(alerts), use_container_width=True)
    
    st.divider()
    
    # 添加监控
    st.subheader("➕ 添加监控")
    
    new_asin = st.text_input("ASIN", placeholder="输入要监控的ASIN")
    
    col1, col2 = st.columns(2)
    with col1:
        st.checkbox("价格变动 >5% 报警", value=True)
        st.checkbox("BSR变动 >20% 报警", value=True)
        st.checkbox("库存状态变化报警", value=True)
    with col2:
        st.checkbox("单日新增评论 >10 报警", value=True)
        st.checkbox("关键词排名掉出首页报警", value=False)
        st.checkbox("Listing内容变更报警", value=False)
    
    st.button("➕ 添加监控", type="primary")

# 页脚
st.sidebar.divider()
st.sidebar.caption("亚马逊竞品分析工具 v1.0")
st.sidebar.caption("© 2026 CompetProduct")
