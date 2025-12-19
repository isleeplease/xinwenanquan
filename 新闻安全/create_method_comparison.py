import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据
df_original = pd.read_excel('bilibili_comment_analysis_results.xlsx')
df_enhanced = pd.read_excel('bilibili_comment_analysis_results_enhanced.xlsx')
df_fuzzy = pd.read_excel('bilibili_comment_analysis_results_fuzzy.xlsx')

# 获取前10个话题
top10_original = df_original.nlargest(10, '综合得分')['话题'].tolist()
top10_enhanced = df_enhanced.nlargest(10, '综合得分')['话题'].tolist()
top10_fuzzy = df_fuzzy.nlargest(10, '综合得分')['话题'].tolist()

# 创建集合以比较话题
original_set = set(top10_original)
enhanced_set = set(top10_enhanced)
fuzzy_set = set(top10_fuzzy)

# 创建维恩图数据
all_topics = list(original_set.union(enhanced_set).union(fuzzy_set))
method_data = {
    '原始方法': [1 if topic in original_set else 0 for topic in all_topics],
    '增强方法': [1 if topic in enhanced_set else 0 for topic in all_topics],
    '模糊匹配方法': [1 if topic in fuzzy_set else 0 for topic in all_topics]
}

# 创建对比图表
fig, axes = plt.subplots(1, 2, figsize=(15, 6))
fig.suptitle('不同分析方法结果对比', fontsize=16, fontweight='bold')

# 1. 方法间共同话题数量
common_original_enhanced = len(original_set.intersection(enhanced_set))
common_original_fuzzy = len(original_set.intersection(fuzzy_set))
common_enhanced_fuzzy = len(enhanced_set.intersection(fuzzy_set))
common_all = len(original_set.intersection(enhanced_set).intersection(fuzzy_set))

venn_data = [common_original_enhanced, common_original_fuzzy, common_enhanced_fuzzy, common_all]
venn_labels = ['原始∩增强', '原始∩模糊', '增强∩模糊', '三者交集']

bars = axes[0].bar(range(len(venn_data)), venn_data, color=['skyblue', 'lightcoral', 'lightgreen', 'gold'])
axes[0].set_xticks(range(len(venn_data)))
axes[0].set_xticklabels(venn_labels, rotation=45)
axes[0].set_ylabel('共同话题数量')
axes[0].set_title('不同方法间共同话题数量')
for i, v in enumerate(venn_data):
    axes[0].text(i, v + 0.5, str(v), ha='center', va='bottom')

# 2. 各方法独特话题数量
unique_original = len(original_set.difference(enhanced_set).difference(fuzzy_set))
unique_enhanced = len(enhanced_set.difference(original_set).difference(fuzzy_set))
unique_fuzzy = len(fuzzy_set.difference(original_set).difference(enhanced_set))

unique_data = [unique_original, unique_enhanced, unique_fuzzy]
unique_labels = ['仅原始方法', '仅增强方法', '仅模糊方法']

bars = axes[1].bar(range(len(unique_data)), unique_data, color=['skyblue', 'lightcoral', 'lightgreen'])
axes[1].set_xticks(range(len(unique_data)))
axes[1].set_xticklabels(unique_labels, rotation=45)
axes[1].set_ylabel('独特话题数量')
axes[1].set_title('各方法独特话题数量')
for i, v in enumerate(unique_data):
    axes[1].text(i, v + 0.5, str(v), ha='center', va='bottom')

plt.tight_layout()
plt.savefig('method_comparison.png', dpi=300, bbox_inches='tight')
plt.close()

# 创建话题排名对比表
# 选取前15个话题进行对比
all_top_topics = list(set(top10_original + top10_enhanced + top10_fuzzy))[:15]

# 创建排名数据
ranking_data = []
for topic in all_top_topics:
    original_rank = df_original[df_original['话题'] == topic].index[0] + 1 if topic in df_original['话题'].values else None
    enhanced_rank = df_enhanced[df_enhanced['话题'] == topic].index[0] + 1 if topic in df_enhanced['话题'].values else None
    fuzzy_rank = df_fuzzy[df_fuzzy['话题'] == topic].index[0] + 1 if topic in df_fuzzy['话题'].values else None
    ranking_data.append([topic, original_rank, enhanced_rank, fuzzy_rank])

ranking_df = pd.DataFrame(ranking_data, columns=['话题', '原始方法排名', '增强方法排名', '模糊方法排名'])
ranking_df.to_csv('topic_ranking_comparison.csv', index=False, encoding='utf-8-sig')

print("方法对比图表已生成：method_comparison.png")
print("话题排名对比数据已生成：topic_ranking_comparison.csv")