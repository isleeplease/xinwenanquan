#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化运行UP主评论爬取脚本
针对特定UP主和时间范围
"""

import subprocess
import sys
import os

def run_up_comments_crawler():
    # 设置参数
    up_name = "哔哩哔哩英雄联盟赛事"
    start_date = "2025-10-14"
    end_date = "2025-11-09"
    max_videos = "100"
    
    # 从.env文件读取cookie
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    cookie = ""
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('BILI_COOKIE='):
                    cookie = line.strip().split('=', 1)[1]
                    break
    
    if not cookie:
        print("错误：未找到BILI_COOKIE，请确保.env文件中包含有效的Cookie")
        return
    
    # 准备输入
    inputs = f"{cookie}\n{up_name}\n{start_date}\n{end_date}\n{max_videos}\n"
    
    # 运行主爬取脚本
    try:
        process = subprocess.Popen([
            sys.executable, 
            os.path.join(os.path.dirname(__file__), 'up_comments_crawler.py')
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
           text=True, encoding='utf-8')
        
        stdout, stderr = process.communicate(input=inputs, timeout=3600)  # 1小时超时
        
        print("STDOUT:")
        print(stdout)
        
        if stderr:
            print("STDERR:")
            print(stderr)
            
        print(f"进程退出码: {process.returncode}")
        
    except subprocess.TimeoutExpired:
        print("任务超时")
    except Exception as e:
        print(f"运行出错: {str(e)}")

if __name__ == "__main__":
    run_up_comments_crawler()