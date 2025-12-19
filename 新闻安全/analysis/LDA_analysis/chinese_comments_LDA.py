# -*- coding: utf-8 -*-
"""
多平台多情感中文评论LDA主题分析完整代码
支持：消极、积极、中立评论的主题挖掘
平台：弹幕、B站评论、微博评论等中文文本数据
新增功能：
1. 解决中文乱码问题
2. 添加点赞数加权的第二张饼图
"""

import pandas as pd
import numpy as np
import re
import jieba
import matplotlib.pyplot as plt
from collections import Counter
import warnings
import matplotlib.font_manager as fm

warnings.filterwarnings('ignore')

# 解决中文乱码问题
plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# Gensim for LDA
from gensim import corpora, models
from gensim.models import CoherenceModel


# 可选: 用于交互式可视化
import pyLDAvis.gensim_models as gensimvis
import pyLDAvis

class UniversalLDAAnalyzer:
    """
    通用LDA分析器，支持多平台多情感中文评论数据
    """

    def __init__(self):
        # 平台配置字典（可根据需要扩展）
        self.platform_configs = {
            'danmu': {
                'text_column': 'cleaned',
                'sentiment_column': 'final_sentiment',
                'like_column': None,  # 弹幕没有点赞数据
                'custom_clean_rules': [r'空降\d+[:：]?\d+', r'UP主.*?'],
                'expected_topics_range': (2, 4)  # 弹幕主题数较少
            },
            'bilibili': {
                'text_column': 'cleaned',
                'sentiment_column': 'final_sentiment',
                'like_column': 'like_count',  # B站点赞数列名
                'custom_clean_rules': [r'av\d+', r'BV\w+', r'一键三连'],
                'expected_topics_range': (3, 6)
            },
            'weibo': {
                'text_column': '清洗后评论',
                'sentiment_column': '情感标签',
                'like_column': '点赞数',  # 微博点赞数列名
                'custom_clean_rules': [r'回复@[^\s]+', r'#.+?#', r'@[^\s]+'],
                'expected_topics_range': (4, 8)
            }
        }

        # 加载中文停用词表
        self.stopwords = self._load_stopwords('chinese_stopwords.txt')

        # 打印可用字体，帮助调试中文显示问题
        self._check_chinese_fonts()

    def _check_chinese_fonts(self):
        """检查可用的中文字体"""
        fonts = [f.name for f in fm.fontManager.ttflist if '宋体' in f.name or '黑体' in f.name or 'Sim' in f.name]
        print("可用的中文字体:", fonts[:5])  # 只显示前5个

    def _load_stopwords(self, file_path):
        """加载停用词表"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return set([line.strip() for line in f.readlines()])
        except:
            # 默认停用词表
            return set(
                ['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到',
                 '说', '要', '去', '你', '会', '着', '没有', '看', '好'])

    def load_data(self, file_path, platform_type, sentiment_type='消极'):
        """
        加载和预处理数据
        platform_type: 'danmu', 'bilibili', 或 'weibo'
        sentiment_type: '消极', '积极', '中立' 或 '全部'
        """
        if platform_type not in self.platform_configs:
            raise ValueError(f"不支持的平台类型: {platform_type}。可选: {list(self.platform_configs.keys())}")

        # 加载数据
        df = pd.read_excel(file_path)
        config = self.platform_configs[platform_type]

        # 检查必要列
        text_col = config['text_column']
        if text_col not in df.columns:
            raise ValueError(f"文件中缺少必要的文本列: {text_col}")

        # 筛选指定情感的评论
        sentiment_col = config.get('sentiment_column')
        if sentiment_col and sentiment_col in df.columns:
            if sentiment_type != '全部':
                df = df[df[sentiment_col] == sentiment_type].copy()
                print(f"筛选后{sentiment_type}评论数量: {len(df)}")
            else:
                print(f"使用全部评论数据，数量: {len(df)}")
        else:
            print("警告: 未找到情感列，将使用全部数据")

        # 检查点赞数列
        like_col = config.get('like_column')
        if like_col and like_col in df.columns:
            print(f"找到点赞数据列: {like_col}")
            # 处理点赞数为空的情况
            df[like_col] = df[like_col].fillna(0).astype(int)
        else:
            print("警告: 未找到点赞数据列")
            like_col = None

        # 应用平台特定清洗规则
        if 'custom_clean_rules' in config:
            for pattern in config['custom_clean_rules']:
                df[text_col] = df[text_col].apply(
                    lambda x: re.sub(pattern, '', str(x))
                )

        # 通用文本清洗
        df['cleaned_text'] = df[text_col].apply(self._clean_text)

        # 分词处理
        df['tokenized'] = df['cleaned_text'].apply(self._tokenize_text)

        return df, config

    def _clean_text(self, text):
        """通用文本清洗"""
        if not isinstance(text, str):
            return ""

        # 移除URL
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        # 移除HTML标签
        text = re.sub(r'<.*?>', '', text)
        # 移除特殊符号
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _tokenize_text(self, text):
        """中文分词处理"""
        if not text.strip():
            return []

        # 使用jieba分词
        words = jieba.lcut(text)
        # 过滤停用词和单字
        words = [word for word in words if word not in self.stopwords and len(word) > 1]

        return words

    def find_optimal_topics(self, tokenized_texts, max_topics=10):
        """通过一致性分数寻找最佳主题数量"""
        # 创建词典和语料
        dictionary = corpora.Dictionary(tokenized_texts)
        dictionary.filter_extremes(no_below=2, no_above=0.8)
        corpus = [dictionary.doc2bow(text) for text in tokenized_texts]

        coherence_scores = []
        for num_topics in range(2, max_topics + 1):
            lda = models.LdaModel(
                corpus=corpus,
                id2word=dictionary,
                num_topics=num_topics,
                passes=10,
                alpha='auto',
                random_state=42
            )
            coherence_model = CoherenceModel(
                model=lda,
                texts=tokenized_texts,
                dictionary=dictionary,
                coherence='c_v'
            )
            coherence_scores.append(coherence_model.get_coherence())
            print(f"主题数: {num_topics}, 一致性分数: {coherence_scores[-1]:.4f}")

        # 选择最佳主题数
        optimal_topics = np.argmax(coherence_scores) + 2
        print(f"最佳主题数量: {optimal_topics}")

        return optimal_topics, dictionary, corpus

    def train_lda_model(self, tokenized_texts, num_topics=None):
        """训练LDA模型"""
        # 创建词典和语料
        dictionary = corpora.Dictionary(tokenized_texts)
        dictionary.filter_extremes(no_below=2, no_above=0.8)
        corpus = [dictionary.doc2bow(text) for text in tokenized_texts]

        # 自动确定主题数（如果未指定）
        if num_topics is None:
            num_topics, _, _ = self.find_optimal_topics(tokenized_texts)

        # 训练LDA模型
        lda_model = models.LdaModel(
            corpus=corpus,
            id2word=dictionary,
            num_topics=num_topics,
            passes=15,
            alpha='auto',
            per_word_topics=True,
            random_state=42
        )

        return lda_model, corpus, dictionary

    def display_topics(self, lda_model, num_words=10, sentiment_type='消极'):
        """显示主题关键词"""
        topics = lda_model.print_topics(num_words=num_words)
        print(f"\n{sentiment_type}评论主题关键词分布:")
        for topic_id, topic_words in topics:
            print(f"主题 {topic_id}: {topic_words}")
        print("-" * 50)

    def visualize_topic_distribution(self, lda_model, corpus, df, platform_name, sentiment_type='消极'):
        """
        可视化主题分布饼图（双图并列）
        左图：基于评论数量的分布
        右图：基于点赞数加权的分布（如有点赞数据）
        """
        # 计算每个文档的主要主题
        topic_distribution = []
        for i, doc in enumerate(corpus):
            topic_probs = lda_model.get_document_topics(doc)
            if topic_probs:
                main_topic = max(topic_probs, key=lambda x: x[1])[0]
                topic_distribution.append((main_topic, i))

        # 统计主题频率（基于评论数量）
        topic_counts = Counter([t for t, idx in topic_distribution])
        labels = [f'主题 {i}' for i in range(lda_model.num_topics)]
        sizes = [topic_counts.get(i, 0) for i in range(lda_model.num_topics)]

        # 创建图形
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))

        # 左图：基于评论数量的分布
        axes[0].pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        axes[0].set_title(f'{platform_name}平台{sentiment_type}评论主题分布\n(基于评论数量)')
        axes[0].axis('equal')

        # 右图：基于点赞数加权的分布（如有点赞数据）
        like_col = self.platform_configs[platform_name].get('like_column')
        if like_col and like_col in df.columns:
            # 计算每个主题的总点赞数
            topic_likes = {i: 0 for i in range(lda_model.num_topics)}
            for topic, doc_idx in topic_distribution:
                like_count = df.iloc[doc_idx][like_col]
                # 使用 1 + 点赞数 作为权重（避免0点赞影响）
                topic_likes[topic] += (1 + like_count)

            like_sizes = [topic_likes.get(i, 0) for i in range(lda_model.num_topics)]
            total_likes = sum(like_sizes)

            # 计算占比
            if total_likes > 0:
                like_percentages = [size / total_likes * 100 for size in like_sizes]
                # 创建饼图
                wedges, texts, autotexts = axes[1].pie(
                    like_sizes, labels=labels, autopct='%1.1f%%', startangle=90
                )
                axes[1].set_title(f'{platform_name}平台{sentiment_type}评论主题分布\n(基于点赞数加权)')
                axes[1].axis('equal')

                # 添加总点赞数说明
                fig.text(0.5, 0.02, f'总点赞数: {total_likes:,}', ha='center', fontsize=12)
            else:
                axes[1].text(0.5, 0.5, '无点赞数据', ha='center', va='center', fontsize=14)
                axes[1].set_title('点赞数据不可用')
        else:
            axes[1].text(0.5, 0.5, '无点赞数据', ha='center', va='center', fontsize=14)
            axes[1].set_title('点赞数据不可用')

        plt.tight_layout()
        plt.show()

    def generate_interactive_visualization(self, lda_model, corpus, dictionary, platform_name, sentiment_type):
        """生成交互式可视化（需要pyLDAvis）"""
        try:
            vis_data = gensimvis.prepare(lda_model, corpus, dictionary)
            pyLDAvis.display(vis_data)
            # 保存为HTML文件
            html_file = f'{platform_name}_{sentiment_type}_topics.html'
            pyLDAvis.save_html(vis_data, html_file)
            print(f"交互式可视化已保存为: {html_file}")
            return vis_data
        except ImportError:
            print("警告: 未安装pyLDAvis，跳过交互式可视化")
            print("安装命令: pip install pyldavis")
            return None

    def analyze_platform(self, file_path, platform_type, sentiment_type='消极', num_topics=None):
        """
        完整分析流程
        """
        print(f"开始分析 {platform_type} 平台的 {sentiment_type} 评论...")
        print("=" * 50)

        # 1. 加载和预处理数据
        df, config = self.load_data(file_path, platform_type, sentiment_type)
        print(f"有效评论数量: {len(df)}")

        if len(df) == 0:
            print(f"警告: 没有找到{sentiment_type}评论，跳过分析")
            return None, None, None, None

        # 2. 准备分词文本
        tokenized_texts = df['tokenized'].tolist()

        # 3. 训练LDA模型
        lda_model, corpus, dictionary = self.train_lda_model(
            tokenized_texts,
            num_topics or config.get('expected_topics_range', (3, 8))[1]
        )

        # 4. 显示主题结果
        self.display_topics(lda_model, sentiment_type=sentiment_type)

        # 5. 可视化主题分布（双图并列）
        self.visualize_topic_distribution(lda_model, corpus, df, platform_type, sentiment_type)

        # 6. 生成交互式可视化（可选）
        # self.generate_interactive_visualization(lda_model, corpus, dictionary, platform_type, sentiment_type)

        return lda_model, corpus, dictionary, df

    def analyze_all_sentiments(self, file_path, platform_type, num_topics=None):
        """
        一次性分析所有情感类型（消极、积极、中立）
        """
        sentiments = ['消极', '积极', '中立']
        results = {}

        for sentiment in sentiments:
            print(f"\n\n开始分析 {sentiment} 评论")
            print("=" * 50)
            try:
                model, corpus, dictionary, df = self.analyze_platform(
                    file_path, platform_type, sentiment, num_topics
                )
                results[sentiment] = {
                    'model': model,
                    'corpus': corpus,
                    'dictionary': dictionary,
                    'data': df
                }
            except Exception as e:
                print(f"分析{sentiment}评论时出错: {str(e)}")
                results[sentiment] = None

        return results


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 初始化分析器
    analyzer = UniversalLDAAnalyzer()

    # 示例1: 分析B站评论的消极评论（有点赞数据）
    # bilibili_negative = analyzer.analyze_platform(
    #     '剧本问题消极评论.xlsx', 'bilibili', '消极'
    # )

    # 示例2: 分析微博评论的积极评论（有点赞数据）
    weibo_positive = analyzer.analyze_platform(
         '微博评论.xlsx', 'weibo', '积极',num_topics=5
     )

    # 示例3: 分析弹幕数据（无点赞数据，只显示一张图）
    # danmu_results = analyzer.analyze_platform(
    #     '弹幕数据.xlsx', 'danmu', '消极'
    # )

    print("代码已准备就绪!")
    print("请取消注释上面的示例代码并提供实际文件路径以运行分析。")