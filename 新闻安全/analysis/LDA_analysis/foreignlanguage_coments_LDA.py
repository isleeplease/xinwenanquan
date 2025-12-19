# -*- coding: utf-8 -*-
"""
多语言社交媒体评论LDA主题分析
支持：Twitter、YouTube等多平台多语言评论
新增功能：点赞数加权的并列饼图可视化
"""

import pandas as pd
import numpy as np
import re
import jieba
import matplotlib.pyplot as plt
from collections import Counter
import warnings

warnings.filterwarnings('ignore')

# 解决中文乱码问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 多语言处理库
import langdetect
from langdetect import DetectorFactory

# 确保语言检测结果一致性
DetectorFactory.seed = 0

# Gensim for LDA
from gensim import corpora, models
from gensim.models import CoherenceModel


class MultilingualLDAAnalyzer:
    """
    多语言LDA分析器 - 增强版
    支持点赞数加权的并列饼图可视化
    """

    def __init__(self):
        # 多语言停用词表
        self.stopwords = {
            'en': set(['the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'on', 'with']),
            'zh': set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人']),
            'de': set(['der', 'die', 'das', 'und', 'in', 'den', 'von', 'zu', 'für']),
            'default': set()
        }

        # 平台配置
        self.platform_configs = {
            'twitter': {
                'text_column': 'cleaned_text',
                'sentiment_column': 'sentiment',
                'language_column': 'language',
                'like_column': '点赞数'
            },
            'youtube': {
                'text_column': 'cleaned_text',
                'sentiment_column': 'sentiment',
                'language_column': 'language',
                'like_column': 'like_count'
            }
        }

    def detect_language(self, text):
        """检测文本语言"""
        try:
            if not isinstance(text, str) or len(text.strip()) < 10:
                return 'unknown'
            return langdetect.detect(text)
        except:
            return 'unknown'

    def tokenize_by_language(self, text, language):
        """根据语言进行分词"""
        if not isinstance(text, str):
            return []

        text = text.lower().strip()

        if language == 'zh':
            words = jieba.lcut(text)
        elif language == 'en':
            words = text.split()
        elif language == 'de':
            words = text.split()
        else:
            words = text.split()

        # 过滤停用词和短词
        stopwords = self.stopwords.get(language, self.stopwords['default'])
        words = [word for word in words if word not in stopwords and len(word) > 2]

        return words

    def load_and_preprocess(self, file_path, platform_type, sentiment_type='all'):
        """加载和预处理多语言数据"""
        df = pd.read_excel(file_path)
        config = self.platform_configs[platform_type]

        print(f"原始数据量: {len(df)}")

        # 情感筛选
        sentiment_col = config['sentiment_column']
        if sentiment_col in df.columns and sentiment_type != 'all':
            df = df[df[sentiment_col] == sentiment_type].copy()
            print(f"筛选后{sentiment_type}评论数量: {len(df)}")

        # 检查点赞数据列
        like_col = config.get('like_column')
        if like_col and like_col in df.columns:
            print(f"找到点赞数据列: {like_col}")
            df[like_col] = df[like_col].fillna(0).astype(int)
        else:
            print("警告: 未找到点赞数据列")
            like_col = None

        # 语言检测
        language_col = config['language_column']
        if language_col not in df.columns:
            print("进行语言检测...")
            df['detected_language'] = df[config['text_column']].apply(self.detect_language)
            language_col = 'detected_language'
        else:
            df['detected_language'] = df[language_col]

        # 语言分布统计
        lang_dist = df['detected_language'].value_counts()
        print("语言分布:")
        for lang, count in lang_dist.head(10).items():
            print(f"  {lang}: {count}条")

        # 分词处理
        print("进行多语言分词...")
        df['tokens'] = df.apply(
            lambda row: self.tokenize_by_language(
                row[config['text_column']],
                row['detected_language']
            ), axis=1
        )

        # 过滤空分词结果
        df = df[df['tokens'].apply(len) > 0].copy()
        print(f"有效分词数据量: {len(df)}")

        return df, config

    def train_multilingual_lda(self, df, num_topics=10, language_weighting=True):
        """训练多语言LDA模型"""
        all_tokens = df['tokens'].tolist()

        # 创建词典
        dictionary = corpora.Dictionary(all_tokens)
        dictionary.filter_extremes(no_below=5, no_above=0.5)
        print(f"词典大小: {len(dictionary)}")

        # 创建语料
        corpus = [dictionary.doc2bow(tokens) for tokens in all_tokens]

        # 语言加权（可选）
        if language_weighting:
            lang_counts = df['detected_language'].value_counts()
            total_docs = len(df)
            language_weights = {}
            for lang, count in lang_counts.items():
                language_weights[lang] = total_docs / count

            weighted_corpus = []
            for i, doc in enumerate(corpus):
                lang = df.iloc[i]['detected_language']
                weight = language_weights.get(lang, 1.0)
                weighted_doc = [(word_id, freq * weight) for word_id, freq in doc]
                weighted_corpus.append(weighted_doc)
            corpus = weighted_corpus

        # 训练LDA模型
        lda_model = models.LdaModel(
            corpus=corpus,
            id2word=dictionary,
            num_topics=num_topics,
            passes=20,
            alpha='auto',
            eta='auto',
            random_state=42
        )

        return lda_model, corpus, dictionary, df

    def find_optimal_topics_multilingual(self, df, max_topics=15):
        """多语言环境下的主题数优化"""
        all_tokens = df['tokens'].tolist()

        dictionary = corpora.Dictionary(all_tokens)
        dictionary.filter_extremes(no_below=5, no_above=0.5)
        corpus = [dictionary.doc2bow(tokens) for tokens in all_tokens]

        coherence_scores = []
        for num_topics in range(2, max_topics + 1):
            lda = models.LdaModel(
                corpus=corpus,
                id2word=dictionary,
                num_topics=num_topics,
                passes=15,
                random_state=42
            )

            coherence_model = CoherenceModel(
                model=lda,
                texts=all_tokens,
                dictionary=dictionary,
                coherence='c_v'
            )
            score = coherence_model.get_coherence()
            coherence_scores.append(score)
            print(f"主题数: {num_topics:2d}, 一致性: {score:.4f}")

        optimal_topics = np.argmax(coherence_scores) + 2
        print(f"最佳主题数: {optimal_topics}")

        return optimal_topics

    def display_multilingual_topics(self, lda_model, dictionary, num_words=10):
        """显示多语言主题结果"""
        topics = lda_model.print_topics(num_words=num_words)

        print("\n=== 多语言主题分析结果 ===")
        for topic_id, topic_words in topics:
            print(f"\n主题 {topic_id}:")
            words = topic_words.split('+')
            for word in words:
                word_data = word.strip().split('*')
                if len(word_data) == 2:
                    weight, word_text = word_data
                    word_text = word_text.replace('"', '')
                    print(f"  {weight} {word_text}")

    def visualize_multilingual_topics(self, lda_model, corpus, df, platform_name, sentiment_type='all'):
        """多语言主题可视化 - 增强版"""
        # 计算每个文档的主要主题
        topic_distribution = []
        for i, doc in enumerate(corpus):
            topic_probs = lda_model.get_document_topics(doc)
            if topic_probs:
                main_topic = max(topic_probs, key=lambda x: x[1])[0]
                topic_distribution.append((main_topic, i))

        # 统计主题频率
        topic_counts = Counter([t for t, idx in topic_distribution])
        labels = [f'Topic {i}' for i in range(lda_model.num_topics)]
        sizes = [topic_counts.get(i, 0) for i in range(lda_model.num_topics)]

        # 创建图形
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))

        # 左图：基于评论数量的分布
        axes[0].pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        axes[0].set_title(f'{platform_name} - Topic Distribution\n(Based on Comment Count)')
        axes[0].axis('equal')

        # 右图：基于点赞数加权的分布
        like_col = self.platform_configs[platform_name].get('like_column')
        if like_col and like_col in df.columns:
            topic_likes = {i: 0 for i in range(lda_model.num_topics)}
            for topic, doc_idx in topic_distribution:
                like_count = df.iloc[doc_idx][like_col]
                topic_likes[topic] += (1 + like_count)

            like_sizes = [topic_likes.get(i, 0) for i in range(lda_model.num_topics)]
            total_likes = sum(like_sizes)

            if total_likes > 0:
                like_percentages = [size / total_likes * 100 for size in like_sizes]
                wedges, texts, autotexts = axes[1].pie(
                    like_sizes, labels=labels, autopct='%1.1f%%', startangle=90
                )
                axes[1].set_title(f'{platform_name} - Topic Distribution\n(Based on Like Count Weighted)')
                axes[1].axis('equal')
                fig.text(0.5, 0.02, f'Total Likes: {total_likes:,}', ha='center', fontsize=12)
            else:
                axes[1].text(0.5, 0.5, 'No Like Data', ha='center', va='center', fontsize=14)
                axes[1].set_title('Like Data Not Available')
        else:
            axes[1].text(0.5, 0.5, 'No Like Data', ha='center', va='center', fontsize=14)
            axes[1].set_title('Like Data Not Available')

        plt.tight_layout()
        plt.show()

    def analyze_by_language(self, lda_model, corpus, df):
        """按语言分析主题分布"""
        doc_topics = []
        for doc in corpus:
            topic_probs = lda_model.get_document_topics(doc)
            if topic_probs:
                main_topic = max(topic_probs, key=lambda x: x[1])[0]
                doc_topics.append(main_topic)

        df['main_topic'] = doc_topics

        print("\n=== 各语言的主题偏好 ===")
        languages = df['detected_language'].unique()

        for lang in languages:
            lang_df = df[df['detected_language'] == lang]
            if len(lang_df) > 10:
                topic_dist = lang_df['main_topic'].value_counts().head(3)
                print(f"\n{lang} 语言最关注的主题:")
                for topic, count in topic_dist.items():
                    proportion = count / len(lang_df) * 100
                    print(f"  主题 {topic}: {proportion:.1f}%")

        return df

    def run_analysis(self, file_path, platform_type, sentiment_type='all', num_topics=None):
        """完整的多语言分析流程"""
        print(f"开始分析 {platform_type} 的 {sentiment_type} 评论")
        print("=" * 60)

        # 1. 加载和预处理
        df, config = self.load_and_preprocess(file_path, platform_type, sentiment_type)

        if len(df) == 0:
            print("没有有效数据，分析终止")
            return None

        # 2. 寻找最佳主题数
        if num_topics is None:
            num_topics = self.find_optimal_topics_multilingual(df)

        # 3. 训练模型
        lda_model, corpus, dictionary, processed_df = self.train_multilingual_lda(df, num_topics)

        # 4. 显示结果
        self.display_multilingual_topics(lda_model, dictionary)

        # 5. 按语言分析
        analyzed_df = self.analyze_by_language(lda_model, corpus, processed_df)

        # 6. 可视化
        self.visualize_multilingual_topics(lda_model, corpus, analyzed_df, platform_type, sentiment_type)

        return lda_model, corpus, dictionary, analyzed_df


# 使用示例
if __name__ == "__main__":
    # 初始化分析器
    analyzer = MultilingualLDAAnalyzer()

    try:
        # 正确的调用方法
        twitter_results = analyzer.run_analysis(
            file_path='twitter_comments.xlsx',
            platform_type='twitter',
            sentiment_type='positive',
            num_topics=5

        )

        if twitter_results is not None:
            print("分析成功完成!")
        else:
            print("分析过程中出现问题，请检查数据文件")

    except FileNotFoundError:
        print("错误：找不到数据文件，请检查文件路径")
    except Exception as e:
        print(f"分析过程中出现错误: {e}")