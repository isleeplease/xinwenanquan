import pandas as pd
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
import jieba
import matplotlib.font_manager as fm
from collections import Counter
import os


# 自动识别中文字体路径
def find_chinese_font():
    """查找系统中的中文字体"""
    font_path = None
    # 常见字体路径
    font_candidates = [
        'simhei.ttf', 'simsun.ttc', 'msyh.ttc', 'msyhbd.ttc',
        'STHeiti Medium.ttc', 'PingFang.ttc', 'NotoSansCJKsc-Regular.otf'
    ]

    # 系统字体目录
    font_dirs = [
        'C:/Windows/Fonts/',
        '/Library/Fonts/',
        '/usr/share/fonts/truetype/'
    ]

    # 尝试查找存在的字体
    for font in font_candidates:
        for directory in font_dirs:
            path = os.path.join(directory, font)
            if os.path.exists(path):
                return path

    # 如果未找到，尝试返回matplotlib已加载的字体
    try:
        for font in fm.findSystemFonts():
            if any(name in font.lower() for name in ['simhei', 'simsun', 'msyh', 'pingfang']):
                return font
    except:
        pass

    return None


# 增强的数据加载函数
def load_comments_data(file_path):
    """加载评论数据，处理常见异常"""
    print(f"加载文件: {file_path}")
    try:
        # 尝试读取Excel文件
        df = pd.read_excel(file_path)
        print(f"✅ 成功读取文件: {len(df)}条记录")

        # 检查列名
        print(f"文件包含的列: {list(df.columns)}")

        # 列名处理 (兼容不同格式的列名)
        rename_map = {}

        # 文本列
        text_cols = ['text', 'cleaned_text', '评论内容', '评论', 'content']
        for col in text_cols:
            if col in df.columns:
                rename_map[col] = 'text'
                break
        else:  # 没有找到任何文本列
            raise ValueError("错误: 文件中没有找到评论文本列")

        # 点赞数列
        like_cols = ['like_count', 'likes', '点赞数', '点赞', 'favorites']
        for col in like_cols:
            if col in df.columns:
                rename_map[col] = 'like_count'
                break

        # 日期列
        date_cols = ['published_at', 'date', '时间', 'timestamp', '评论时间']
        for col in date_cols:
            if col in df.columns:
                rename_map[col] = 'published_at'
                break

        # 情感列
        sentiment_cols = ['sentiment', '情感', '情感分析', 'emotion']
        for col in sentiment_cols:
            if col in df.columns:
                rename_map[col] = 'sentiment'
                break

        # 应用列重命名
        df = df.rename(columns=rename_map)

        # 确保必要列存在
        required_cols = ['text']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"错误: 必需的列 '{col}' 缺失")

        # 填充缺失值
        if 'like_count' not in df.columns:
            print("⚠️ 警告: 点赞数列缺失，所有评论点赞数设为1")
            df['like_count'] = 1

        if 'published_at' not in df.columns:
            print("⚠️ 警告: 时间戳列缺失，所有评论设为当前时间")
            df['published_at'] = pd.Timestamp.now()

        if 'sentiment' not in df.columns:
            print("⚠️ 警告: 情感分析列缺失，所有评论设为'neutral'")
            df['sentiment'] = 'neutral'

        # 打印信息
        print(f"处理后包含的列: {list(df.columns)}")
        if 'like_count' in df.columns:
            print(
                f"点赞数统计 (min/max/avg): {df['like_count'].min():,}/{df['like_count'].max():,}/{df['like_count'].mean():.1f}")

        return df

    except Exception as e:
        print(f"❌ 加载失败: {str(e)}")
        return pd.DataFrame()


# 多语言文本处理
def process_multilingual_text(text):
    """处理多语言混合文本"""
    if not isinstance(text, str):
        return []

    # 基本清理
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)  # 保留中文文字字符
    text = text.lower()

    # 语言检测
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
    has_english = bool(re.search(r'[a-z]', text))

    # 混合语言处理
    words = []

    # 中文分词 (使用jieba)
    if has_chinese:
        try:
            # 中文文本分
            ch_words = [word for word in jieba.cut(text) if len(word) > 1]
            words.extend(ch_words)
        except:
            # 如果jieba处理失败，回退到简单分词
            ch_words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
            words.extend(ch_words)

    # 英文分词
    if has_english:
        en_words = re.findall(r'[a-z]{3,}', text)  # 仅保留3字符以上的英文单词
        words.extend(en_words)

    return words


