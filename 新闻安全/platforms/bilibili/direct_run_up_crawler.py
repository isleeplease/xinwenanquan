#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接运行UP主评论爬取，避免编码问题
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_bilibili_cookie():
    """从.env文件获取B站Cookie"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('BILI_COOKIE='):
                    return line.strip().split('=', 1)[1]
    return ""

def main():
    print("=" * 60)
    print("直接运行UP主评论爬取工具")
    print("=" * 60)
    
    # 设置参数
    up_name = "哔哩哔哩英雄联盟赛事"
    start_date = "2025-10-14"
    end_date = "2025-11-09"
    max_videos = 100
    
    print(f"配置信息:")
    print(f"UP主: {up_name}")
    print(f"时间范围: {start_date} 至 {end_date}")
    print(f"最大视频数: {max_videos}")
    
    # 修改interaction_data.py的配置
    interaction_file = os.path.join(os.path.dirname(__file__), 'interaction_data.py')
    
    if os.path.exists(interaction_file):
        # 读取原文件内容
        with open(interaction_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修改配置参数
        content = content.replace('KEYWORDS = ["哔哩哔哩英雄联盟赛事"]', f'KEYWORDS = ["{up_name}"]')
        content = content.replace('START_DATE = "2025-10-14"', f'START_DATE = "{start_date}"')
        content = content.replace('END_DATE = "2025-11-09"', f'END_DATE = "{end_date}"')
        content = content.replace('RESULTS_PER_KEYWORD = 100', f'RESULTS_PER_KEYWORD = {max_videos}')
        
        # 写回文件
        with open(interaction_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("已更新配置文件")
    else:
        print("错误：找不到interaction_data.py文件")
        return
    
    # 直接调用up_comments_crawler.py的main函数
    try:
        sys.path.append(os.path.dirname(__file__))
        import up_comments_crawler
        
        # 调用main函数并传递参数
        up_comments_crawler.main(up_name=up_name, start_date=start_date, end_date=end_date, max_videos=max_videos)
        
    except Exception as e:
        print(f"运行出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()