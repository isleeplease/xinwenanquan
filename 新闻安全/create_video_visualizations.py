import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import matplotlib.dates as mdates

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 读取视频数据
df_videos = pd.read_csv('platforms/bilibili/bilibili_results_20251219_153805.csv')

# 转换日期格式
df_videos['发布时间'] = pd.to_datetime(df_videos['发布时间'])
df_videos = df_videos.dropna(subset=['标题'])  # 移除标题为空的行

# 创建图表
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle('电竞赛事视频数据分析', fontsize=16, fontweight='bold')

# 1. 播放量和评论数的时间序列
daily_stats = df_videos.groupby(df_videos['发布时间'].dt.date).agg({
    '播放量': 'sum',
    '评论数': 'sum'
}).reset_index()

daily_stats['发布时间'] = pd.to_datetime(daily_stats['发布时间'])

axes[0, 0].plot(daily_stats['发布时间'], daily_stats['播放量'], marker='o', label='播放量')
axes[0, 0].set_xlabel('日期')
axes[0, 0].set_ylabel('播放量')
axes[0, 0].set_title('每日播放量趋势')
axes[0, 0].tick_params(axis='x', rotation=45)
axes[0, 0].grid(True, alpha=0.3)

ax_twin = axes[0, 0].twinx()
ax_twin.plot(daily_stats['发布时间'], daily_stats['评论数'], marker='s', color='orange', label='评论数')
ax_twin.set_ylabel('评论数')

# 2. 播放量 vs 评论数散点图
axes[0, 1].scatter(df_videos['播放量'], df_videos['评论数'], alpha=0.6)
axes[0, 1].set_xlabel('播放量')
axes[0, 1].set_ylabel('评论数')
axes[0, 1].set_title('播放量 vs 评论数')
axes[0, 1].grid(True, alpha=0.3)

# 添加趋势线
z = np.polyfit(df_videos['播放量'], df_videos['评论数'], 1)
p = np.poly1d(z)
axes[0, 1].plot(df_videos['播放量'], p(df_videos['播放量']), "r--", alpha=0.8)

# 3. Top 10 视频评论数
top_videos_comments = df_videos.nlargest(10, '评论数')
bars = axes[1, 0].barh(range(len(top_videos_comments)), top_videos_comments['评论数'], color='lightblue')
axes[1, 0].set_yticks(range(len(top_videos_comments)))
axes[1, 0].set_yticklabels([title[:30] + '...' if len(title) > 30 else title for title in top_videos_comments['标题']])
axes[1, 0].set_xlabel('评论数')
axes[1, 0].set_title('Top 10 视频 (按评论数)')
axes[1, 0].invert_yaxis()

# 4. 视频类型分布 (根据标题关键词)
def categorize_video(title):
    if '决赛' in title:
        return '决赛'
    elif '淘汰赛' in title:
        return '淘汰赛'
    elif '小组赛' in title:
        return '小组赛'
    elif '采访' in title:
        return '选手采访'
    elif 'TOP5' in title:
        return '精彩集锦'
    else:
        return '其他'

df_videos['类型'] = df_videos['标题'].apply(categorize_video)
type_counts = df_videos['类型'].value_counts()

axes[1, 1].pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%', startangle=90)
axes[1, 1].set_title('视频类型分布')

plt.tight_layout()
plt.savefig('video_analysis_visualizations.png', dpi=300, bbox_inches='tight')
plt.close()

print("视频数据分析图表已生成：video_analysis_visualizations.png")