import pandas as pd
import re
import numpy as np

# 读取数据
df = pd.read_excel('非英文评论后续处理.xlsx')


# 定义优化版多语种情感分析规则
def optimized_multilingual_sentiment_analysis(text, language, cleaned_text):
    """
    优化版多语种情感分析函数
    """
    # 转换为字符串并小写处理
    text_str = str(text) if pd.notna(text) else ""
    text_lower = text_str.lower()
    cleaned_str = str(cleaned_text) if pd.notna(cleaned_text) else ""
    cleaned_lower = cleaned_str.lower()

    # 1. 高置信度规则 - YouTube特有的"W"表达规则（跨语言适用）
    w_patterns = [
        r'\bw\b', r'w stream', r'w china', r'w speed', r'w end',
        r'w guy', r'w man', r'w con', r'w gg', r'w lets go', r'w million',
        r'congrat', r'congrats', r'gg wp', r'good job', r'well done'
    ]
    if any(re.search(pattern, cleaned_lower, re.IGNORECASE) for pattern in w_patterns):
        return 'positive', 'high'

    # 2. 高置信度规则 - 积极表情符号规则（跨语言适用）
    positive_emoticons = [
        r'❤', r'💚', r'💙', r'💜', r'💛', r'🧡', r'🤍', r'🖤', r'🤎',
        r'🎉', r'🎊', r'🥳', r'😍', r'😊', r'😀', r'😃', r'😄', r'😁',
        r'😆', r'😅', r'😂', r'🤣', r'🥰', r'😘', r'😗', r'😙', r'😚',
        r'😋', r'😛', r'😝', r'😜', r'🤪', r'🤩', r'🤗', r'🤠',
        r'💪', r'👍', r'👏', r'🙌', r'💯', r'🔥', r'✨', r'🌟', r'⭐',
        r'💫', r'💥', r'🎯', r'🏆', r'🥇', r'🥈', r'🥉', r'🏅'
    ]
    if any(re.search(pattern, text_str) for pattern in positive_emoticons):
        return 'positive', 'high'

    # 3. 高置信度规则 - 消极表情符号规则（跨语言适用）
    negative_emoticons = [
        r'💔', r'😭', r'😢', r'😞', r'😔', r'😟', r'😕', r'🙁', r'☹️',
        r'😣', r'😖', r'😫', r'😩', r'🥺', r'😦', r'😧', r'😨', r'😰',
        r'😥', r'😓', r'😱', r'😡', r'😠', r'🤬', r'😤', r'🤮',
        r'🤢', r'👿', r'💀', r'💩', r'🤡', r'👹', r'👺', r'👻', r'👽',
        r'👾', r'🤖', r'💣', r'🔥', r'🖕', r'👎'
    ]
    if any(re.search(pattern, text_str) for pattern in negative_emoticons):
        return 'negative', 'high'

    # 4. 中等置信度规则 - 英语关键词规则（跨语言适用）
    english_positive_keywords = [
        'love', 'great', 'amazing', 'awesome', 'cool', 'nice', 'good',
        'best', 'perfect', 'fantastic', 'excellent', 'brilliant', 'wonderful',
        'congratulations', 'congrats', 'happy', 'fun', 'enjoy', 'like',
        'beautiful', 'gorgeous', 'fabulous', 'incredible', 'outstanding',
        'win', 'wins', 'won', 'victory', 'success', 'successful',
        'yes', 'yeah', 'yay', 'hurray', 'omg', 'wow'
    ]

    english_negative_keywords = [
        'hate', 'bad', 'terrible', 'awful', 'worst', 'horrible', 'disgusting',
        'stupid', 'idiot', 'dumb', 'fool', 'angry', 'mad', 'suck', 'sucks',
        'ridiculous', 'annoying', 'boring', 'fake', 'liar', 'scam',
        'lose', 'lost', 'failure', 'fail', 'dead', 'die', 'kill',
        'no', 'nooo', 'wtf', 'omg'
    ]

    pos_keyword_match = any(keyword in text_lower for keyword in english_positive_keywords)
    neg_keyword_match = any(keyword in text_lower for keyword in english_negative_keywords)

    if pos_keyword_match and not neg_keyword_match:
        return 'positive', 'medium'
    elif neg_keyword_match and not pos_keyword_match:
        return 'negative', 'medium'

    # 5. 中等置信度规则 - 特定语言关键词规则
    confidence_level = 'medium'

    # 韩语关键词
    if language == 'ko':
        korean_positive_keywords = ['좋아', '좋다', '멋지다', '최고', '짱', '사랑', '행복', '기뻐', '좋네요', '대박']
        korean_negative_keywords = ['싫어', '나빠', '미워', '화나', '짜증', '빡쳐', '싫어요', '병신']

        if any(keyword in text_str for keyword in korean_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in text_str for keyword in korean_negative_keywords):
            return 'negative', confidence_level

    # 越南语关键词
    if language == 'vi':
        vietnamese_positive_keywords = ['yêu', 'thích', 'tuyệt', 'tốt', 'đẹp', 'vui', 'hạnh phúc', 'tuyệt vời',
                                        'tuyệt zời']
        vietnamese_negative_keywords = ['ghét', 'tệ', 'xấu', 'buồn', 'giận', 'ghê tởm', 'tức giận', 'điên']

        if any(keyword in text_str for keyword in vietnamese_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in text_str for keyword in vietnamese_negative_keywords):
            return 'negative', confidence_level

    # 法语关键词
    if language == 'fr':
        french_positive_keywords = ['aimer', 'bien', 'super', 'bon', 'beau', 'heureux', 'parfait', 'magnifique',
                                    'génial']
        french_negative_keywords = ['détester', 'mal', 'terrible', 'mauvais', 'triste', 'énervé', 'horrible', 'nul']

        if any(keyword in text_str for keyword in french_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in text_str for keyword in french_negative_keywords):
            return 'negative', confidence_level

    # 德语关键词
    if language == 'de':
        german_positive_keywords = ['lieben', 'gut', 'super', 'schön', 'perfekt', 'glücklich', 'wunderbar',
                                    'fantastisch']
        german_negative_keywords = ['hassen', 'schlecht', 'schrecklich', 'traurig', 'ärgerlich', 'schlimm', 'schrott']

        if any(keyword in text_str for keyword in german_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in text_str for keyword in german_negative_keywords):
            return 'negative', confidence_level

    # 西班牙语关键词
    if language == 'es':
        spanish_positive_keywords = ['amar', 'bueno', 'genial', 'hermoso', 'feliz', 'perfecto', 'maravilloso',
                                     'increíble']
        spanish_negative_keywords = ['odiar', 'malo', 'terrible', 'triste', 'enojado', 'horrible', 'feo', 'estúpido']

        if any(keyword in text_str for keyword in spanish_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in text_str for keyword in spanish_negative_keywords):
            return 'negative', confidence_level

    # 6. 中等置信度规则 - 数字和百分比相关的积极表达
    if re.search(r'\d+%.*(?:stream|speed|china)', text_lower):
        return 'neutral', 'medium'  # 百分比表达通常是中性

    # 7. 中等置信度规则 - 特殊数字表达（如百万订阅）
    if re.search(r'\d+\s*(?:million|mio|mill|млн|millione|millones)', text_lower):
        return 'positive', 'medium'  # 提及百万级数字通常是积极的

    # 8. 中等置信度规则 - 特殊积极表达
    special_positive_patterns = [
        r'\d+\s*million', r'\d+\s*m', r'\d+\s*suscriber',
        r'lets go', r'let\'?s go', r'go go', r'yay', r'hurray'
    ]
    if any(re.search(pattern, text_lower) for pattern in special_positive_patterns):
        return 'positive', 'medium'

    # 9. 低置信度规则 - 默认返回中性
    return 'neutral', 'low'


