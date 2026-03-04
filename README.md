# 🔍 亚马逊竞品分析工具

一站式亚马逊竞品分析平台，帮助卖家发现竞品优势、运营漏洞和流量逻辑。

## ✨ 功能特性

- 📦 **ASIN查询** - 快速获取商品基础信息、价格、BSR、评分
- 📊 **竞品对比** - 多ASIN横向对比，雷达图可视化
- 🔑 **关键词分析** - ASIN反查关键词、关键词矩阵
- 💬 **Review分析** - 评论情感分析、痛点/卖点提取
- 🔔 **监控报警** - 价格/BSR/库存变动实时监控

## 🚀 快速开始

### 1. 安装依赖

```bash
cd compet_product
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

### 3. 启动应用

```bash
python run.py
# 或
streamlit run src/ui/app.py
```

访问 http://localhost:8501

## 📁 项目结构

```
compet_product/
├── docs/                    # 文档
│   ├── 01_需求分析.md
│   ├── 02_竞品分析模板.md
│   ├── 03_产品原型.md
│   └── 04_技术方案.md
├── src/
│   ├── collectors/          # 数据采集器
│   │   ├── keepa.py         # Keepa API
│   │   └── amazon_scraper.py # 爬虫(备用)
│   ├── engines/             # 分析引擎
│   │   └── review_analyzer.py # Review NLP分析
│   ├── models/              # 数据模型
│   │   └── database.py      # SQLAlchemy模型
│   ├── ui/                  # 前端界面
│   │   └── app.py           # Streamlit应用
│   └── config.py            # 配置管理
├── data/                    # 数据存储
├── tests/                   # 测试用例
├── requirements.txt         # 依赖清单
├── run.py                   # 启动脚本
└── .env.example             # 环境变量模板
```

## 🔧 数据源

| 数据源 | 用途 | 成本 |
|--------|------|------|
| Keepa API | 价格历史、BSR历史、销量估算 | $19-49/月 |
| Amazon爬虫 | 基础信息、评论内容 | 免费(需谨慎) |

## 📊 技术栈

- **后端**: Python 3.9+
- **前端**: Streamlit
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **可视化**: Plotly
- **NLP**: TextBlob, 自定义规则

## 📝 开发计划

- [x] Phase 1: 基础架构 + Keepa集成
- [x] Phase 2: Review分析引擎
- [ ] Phase 3: 关键词分析 (需第三方API)
- [ ] Phase 4: 监控调度系统
- [ ] Phase 5: 报告导出

## ⚠️ 免责声明

本工具仅供学习研究使用，请遵守亚马逊服务条款和相关法律法规。

## 📄 License

MIT

---

*Built with ❤️ by Claude 军团*
