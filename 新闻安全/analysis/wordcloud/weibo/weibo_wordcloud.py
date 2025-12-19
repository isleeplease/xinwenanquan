# -*- coding: utf-8 -*-
"""
微博评论词云生成代码
基于B站评论词云代码优化设计
"""

import re
import pandas as pd
import jieba
import jieba.posseg as psg
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from sklearn.feature_extraction.text import TfidfVectorizer
from datetime import datetime
import numpy as np
import os


# ===== 1. 微博评论数据清洗模块 =====
def auto_clean_weibo_comments(df):
    """微博评论智能清洗"""
    # 检查是否存在有效列
    if '评论内容' not in df.columns:
        print("错误：Excel文件中缺少'评论内容'列")
        return df

    # 删除无效数据
    df = df.dropna(subset=['评论内容'])
    df = df[~df['评论内容'].str.contains(r'^[\.\?。！!？,\s]+$', na=False)]  # 删除纯符号

    # 清洗规则（针对微博评论特点）
    patterns = [
        r'回复@.*?:',  # 回复标记
        r'@[^\s]+',  # @用户标记
        r'#.+#',  # 话题标签
        r'\[.*?\]',  # 表情符号 [微笑] 等
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # URL链接
        r'^[0-9a-zA-Z\s]+$',  # 纯英文数字
        r'^\.{3,}$',  # 连续省略号
        r'转发理由:.*',  # 转发理由
        r'收起全文d+',  # 收起全文标记
    ]

    for p in patterns:
        df = df[~df['评论内容'].str.contains(p, na=False)]

    # 特殊符号处理
    df['cleaned'] = df['评论内容'].apply(
        lambda x: re.sub(r'[【】｛｝［］()（）&%$#@^]+', '', str(x))
    )
    df['cleaned'] = df['cleaned'].str.replace(r'[^\w\s!,?？！。.一-鿿]', '', regex=True)

    # 过滤空文本
    df = df[df['cleaned'].str.strip().astype(bool)]
    df = df[df['cleaned'].str.len() >= 2]  # 保留至少2个字符的文本

    return df


# ===== 2. 微博评论词云生成模块 =====
def generate_weibo_comment_wordcloud(df):
    """生成微博评论词云（考虑点赞权重）"""
    # 添加微博相关的停用词
    custom_stopwords = {
        "哈哈", "哈哈哈", "哈哈哈哈", "哈", "啊", "哦", "呃", "了", "的", "是", "回复",
        "这个", "那个", "什么", "怎么", "为什么", "可以", "应该", "会", "能", "要",
        "就", "还", "也", "都", "又", "很", "太", "最", "没", "不", "说", "看", "做",
        "想", "知道", "觉得", "感觉", "觉得", "认为", "希望", "需要", "喜欢", "支持"
    }

    # 创建词权重字典（考虑点赞数）
    word_weights = {}

    # 遍历每条评论
    for index, row in df.iterrows():
        text = str(row['cleaned'])
        like_count = row.get('点赞数', 1)  # 默认点赞数为1

        # 分词并过滤
        words_gen = psg.cut(text)
        for pair in words_gen:
            word = pair.word
            flag = pair.flag

            # 过滤条件
            if (word not in custom_stopwords and
                    len(word) > 1 and
                    flag in ['n', 'v', 'a', 'l'] and  # 名词、动词、形容词、习语
                    not re.match(r'^\d+$', word)):

                # 计算词权重（词频 * (点赞数 + 1)）
                weight = 1 * (like_count + 1)

                # 累加到总权重
                if word in word_weights:
                    word_weights[word] += weight
                else:
                    word_weights[word] = weight

    # 如果没有点赞数据，回退到词频统计
    if not word_weights:
        print("警告：未找到点赞数据，使用普通词频统计")
        all_text = " ".join(df['cleaned'])
        words_gen = psg.cut(all_text)
        filtered_words = []
        for pair in words_gen:
            word = pair.word
            flag = pair.flag
            if (word not in custom_stopwords and
                    flag in ['n', 'v', 'a', 'l'] and
                    len(word) > 1):
                filtered_words.append(word)

        # 使用TF-IDF加权
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([" ".join(filtered_words)])
        word_weights = dict(zip(vectorizer.get_feature_names_out(),
                                tfidf_matrix.sum(axis=0).tolist()[0]))

    # 生成加权词云
    wc = WordCloud(
        font_path='simhei.ttf',  # Windows系统黑体字体
        width=1200,
        height=800,
        background_color='white',
        colormap='viridis',
        prefer_horizontal=0.8,
        relative_scaling=0.8,
        min_font_size=10,
        max_words=200
    )
    return wc.generate_from_frequencies(word_weights)


