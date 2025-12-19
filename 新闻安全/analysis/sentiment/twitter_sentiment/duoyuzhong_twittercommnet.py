import pandas as pd
import re
import numpy as np

# 读取数据
df = pd.read_excel('推特非英文评论后续处理.xlsx')


# 定义最终版多语种情感分析函数
def final_multilingual_sentiment_analysis(comment, language, cleaned_text):
    """
    最终版多语种情感分析函数
    """
    # 转换为字符串处理
    comment_str = str(comment) if pd.notna(comment) else ""
    comment_lower = comment_str.lower()
    cleaned_str = str(cleaned_text) if pd.notna(cleaned_text) else ""
    cleaned_lower = cleaned_str.lower()

    # 1. 高置信度规则 - 积极表情符号
    positive_emoticons = [
        r'❤', r'💚', r'💙', r'💜', r'💛', r'🧡', r'🤍', r'🖤', r'🤎',
        r'🎉', r'🎊', r'🥳', r'😍', r'😊', r'😀', r'😃', r'😄', r'😁',
        r'😆', r'😅', r'😂', r'🤣', r'🥰', r'😘', r'😗', r'😙', r'😚',
        r'😋', r'😛', r'😝', r'😜', r'🤪', r'🤩', r'🤗', r'🤠',
        r'💪', r'👍', r'👏', r'🙌', r'💯', r'🔥', r'✨', r'🌟', r'⭐',
        r'💫', r'💥', r'🎯', r'🏆', r'🥇', r'🥈', r'🥉', r'🏅'
    ]
    if any(re.search(pattern, comment_str) for pattern in positive_emoticons):
        return 'positive', 'high'

    # 2. 高置信度规则 - 消极表情符号
    negative_emoticons = [
        r'💔', r'😭', r'😢', r'😞', r'😔', r'😟', r'😕', r'🙁', r'☹️',
        r'😣', r'😖', r'😫', r'😩', r'🥺', r'😦', r'😧', r'😨', r'😰',
        r'😥', r'😓', r'😱', r'😡', r'😠', r'🤬', r'😤', r'🤮',
        r'🤢', r'👿', r'💀', r'💩', r'🤡', r'👹', r'👺', r'👻', r'👽',
        r'👾', r'🤖', r'💣', r'🔥', r'🖕', r'👎'
    ]
    if any(re.search(pattern, comment_str) for pattern in negative_emoticons):
        return 'negative', 'high'

    # 3. 高置信度规则 - 明确的英文积极关键词
    english_positive_keywords = [
        'love', 'great', 'amazing', 'awesome', 'cool', 'nice', 'good',
        'best', 'perfect', 'fantastic', 'excellent', 'brilliant', 'wonderful',
        'congratulations', 'congrats', 'happy', 'fun', 'enjoy', 'like',
        'beautiful', 'gorgeous', 'fabulous', 'incredible', 'outstanding',
        'win', 'wins', 'won', 'victory', 'success', 'successful',
        'yes', 'yeah', 'yay', 'hurray', 'omg', 'wow', 'fantastic'
    ]

    # 4. 高置信度规则 - 明确的英文消极关键词
    english_negative_keywords = [
        'hate', 'bad', 'terrible', 'awful', 'worst', 'horrible', 'disgusting',
        'stupid', 'idiot', 'dumb', 'fool', 'angry', 'mad', 'suck', 'sucks',
        'ridiculous', 'annoying', 'boring', 'fake', 'liar', 'scam',
        'lose', 'lost', 'failure', 'fail', 'dead', 'die', 'kill',
        'no', 'wtf', 'bullshit', 'crap', 'shit'
    ]

    has_positive_keyword = any(keyword in comment_lower for keyword in english_positive_keywords)
    has_negative_keyword = any(keyword in comment_lower for keyword in english_negative_keywords)

    if has_positive_keyword and not has_negative_keyword:
        return 'positive', 'high'
    elif has_negative_keyword and not has_positive_keyword:
        return 'negative', 'high'

    # 5. 中等置信度规则 - 特定语言关键词
    confidence_level = 'medium'

    # 葡萄牙语关键词
    if language == 'pt':
        portuguese_positive_keywords = ['amo', 'ótimo', 'incrível', 'lindo', 'maravilha', 'perfeito', 'excelente',
                                        'gostei']
        portuguese_negative_keywords = ['odeio', 'horrível', 'terrível', 'péssimo', 'idiota', 'burro', 'ódio']

        if any(keyword in comment_str.lower() for keyword in portuguese_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in comment_str.lower() for keyword in portuguese_negative_keywords):
            return 'negative', confidence_level

    # 法语关键词
    if language == 'fr':
        french_positive_keywords = ['aimer', 'bien', 'super', 'bon', 'beau', 'heureux', 'parfait', 'magnifique',
                                    'excellent']
        french_negative_keywords = ['détester', 'mal', 'terrible', 'mauvais', 'triste', 'énervé', 'horrible', 'stupide']

        if any(keyword in comment_str.lower() for keyword in french_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in comment_str.lower() for keyword in french_negative_keywords):
            return 'negative', confidence_level

    # 德语关键词
    if language == 'de':
        german_positive_keywords = ['lieben', 'gut', 'super', 'schön', 'perfekt', 'glücklich', 'wunderbar',
                                    'fantastisch']
        german_negative_keywords = ['hassen', 'schlecht', 'schrecklich', 'traurig', 'ärgerlich', 'schlimm', 'dumm']

        if any(keyword in comment_str.lower() for keyword in german_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in comment_str.lower() for keyword in german_negative_keywords):
            return 'negative', confidence_level

    # 西班牙语关键词
    if language == 'es':
        spanish_positive_keywords = ['amar', 'bueno', 'genial', 'hermoso', 'feliz', 'perfecto', 'maravilloso',
                                     'excelente']
        spanish_negative_keywords = ['odiar', 'malo', 'terrible', 'triste', 'enojado', 'horrible', 'estúpido', 'idiota']

        if any(keyword in comment_str.lower() for keyword in spanish_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in comment_str.lower() for keyword in spanish_negative_keywords):
            return 'negative', confidence_level

    # 意大利语关键词
    if language == 'it':
        italian_positive_keywords = ['amare', 'buono', 'grande', 'bello', 'felice', 'perfetto', 'meraviglia',
                                     'eccellente']
        italian_negative_keywords = ['odiare', 'cattivo', 'terribile', 'triste', 'arrabbiato', 'stupido', 'idiota']

        if any(keyword in comment_str.lower() for keyword in italian_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in comment_str.lower() for keyword in italian_negative_keywords):
            return 'negative', confidence_level

    # 荷兰语关键词
    if language == 'nl':
        dutch_positive_keywords = ['liefde', 'geweldig', 'fantastisch', 'mooi', 'gelukkig', 'perfect', 'uitstekend']
        dutch_negative_keywords = ['haat', 'verschrikkelijk', 'vreselijk', 'boos', 'dom', 'idioot']

        if any(keyword in comment_str.lower() for keyword in dutch_positive_keywords):
            return 'positive', confidence_level
        if any(keyword in comment_str.lower() for keyword in dutch_negative_keywords):
            return 'negative', confidence_level

    # 6. 中等置信度规则 - 特殊表达
    special_positive_patterns = [
        r'\bomg\b', r'\bwow\b', r'\byay\b', r'\bhurray\b', r'\byeah\b',
        r'\d+\s*(?:million|millionen|millions|millió|milhões|millones)',  # 百万级数字
        r'amazing', r'incredible', r'outstanding', r'brilliant', r'fantastic'
    ]

    special_negative_patterns = [
        r'\bwtf\b', r'\bbullshit\b', r'\bfake\b', r'\bscam\b',
        r'stupid', r'idiot', r'moron', r'crap', r'shit'
    ]

    if any(re.search(pattern, comment_lower) for pattern in special_positive_patterns):
        return 'positive', 'medium'
    elif any(re.search(pattern, comment_lower) for pattern in special_negative_patterns):
        return 'negative', 'medium'

    # 7. 中等置信度规则 - 夸张表达
    exaggeration_patterns = [
        r'\b(so|very|extremely|really|absolutely)\s+(good|nice|great|awesome|perfect|excellent)',
        r'\b(so|very|extremely|really|absolutely)\s+(bad|terrible|awful|horrible|worst)'
    ]

    for pattern in exaggeration_patterns:
        match = re.search(pattern, comment_lower)
        if match:
            if 'good' in match.group() or 'nice' in match.group() or 'great' in match.group() or 'awesome' in match.group() or 'perfect' in match.group() or 'excellent' in match.group():
                return 'positive', 'medium'
            elif 'bad' in match.group() or 'terrible' in match.group() or 'awful' in match.group() or 'horrible' in match.group() or 'worst' in match.group():
                return 'negative', 'medium'

    # 8. 中等置信度规则 - 感叹句
    if re.search(r'(what a|such a)\s+(great|good|amazing|wonderful|terrible|awful)', comment_lower):
        if 'great' in comment_lower or 'good' in comment_lower or 'amazing' in comment_lower or 'wonderful' in comment_lower:
            return 'positive', 'medium'
        elif 'terrible' in comment_lower or 'awful' in comment_lower:
            return 'negative', 'medium'

    # 9. 低置信度规则 - 默认返回中性
    return 'neutral', 'low'


# 应用最终版多语种情感分析
print("正在进行最终版多语种情感分析...")
results = df.apply(
    lambda row: final_multilingual_sentiment_analysis(row['评论内容'], row['language'], row['cleaned_text']),
    axis=1
)

# 分离情感标签和置信度
df['final_auto_sentiment'] = [result[0] for result in results]
df['confidence_level'] = [result[1] for result in results]

# 查看一些低置信度评论示例，分析为何无法自动标注
low_confidence_df = df[df['confidence_level'] == 'low']
print("低置信度评论示例分析:")
print(f"总共{len(low_confidence_df)}条低置信度评论")

# 按语言查看低置信度评论分布
print("\n低置信度评论语言分布:")
language_dist = low_confidence_df['language'].value_counts().head(10)
print(language_dist)

# 查看前20条低置信度评论示例
print("\n前20条低置信度评论示例:")
for idx, row in low_confidence_df.head(20).iterrows():
    print(f"语言: {row['language']} | 评论: {row['评论内容']}")
    print("---")