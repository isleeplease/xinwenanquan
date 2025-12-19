import pandas as pd
import os
import requests
import jieba
import openpyxl
import time
import sys
import glob

# 1. 读取Excel文件
try:
    df = pd.read_excel(".xlsx", sheet_name="Sheet1")
    print("Excel文件读取成功！")
except Exception as e:
    print(f"读取Excel文件失败: {e}")
    sys.exit(1)


# 2. 加载情感词典（优先使用本地文件）
def load_sentiment_dict():
    # 获取当前目录下的所有文件
    all_files = os.listdir()
    print("当前目录下的文件:", all_files)

    # 查找可能的正面词典文件
    pos_files = []
    for file in all_files:
        if "positive" in file.lower() or "pos" in file.lower():
            pos_files.append(file)

    # 查找可能的负面词典文件
    neg_files = []
    for file in all_files:
        if "negative" in file.lower() or "neg" in file.lower():
            neg_files.append(file)

    print("检测到的正面词典文件:", pos_files)
    print("检测到的负面词典文件:", neg_files)

    pos_words = set()
    neg_words = set()

    # 加载正面词典文件 - 使用GBK编码
    if pos_files:
        for pos_file in pos_files:
            try:
                # 尝试使用GBK编码打开文件
                with open(pos_file, "r", encoding="gbk") as f:
                    for line in f:
                        word = line.strip()
                        if word:
                            pos_words.add(word)
                print(f"成功从本地文件 {pos_file} 加载正面词: {len(pos_words)}个")
                break  # 加载一个文件后就停止
            except UnicodeDecodeError:
                # 如果GBK失败，尝试使用GB18030编码
                try:
                    with open(pos_file, "r", encoding="gb18030") as f:
                        for line in f:
                            word = line.strip()
                            if word:
                                pos_words.add(word)
                    print(f"成功从本地文件 {pos_file} 加载正面词: {len(pos_words)}个")
                    break
                except Exception as e:
                    print(f"读取本地正面词典 {pos_file} 失败: {e}")
            except Exception as e:
                print(f"读取本地正面词典 {pos_file} 失败: {e}")
    else:
        print("未找到任何本地正面词典文件")

    # 加载负面词典文件 - 使用GBK编码
    if neg_files:
        for neg_file in neg_files:
            try:
                # 尝试使用GBK编码打开文件
                with open(neg_file, "r", encoding="gbk") as f:
                    for line in f:
                        word = line.strip()
                        if word:
                            neg_words.add(word)
                print(f"成功从本地文件 {neg_file} 加载负面词: {len(neg_words)}个")
                break  # 加载一个文件后就停止
            except UnicodeDecodeError:
                # 如果GBK失败，尝试使用GB18030编码
                try:
                    with open(neg_file, "r", encoding="gb18030") as f:
                        for line in f:
                            word = line.strip()
                            if word:
                                neg_words.add(word)
                    print(f"成功从本地文件 {neg_file} 加载负面词: {len(neg_words)}个")
                    break
                except Exception as e:
                    print(f"读取本地负面词典 {neg_file} 失败: {e}")
            except Exception as e:
                print(f"读取本地负面词典 {neg_file} 失败: {e}")
    else:
        print("未找到任何本地负面词典文件")

    # 如果本地词典已加载，直接返回
    if len(pos_words) > 0 or len(neg_words) > 0:
        print(f"本地词典加载完成！正面词数量: {len(pos_words)}, 负面词数量: {len(neg_words)}")
        return pos_words, neg_words

    # 如果本地词典不完整，尝试从网络下载
    print("本地词典不完整，尝试从网络下载...")

    # 备选情感词典源
    dict_sources = [
        {
            "name": "大连理工大学情感词典",
            "pos": "https://raw.githubusercontent.com/rainarch/SentiBridge/master/EntityEmotion/pos.txt",
            "neg": "https://raw.githubusercontent.com/rainarch/SentiBridge/master/EntityEmotion/neg.txt"
        },
        {
            "name": "清华大学情感词典",
            "pos": "https://raw.githubusercontent.com/AI-Light/TextEmotionAnalysis/master/dict/positive.txt",
            "neg": "https://raw.githubusercontent.com/AI-Light/TextEmotionAnalysis/master/dict/negative.txt"
        }
    ]

    # 尝试从不同源下载词典
    for source in dict_sources:
        print(f"尝试下载 {source['name']}...")

        # 下载正面词典
        try:
            response = requests.get(source["pos"], timeout=10)
            response.raise_for_status()
            words = response.text.splitlines()
            new_words = set([word.strip() for word in words if word.strip()])
            pos_words.update(new_words)
            print(f"新增正面词: {len(new_words)}个")
        except Exception as e:
            print(f"下载正面词典失败: {e}")

        # 下载负面词典
        try:
            response = requests.get(source["neg"], timeout=10)
            response.raise_for_status()
            words = response.text.splitlines()
            new_words = set([word.strip() for word in words if word.strip()])
            neg_words.update(new_words)
            print(f"新增负面词: {len(new_words)}个")
        except Exception as e:
            print(f"下载负面词典失败: {e}")

        # 如果已经获取到足够词汇，提前结束
        if len(pos_words) > 100 and len(neg_words) > 100:
            break

    # 如果仍然不完整，使用基础词典
    if len(pos_words) < 50 or len(neg_words) < 50:
        print("词典不完整，使用内置基础词典")
        base_pos = {"好", "喜欢", "支持", "棒", "优秀", "赞", "不错", "精彩", "完美", "满意",
                    "可爱", "漂亮", "美丽", "开心", "高兴", "棒极了", "超赞", "给力", "太棒了",
                    "很好", "非常好", "厉害", "牛逼", "牛", "强", "精彩", "感动", "温暖", "温馨"}
        base_neg = {"差", "讨厌", "反对", "垃圾", "糟糕", "烂", "失望", "问题", "批评", "不满",
                    "恶心", "丑陋", "伤心", "难过", "愤怒", "差劲", "无语", "坑爹", "骗人", "虚假",
                    "恶心", "吐", "难受", "痛苦", "郁闷", "烦躁", "生气", "愤怒", "恨", "可恶"}
        pos_words.update(base_pos)
        neg_words.update(base_neg)

    print(f"情感词典加载完成！正面词数量: {len(pos_words)}, 负面词数量: {len(neg_words)}")
    return pos_words, neg_words


