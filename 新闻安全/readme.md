# 新闻安全课程项目 - 社交媒体多平台分析工具

## 项目简介

本项目是新闻安全课程的期末作业，旨在构建一套完整的社交媒体数据分析工具集。该工具集支持从bilibili采集数据，并提供情感分析、主题建模、词云生成等多种分析功能。

## 功能特点

- **情感分析**：针对不同平台和语言提供定制化的情感分析方案
- **主题建模**：使用LDA算法进行主题分析，发现内容趋势
- **可视化展示**：生成词云图、主题分布图等多种可视化图表
- **可扩展架构**：模块化设计，易于添加新的平台支持

## 技术栈

- Python 3.x
- 数据处理：pandas, numpy
- 网络请求：requests, aiohttp
- 网页解析：beautifulsoup4
- 自然语言处理：jieba, nltk, langdetect, snownlp, gensim
- 数据可视化：matplotlib, wordcloud, pyLDAvis
- Web API客户端：google-api-python-client, praw
- 浏览器自动化：selenium

## 安装说明

### 环境要求

- Python 3.7+
- pip包管理器
- Chrome浏览器（用于数据采集）
- ChromeDriver（与Chrome版本匹配）

### 安装步骤

1. 克隆项目代码：
```bash
git clone <repository-url>
cd 新闻安全
```

2. 安装依赖包：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp config/.env.example .env
```
编辑`.env`文件，填入各平台所需的API密钥和认证信息。

## 使用指南

### 1. 平台数据采集

#### B站数据采集
- 互动数据：`platforms/bilibili/interaction_data.py`
- 评论数据：`platforms/bilibili/comments_crawler.py`
- 弹幕数据：`platforms/bilibili/danmu_crawler.py`

### 2. 数据分析模块

#### 情感分析
- B站情感分析：`analysis/sentiment/bilibili_sentiment/`

#### 词云生成
- 多平台词云：`analysis/wordcloud/`下的各个平台目录

#### 主题建模
- 中文评论主题分析：`analysis/LDA_analysis/chinese_comments_LDA.py`
- 多语言评论主题分析：`analysis/LDA_analysis/foreignlanguage_coments_LDA.py`

## 项目结构

```
新闻安全/
├── analysis/              # 数据分析模块
│   ├── LDA_analysis/      # 主题建模分析
│   ├── sentiment/         # 情感分析
│   └── wordcloud/         # 词云生成
├── platforms/             # 各平台数据采集工具
│   ├── bilibili/          # B站相关工具
│   ├── reddit/            # Reddit相关工具
│   ├── weibo_comment/     # 微博评论工具
│   └── youtube/           # YouTube相关工具
├── config/                # 配置文件
├── utils/                 # 通用工具函数
├── requirements.txt       # 项目依赖
└── readme.md             # 项目说明文档
```

## 配置说明

B站Cookie需要配置在`.env`文件中：


## 注意事项

本工具仅供学习研究使用，请勿用于商业用途