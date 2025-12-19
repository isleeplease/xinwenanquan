# -*- coding: utf-8 -*-
import re
import os
import pandas as pd
import jieba
from snownlp import SnowNLP


# ===== 1. 数据清洗模块 =====
def auto_clean_danmu(df):
    """弹幕智能清洗"""
    # 确保有raw_text列
    if 'raw_text' not in df.columns:
        # 尝试找到可能的列名
        text_col = None
        for col in df.columns:
            if 'text' in col.lower() or '内容' in col or '弹幕' in col:
                text_col = col
                break
        if text_col is None:
            text_col = df.columns[1]  # 默认第二列
        df['raw_text'] = df[text_col]

    # 删除无效数据
    df = df.dropna(subset=['raw_text'])
    df = df[~df['raw_text'].str.contains(r'^[\.\?。！!？,\s]+$', regex=True)]  # 删除纯符号

    # 清洗规则
    patterns = [
        r'空降\d+[:：]?\d+',  # 空降指令
        r'^[0-9a-zA-Z\s]+$',  # 纯英文数字
        r'^\.{3,}$',  # 连续省略号
        r'点击.*继续|屏蔽.*关键词|回复：|转发'  # 系统提示
    ]

    for p in patterns:
        df = df[~df['raw_text'].str.contains(p)]

    # 特殊符号处理
    df['cleaned'] = df['raw_text'].apply(
        lambda x: re.sub(r'[【】｛｛｝｝［］()（）&%$#@^]+', '', str(x))
    )
    df['cleaned'] = df['cleaned'].str.replace(r'[^\w\s!,?？！。.\u4e00-\u9fff]', '', regex=True)

    # 过滤空文本
    df = df[df['cleaned'].str.strip().astype(bool)]
    df = df[df['cleaned'].str.len() >= 2]  # 保留至少2个字符

    return df