# 3. 情感分析函数（使用jieba分词）
def sentiment_analysis(text, positive_words, negative_words):
    try:
        # 使用jieba进行分词
        words = jieba.lcut(text)

        # 计算情感得分
        positive_score = 0
        negative_score = 0

        for word in words:
            if word in positive_words:
                positive_score += 1
            elif word in negative_words:
                negative_score += 1

        total_score = positive_score - negative_score

        # 根据得分判断情感
        if total_score > 0:
            sentiment_label = "正面"
        elif total_score < 0:
            sentiment_label = "负面"
        else:
            sentiment_label = "中性"

        return sentiment_label, positive_score, negative_score, words
    except Exception as e:
        print(f"情感分析失败: {e}")
        return "错误", 0, 0, []


# 4. 添加自定义词典
def add_custom_dict():
    # 添加一些常见的网络用语和特定领域的词汇
    custom_words = {
        "绝绝子": "正面",
        "yyds": "正面",
        "破防": "负面",
        "栓Q": "负面",
        "芭比Q": "负面",
        "无语": "负面",
        "爱了": "正面",
        "神仙": "正面",
        "宝藏": "正面",
        "避雷": "负面",
        "拔草": "负面",
        "种草": "正面",
        "安利": "正面",
        "踩雷": "负面",
        "翻车": "负面",
        "天花板": "正面",
        "下头": "负面",
        "上头": "正面",
        "尬": "负面",
        "牛排": "负面",
        "猪排": "负面",
        "尴尬": "负面",
        "演员": "负面",
        "剧本": "负面",
        "神人": "负面",
        "有活": "正面",
        "有节目": "正面",
        "辣眼睛": "负面",
        "逆天玩意": "负面",
        "绝了": "正面",
        "符文": "负面",
        "裂开": "负面",
        "针不戳": "正面",
        "蚌埠住了": "中立",
        "欧买噶": "正面",  # 甲亢哥常用语
        "抽象": "中立",  # 网络用语
        "整活": "中立",  # 网络用语
        "绷不住了": "中立"  # 网络用语
    }

    for word, sentiment in custom_words.items():
        jieba.add_word(word)


# 主程序
if __name__ == "__main__":
    # 初始化jieba分词器
    jieba.initialize()

    # 添加自定义词典
    add_custom_dict()

    # 加载情感词典（优先使用本地文件）
    print("\n===== 开始加载情感词典 =====")
    positive_words, negative_words = load_sentiment_dict()
    print("===========================\n")

    # 应用情感分析
    results = []
    total = len(df)
    start_time = time.time()
    for i, row in df.iterrows():
        cleaned_text = str(row["cleaned"]) if pd.notna(row["cleaned"]) else ""
        try:
            sentiment_label, pos_score, neg_score, words = sentiment_analysis(
                cleaned_text, positive_words, negative_words
            )
            results.append({
                "cleaned_text": cleaned_text,
                "words": "|".join(words),
                "positive_score": pos_score,
                "negative_score": neg_score,
                "sentiment_label": sentiment_label
            })

            # 打印进度（每10条或每分钟）
            if (i + 1) % 10 == 0 or (i + 1) == total:
                elapsed = time.time() - start_time
                mins, secs = divmod(elapsed, 60)
                print(
                    f"处理进度: {i + 1}/{total} ({((i + 1) / total) * 100:.1f}%) | 已用时间: {int(mins)}分{int(secs)}秒",
                    end='\r')
        except Exception as e:
            print(f"\n处理失败: {cleaned_text[:50]}... 错误: {e}")
            results.append({
                "cleaned_text": cleaned_text,
                "words": "ERROR",
                "positive_score": -1,
                "negative_score": -1,
                "sentiment_label": "ERROR"
            })

    # 保存结果到新Excel
    result_df = pd.DataFrame(results)
    result_df.to_excel("情感分析结果.xlsx", index=False)
    print("\n情感分析完成！结果已保存到 '情感分析结果.xlsx'")

    # 添加统计信息
    try:
        # 统计各类情感的比例
        sentiment_counts = result_df['sentiment_label'].value_counts()
        total_comments = len(result_df)

        # 创建新的工作簿
        book = openpyxl.load_workbook("情感分析结果.xlsx")
        sheet = book.active

        # 添加统计信息
        sheet.append([])  # 空行
        sheet.append(["情感分析统计"])
        sheet.append(["情感类型", "数量", "占比"])

        for sentiment, count in sentiment_counts.items():
            percentage = count / total_comments * 100
            sheet.append([sentiment, count, f"{percentage:.2f}%"])

        # 添加总体统计
        sheet.append([])
        sheet.append(["总计", total_comments, "100%"])

        # 保存修改
        book.save("情感分析结果.xlsx")
        print("已添加情感分析统计信息到Excel文件")
    except Exception as e:
        print(f"添加统计信息失败: {e}")