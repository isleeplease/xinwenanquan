#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从CSV文件中提取BV号并爬取对应视频的评论
"""

import csv
import os
import sys
import time
import pandas as pd
from pathlib import Path
import importlib.util
from io import StringIO

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


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

def extract_bv_numbers(csv_file_path):
    """从CSV文件中提取所有BV号"""
    bv_numbers = []
    
    print(f"正在读取CSV文件: {csv_file_path}")
    
    try:
        # 使用pandas读取CSV文件
        df = pd.read_csv(csv_file_path, encoding='utf-8')
        
        # 提取BV号列
        if 'BV号' in df.columns:
            bv_numbers = df['BV号'].tolist()
        elif 'BV号' in df.columns:
            bv_numbers = df['BV号'].tolist()
        else:
            print("错误: CSV文件中未找到'BV号'列")
            return []
            
        print(f"成功提取到 {len(bv_numbers)} 个BV号")
        return bv_numbers
        
    except Exception as e:
        print(f"读取CSV文件时出错: {e}")
        return []

def crawl_comments_for_bv(bv_number):
    """为单个BV号爬取评论"""
    try:
        print(f"正在爬取BV号 {bv_number} 的评论...")
        
        # 使用subprocess调用自动爬虫
        import subprocess
        import sys
        
        crawler_path = os.path.join(os.path.dirname(__file__), "auto_comments_crawler.py")
        result = subprocess.run([sys.executable, crawler_path, bv_number], 
                              capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print(f"成功爬取BV号 {bv_number} 的评论")
            return True
        else:
            print(f"爬取BV号 {bv_number} 的评论时出错: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"爬取BV号 {bv_number} 的评论时出错: {e}")
        return False

def find_generated_files():
    """查找生成的评论文件"""
    try:
        output_dir = os.path.join(os.path.dirname(__file__), "B站评论数据")
        if not os.path.exists(output_dir):
            print("未找到评论数据目录")
            return []
        
        # 查找所有Excel文件
        excel_files = []
        for file in os.listdir(output_dir):
            if file.endswith(".xlsx") and "完整评论" in file:
                excel_files.append(os.path.join(output_dir, file))
        
        print(f"找到 {len(excel_files)} 个评论文件")
        return excel_files
        
    except Exception as e:
        print(f"查找生成文件时出错: {e}")
        return []

def merge_comment_files(final_output="final_up_comments.xlsx"):
    """合并所有评论文件到一个Excel文件"""
    try:
        print("正在合并所有评论文件...")
        
        # 查找生成的评论文件
        excel_files = find_generated_files()
        
        if not excel_files:
            print("未找到任何评论文件")
            return False
            
        print(f"找到 {len(excel_files)} 个评论文件")
        
        # 读取所有Excel文件并合并
        all_data = []
        for excel_file in excel_files:
            try:
                df = pd.read_excel(excel_file)
                # 添加视频BV号列
                bv_number = os.path.basename(excel_file).split("】")[0].split("【")[1]
                df['来源视频BV号'] = bv_number
                all_data.append(df)
                print(f"已读取: {os.path.basename(excel_file)} ({len(df)} 条记录)")
            except Exception as e:
                print(f"读取文件 {excel_file} 时出错: {e}")
        
        if not all_data:
            print("没有成功读取任何评论数据")
            return False
            
        # 合并所有数据
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"合并后总共有 {len(combined_df)} 条评论")
        
        # 保存到Excel文件
        output_path = os.path.join(os.path.dirname(__file__), final_output)
        combined_df.to_excel(output_path, index=False)
        print(f"评论数据已保存到: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"合并评论文件时出错: {e}")
        return False

def main():
    print("=" * 60)
    print("B站视频评论批量爬取工具")
    print("=" * 60)
    
    # CSV文件路径
    csv_file_path = os.path.join(os.path.dirname(__file__), "bilibili_results_20251219_153805.csv")
    
    # 检查CSV文件是否存在
    if not os.path.exists(csv_file_path):
        print(f"错误: CSV文件不存在: {csv_file_path}")
        return
    
    # 提取BV号
    bv_numbers = extract_bv_numbers(csv_file_path)
    
    if not bv_numbers:
        print("未能提取到任何BV号，程序退出")
        return
    
    print(f"\n开始处理 {len(bv_numbers)} 个视频的评论爬取任务")
    
    # 爬取每个BV号的评论
    success_count = 0
    failed_bv = []
    
    for i, bv_number in enumerate(bv_numbers, 1):
        print(f"\n[{i}/{len(bv_numbers)}] 处理BV号: {bv_number}")
        
        # 爬取评论
        if crawl_comments_for_bv(bv_number):
            success_count += 1
            print(f"✓ 成功爬取 {bv_number} 的评论")
        else:
            failed_bv.append(bv_number)
            print(f"✗ 爬取 {bv_number} 的评论失败")
        
        # 添加延迟避免请求过快
        if i < len(bv_numbers):
            print("等待3秒后继续...")
            time.sleep(3)
    
    # 输出统计结果
    print("\n" + "=" * 60)
    print("爬取任务完成统计")
    print("=" * 60)
    print(f"总计视频数: {len(bv_numbers)}")
    print(f"成功爬取: {success_count}")
    print(f"失败数量: {len(failed_bv)}")
    
    if failed_bv:
        print("失败的BV号:")
        for bv in failed_bv:
            print(f"  - {bv}")
    
    # 合并评论文件
    print("\n开始合并评论文件...")
    if merge_comment_files():
        print("评论文件合并完成")
    else:
        print("评论文件合并失败")

if __name__ == "__main__":
    main()