# ===== 3. 时间筛选功能 =====
def filter_by_time(df, time_column='发布时间'):
    """根据时间范围筛选数据"""
    if time_column not in df.columns:
        print(f"警告: 数据中未找到'{time_column}'列，将跳过时间筛选")
        return df, False, ""

    print("数据中的时间格式示例:")
    print(df[time_column].iloc[0] if len(df) > 0 else "无数据")

    # 询问是否进行时间筛选
    time_filter_choice = input("是否要根据时间筛选数据？(y/n): ").strip().lower()
    if time_filter_choice != 'y':
        return df, False, ""

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
            return df, False, ""

        # 筛选数据
        original_count = len(df)
        time_mask = (df[time_column] >= start_time) & (df[time_column] <= end_time)
        df = df[time_mask]
        filtered_count = len(df)

        print(f"时间筛选后数据: {filtered_count}条 (筛选前: {original_count}条)")
        print(f"时间范围: {start_time} 至 {end_time}")

        # 生成时间范围标签
        time_range_str = f"_{start_time.strftime('%Y%m%d')}-{end_time.strftime('%Y%m%d')}"

        if filtered_count == 0:
            print("警告: 时间筛选后无数据")

        return df, True, time_range_str

    except Exception as e:
        print(f"时间筛选过程中发生错误: {str(e)}")
        return df, False, ""


# ===== 4. IP属地筛选功能 =====
def filter_by_location(df):
    """根据IP属地筛选数据"""
    location_suffix = ""
    if 'IP属地' in df.columns:
        filter_choice = input("是否要根据IP属地筛选数据？(y/n): ").strip().lower()
        if filter_choice == 'y':
            print("可选IP属地示例:", df['IP属地'].dropna().unique()[:10])  # 显示前10个不同的属地
            location_filter = input("请输入要筛选的IP属地(多个属地用逗号分隔): ").strip()

            # 处理用户输入的多个标签
            selected_locations = [s.strip() for s in location_filter.split(',')]

            # 筛选数据
            original_count = len(df)
            df = df[df['IP属地'].isin(selected_locations)]
            filtered_count = len(df)

            print(f"IP属地筛选后数据: {filtered_count}条 (筛选前: {original_count}条)")
            location_suffix = f"_{'_'.join(selected_locations)}"

            if filtered_count == 0:
                print("警告: 筛选后无数据")

    else:
        print("警告: 数据中未找到'IP属地'列，将使用全部数据")

    return df, location_suffix


# ===== 5. 情感标签筛选功能 =====
def filter_by_sentiment(df):
    """根据情感标签筛选数据"""
    sentiment_suffix = ""
    # 检查情感标签列是否存在
    sentiment_columns = ['sentiment', '情感标签']
    sentiment_col = None
    for col in sentiment_columns:
        if col in df.columns:
            sentiment_col = col
            break

    if sentiment_col:
        filter_choice = input("是否要根据情感标签筛选数据？(y/n): ").strip().lower()
        if filter_choice == 'y':
            # 显示可用的情感标签
            available_sentiments = df[sentiment_col].dropna().unique()
            print(f"可用的情感标签: {available_sentiments}")

            # 提示用户选择情感标签
            print("情感标签选项: 积极, 消极, 中立 (可输入多个，用逗号分隔)")
            sentiment_filter = input("请输入要筛选的情感标签: ").strip()

            # 处理用户输入的多个标签
            selected_sentiments = [s.strip() for s in sentiment_filter.split(',')]

            # 筛选数据
            original_count = len(df)
            df = df[df[sentiment_col].isin(selected_sentiments)]
            filtered_count = len(df)

            print(f"情感标签筛选后数据: {filtered_count}条 (筛选前: {original_count}条)")
            sentiment_suffix = f"_{'_'.join(selected_sentiments)}"

            if filtered_count == 0:
                print("警告: 筛选后无数据")

    else:
        print(f"警告: 数据中未找到'{sentiment_columns}'列，将使用全部数据")

    return df, sentiment_suffix


