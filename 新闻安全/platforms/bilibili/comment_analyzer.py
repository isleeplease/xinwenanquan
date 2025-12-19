#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站电竞赛事评论数据分析脚本
用于提取高频敏感话题讨论点并判断真实性
"""

import pandas as pd
import os
import jieba
import jieba.analyse
import jieba.posseg as pseg
from collections import Counter
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import warnings
warnings.filterwarnings('ignore')

# 导入模糊匹配库
from fuzzywuzzy import fuzz, process

# 导入自定义情感分析器
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))
from sentiment_analyzer import CommentSentimentAnalyzer

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class BilibiliCommentAnalyzer:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.all_comments = pd.DataFrame()
        self.processed_comments = pd.DataFrame()
        # 初始化情感分析器
        self.sentiment_analyzer = CommentSentimentAnalyzer()
        
    def load_all_comments(self):
        """加载所有评论数据"""
        print("正在加载所有评论数据...")
        all_data = []
        
        # 检查主目录和B站评论数据子目录
        search_dirs = [self.data_dir, os.path.join(self.data_dir, "B站评论数据")]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for file in os.listdir(search_dir):
                    if file.endswith('.xlsx') and '完整评论' in file:
                        file_path = os.path.join(search_dir, file)
                        try:
                            df = pd.read_excel(file_path)
                            # 添加视频标识
                            bv_number = file.split('【')[1].split('】')[0]
                            df['视频BV号'] = bv_number
                            df['视频标题'] = file.split('】')[1].split('_完整评论')[0]
                            all_data.append(df)
                            print(f"已加载: {file}")
                        except Exception as e:
                            print(f"加载文件 {file} 时出错: {e}")
        
        if all_data:
            self.all_comments = pd.concat(all_data, ignore_index=True)
            print(f"成功加载 {len(self.all_comments)} 条评论数据")
            return True
        else:
            print("未找到任何评论数据文件")
            return False
    
    def preprocess_comments(self):
        """预处理评论数据"""
        print("正在预处理评论数据...")
        if self.all_comments.empty:
            print("没有评论数据可处理")
            return False
            
        # 选择需要的列
        cols_to_keep = ['评论内容', '点赞数', '评论时间', '用户名', '评论类型', '视频BV号', '视频标题']
        available_cols = [col for col in cols_to_keep if col in self.all_comments.columns]
        self.processed_comments = self.all_comments[available_cols].copy()
        
        # 清理评论内容
        self.processed_comments['评论内容'] = self.processed_comments['评论内容'].astype(str)
        self.processed_comments['评论内容_clean'] = self.processed_comments['评论内容'].apply(
            lambda x: re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', x)
        )
        
        # 移除空评论
        self.processed_comments = self.processed_comments[
            self.processed_comments['评论内容_clean'].str.len() > 0
        ]
        
        print(f"预处理完成，剩余 {len(self.processed_comments)} 条有效评论")
        return True
    
    def extract_high_freq_topics(self, top_k=50):
        """提取高频话题词"""
        print("正在提取高频话题词...")
        if self.processed_comments.empty:
            print("没有评论数据可分析")
            return []
            
        # 合并所有评论内容
        all_text = ' '.join(self.processed_comments['评论内容_clean'].tolist())
        
        # 使用jieba进行分词和关键词提取（基于词性标注改进）
        # TF-IDF关键词提取（增加词性过滤）
        tfidf_words = jieba.analyse.extract_tags(all_text, topK=top_k*2, withWeight=True)
        # 过滤掉无意义的词性
        tfidf_keywords = []
        for word, weight in tfidf_words:
            # 使用词性标注检查词性
            pos_tags = [tag for _, tag in pseg.cut(word)]
            # 只保留名词、动词、形容词
            if any(tag.startswith(('n', 'v', 'a')) for tag in pos_tags) and len(word) > 1:
                tfidf_keywords.append((word, weight))
        tfidf_keywords = tfidf_keywords[:top_k]
        
        # TextRank关键词提取（同样增加词性过滤）
        textrank_words = jieba.analyse.textrank(all_text, topK=top_k*2, withWeight=True)
        textrank_keywords = []
        for word, weight in textrank_words:
            # 使用词性标注检查词性
            pos_tags = [tag for _, tag in pseg.cut(word)]
            # 只保留名词、动词、形容词
            if any(tag.startswith(('n', 'v', 'a')) for tag in pos_tags) and len(word) > 1:
                textrank_keywords.append((word, weight))
        textrank_keywords = textrank_keywords[:top_k]
        
        # 词频统计（增强版，使用词性标注）
        words_with_pos = [(word, flag) for word, flag in pseg.cut(all_text)]
        # 过滤掉停用词和不需要的词性
        stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        filtered_words = [word for word, flag in words_with_pos 
                         if len(word) > 1 and word not in stopwords 
                         and flag.startswith(('n', 'v', 'a', 'l'))]  # 名词、动词、形容词、习语
        word_freq = Counter(filtered_words)
        freq_keywords = [(word, count) for word, count in word_freq.most_common(top_k)]
        
        # 提取长意见性短语（增强版）
        opinion_phrases = []
        sample_texts = self.processed_comments['评论内容_clean'].sample(min(200, len(self.processed_comments))).tolist()
        for text in sample_texts:
            phrases = self.sentiment_analyzer.extract_opinion_phrases(text)
            opinion_phrases.extend(phrases)
        
        # 统计意见性短语频率
        phrase_freq = Counter(opinion_phrases)
        opinion_keywords = [(phrase, count) for phrase, count in phrase_freq.most_common(top_k)]
        
        # 使用模糊匹配合并相似的话题词
        merged_topics = {}
        all_candidate_words = [word for word, _ in tfidf_keywords] + \
                             [word for word, _ in textrank_keywords] + \
                             [word for word, _ in freq_keywords] + \
                             [phrase for phrase, _ in opinion_keywords]
        
        # 去重但保持顺序
        unique_candidates = []
        seen = set()
        for word in all_candidate_words:
            if word not in seen:
                unique_candidates.append(word)
                seen.add(word)
        
        # 使用模糊匹配合并相似词
        processed_groups = set()
        for word in unique_candidates:
            if word in processed_groups:
                continue
                
            # 查找相似的词（相似度大于80%）
            similar_words = process.extract(word, unique_candidates, limit=10)
            group = [w for w, score in similar_words if score >= 80]
            
            # 将组中的词标记为已处理
            for w in group:
                processed_groups.add(w)
            
            # 选择组中最长的词作为代表
            representative = max(group, key=len) if group else word
            
            # 合并统计数据
            merged_topics[representative] = {
                'similar_words': group,
                'tfidf': sum([weight for w, weight in tfidf_keywords if w in group]),
                'textrank': sum([weight for w, weight in textrank_keywords if w in group]),
                'freq': sum([count for w, count in freq_keywords if w in group]),
                'opinion': sum([count for w, count in opinion_keywords if w in group])
            }
        
        # 如果模糊匹配效果不好，直接使用原始词
        if not merged_topics:
            topic_dict = {}
            # 添加TF-IDF关键词
            for word, weight in tfidf_keywords:
                if word in topic_dict:
                    topic_dict[word]['tfidf'] = weight
                else:
                    topic_dict[word] = {'tfidf': weight, 'textrank': 0, 'freq': 0, 'opinion': 0}
            
            # 添加TextRank关键词
            for word, weight in textrank_keywords:
                if word in topic_dict:
                    topic_dict[word]['textrank'] = weight
                else:
                    topic_dict[word] = {'tfidf': 0, 'textrank': weight, 'freq': 0, 'opinion': 0}
            
            # 添加词频
            for word, freq in freq_keywords:
                if word in topic_dict:
                    topic_dict[word]['freq'] = freq
                else:
                    topic_dict[word] = {'tfidf': 0, 'textrank': 0, 'freq': freq, 'opinion': 0}
            
            # 添加意见性短语
            for phrase, freq in opinion_keywords:
                if phrase in topic_dict:
                    topic_dict[phrase]['opinion'] = freq
                else:
                    # 为意见性短语设置较高的初始权重
                    topic_dict[phrase] = {'tfidf': 0, 'textrank': 0, 'freq': 0, 'opinion': freq}
            merged_topics = topic_dict
        
        # 计算综合得分
        topics = []
        for word, scores in merged_topics.items():
            # 综合得分 = 0.3*TF-IDF + 0.2*TextRank + 0.2*(词频/最大词频) + 0.3*(意见性得分/最大意见性得分)
            max_freq = max([item['freq'] for item in merged_topics.values()]) if merged_topics else 1
            max_opinion = max([item['opinion'] for item in merged_topics.values()]) if merged_topics else 1
            composite_score = (0.3 * scores['tfidf'] + 
                             0.2 * scores['textrank'] + 
                             0.2 * (scores['freq'] / max_freq if max_freq > 0 else 0) +
                             0.3 * (scores['opinion'] / max_opinion if max_opinion > 0 else 0))
            topics.append((word, composite_score, scores))
        
        # 按综合得分排序
        topics.sort(key=lambda x: x[1], reverse=True)
        
        print(f"提取到 {len(topics)} 个高频话题词")
        return topics[:top_k]
    
    def analyze_sentiment_by_topic(self, topics):
        """根据话题分析情感倾向"""
        print("正在分析话题情感倾向...")
        topic_sentiments = []
        
        for word, score, details in topics[:30]:  # 分析前30个话题
            # 筛选包含该话题词的评论（使用模糊匹配）
            related_comments = []
            
            # 如果有相似词组，则使用模糊匹配查找相关评论
            similar_words = details.get('similar_words', [word]) if isinstance(details, dict) else [word]
            
            for _, comment_row in self.processed_comments.iterrows():
                comment_text = comment_row['评论内容_clean']
                # 检查是否包含话题词或相似词
                contains_topic = any(word in comment_text for word in similar_words)
                
                # 如果直接匹配失败，尝试模糊匹配
                if not contains_topic and len(similar_words) > 0:
                    # 使用模糊匹配检查相似度
                    best_match = process.extractOne(word, [comment_text])
                    if best_match and best_match[1] >= 70:  # 相似度阈值70%
                        contains_topic = True
                
                if contains_topic:
                    related_comments.append(comment_row)
            
            # 转换为DataFrame
            if related_comments:
                related_comments = pd.DataFrame(related_comments)
            else:
                # 回退到精确匹配
                related_comments = self.processed_comments[
                    self.processed_comments['评论内容_clean'].str.contains(word, na=False)
                ]
            
            if len(related_comments) > 0:
                # 计算平均点赞数作为情感指标（简化处理）
                avg_likes = related_comments['点赞数'].mean() if '点赞数' in related_comments.columns else 0
                
                # 根据反对声音越小，真实性越高处理
                # 这里假设点赞数高的评论真实性更高
                authenticity_score = avg_likes  # 简化处理，实际应该有反对数
                
                # 对相关评论进行情感分析
                sentiment_scores = []
                for _, comment_row in related_comments.head(100).iterrows():  # 增加分析评论数量到100条
                    comment_text = comment_row['评论内容_clean']
                    sentiment, pos_score, neg_score = self.sentiment_analyzer.analyze_sentiment(comment_text)
                    sentiment_scores.append((sentiment, pos_score, neg_score))
                
                # 统计情感分布
                sentiment_counts = {'正面': 0, '负面': 0, '中性': 0}
                total_pos_score = 0
                total_neg_score = 0
                
                for sentiment, pos_score, neg_score in sentiment_scores:
                    sentiment_counts[sentiment] += 1
                    total_pos_score += pos_score
                    total_neg_score += neg_score
                
                # 确定主导情感
                dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get)
                
                # 计算情感强度
                total_sentiments = sum(sentiment_counts.values())
                sentiment_strength = (sentiment_counts['正面'] - sentiment_counts['负面']) / total_sentiments if total_sentiments > 0 else 0
                
                topic_sentiments.append({
                    '话题': word,
                    '综合得分': score,
                    '相关评论数': len(related_comments),
                    '平均点赞数': avg_likes,
                    '真实性得分': authenticity_score,
                    '主导情感': dominant_sentiment,
                    '情感强度': sentiment_strength,  # 新增：情感强度指标
                    '正面评论数': sentiment_counts['正面'],
                    '负面评论数': sentiment_counts['负面'],
                    '中性评论数': sentiment_counts['中性'],
                    '总正面得分': total_pos_score,
                    '总负面得分': total_neg_score,
                    'TF-IDF': details['tfidf'],
                    'TextRank': details['textrank'],
                    '词频': details['freq'],
                    '意见性得分': details.get('opinion', 0),
                    '相似词': ', '.join(similar_words[:5]) if isinstance(details, dict) and 'similar_words' in details else ''  # 新增：显示相似词
                })
        
        return pd.DataFrame(topic_sentiments)
    
    def cluster_comments(self, n_clusters=5):
        """对评论进行聚类分析"""
        print("正在进行评论聚类分析...")
        if self.processed_comments.empty:
            print("没有评论数据可聚类")
            return None
            
        # 准备文本数据
        texts = self.processed_comments['评论内容_clean'].tolist()
        
        # TF-IDF向量化
        vectorizer = TfidfVectorizer(max_features=1000, stop_words=None)
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        # K-means聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(tfidf_matrix)
        
        # 添加聚类标签到数据
        self.processed_comments['聚类标签'] = cluster_labels
        
        # 分析每个聚类的特征
        cluster_analysis = []
        for i in range(n_clusters):
            cluster_comments = self.processed_comments[self.processed_comments['聚类标签'] == i]
            if len(cluster_comments) > 0:
                # 提取该聚类的关键词
                cluster_text = ' '.join(cluster_comments['评论内容_clean'].tolist())
                keywords = jieba.analyse.extract_tags(cluster_text, topK=10)
                
                cluster_analysis.append({
                    '聚类ID': i,
                    '评论数量': len(cluster_comments),
                    '平均点赞数': cluster_comments['点赞数'].mean() if '点赞数' in cluster_comments.columns else 0,
                    '关键词': ', '.join(keywords),
                    '代表性评论': cluster_comments.iloc[0]['评论内容'] if len(cluster_comments) > 0 else ""
                })
        
        return pd.DataFrame(cluster_analysis)
    
    def generate_wordcloud(self, topics, output_path="topic_wordcloud.png"):
        """生成话题词云"""
        print("正在生成话题词云...")
        if not topics:
            print("没有话题数据可生成词云")
            return
            
        # 准备词云数据
        word_freq = {word: score for word, score, _ in topics[:30]}
        
        # 创建词云
        wordcloud = WordCloud(
            font_path="simhei.ttf",  # Windows下的黑体字体
            width=800, 
            height=600, 
            background_color='white',
            max_words=100
        ).generate_from_frequencies(word_freq)
        
        # 显示和保存
        plt.figure(figsize=(10, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('B站电竞赛事评论高频话题词云', fontsize=16)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"词云已保存至: {output_path}")
    
    def save_analysis_results(self, topics, sentiment_df, cluster_df, output_filename="bilibili_comment_analysis_results_fuzzy.xlsx"):
        """保存分析结果到Excel文件"""
        print("正在保存分析结果...")
        
        # 准备话题数据
        topic_data = []
        for word, score, details in topics[:50]:
            topic_data.append({
                '话题': word,
                '综合得分': score,
                'TF-IDF': details['tfidf'],
                'TextRank': details['textrank'],
                '词频': details['freq'],
                '意见性得分': details.get('opinion', 0)
            })
        topic_df = pd.DataFrame(topic_data)
        
        # 如果文件已存在且被锁定，尝试使用不同的文件名
        final_filename = output_filename
        counter = 1
        while os.path.exists(final_filename):
            try:
                with pd.ExcelWriter(final_filename) as writer:
                    topic_df.to_excel(writer, sheet_name='高频话题', index=False)
                    if not sentiment_df.empty:
                        sentiment_df.to_excel(writer, sheet_name='情感分析', index=False)
                    if cluster_df is not None and not cluster_df.empty:
                        cluster_df.to_excel(writer, sheet_name='聚类分析', index=False)
                break  # 成功写入则退出循环
            except PermissionError:
                # 文件被锁定，尝试使用不同的文件名
                name, ext = os.path.splitext(output_filename)
                final_filename = f"{name}_{counter}{ext}"
                counter += 1
                if counter > 10:  # 避免无限循环
                    raise
        else:
            # 文件不存在，正常写入
            with pd.ExcelWriter(final_filename) as writer:
                topic_df.to_excel(writer, sheet_name='高频话题', index=False)
                if not sentiment_df.empty:
                    sentiment_df.to_excel(writer, sheet_name='情感分析', index=False)
                if cluster_df is not None and not cluster_df.empty:
                    cluster_df.to_excel(writer, sheet_name='聚类分析', index=False)
        
        print(f"分析结果已保存至: {final_filename}")
        
        # 保存词云
        if topics:
            self.generate_wordcloud(topics, "topic_wordcloud_fuzzy.png")
    
    def run_complete_analysis(self):
        """运行完整分析流程"""
        print("=" * 60)
        print("B站电竞赛事评论数据分析")
        print("=" * 60)
        
        # 1. 加载数据
        if not self.load_all_comments():
            return False
            
        # 2. 预处理数据
        if not self.preprocess_comments():
            return False
            
        # 3. 提取高频话题
        topics = self.extract_high_freq_topics(top_k=50)
        
        # 4. 分析话题情感倾向
        sentiment_df = self.analyze_sentiment_by_topic(topics)
        
        # 5. 评论聚类分析
        cluster_df = self.cluster_comments(n_clusters=5)
        
        # 6. 生成词云
        self.generate_wordcloud(topics)
        
        # 7. 保存结果
        self.save_analysis_results(topics, sentiment_df, cluster_df)
        
        # 8. 输出关键发现
        print("\n" + "=" * 60)
        print("分析完成，关键发现:")
        print("=" * 60)
        
        print(f"1. 总共分析了 {len(self.processed_comments)} 条评论")
        print(f"2. 提取出 {len(topics)} 个高频话题词")
        
        if not sentiment_df.empty:
            print("\n3. 真实性较高的话题 (基于点赞数):")
            top_authentic = sentiment_df.nlargest(5, '真实性得分')
            for _, row in top_authentic.iterrows():
                print(f"   - {row['话题']}: 真实性得分 {row['真实性得分']:.2f}, 主导情感: {row['主导情感']}")
            
            print("\n4. 不同情感倾向的话题分布:")
            sentiment_distribution = sentiment_df['主导情感'].value_counts()
            for sentiment, count in sentiment_distribution.items():
                print(f"   - {sentiment}: {count} 个话题")
            
            print("\n5. 包含意见性表达的高频话题:")
            opinion_topics = sentiment_df[sentiment_df['意见性得分'] > 0].nlargest(5, '意见性得分')
            for _, row in opinion_topics.iterrows():
                print(f"   - {row['话题']}: 意见性得分 {row['意见性得分']}, 主导情感: {row['主导情感']}")
        
        if cluster_df is not None and not cluster_df.empty:
            print("\n6. 评论主要分为以下几类:")
            for _, row in cluster_df.iterrows():
                print(f"   - 类别 {row['聚类ID']}: {row['关键词']}")
        
        return True

def main():
    """主函数"""
    # 设置数据目录
    data_dir = "e:\\cross-sentiment-main\\platforms\\bilibili\\B站评论数据"
    
    # 检查目录是否存在
    if not os.path.exists(data_dir):
        print(f"错误: 数据目录不存在 {data_dir}")
        return
    
    # 创建分析器实例
    analyzer = BilibiliCommentAnalyzer(data_dir)
    
    # 运行完整分析
    if analyzer.run_complete_analysis():
        print("\n数据分析完成！")
        print("详细结果请查看生成的Excel文件和词云图片。")
    else:
        print("\n数据分析过程中出现错误。")

if __name__ == "__main__":
    main()