# ===== 2. 情感词典加载 =====
def load_lexicon():
    """加载情感词典 - 修改版：区分自定义词典和清华词典"""
    # 创建独立词典
    custom_lex = {'positive': set(), 'negative': set(), 'neutral': set()}
    tsinghua_lex = {'positive': set(), 'negative': set()}
    merged_lex = {'positive': set(), 'negative': set(), 'neutral': set()}

    # 1. 优先加载自定义词典（最高优先级）
    custom_files = {
        'positive': 'positive_custom.txt',
        'negative': 'negative_custom.txt',
        'neutral': 'neutral_custom.txt'
    }

    for sentiment, file in custom_files.items():
        if os.path.exists(file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        custom_lex[sentiment].add(word)
                        merged_lex[sentiment].add(word)
                print(f"加载自定义词典: {file} ({len(custom_lex[sentiment])} 个词)")
            except Exception as e:
                print(f"读取自定义词典 {file} 失败: {str(e)}")
        else:
            print(f"未找到自定义词典: {file}")

    # 2. 加载清华词典（次优先级）
    tsinghua_files = [
        'tsinghua.negative.gb.txt',
        'tsinghua_positive_gb.txt',
        'tsinghua_positive_gb_1.txt'
    ]

    for file in tsinghua_files:
        if not os.path.exists(file):
            print(f"清华词典文件不存在: {file}")
            continue

        try:
            # 尝试使用GBK编码
            with open(file, 'r', encoding='gbk') as f:
                for line in f:
                    word = line.strip()
                    if 'negative' in file:
                        tsinghua_lex['negative'].add(word)
                        merged_lex['negative'].add(word)
                    else:
                        tsinghua_lex['positive'].add(word)
                        merged_lex['positive'].add(word)
        except UnicodeDecodeError:
            try:
                # 如果GBK失败，尝试UTF-8
                with open(file, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        if 'negative' in file:
                            tsinghua_lex['negative'].add(word)
                            merged_lex['negative'].add(word)
                        else:
                            tsinghua_lex['positive'].add(word)
                            merged_lex['positive'].add(word)
            except Exception as e:
                print(f"读取清华词典文件 {file} 失败: {str(e)}")

    print(
        f"词典统计: 自定义词(积极:{len(custom_lex['positive'])}, 消极:{len(custom_lex['negative'])}, 中立:{len(custom_lex['neutral'])}) | "
        f"清华词(积极:{len(tsinghua_lex['positive'])}, 消极:{len(tsinghua_lex['negative'])})")

    return {
        'custom': custom_lex,
        'tsinghua': tsinghua_lex,
        'merged': merged_lex
    }


# ===== 3. 反讽识别模块 =====
class IronyDetector:
    def __init__(self):
        # 反讽关键词
        self.irony_keywords = [
            "呵呵", "哈哈", "真好", "太棒了", "不错", "厉害", "可以",
            "行", "不错", "挺好", "有意思", "真行", "真不错", "真厉害",
            "真可以", "真行", "真有意思", "真会玩", "真会说话", "真会做事",
            "真会做人", "真会来事", "真会装", "真会演", "真会玩", "真会玩啊",
            "真会玩呢", "真会玩哦", "真会玩呀", "真会玩嘛", "真会玩啦"
        ]

        # 反讽模式
        self.irony_patterns = [
            r"太(\w{1,4})了吧",  # 太...了吧
            r"真是(\w{1,4})啊",  # 真是...啊
            r"(\w{1,4})死我了",  # ...死我了
            r"好一个(\w{1,4})",  # 好一个...
            r"多么(\w{1,4})啊",  # 多么...啊
        ]

        # 加载自定义反讽词典
        if os.path.exists('irony_custom.txt'):
            try:
                with open('irony_custom.txt', 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        self.irony_keywords.append(word)
                print(f"加载自定义反讽词典: {len(self.irony_keywords)} 个词")
            except Exception as e:
                print(f"读取自定义反讽词典失败: {str(e)}")

    def detect(self, text):
        """检测文本是否包含反讽"""
        # 检查关键词
        for keyword in self.irony_keywords:
            if keyword in text:
                return True

        # 检查模式
        for pattern in self.irony_patterns:
            if re.search(pattern, text):
                return True

        return False


# ===== 4. 情感分析引擎 =====
# ===== 4. 情感分析引擎 =====
class SentimentAnalyzer:
    def __init__(self):
        self.lexicon = load_lexicon()
        self.irony_detector = IronyDetector()

        # 加载分词词典
        custom_dict_files = [
            'custom_dict.txt',
            'positive_custom.txt',
            'negative_custom.txt',
            'neutral_custom.txt'
        ]

        loaded = False
        for file in custom_dict_files:
            if os.path.exists(file):
                try:
                    jieba.load_userdict(file)
                    print(f"加载分词词典: {file}")
                    loaded = True
                except Exception as e:
                    print(f"加载分词词典 {file} 失败: {str(e)}")

        if not loaded:
            print("未加载自定义分词词典")

        # 加载中性表达模式
        self.neutral_patterns = [
            r'^[^!?。！？]*[吗呢吧啊呀]?$',  # 陈述句
            r'^[^!?。！？]*[吗呢吧啊呀]\?$',  # 疑问句
            r'^[^!?。！？]*的$',  # 描述性句子
            r'^[^!?。！？]*了$',  # 完成态句子
        ]

    def is_neutral_structure(self, text):
        """判断句子是否为中性结构"""
        # 短句直接视为中性
        if len(text) <= 4:
            return True

        # 检查中性模式
        for pattern in self.neutral_patterns:
            if re.match(pattern, text):
                return True

        # 包含疑问词
        question_words = ["吗", "呢", "吧", "啊", "呀", "什么", "哪里", "何时", "怎么"]
        if any(word in text for word in question_words) and "?" not in text and "？" not in text:
            return True

        return False

    def analyze(self, text):
        """分析单条文本情感 - 重构版：优先识别中性表达"""
        if not text.strip() or len(text) < 2:
            return {'sentiment': '中立', 'confidence': 0.0, 'irony': False, 'segmented': ''}

        # 中文分词
        words = jieba.lcut(text)
        segmented_text = " ".join(words)

        # 1. 优先检查反讽
        is_irony = self.irony_detector.detect(text)

        # 2. 情感词典分析（优先级：自定义词典 > 清华词典）
        custom_pos = sum(1 for word in words if word in self.lexicon['custom']['positive'])
        custom_neg = sum(1 for word in words if word in self.lexicon['custom']['negative'])
        custom_neu = sum(1 for word in words if word in self.lexicon['custom']['neutral'])

        tsinghua_pos = sum(1 for word in words if word in self.lexicon['tsinghua']['positive'])
        tsinghua_neg = sum(1 for word in words if word in self.lexicon['tsinghua']['negative'])

        # 3. 如果有情感词，优先处理（自定义词典优先级最高）
        if custom_pos > 0 or custom_neg > 0 or custom_neu > 0:
            # 自定义词典有明确情感倾向
            if custom_pos > 0:
                sentiment = '积极'
                confidence = min(0.95, 0.7 + custom_pos * 0.2)
            elif custom_neg > 0:
                sentiment = '消极'
                confidence = min(0.95, 0.7 + custom_neg * 0.2)
            else:  # 只有中立词
                sentiment = '中立'
                confidence = min(0.95, 0.7 + custom_neu * 0.2)

            # 清华词典作为辅助
            if sentiment == '积极':
                confidence += tsinghua_pos * 0.1 - tsinghua_neg * 0.1
            elif sentiment == '消极':
                confidence += tsinghua_neg * 0.1 - tsinghua_pos * 0.1
            else:
                confidence += (tsinghua_pos - tsinghua_neg) * 0.05

            confidence = max(0.4, min(0.95, confidence))

            # 反讽处理
            if is_irony:
                if sentiment == '积极':
                    sentiment = '消极'
                elif sentiment == '消极':
                    sentiment = '积极'
                confidence = max(0.4, confidence * 0.8)

            return {
                'sentiment': sentiment,
                'confidence': round(confidence, 2),
                'irony': is_irony,
                'segmented': segmented_text
            }

        # 4. 处理清华词典中的词
        if tsinghua_pos > 0 or tsinghua_neg > 0:
            dict_score = tsinghua_pos - tsinghua_neg

            if dict_score > 0:
                sentiment = '积极'
                confidence = min(0.95, 0.6 + dict_score * 0.15)
            elif dict_score < 0:
                sentiment = '消极'
                confidence = min(0.95, 0.6 + abs(dict_score) * 0.15)
            else:
                sentiment = '中立'
                confidence = 0.6

            # 反讽处理
            if is_irony:
                if sentiment == '积极':
                    sentiment = '消极'
                elif sentiment == '消极':
                    sentiment = '积极'
                confidence = max(0.4, confidence * 0.8)

            return {
                'sentiment': sentiment,
                'confidence': round(confidence, 2),
                'irony': is_irony,
                'segmented': segmented_text
            }

        # 5. 检查句子结构是否为中性
        if self.is_neutral_structure(text):
            return {
                'sentiment': '中立',
                'confidence': 0.7,  # 结构分析置信度
                'irony': is_irony,
                'segmented': segmented_text
            }

        # 6. 使用SnowNLP作为后备
        try:
            s = SnowNLP(text)
            snow_score = s.sentiments
        except:
            snow_score = 0.5

        if snow_score > 0.7:
            sentiment = '积极'
            confidence = snow_score
        elif snow_score < 0.3:
            sentiment = '消极'
            confidence = 1 - snow_score
        else:
            sentiment = '中立'
            confidence = 0.6

        # 7. 最终反讽处理
        if is_irony:
            if sentiment == '积极':
                sentiment = '消极'
            elif sentiment == '消极':
                sentiment = '积极'
            confidence = max(0.4, confidence * 0.8)

        return {
            'sentiment': sentiment,
            'confidence': round(confidence, 2),
            'irony': is_irony,
            'segmented': segmented_text
        }

# ===== 5. 主处理流程 =====
def main():
    # 读取弹幕数据
    try:
        # 尝试多种可能的文件名
        possible_files = ['重塑弹幕.xlsx', 'danmu.xlsx', '弹幕.xlsx', 'data.xlsx']
        for file in possible_files:
            if os.path.exists(file):
                danmu_df = pd.read_excel(file)
                print(f"成功读取文件: {file}")
                break
        else:
            print("未找到弹幕数据文件")
            return
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        return

    # 数据清洗
    cleaned_df = auto_clean_danmu(danmu_df)
    print(f"原始数据: {len(danmu_df)}条, 清洗后: {len(cleaned_df)}条")

    # 初始化分析器
    analyzer = SentimentAnalyzer()

    # 情感分析
    results = []
    for text in cleaned_df['cleaned']:
        result = analyzer.analyze(text)
        results.append(result)

    # 添加结果到DataFrame
    cleaned_df['sentiment'] = [r['sentiment'] for r in results]
    cleaned_df['confidence'] = [r['confidence'] for r in results]
    cleaned_df['irony'] = [r['irony'] for r in results]
    cleaned_df['segmented'] = [r['segmented'] for r in results]  # 添加分词结果列

    # 保存结果
    output_file = "弹幕情感分析结果.xlsx"
    cleaned_df.to_excel(output_file, index=False)
    print(f"分析完成! 结果已保存至: {output_file}")

    # 显示统计结果
    sentiment_counts = cleaned_df['sentiment'].value_counts()
    irony_count = cleaned_df['irony'].sum()
    print("\n=== 情感分布 ===")
    print(sentiment_counts)
    print(f"检测到反讽: {irony_count} 条")

    # 显示分词示例
    print("\n=== 分词示例 ===")
    for i in range(min(10, len(cleaned_df))):
        row = cleaned_df.iloc[i]
        print(f"原始弹幕: {row['cleaned']}")
        print(f"分词结果: {row['segmented']}")
        print(f"情感: {row['sentiment']}, 置信度: {row['confidence']}, 反讽: {'是' if row['irony'] else '否'}")
        print("=" * 50)


if __name__ == "__main__":
    main()