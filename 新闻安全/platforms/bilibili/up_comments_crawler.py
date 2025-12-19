#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站UP主评论批量爬取工具
功能：根据UP主名称搜索其视频，并批量爬取所有视频的评论
"""

import os
import sys
import time
import json
import csv
import pandas as pd
from datetime import datetime
import subprocess
import importlib.util

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_bilibili_cookie():
    """获取B站Cookie"""
    # 尝试从.env文件读取cookie
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('BILI_COOKIE='):
                    return line.strip().split('=', 1)[1]
    
    # 如果.env文件中没有cookie，则要求用户输入
    print("=" * 60)
    print("为了绕过B站的反爬机制，需要提供您的B站Cookie")
    print("请按以下步骤获取Cookie：")
    print("1. 登录B站网页版 (https://www.bilibili.com)")
    print("2. 按F12打开开发者工具")
    print("3. 进入'网络'(Network)选项卡")
    print("4. 刷新页面")
    print("5. 找到任意请求，复制'请求头'中的Cookie值")
    print("6. 格式通常为: SESSDATA=xxxxxx; bili_jct=xxxxxx")
    print("=" * 60)

    cookie = input("请输入您的B站Cookie（粘贴后按Enter）: ").strip()
    return cookie


def collect_up_videos(up_name, start_date, end_date, max_videos=100):
    """
    收集UP主的视频列表
    :param up_name: UP主名称
    :param start_date: 开始日期 (YYYY-MM-DD)
    :param end_date: 结束日期 (YYYY-MM-DD)
    :param max_videos: 最大视频数量
    :return: 视频列表 [{'BV号': 'BVxxx', '标题': 'xxx', ...}]
    """
    print(f"开始收集UP主 '{up_name}' 的视频...")
    
    # 修改interaction_data.py的配置
    interaction_file = os.path.join(os.path.dirname(__file__), 'interaction_data.py')
    
    if not os.path.exists(interaction_file):
        print("错误：找不到interaction_data.py文件")
        return []
    
    # 读取原文件内容
    with open(interaction_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修改配置参数
    # 更新UP主名称
    content = content.replace('KEYWORDS = ["UP主名字"]', f'KEYWORDS = ["{up_name}"]')
    
    # 更新时间范围
    content = content.replace('START_DATE = "2024-01-01"', f'START_DATE = "{start_date}"')
    content = content.replace('END_DATE = "2025-12-31"', f'END_DATE = "{end_date}"')
    
    # 更新结果数量
    content = content.replace('RESULTS_PER_KEYWORD = 900', f'RESULTS_PER_KEYWORD = {max_videos}')
    
    # 写回文件
    with open(interaction_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("已更新配置，开始运行视频收集...")
    
    # 运行interaction_data.py
    try:
        result = subprocess.run([
            sys.executable, 
            os.path.join(os.path.dirname(__file__), 'interaction_data.py')
        ], capture_output=True, text=True, encoding='utf-8')
        
        print("视频收集完成")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("stderr:", result.stderr)
            
        # 查找生成的CSV文件
        csv_files = []
        for file in os.listdir('.'):
            if file.startswith('bilibili_results_') and file.endswith('.csv'):
                csv_files.append(file)
        
        if not csv_files:
            print("未找到生成的CSV文件")
            return []
        
        # 获取最新的CSV文件
        latest_csv = max(csv_files, key=os.path.getctime)
        print(f"找到CSV文件: {latest_csv}")
        
        # 读取CSV文件中的视频信息
        videos = []
        with open(latest_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('BV号') and row['BV号'] != '未知':
                    videos.append({
                        'BV号': row['BV号'],
                        '标题': row.get('标题', ''),
                        '发布时间': row.get('发布时间', ''),
                        'URL': row.get('URL', '')
                    })
        
        print(f"共收集到 {len(videos)} 个视频")
        return videos[:max_videos]
        
    except Exception as e:
        print(f"运行视频收集时出错: {str(e)}")
        return []


def crawl_video_comments(bvid, cookie, output_dir="UP主评论数据"):
    """
    爬取单个视频的评论
    :param bvid: 视频BV号
    :param cookie: B站Cookie
    :param output_dir: 输出目录
    :return: 是否成功
    """
    print(f"开始爬取视频 {bvid} 的评论...")
    
    # 准备comments_crawler.py的输入
    comments_file = os.path.join(os.path.dirname(__file__), 'comments_crawler.py')
    
    if not os.path.exists(comments_file):
        print("错误：找不到comments_crawler.py文件")
        return False
    
    try:
        # 运行comments_crawler.py并自动输入参数
        process = subprocess.Popen([
            sys.executable, comments_file
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
           text=True, encoding='utf-8')
        
        # 自动输入cookie和BV号
        inputs = f"{cookie}\n{bvid}\n"
        stdout, stderr = process.communicate(input=inputs, timeout=300)  # 5分钟超时
        
        print(f"视频 {bvid} 评论爬取完成")
        if stdout:
            print(stdout)
        if stderr:
            print("stderr:", stderr)
            
        return True
        
    except subprocess.TimeoutExpired:
        print(f"视频 {bvid} 评论爬取超时")
        return False
    except Exception as e:
        print(f"爬取视频 {bvid} 评论时出错: {str(e)}")
        return False


def merge_excel_files(up_name, output_dir="UP主评论数据"):
    """
    合并所有Excel文件
    :param up_name: UP主名称
    :param output_dir: 输出目录
    """
    if not os.path.exists(output_dir):
        print(f"目录 {output_dir} 不存在")
        return
    
    # 查找所有Excel文件
    excel_files = []
    for file in os.listdir(output_dir):
        if file.endswith('_完整评论.xlsx'):
            excel_files.append(os.path.join(output_dir, file))
    
    if not excel_files:
        print("未找到评论Excel文件")
        return
    
    print(f"找到 {len(excel_files)} 个Excel文件，开始合并...")
    
    # 合并所有数据
    all_data = []
    for file in excel_files:
        try:
            df = pd.read_excel(file)
            # 添加视频标识列
            video_bvid = os.path.basename(file).split('【')[1].split('】')[0] if '【' in file and '】' in file else '未知'
            df['视频BV号'] = video_bvid
            all_data.append(df)
        except Exception as e:
            print(f"读取文件 {file} 时出错: {str(e)}")
    
    if not all_data:
        print("没有数据可合并")
        return
    
    # 合并所有数据框
    merged_df = pd.concat(all_data, ignore_index=True)
    
    # 保存合并后的文件
    output_file = os.path.join(output_dir, f'{up_name}_全部评论_合并版.xlsx')
    merged_df.to_excel(output_file, index=False)
    print(f"合并完成，文件保存至: {output_file}")


def main(up_name=None, start_date=None, end_date=None, max_videos=None):
    print("=" * 60)
    print("B站UP主评论批量爬取工具")
    print("=" * 60)
    
    # 获取Cookie
    cookie = get_bilibili_cookie()
    if not cookie:
        print("未提供Cookie，程序退出")
        return
    
    # 获取参数，如果未提供则询问用户
    if not up_name:
        up_name = input("请输入UP主名称: ").strip()
    if not up_name:
        print("未提供UP主名称，程序退出")
        return
    
    if not start_date:
        start_date = input("请输入开始日期 (YYYY-MM-DD，默认2024-01-01): ").strip() or "2024-01-01"
    if not end_date:
        end_date = input("请输入结束日期 (YYYY-MM-DD，默认今天): ").strip() or datetime.now().strftime("%Y-%m-%d")
    if not max_videos:
        max_videos_input = input("请输入最大爬取视频数 (默认100): ").strip()
        max_videos = int(max_videos_input) if max_videos_input.isdigit() else 100
    else:
        max_videos = int(max_videos)
    
    print(f"\n配置信息:")
    print(f"UP主: {up_name}")
    print(f"时间范围: {start_date} 至 {end_date}")
    print(f"最大视频数: {max_videos}")
    
    # 收集UP主的视频
    videos = collect_up_videos(up_name, start_date, end_date, max_videos)
    if not videos:
        print("未能收集到视频信息")
        return
    
    print(f"\n开始批量爬取 {len(videos)} 个视频的评论...")
    
    # 爬取每个视频的评论
    success_count = 0
    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] 处理视频: {video['BV号']} - {video['标题']}")
        
        # 检查是否已经爬取过该视频的评论
        output_dir = "B站评论数据"
        expected_file = os.path.join(output_dir, f"【{video['BV号']}】*_完整评论.xlsx")
        
        # 检查是否存在匹配的文件
        import glob
        existing_files = glob.glob(expected_file)
        if existing_files:
            print(f"视频 {video['BV号']} 的评论已存在，跳过")
            success_count += 1
            continue
        
        # 爬取评论
        if crawl_video_comments(video['BV号'], cookie, output_dir):
            success_count += 1
            print(f"视频 {video['BV号']} 评论爬取成功")
        else:
            print(f"视频 {video['BV号']} 评论爬取失败")
        
        # 添加延迟避免被封
        time.sleep(3)
    
    print(f"\n评论爬取完成: {success_count}/{len(videos)} 个视频成功")
    
    # 合并所有评论文件
    print("\n开始合并所有评论文件...")
    merge_excel_files(up_name)
    
    print("\n所有任务完成!")


if __name__ == "__main__":
    main()