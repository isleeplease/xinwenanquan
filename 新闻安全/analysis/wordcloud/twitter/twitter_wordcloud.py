# -*- coding: utf-8 -*-
"""
简化版推特评论词云生成器
直接处理推特评论数据
"""

import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import re
from collections import Counter, defaultdict
import jieba

# ===== 1. 文本清理函数 =====
def clean_text(text, lang='en'):
    """清理文本"""
    if not isinstance(text, str):
        return ""

    # 转换为小写（仅对英语）
    if lang == 'en':
        text = text.lower()

    # 移除URL
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

    # 移除@用户名和#话题标签（但保留内容）
    text = re.sub(r'@[\w_]+', '', text)
    text = re.sub(r'#([\w_]+)', r'\1', text)

    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text).strip()

    return text

# ===== 2. 分词函数 =====
def tokenize_text(text, lang='en'):
    """根据语言对文本进行分词"""
    if not text:
        return []

    tokens = []

    # 中文分词
    if lang.startswith('zh'):
        tokens = list(jieba.cut(text))
    else:
        # 其他语言按空格分割
        tokens = text.split()

    # 停用词列表
    stopwords = {
        # 英语停用词
        'en': {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
               'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
               'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
               'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
               'rt', 'http', 'https', 'www', 'com', 'co', 'amp'},

        # 中文停用词
        'zh': {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
               '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
               '自己', '这', '那', '里', '就是', '还是', '为了', '但是', '或者', '而且', '所以'},

        # 通用停用词
        'universal': {'', ' ', '\n', '\t'}
    }

    # 获取对应语言的停用词
    lang_prefix = lang.split('-')[0]  # 获取语言前缀
    lang_stopwords = stopwords.get(lang_prefix, set())
    universal_stopwords = stopwords.get('universal', set())

    # 过滤token
    filtered_tokens = []
    for token in tokens:
        # 过滤条件
        if (len(token) > 1 and  # 长度大于1
            not token.isdigit() and  # 不是纯数字
            token not in lang_stopwords and  # 不在停用词中
            token not in universal_stopwords and  # 不在通用停用词中
            not re.match(r'^[@#\W]+$', token)):  # 不是纯符号
            filtered_tokens.append(token)

    return filtered_tokens

# ===== 3. 词云生成函数 =====
def generate_wordcloud(word_weights):
    """生成词云"""
    # 生成词云
    wc = WordCloud(
        width=1200,
        height=600,
        background_color='white',
        colormap='viridis',
        prefer_horizontal=0.8,
        relative_scaling=0.8,
        min_font_size=10,
        max_words=200
    )
    return wc.generate_from_frequencies(word_weights)

# ===== 4. 主函数 =====
def main():
    # 读取数据
    try:
        df = pd.read_excel('推特评论.xlsx', sheet_name='Sheet1')
        print(f"成功读取文件: {len(df)}条记录")
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        return

    # 检查必要列
    if 'cleaned_text' not in df.columns:
        print("错误：缺少'cleaned_text'列")
        return

    if 'language' not in df.columns:
        print("警告：缺少'language'列，将默认使用'en'")
        df['language'] = 'en'

    if '点赞数' not in df.columns:
        print("警告：缺少'点赞数'列，将默认使用1")
        df['点赞数'] = 1

    # 计算词权重
    print("正在计算词权重...")
    word_weights = defaultdict(float)

    # 遍历每条评论
    for index, row in df.iterrows():
        text = str(row['cleaned_text']) if pd.notna(row['cleaned_text']) else ""
        like_count = int(row['点赞数']) if pd.notna(row['点赞数']) else 1
        lang = str(row['language']) if pd.notna(row['language']) else 'en'

        # 清理和分词
        cleaned_text = clean_text(text, lang)
        tokens = tokenize_text(cleaned_text, lang)

        # 计算词权重（词频 * (点赞数 + 1)）
        for token in tokens:
            weight = 1.0 * (like_count + 1)
            word_weights[token] += weight

    # 生成总体词云
    if word_weights:
        print(f"共识别到 {len(word_weights)} 个词汇")
        wordcloud = generate_wordcloud(word_weights)

        # 保存词云图片
        plt.figure(figsize=(14, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('推特评论词云图')

        output_filename = '推特评论词云.png'
        plt.savefig(output_filename, bbox_inches='tight', dpi=300)
        print(f"词云已保存为 '{output_filename}'")

        # 输出高频词
        top_words = Counter(word_weights).most_common(20)
        print("\n前20个高频词:")
        for word, weight in top_words:
            print(f"{word}: {weight:.2f}")

        # 按语言生成词云
        print("\n按语言生成词云...")
        languages = df['language'].value_counts().head(5)  # 取前5种主要语言

        for lang, count in languages.items():
            print(f"处理 {lang} 语言 ({count} 条评论)...")
            lang_df = df[df['language'] == lang]
            if len(lang_df) > 0:
                lang_word_weights = defaultdict(float)
                for index, row in lang_df.iterrows():
                    text = str(row['cleaned_text']) if pd.notna(row['cleaned_text']) else ""
                    like_count = int(row['点赞数']) if pd.notna(row['点赞数']) else 1

                    # 清理和分词
                    cleaned_text = clean_text(text, lang)
                    tokens = tokenize_text(cleaned_text, lang)

                    # 计算词权重
                    for token in tokens:
                        weight = 1.0 * (like_count + 1)
                        lang_word_weights[token] += weight

                if lang_word_weights:
                    lang_wordcloud = generate_wordcloud(lang_word_weights)

                    plt.figure(figsize=(14, 8))
                    plt.imshow(lang_wordcloud, interpolation='bilinear')
                    plt.axis('off')
                    plt.title(f'{lang.upper()}语言推特评论词云图')

                    lang_output_filename = f'推特评论词云_{lang}.png'
                    plt.savefig(lang_output_filename, bbox_inches='tight', dpi=300)
                    print(f"{lang}语言词云已保存为 '{lang_output_filename}'")
    else:
        print("警告: 未能识别到有效词汇，无法生成词云")

if __name__ == "__main__":
    main()
