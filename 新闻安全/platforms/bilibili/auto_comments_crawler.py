#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动爬取B站视频评论的脚本
"""

import requests
import json
import time
import pandas as pd
from datetime import datetime
import os
import sys
import traceback
import openpyxl
from openpyxl.utils import get_column_letter
import random
import re

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# 用户代理列表，用于随机选择
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]


def get_bilibili_cookie():
    """获取B站Cookie"""
    # 尝试从.env文件读取cookie
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('BILI_COOKIE='):
                    return line.strip().split('=', 1)[1]
    return ""


def get_random_headers(bvid, cookie=""):
    """生成随机请求头"""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": f"https://www.bilibili.com/video/{bvid}",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
    }
    
    if cookie:
        headers["Cookie"] = cookie
        
    return headers


def get_bvid_info(bvid, cookie=""):
    """
    获取视频信息(AID和标题)
    :param bvid: BV号
    :param cookie: B站Cookie
    :return: (aid, title) 或 (None, None)
    """
    try:
        url = f"https://api.bilibili.com/x/web-interface/view"
        params = {"bvid": bvid}
        headers = get_random_headers(bvid, cookie)
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data.get("code") == 0:
            aid = data["data"]["aid"]
            title = data["data"]["title"]
            return aid, title
        else:
            print(f"获取视频信息失败: {data.get('message', '未知错误')}")
            return None, None
            
    except Exception as e:
        print(f"获取视频信息时出错: {e}")
        return None, None


def parse_comment_data(comment_data):
    """
    解析评论数据为DataFrame格式
    :param comment_data: 评论数据字典
    :return: DataFrame
    """
    comments = []
    
    # 主评论
    if "replies" in comment_data and comment_data["replies"]:
        for reply in comment_data["replies"]:
            # 主评论信息
            main_comment = {
                "层级": "主评论",
                "用户名": reply.get("member", {}).get("uname", ""),
                "性别": reply.get("member", {}).get("sex", ""),
                "评论时间": datetime.fromtimestamp(reply.get("ctime", 0)).strftime('%Y-%m-%d %H:%M:%S') if reply.get("ctime") else "",
                "点赞数": reply.get("like", 0),
                "评论内容": reply.get("content", {}).get("message", ""),
                "评论类型": "置顶" if reply.get("is_up_top", False) else "普通",
                "用户等级": reply.get("member", {}).get("level_info", {}).get("current_level", 0),
                "用户头像": reply.get("member", {}).get("avatar", ""),
                "用户ID": reply.get("member", {}).get("mid", ""),
                "回复数": reply.get("rcount", 0),
                "评论ID": reply.get("rpid", "")
            }
            comments.append(main_comment)
            
            # 子评论（回复）
            if "replies" in reply and reply["replies"]:
                for sub_reply in reply["replies"]:
                    sub_comment = {
                        "层级": "子评论",
                        "用户名": sub_reply.get("member", {}).get("uname", ""),
                        "性别": sub_reply.get("member", {}).get("sex", ""),
                        "评论时间": datetime.fromtimestamp(sub_reply.get("ctime", 0)).strftime('%Y-%m-%d %H:%M:%S') if sub_reply.get("ctime") else "",
                        "点赞数": sub_reply.get("like", 0),
                        "评论内容": sub_reply.get("content", {}).get("message", ""),
                        "评论类型": "普通",
                        "用户等级": sub_reply.get("member", {}).get("level_info", {}).get("current_level", 0),
                        "用户头像": sub_reply.get("member", {}).get("avatar", ""),
                        "用户ID": sub_reply.get("member", {}).get("mid", ""),
                        "回复数": 0,
                        "评论ID": sub_reply.get("rpid", "")
                    }
                    comments.append(sub_comment)
                    
    return pd.DataFrame(comments)


def get_video_comments(bvid, cookie="", max_pages=50, sort_mode=0):
    """
    获取视频评论
    :param bvid: BV号
    :param cookie: B站Cookie
    :param max_pages: 最大页数
    :param sort_mode: 排序模式 (0=按热度, 2=按时间)
    :return: DataFrame
    """
    print(f"开始获取视频 {bvid} 的评论...")
    
    # 获取视频信息
    aid, video_title = get_bvid_info(bvid, cookie)
    if not aid:
        print("无法获取视频信息")
        return pd.DataFrame()
        
    print(f"视频标题: {video_title}")
    
    all_comments = []
    page = 1
    
    while page <= max_pages:
        try:
            print(f"正在获取第 {page} 页评论...")
            
            # 构造API请求
            url = "https://api.bilibili.com/x/v2/reply"
            params = {
                "pn": page,
                "type": 1,
                "oid": aid,
                "sort": sort_mode
            }
            
            headers = get_random_headers(bvid, cookie)
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 检查是否有评论数据
                if data.get("code") == 0 and data.get("data") and data["data"].get("replies"):
                    # 解析评论数据
                    df = parse_comment_data(data["data"])
                    if not df.empty:
                        all_comments.append(df)
                        print(f"第 {page} 页获取到 {len(df)} 条评论")
                    else:
                        print(f"第 {page} 页无评论数据")
                        break
                else:
                    print(f"第 {page} 页无评论数据或请求失败")
                    break
            else:
                print(f"请求失败，状态码: {response.status_code}")
                break
                
            page += 1
            # 添加延迟避免请求过快
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            print(f"处理第 {page} 页时出错: {e}")
            break
    
    if all_comments:
        # 合并所有评论数据
        combined_df = pd.concat(all_comments, ignore_index=True)
        print(f"总共获取到 {len(combined_df)} 条评论")
        return combined_df
    else:
        print("未获取到任何评论数据")
        return pd.DataFrame()


def save_to_excel(df, bvid, video_title):
    """保存DataFrame到Excel文件"""
    if df.empty:
        print("没有数据可保存")
        return None

    # 创建输出目录
    output_dir = os.path.join(os.path.dirname(__file__), "B站评论数据")
    os.makedirs(output_dir, exist_ok=True)

    # 清理文件名中的非法字符
    clean_title = re.sub(r'[\\/*?:"<>|]', '', video_title).strip()
    if not clean_title:
        clean_title = "无标题"

    # 缩短文件名长度
    if len(clean_title) > 50:
        clean_title = clean_title[:50] + "..."

    filename = f"{output_dir}/【{bvid}】{clean_title}_完整评论.xlsx"

    try:
        # 使用openpyxl引擎
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='评论数据')

            # 获取工作表
            workbook = writer.book
            worksheet = writer.sheets['评论数据']

            # 自动调整列宽
            for column in worksheet.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                        
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        print(f"评论数据已保存至: {filename}")
        return filename
        
    except Exception as e:
        print(f"保存Excel文件时出错: {e}")
        return None


def crawl_comments(bvid):
    """爬取指定BV号的评论"""
    # 获取Cookie
    cookie = get_bilibili_cookie()
    
    # 获取评论数据
    df = get_video_comments(bvid, cookie)
    
    if not df.empty:
        # 获取视频标题
        aid, video_title = get_bvid_info(bvid, cookie)
        if not video_title:
            video_title = "未知视频"
            
        # 保存到Excel
        saved_path = save_to_excel(df, bvid, video_title)
        return saved_path
    else:
        print("未获取到评论数据")
        return None


def main():
    """主函数"""
    print("=" * 60)
    print("B站视频评论自动抓取工具")
    print("=" * 60)
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python auto_comments_crawler.py <BV号>")
        return
    
    bvid = sys.argv[1].strip()
    print(f"目标视频BV号: {bvid}")
    
    # 爬取评论
    result = crawl_comments(bvid)
    
    if result:
        print(f"\n评论数据已保存至: {result}")
    else:
        print("\n评论爬取失败")


if __name__ == "__main__":
    main()