def get_stopwords():
    """获取中英文停用词列表"""
    # 中文停用词
    chinese_stopwords = set([
        '的', '了', '在', '和', '是', '我', '你', '他', '她', '它', '这', '那', '就', '不', '也', '有', '没有',
        '没', '啊', '哦', '嗯', '呀', '吧', '呢', '吗', '啦', '哇', '哈', '唉', '哟', '呵', '嘿', '哼', '自己',
        '什么', '怎么', '为什么', '如何', '可以', '可能', '可是', '让', '把', '被', '给', '对', '向', '跟', '和',
        '与', '同', '了', '着', '过', '得', '地', '的', '啊', '吧', '呢', '吗'
    ])

    # 英文停用词 - 特别添加了代词、介词和常用动词
    english_stopwords = set([
        'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what', 'which', 'this', 'that',
        'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'having', 'do', 'does', 'did', 'doing', 'will', 'would', 'shall', 'should', 'can', 'could', 'may',
        'might', 'must', 'to', 'from', 'in', 'on', 'at', 'by', 'with', 'about', 'against', 'between',
        'into', 'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over',
        'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
        'any', 'both', 'each', 'few', 'more', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're",
        "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
        'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their',
        'theirs', 'themselves'
    ])

    # 数字和特殊字符
    numbers = set([str(i) for i in range(0, 100)])
    special_chars = set(['', ' ', '..', '...', '....', '.....', 'rt'])

    # 合并所有停用词
    return chinese_stopwords | english_stopwords | numbers | special_chars


# 主词云生成函数
def generate_wordcloud(df, font_path=None):
    """从数据框生成词云"""
    if df.empty:
        print("错误: 数据框为空")
        return

    # 获取扩展的停用词列表
    stopwords = get_stopwords()

    # 准备权重计数器
    word_weights = Counter()

    # 处理每条评论
    total = len(df)
    for i, row in df.iterrows():
        text = row.get('text', '')
        if not text:
            continue

        # 分词
        words = process_multilingual_text(text)

        # 计算权重 (使用点赞数的对数，防止极端值主导)
        weight = np.log1p(row.get('like_count', 1))

        # 更新词权重
        for word in set(words):  # 每条评论中每个词只计一次
            # 检查单词是否在停用词列表中
            if (len(word) >= 2 and
                    word not in stopwords and
                    not word.isnumeric()):
                word_weights[word] += weight

    # 检查是否有有效词汇
    if not word_weights:
        print("警告: 没有找到任何有效关键词")
        return

    # 获取最高权重词
    top_words = word_weights.most_common(10)
    print(f"\n🔝🔝 最高权重词: ")
    for word, weight in top_words:
        print(f"  {word}: {weight:.1f}")

    # 自动获取字体
    if not font_path:
        font_path = find_chinese_font()

    if not font_path:
        print("⚠️ 警告：未找到中文字体，使用默认字体")
        font_path = None
    else:
        print(f"✅ 使用字体: {os.path.basename(font_path)}")

    # 生成词云
    print("\n🖼🖼🖼️ 生成词云中...")
    wc = WordCloud(
        font_path=font_path,
        width=1200,
        height=800,
        background_color='white',
        max_words=200,
        collocations=False,
        prefer_horizontal=0.8,
        colormap='viridis'
    ).generate_from_frequencies(word_weights)

    # 显示词云
    plt.figure(figsize=(15, 10))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    plt.title(f"YouTube评论词云 (共{total}条评论)", fontsize=16)
    plt.tight_layout()
    plt.show()
    print("✅ 词云生成完成!")


# 主程序
# 主程序
if __name__ == "__main__":
    # 文件路径
    file_path = "C:/wordcloud/YouTube评论.xlsx"

    # 加载数据
    df = load_comments_data(file_path)

    if not df.empty:
        # ==== 添加筛选功能 ====
        print("\n==== 筛选选项 ====")

        # 1. 时间筛选 (如果存在时间列)
        if 'published_at' in df.columns:
            # 转换为日期类型
            df['published_at'] = pd.to_datetime(df['published_at'])

            # 获取时间范围
            min_date = df['published_at'].min().strftime('%Y-%m-%d')
            max_date = df['published_at'].max().strftime('%Y-%m-%d')
            print(f"数据时间范围: {min_date} 至 {max_date}")

            # 用户输入时间范围
            start_date = input(f"输入开始日期(格式:YYYY-MM-DD, 留空则从 {min_date} 开始): ") or min_date
            end_date = input(f"输入结束日期(格式:YYYY-MM-DD, 留空则到 {max_date} 结束): ") or max_date

            # 应用筛选
            df = df[(df['published_at'] >= start_date) &
                    (df['published_at'] <= end_date)]
            print(f"⏰ 时间筛选: {start_date} 至 {end_date}, 剩余 {len(df)} 条评论")

        # 2. 情感筛选 (如果存在情感列)
        if 'sentiment' in df.columns:
            # 获取所有情感类别
            sentiments = df['sentiment'].unique()
            print(f"可用的情感标签: {', '.join(sentiments)}")

            # 用户输入情感筛选
            selected = input("输入要包含的情感(多个用逗号分隔, 留空则包含所有): ")
            if selected:
                selected_sentiments = [s.strip() for s in selected.split(',')]
                df = df[df['sentiment'].isin(selected_sentiments)]
                print(f"😊 情感筛选: {selected_sentiments}, 剩余 {len(df)} 条评论")
        # ==== 结束筛选 ====

        # 生成词云
        if not df.empty:
            generate_wordcloud(df)
        else:
            print("⚠️ 筛选后数据为空，无法生成词云")