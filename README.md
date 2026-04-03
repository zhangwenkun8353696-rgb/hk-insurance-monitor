# 香港保险行业舆情监控系统

基于 Python + Flask 的香港保险行业舆情监控与分析系统，提供实时新闻采集、情感分析、风险评估和策略建议。

## 功能特性

- **舆情采集**：自动抓取多来源新闻（新闻媒体、官方公告、社交平台）
- **情感分析**：对舆情进行正面/中性/负面情感分类
- **风险评估**：高/中/低风险等级自动评估
- **行业分析**：话题分布、风险预警、行业趋势总览
- **目标公司分析**：设定目标公司，深度追踪其相关舆情
- **策略建议**：基于舆情数据生成可操作的策略建议，关联具体新闻
- **可视化仪表板**：前端展示总览、行业分析、公司分析、分布统计

## 技术栈

- **后端**：Python 3 + Flask
- **数据库**：SQLite
- **前端**：HTML + CSS + JavaScript（Chart.js 图表）
- **数据采集**：自定义爬虫框架

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

服务启动后访问 http://127.0.0.1:5001

## 项目结构

```
hk-insurance-monitor/
├── app.py              # Flask 主应用 & API
├── database.py         # 数据库操作层
├── requirements.txt    # Python 依赖
├── data/
│   └── monitor.db      # SQLite 数据库（含示例数据）
├── scrapers/
│   ├── base.py         # 爬虫基类
│   ├── news_scraper.py # 新闻爬虫
│   ├── official_scraper.py # 官方公告爬虫
│   └── social_scraper.py   # 社交媒体爬虫
└── static/
    └── index.html      # 前端仪表板
```

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/news` | 获取新闻列表 |
| `GET /api/stats` | 统计概览 |
| `GET /api/strategies` | 策略建议（含关联舆情） |
| `GET /api/industry_analysis` | 行业分析 |
| `GET /api/company_analysis` | 目标公司分析 |
