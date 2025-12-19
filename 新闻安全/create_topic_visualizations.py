import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from wordcloud import WordCloud
import matplotlib.font_manager as fm

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据
df_fuzzy = pd.read_excel('bilibili_comment_analysis_results_fuzzy.xlsx')

# 创建图表
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle('电竞赛事评论话题分析结果', fontsize=16, fontweight='bold')

# 1. Top 10 topics by 综合得分
top_composite = df_fuzzy.nlargest(10, '综合得分')
axes[0, 0].barh(range(len(top_composite)), top_composite['综合得分'], color='skyblue')
axes[0, 0].set_yticks(range(len(top_composite)))
axes[0, 0].set_yticklabels(top_composite['话题'])
axes[0, 0].set_xlabel('综合得分')
axes[0, 0].set_title('Top 10 高频话题 (按综合得分)')
axes[0, 0].invert_yaxis()

# 2. Top 10 topics by 意见性得分
top_opinion = df_fuzzy.nlargest(10, '意见性得分')
axes[0, 1].barh(range(len(top_opinion)), top_opinion['意见性得分'], color='lightcoral')
axes[0, 1].set_yticks(range(len(top_opinion)))
axes[0, 1].set_yticklabels(top_opinion['话题'])
axes[0, 1].set_xlabel('意见性得分')
axes[0, 1].set_title('Top 10 意见性话题')
axes[0, 1].invert_yaxis()

# 3. 话题词频分布
axes[1, 0].hist(df_fuzzy['词频'], bins=30, color='lightgreen', alpha=0.7)
axes[1, 0].set_xlabel('词频')
axes[1, 0].set_ylabel('话题数量')
axes[1, 0].set_title('话题词频分布')

# 4. 综合得分 vs 意见性得分散点图
scatter = axes[1, 1].scatter(df_fuzzy['综合得分'], df_fuzzy['意见性得分'], 
                           c=df_fuzzy['词频'], cmap='viridis', alpha=0.6)
axes[1, 1].set_xlabel('综合得分')
axes[1, 1].set_ylabel('意见性得分')
axes[1, 1].set_title('话题综合得分 vs 意见性得分')
plt.colorbar(scatter, ax=axes[1, 1], label='词频')

plt.tight_layout()
plt.savefig('topic_analysis_visualizations.png', dpi=300, bbox_inches='tight')
plt.close()

# 创建词云图
# 准备词云数据
topic_freq_dict = dict(zip(df_fuzzy['话题'], df_fuzzy['词频']))

# 生成词云
wordcloud = WordCloud(width=800, height=400, 
                     background_color='white',
                     font_path='simhei.ttf',  # Windows中文字体
                     max_words=100).generate_from_frequencies(topic_freq_dict)

plt.figure(figsize=(10, 5))
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis('off')
plt.title('电竞赛事评论话题词云', fontsize=16, fontweight='bold')
plt.savefig('topic_wordcloud_updated.png', dpi=300, bbox_inches='tight')
plt.close()

print("可视化图表已生成：topic_analysis_visualizations.png 和 topic_wordcloud_updated.png")