# ===== 6. 主执行流程 =====
if __name__ == "__main__":
    # 1. 用户输入文件路径
    file_path = input("请输入Excel文件路径 (直接回车使用默认文件'微博上海评论.xlsx'): ").strip()
    if not file_path:
        file_path = '微博上海评论.xlsx'

    # 2. 读取数据
    try:
        # 读取Excel文件
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        print(f"文件中包含的工作表: {sheet_names}")

        # 如果只有一个工作表，直接读取；否则让用户选择
        if len(sheet_names) == 1:
            df = excel_file.parse(sheet_names[0])
            print(f"已读取工作表: {sheet_names[0]}")
        else:
            print("请选择要分析的工作表:")
            for i, name in enumerate(sheet_names):
                print(f"{i + 1}. {name}")
            choice = input("请输入序号 (默认为1): ").strip()
            try:
                idx = int(choice) - 1 if choice else 0
                if 0 <= idx < len(sheet_names):
                    df = excel_file.parse(sheet_names[idx])
                    print(f"已读取工作表: {sheet_names[idx]}")
                else:
                    raise ValueError("序号超出范围")
            except (ValueError, IndexError):
                df = excel_file.parse(sheet_names[0])
                print(f"输入无效，已读取默认工作表: {sheet_names[0]}")

        print(f"成功读取文件: {len(df)}条记录")
        print("数据列名:", df.columns.tolist())
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        exit()

    # 3. 时间筛选
    df, time_filter_applied, time_suffix = filter_by_time(df, '发布时间')

    # 4. IP属地筛选
    df, location_suffix = filter_by_location(df)

    # 5. 情感标签筛选
    df, sentiment_suffix = filter_by_sentiment(df)

    # 6. 数据清洗
    cleaned_df = auto_clean_weibo_comments(df)
    print(f"清洗后数据: {len(cleaned_df)}条")

    # 7. 词云生成
    if len(cleaned_df) > 0:
        print("正在生成词云...")
        wordcloud = generate_weibo_comment_wordcloud(cleaned_df)

        # 8. 保存词云图片
        plt.figure(figsize=(14, 10))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')

        # 设置标题
        title_parts = []
        if time_filter_applied:
            title_parts.append("时间筛选")
        if location_suffix:
            title_parts.append(f"地域: {location_suffix.replace('_', '')}")
        if sentiment_suffix:
            title_parts.append(f"情感: {sentiment_suffix.replace('_', '')}")

        if title_parts:
            plt.title(f'微博评论关键词云图 - {" & ".join(title_parts)}', fontsize=16)
        else:
            plt.title('微博评论关键词云图', fontsize=16)

        # 生成输出文件名
        filename_suffix = f"{time_suffix}{location_suffix}{sentiment_suffix}"
        output_filename = f'微博评论词云{filename_suffix}.png'

        # 确保保存目录存在
        os.makedirs('output', exist_ok=True)
        full_output_path = os.path.join('output', output_filename)

        plt.savefig(full_output_path, bbox_inches='tight', dpi=300)
        print(f"词云已保存为 '{full_output_path}'")

        # 9. 添加图例说明
        plt.figure(figsize=(10, 1))
        plt.text(0.5, 0.5, "词云大小反映关键词重要性（考虑词频和点赞数）",
                 ha='center', va='center', fontsize=12)
        plt.axis('off')

        legend_filename = os.path.join('output', '词云说明.png')
        plt.savefig(legend_filename, bbox_inches='tight')
        print(f"已生成词云说明图 '{legend_filename}'")

        # 10. 保存清洗后的数据
        output_data_filename = f'清洗后的微博评论数据{filename_suffix}.xlsx'
        full_data_path = os.path.join('output', output_data_filename)
        cleaned_df.to_excel(full_data_path, index=False)
        print(f"清洗后的数据已保存为 '{full_data_path}'")

        # 11. 显示词频统计Top20
        print("\n词频统计Top20:")
        word_freq = {}
        for index, row in cleaned_df.iterrows():
            text = str(row['cleaned'])
            like_count = row.get('点赞数', 1)

            words_gen = psg.cut(text)
            for pair in words_gen:
                word = pair.word
                flag = pair.flag

                if (word not in {"哈哈", "哈哈哈", "哈哈哈哈", "哈", "啊", "哦", "呃", "了", "的", "是", "回复",
                                 "这个", "那个", "什么", "怎么", "为什么", "可以", "应该", "会", "能", "要",
                                 "就", "还", "也", "都", "又", "很", "太", "最", "没", "不", "说", "看", "做",
                                 "想", "知道", "觉得", "感觉", "觉得", "认为", "希望", "需要", "喜欢", "支持"} and
                        len(word) > 1 and
                        flag in ['n', 'v', 'a', 'l']):

                    weight = 1 * (like_count + 1)
                    if word in word_freq:
                        word_freq[word] += weight
                    else:
                        word_freq[word] = weight

        # 排序并显示前20个
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        for i, (word, freq) in enumerate(sorted_words, 1):
            print(f"{i:2d}. {word:<10} ({freq})")

    else:
        print("警告: 清洗后无数据可用，无法生成词云")