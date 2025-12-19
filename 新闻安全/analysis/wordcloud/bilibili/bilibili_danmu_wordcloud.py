# -*- coding: utf-8 -*-
import re
import pandas as pd
import jieba
import jieba.posseg as psg
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from sklearn.feature_extraction.text import TfidfVectorizer
from datetime import datetime


# ===== 1. 自动化清洗模块 =====
def auto_clean_danmu(df):
    """弹幕智能清洗"""
    # 检查是否存在有效列
    if 'raw_text' not in df.columns:
        print("错误：Excel文件中缺少'raw_text'列")
        return df

    # 删除无效数据
    df = df.dropna(subset=['raw_text'])
    df = df[~df['raw_text'].str.contains(r'^[\.\?。！!？,\s]+$', na=False)]  # 删除纯符号

    # 清洗规则
    patterns = [
        r'空降\d+[:：]?\d+',  # 空降指令
        r'^[0-9a-zA-Z\s]+$',  # 纯英文数字
        r'^\.{3,}$',  # 连续省略号
        r'点击.*继续|屏蔽.*关键词|回复：|转发'  # 系统提示
    ]
    for p in patterns:
        df = df[~df['raw_text'].str.contains(p, na=False)]

    # 特殊符号处理
    df['cleaned'] = df['raw_text'].apply(
        lambda x: re.sub(r'[【】｛｛｛｛｛｛｛｛｝｝｝｝｝｝｝｝［］()（）&%$#@^]+', '', str(x))
    )
    df['cleaned'] = df['cleaned'].str.replace(r'[^\w\s!,?？！。.\u4e00-\u9fff]', '', regex=True)

    # 过滤空文本
    df = df[df['cleaned'].str.strip().astype(bool)]
    df = df[df['cleaned'].str.len() >= 2]  # 保留至少2个字符的文本

    return df


# ===== 2. 词云生成模块 =====
def generate_meaningful_wordcloud(text):
    """生成有意义的词云（过滤无意义词汇）"""
    # 添加高级停用词过滤
    custom_stopwords = {"哈哈", "哈哈哈", "哈哈哈哈", "哈", "啊", "哦", "呃", "了", "的", "是"}

    # 添加词性过滤（保留名词、动词、形容词）
    # 修复：正确处理jieba.posseg.cut()返回的pair对象
    words_gen = psg.cut(text)
    filtered_words = []
    for pair in words_gen:
        word = pair.word
        flag = pair.flag
        if word not in custom_stopwords and flag in ['n', 'v', 'a', 'l'] and len(word) > 1:
            filtered_words.append(word)

    # 使用TF-IDF加权
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([" ".join(filtered_words)])
    word_weights = dict(zip(vectorizer.get_feature_names_out(),
                            tfidf_matrix.sum(axis=0).tolist()[0]))

    # 生成加权词云
    wc = WordCloud(
        font_path='simhei.ttf',
        width=1200,
        height=600,
        background_color='white',
        colormap='viridis',
        prefer_horizontal=0.8,
        relative_scaling=0.5
    )
    return wc.generate_from_frequencies(word_weights)