# 应用优化版多语种情感分析
print("正在进行优化版多语种情感分析...")
results = df.apply(
    lambda row: optimized_multilingual_sentiment_analysis(row['text'], row['language'], row['cleaned_text']),
    axis=1
)

# 分离情感标签和置信度
df['optimized_auto_sentiment'] = [result[0] for result in results]
df['confidence_level'] = [result[1] for result in results]

# 统计总体情感分布
print("\n优化版自动标注情感分布:")
overall_sentiment = df['optimized_auto_sentiment'].value_counts()
print(overall_sentiment)

# 按置信度统计
print("\n按置信度级别统计:")
confidence_stats = df.groupby(['confidence_level', 'optimized_auto_sentiment']).size().unstack(fill_value=0)
print(confidence_stats)

# 计算高置信度标注比例
high_confidence = df[df['confidence_level'] == 'high']
medium_confidence = df[df['confidence_level'] == 'medium']
low_confidence = df[df['confidence_level'] == 'low']

total_count = len(df)
high_count = len(high_confidence)
medium_count = len(medium_confidence)
low_count = len(low_confidence)

print(f"\n置信度分布:")
print(f"高置信度标注: {high_count} ({high_count / total_count * 100:.1f}%)")
print(f"中等置信度标注: {medium_count} ({medium_count / total_count * 100:.1f}%)")
print(f"低置信度标注: {low_count} ({low_count / total_count * 100:.1f}%)")
print(f"总计: {total_count} (100.0%)")

# 保存带有优化版自动标注结果的文件
output_filename = '优化版多语种自动标注结果.xlsx'
df.to_excel(output_filename, index=False)
print(f"\n已保存带有优化版自动标注结果的文件: {output_filename}")

# 显示各类别示例
print("\n标注示例 (按置信度和情感分类):")

for confidence in ['high', 'medium']:
    print(f"\n{confidence.upper()} 置信度示例:")
    for sentiment in ['positive', 'negative']:
        print(f"  {sentiment.upper()} 标注:")
        sample = df[(df['confidence_level'] == confidence) & (df['optimized_auto_sentiment'] == sentiment)].head(2)
        for idx, row in sample.iterrows():
            print(f"    语言: {row['language']} | 评论: {row['text']}")
            print(f"    标注: {row['optimized_auto_sentiment']} | 置信度: {row['confidence_level']}")
            print("    ---")