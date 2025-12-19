# -*- coding: utf-8 -*-
"""
B站评论情感分析工具
用于为话题分配情感倾向
"""

import os
import jieba
import jieba.posseg as pseg
import codecs

class CommentSentimentAnalyzer:
    def __init__(self):
        # 初始化jieba
        jieba.initialize()
        
        # 加载情感词典
        self.positive_words, self.negative_words = self._load_sentiment_dicts()
        
    def _load_sentiment_dicts(self):
        """加载情感词典"""
        positive_words = set()
        negative_words = set()
        
        # 获取情感词典文件路径
        sentiment_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'analysis', 'sentiment', 'bilibili_sentiment')
        
        # 加载正面词典
        pos_files = [
            os.path.join(sentiment_dir, 'tsinghua_positive_gb.txt'),
            os.path.join(sentiment_dir, 'tsinghua_positive_gb_1.txt')
        ]
        
        for file_path in pos_files:
            if os.path.exists(file_path):
                try:
                    # 使用codecs以正确编码读取
                    with codecs.open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                        for line in f:
                            word = line.strip()
                            if word:
                                positive_words.add(word)
                except Exception as e:
                    print(f"加载正面词典 {file_path} 失败: {e}")
        
        # 加载负面词典
        neg_files = [os.path.join(sentiment_dir, 'tsinghua.negative.gb.txt')]
        
        for file_path in neg_files:
            if os.path.exists(file_path):
                try:
                    # 使用codecs以正确编码读取
                    with codecs.open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                        for line in f:
                            word = line.strip()
                            if word:
                                negative_words.add(word)
                except Exception as e:
                    print(f"加载负面词典 {file_path} 失败: {e}")
        
        print(f"加载情感词典完成 - 正面词: {len(positive_words)}, 负面词: {len(negative_words)}")
        return positive_words, negative_words
    
    def analyze_sentiment(self, text):
        """
        分析文本情感倾向
        返回: (情感标签, 正面得分, 负面得分)
        """
        if not text or not isinstance(text, str):
            return ("中性", 0, 0)
        
        # 分词
        words = jieba.lcut(text)
        
        # 计算情感得分
        positive_score = sum(1 for word in words if word in self.positive_words)
        negative_score = sum(1 for word in words if word in self.negative_words)
        
        # 判断情感倾向
        if positive_score > negative_score:
            sentiment = "正面"
        elif negative_score > positive_score:
            sentiment = "负面"
        else:
            sentiment = "中性"
        
        return (sentiment, positive_score, negative_score)
    
    def extract_opinion_phrases(self, text, min_length=8, max_length=20):
        """
        提取意见性短语（较长的表达观点的短语）
        参数:
        - text: 输入文本
        - min_length: 最小长度（字符数）
        - max_length: 最大长度（字符数）
        返回: 意见性短语列表
        """
        if not text or not isinstance(text, str):
            return []
        
        # 使用jieba进行分词（带词性标注）
        words_with_pos = [(word, flag) for word, flag in pseg.cut(text)]
        
        # 构建短语（基于词性规则）
        phrases = []
        
        # 滑动窗口提取短语
        for i in range(len(words_with_pos)):
            for j in range(i + 1, min(len(words_with_pos) + 1, i + 8)):  # 最多7个词组合
                phrase_words = words_with_pos[i:j]
                phrase = ''.join([word for word, _ in phrase_words])
                
                # 过滤条件：长度适中且包含一定信息量
                if min_length <= len(phrase) <= max_length:
                    # 过滤掉纯数字和特殊符号
                    if any(char.isalpha() or '\u4e00' <= char <= '\u9fff' for char in phrase):
                        # 基于词性规则筛选更有意义的短语
                        pos_tags = [flag for _, flag in phrase_words]
                        
                        # 规则1: 包含至少一个动词或形容词
                        has_meaningful_pos = any(tag.startswith(('v', 'a')) for tag in pos_tags)
                        
                        # 规则2: 不以介词、连词开头
                        starts_with_good_pos = not pos_tags[0].startswith(('p', 'c'))
                        
                        # 规则3: 不以助词、语气词结尾
                        ends_with_good_pos = not pos_tags[-1].startswith(('u', 'e'))
                        
                        if has_meaningful_pos and starts_with_good_pos and ends_with_good_pos:
                            phrases.append(phrase)
        
        # 去重并按长度排序
        phrases = list(set(phrases))
        phrases.sort(key=len, reverse=True)
        
        return phrases[:15]  # 返回前15个最长的短语