# ===== 3. 时间筛选功能 =====
def filter_by_time(df, time_column='abs_time'):
    """根据时间范围筛选数据"""
    if time_column not in df.columns:
        print(f"警告: 数据中未找到'{time_column}'列，将跳过时间筛选")
        return df, False

    print("数据中的时间格式示例:")
    print(df[time_column].iloc[0] if len(df) > 0 else "无数据")

    # 询问是否进行时间筛选
    time_filter_choice = input("是否要根据时间筛选数据？(y/n): ").strip().lower()
    if time_filter_choice != 'y':
        return df, False

    # 获取时间筛选范围
    print("\n请输入时间范围(支持多种格式: 2025-03-29 00:00:00 或 2025/3/29 0:00:46)")
    start_time_input = input("请输入起始时间: ").strip()
    end_time_input = input("请输入结束时间: ").strip()

    try:
        # 转换时间格式
        df[time_column] = pd.to_datetime(df[time_column], errors='coerce')

        # 解析用户输入的时间
        start_time = pd.to_datetime(start_time_input)
        end_time = pd.to_datetime(end_time_input)

        if pd.isna(start_time) or pd.isna(end_time):
            print("错误: 时间格式解析失败，请检查输入格式")
            return df, False

        # 筛选数据
        original_count = len(df)
        time_mask = (df[time_column] >= start_time) & (df[time_column] <= end_time)
        df = df[time_mask]
        filtered_count = len(df)

        print(f"时间筛选后数据: {filtered_count}条 (筛选前: {original_count}条)")
        print(f"时间范围: {start_time} 至 {end_time}")

        if filtered_count == 0:
            print("警告: 时间筛选后无数据")

        return df, True

    except Exception as e:
        print(f"时间筛选过程中发生错误: {str(e)}")
        return df, False


# ===== 4. 主执行流程 =====
if __name__ == "__main__":
    # 1. 用户输入文件路径
    file_path = input("请输入Excel文件路径: ").strip()

    # 2. 读取数据
    try:
        df = pd.read_excel(file_path)
        print(f"成功读取文件: {len(df)}条记录")
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        exit()

    # 3. 时间筛选
    df, time_filter_applied = filter_by_time(df, 'abs_time')
    time_suffix = ""

    if time_filter_applied:
        # 为输出文件名生成时间后缀
        time_suffix = "_时间筛选"

    # 4. 情感筛选功能
    sentiment_suffix = ""
    if 'final_sentiment' in df.columns:
        filter_choice = input("是否要根据情感标注筛选数据？(y/n): ").strip().lower()
        if filter_choice == 'y':
            print("可选情感标签: 积极, 中立, 消极")
            sentiment_filter = input("请输入要筛选的情感标签(多个标签用逗号分隔): ").strip()

            # 处理用户输入的多个标签
            selected_sentiments = [s.strip() for s in sentiment_filter.split(',')]

            # 筛选数据
            original_count = len(df)
            df = df[df['final_sentiment'].isin(selected_sentiments)]
            filtered_count = len(df)

            print(f"情感筛选后数据: {filtered_count}条 (筛选前: {original_count}条)")
            sentiment_suffix = f"_{'_'.join(selected_sentiments)}"

            if filtered_count == 0:
                print("警告: 筛选后无数据，程序将退出")
                exit()
    else:
        print("警告: 数据中未找到'final_sentiment'列，将使用全部数据")

    # 5. 数据清洗
    cleaned_df = auto_clean_danmu(df)
    print(f"清洗后数据: {len(cleaned_df)}条")

    # 6. 分词和词云生成
    if len(cleaned_df) > 0:
        all_text = " ".join(cleaned_df['cleaned'])
        wordcloud = generate_meaningful_wordcloud(all_text)

        # 7. 保存词云图片
        plt.figure(figsize=(12, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')

        # 设置标题
        title_parts = []
        if time_filter_applied:
            title_parts.append("时间筛选")
        if sentiment_suffix:
            title_parts.append(f"情感: {sentiment_suffix.replace('_', '')}")

        if title_parts:
            plt.title(f'弹幕关键词云图 - {" & ".join(title_parts)}')
        else:
            plt.title('弹幕关键词云图')

        # 生成输出文件名
        filename_suffix = f"{time_suffix}{sentiment_suffix}"
        output_filename = f'弹幕词云{filename_suffix}.png'
        plt.savefig(output_filename, bbox_inches='tight', dpi=300)
        print(f"词云已保存为 '{output_filename}'")

        # 8. 保存清洗后的数据
        output_data_filename = f'清洗后的弹幕数据{filename_suffix}.xlsx'
        cleaned_df.to_excel(output_data_filename, index=False)
        print(f"清洗后的数据已保存为 '{output_data_filename}'")
    else:
        print("警告: 清洗后无数据可用，无法生成词云")