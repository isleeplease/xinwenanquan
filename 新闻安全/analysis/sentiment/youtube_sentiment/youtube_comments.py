import pandas as pd
import re
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from langdetect import detect, LangDetectException
import os


# 确保下载所需资源
def download_nltk_resources():
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError:
        print("下载 vader_lexicon...")
        nltk.download('vader_lexicon', quiet=True)

    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("下载 punkt...")
        nltk.download('punkt', quiet=True)

    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        print("下载 stopwords...")
        nltk.download('stopwords', quiet=True)


download_nltk_resources()


def detect_language(text):
    """检测文本语言，返回语言代码"""
    if pd.isna(text) or not isinstance(text, str) or not text.strip():
        return "unknown"

    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


# 修改清洗函数，保留单独的"W"字符
def clean_english_text(text):
    """专门清洗英文文本，保留单独的W字符"""
    if not isinstance(text, str):
        return ""

    # 基础清洗
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)  # 保留字母数字和空格

    # 特殊处理：保护单独的"W"不被移除
    text = re.sub(r'\bw\b', ' W ', text, flags=re.IGNORECASE)

    text = text.lower()

    # 移除英文停用词（但保留"w"）
    stop_words = set(nltk.corpus.stopwords.words('english'))
    words = text.split()

    # 保留单独的"w"和长度大于1的词
    filtered = [word for word in words if (word == "w" or (word not in stop_words and len(word) > 1))]

    return ' '.join(filtered).strip()


def clean_non_english_text(text):
    """基础清洗保留非英文内容"""
    if not isinstance(text, str):
        return ""

    # 仅移除URL和特殊符号
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'<.*?>', '', text)
    return text.strip()


# 增强W表达检测
def enhance_youtube_rules(text):
    """增强处理YouTube特有的表达方式"""
    # 检测单独的"W"或上下文中的积极表达
    if re.search(r'\bw\b', text, re.IGNORECASE):
        return True

    # 检测常见的YouTube积极短语
    youtube_positives = ["w stream", "w china", "w speed", "w man", "w end", "w con", "w gg"]
    for phrase in youtube_positives:
        if phrase in text.lower():
            return True

    return False


def analyze_sentiment(text):
    """英文情感分析，加入YouTube特定规则"""
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(text)

    # 应用YouTube特定规则
    if enhance_youtube_rules(text):
        # 如果检测到"W"表达，强制设为积极
        return scores, "positive"

    compound = scores['compound']
    if compound >= 0.05:
        sentiment = "positive"
    elif compound <= -0.05:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return scores, sentiment


def process_comments(file_path):
    # 读取Excel文件
    try:
        df = pd.read_excel(file_path)
        print(f"成功读取 {len(df)} 条评论")
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None, None

    # 步骤1: 检测语言
    print("正在检测评论语言...")
    df['language'] = df['text'].apply(detect_language)

    # 分离英文和非英文评论
    en_df = df[df['language'] == 'en'].copy()
    non_en_df = df[df['language'] != 'en'].copy()

    print(f"检测完成: {len(en_df)} 条英文评论, {len(non_en_df)} 条非英文评论")

    # 步骤2: 处理英文评论
    print("处理英文评论...")
    if not en_df.empty:
        en_df['cleaned_text'] = en_df['text'].apply(clean_english_text)

        # 确保清洗后的文本不为空
        en_df = en_df[en_df['cleaned_text'].str.strip().astype(bool)]

        # 检测YouTube特有的"W"表达
        en_df['has_w_expression'] = en_df['cleaned_text'].apply(enhance_youtube_rules)

        sentiment_results = en_df.apply(
            lambda row: analyze_sentiment(row['cleaned_text']),
            axis=1
        )
        en_df[['vader_scores', 'sentiment']] = sentiment_results.apply(
            lambda x: pd.Series([x[0], x[1]]))
    else:
        print("未找到英文评论")

    # 步骤3: 处理非英文评论
    print("处理非英文评论...")
    if not non_en_df.empty:
        non_en_df['cleaned_text'] = non_en_df['text'].apply(clean_non_english_text)
        non_en_df['vader_scores'] = None
        non_en_df['sentiment'] = "需要手动分析"
    else:
        print("未找到非英文评论")

    return en_df, non_en_df


if __name__ == "__main__":
    # 替换为您的文件路径
    input_file = "上海YouTube评论.xlsx"

    try:
        # 执行处理
        english_df, non_english_df = process_comments(input_file)

        # 保存结果
        if english_df is not None and not english_df.empty:
            output_en = "英文评论分析结果.xlsx"
            english_df.to_excel(output_en, index=False)
            print(f"英文评论结果已保存至: {output_en}")

            # 统计"W"表达的使用情况
            w_count = english_df['has_w_expression'].sum()
            w_positive = english_df[english_df['has_w_expression']]['sentiment'].value_counts()
            print(f"检测到 {w_count} 条包含'W'表达的评论")
            print(f"'W'表达评论的情感分布:\n{w_positive}")

            # 整体情感分布
            print(f"英文评论整体情感分布:\n{english_df['sentiment'].value_counts()}")

        if non_english_df is not None and not non_english_df.empty:
            output_non_en = "非英文评论后续处理.xlsx"
            non_english_df.to_excel(output_non_en, index=False)
            print(f"非英文评论已单独保存至: {output_non_en}")
            print(f"非英文语言分布:\n{non_english_df['language'].value_counts().head(10)}")

    except Exception as e:
        print(f"处理失败: {e}")
        import traceback

        traceback.print_exc()