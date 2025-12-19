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

# 用户代理列表，用于随机选择
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]

# 删除全局Cookie变量
# BILI_COOKIE = " "


def get_bilibili_cookie():
    """获取B站Cookie"""
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


def get_random_headers(bvid, cookie):
    """生成随机请求头"""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": f"https://www.bilibili.com/video/{bvid}",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache"
    }

    # 添加Cookie
    if cookie:
        headers["Cookie"] = cookie

    return headers


def get_bvid_info(bvid: str, cookie: str):
    """获取视频基本信息（含aid和标题）"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    try:
        print(f"正在获取视频信息: BV号 {bvid}...")
        response = requests.get(url, headers=get_random_headers(bvid, cookie), timeout=15)
        response.raise_for_status()

        data = response.json()
        if data.get('code') != 0:
            print(f"API返回错误: {data.get('message')}")
            return None, None

        video_info = data['data']
        aid = video_info['aid']
        title = video_info['title']
        print(f"视频标题: {title}")
        print(f"视频AID: {aid}")
        return aid, title
    except Exception as e:
        print(f"获取视频信息失败: {str(e)}")
        return None, None


def get_top_comments(aid: int, bvid: str, cookie: str):
    """获取置顶评论"""
    url = "https://api.bilibili.com/x/v2/reply/main"
    params = {
        "next": 0,  # 第一页
        "type": 1,  # 1=视频
        "oid": aid,  # 视频aid
        "mode": 3  # 3=热评模式
    }

    try:
        print("正在获取置顶评论...")
        headers = get_random_headers(bvid, cookie)

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=20
        )
        response.raise_for_status()

        data = response.json()

        if data.get('code') != 0:
            print(f"获取置顶评论失败: {data.get('message')}")
            return []

        # 获取置顶评论
        top_comments = []
        if 'upper' in data['data'] and data['data']['upper']:
            top_comment = data['data']['upper']
            top_comments.append(top_comment)

        return top_comments
    except Exception as e:
        print(f"获取置顶评论失败: {str(e)}")
        return []


def get_comments(aid: int, bvid: str, cookie: str, page=1, sort_mode=0):
    """使用标准API获取评论"""
    url = "https://api.bilibili.com/x/v2/reply"
    params = {
        "pn": page,  # 页码
        "type": 1,  # 1=视频
        "oid": aid,  # 视频aid
        "sort": sort_mode  # 0=按热度排序，2=按时间排序
    }

    try:
        sort_name = "热度" if sort_mode == 0 else "时间"
        print(f"正在获取第 {page} 页评论 (按{sort_name}排序)...")
        headers = get_random_headers(bvid, cookie)

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=20
        )
        response.raise_for_status()

        data = response.json()

        if data.get('code') != 0:
            print(f"API返回错误: {data.get('message')} (代码: {data.get('code')})")
            return None, 0

        # 返回评论数据和总评论数
        total = data['data'].get('page', {}).get('count', 0)
        return data, total
    except Exception as e:
        print(f"获取评论失败: {str(e)}")
        return None, 0


def format_time(timestamp):
    """将时间戳转换为可读格式"""
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return "时间解析错误"


def parse_comments_to_dataframe(data: dict, is_top=False):
    """将评论数据解析为DataFrame格式"""
    excel_data = []

    # 检查API返回数据是否有效
    if not data or 'data' not in data:
        print("API返回数据格式无效")
        return pd.DataFrame()

    # 处理置顶评论
    if is_top:
        for reply in data:
            main_comment = {
                "评论ID": reply['rpid'],
                "父评论ID": "置顶评论",
                "用户名": reply['member']['uname'],
                "评论内容": reply['content']['message'],
                "点赞数": reply['like'],
                "评论时间": format_time(reply['ctime']),
                "层级": "主评论",
                "回复数": reply['rcount'] if 'rcount' in reply else 0,
                "评论类型": "置顶"
            }
            excel_data.append(main_comment)
        return pd.DataFrame(excel_data)

    # 检查是否有评论数据
    if 'replies' not in data['data']:
        print("API返回数据中缺少'replies'字段")
        return pd.DataFrame()

    replies = data['data']['replies']
    if not replies:
        print("本页没有评论数据 (replies为空)")
        return pd.DataFrame()

    print(f"本页找到 {len(replies)} 条主评论")

    total_sub_replies = 0
    for reply in replies:
        # 主评论
        main_comment = {
            "评论ID": reply['rpid'],
            "父评论ID": "主评论",
            "用户名": reply['member']['uname'],
            "评论内容": reply['content']['message'],
            "点赞数": reply['like'],
            "评论时间": format_time(reply['ctime']),
            "层级": "主评论",
            "回复数": reply['rcount'] if 'rcount' in reply else 0,
            "评论类型": "普通"
        }
        excel_data.append(main_comment)

        # 子评论
        if 'replies' in reply and reply['replies']:
            total_sub_replies += len(reply['replies'])
            for sub_reply in reply['replies']:
                sub_comment = {
                    "评论ID": sub_reply['rpid'],
                    "父评论ID": reply['rpid'],
                    "用户名": sub_reply['member']['uname'],
                    "评论内容": sub_reply['content']['message'],
                    "点赞数": sub_reply['like'],
                    "评论时间": format_time(sub_reply['ctime']),
                    "层级": "子评论",
                    "回复数": "",
                    "评论类型": "回复"
                }
                excel_data.append(sub_comment)

    print(f"本页找到 {total_sub_replies} 条子评论")
    return pd.DataFrame(excel_data)


def save_to_excel(df, bvid, video_title):
    """保存DataFrame到Excel文件"""
    if df.empty:
        print("没有数据可保存")
        return None

    # 创建输出目录
    output_dir = "B站评论数据"
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

            # 设置列宽
            column_widths = {
                '评论ID': 12,
                '父评论ID': 12,
                '用户名': 15,
                '评论内容': 50,
                '点赞数': 10,
                '评论时间': 18,
                '层级': 8,
                '回复数': 8,
                '评论类型': 8
            }

            # 设置列宽
            for i, col in enumerate(df.columns):
                col_letter = get_column_letter(i + 1)
                if col in column_widths:
                    worksheet.column_dimensions[col_letter].width = column_widths[col]
                else:
                    worksheet.column_dimensions[col_letter].width = 15

            # 设置标题行格式
            for cell in worksheet[1]:
                cell.font = openpyxl.styles.Font(bold=True)
                cell.alignment = openpyxl.styles.Alignment(horizontal='center')

        print(f"Excel文件已保存: {os.path.abspath(filename)}")
        return filename
    except Exception as e:
        print(f"保存Excel文件失败: {str(e)}")
        return None


def print_summary(df, total_comments):
    """打印数据摘要"""
    if df.empty:
        print("没有数据可汇总")
        return

    main_comments = df[df['层级'] == '主评论']
    top_comments = df[df['评论类型'] == '置顶']

    print("\n" + "=" * 60)
    print("数据汇总:")
    print(f"视频总评论数: {total_comments} 条")
    print(f"实际抓取评论数: {len(df)} 条")
    print(f"主评论数: {len(main_comments)} 条")
    print(f"置顶评论数: {len(top_comments)} 条")

    if not df.empty:
        # 点赞最多的前20条评论
        top_likes = df.nlargest(20, '点赞数')
        print("\n点赞最高的评论:")
        for i, row in top_likes.iterrows():
            comment_type = "置顶" if row['评论类型'] == '置顶' else "普通"
            print(f"[{comment_type}] [{row['点赞数']}赞] {row['用户名']}: {row['评论内容'][:50]}...")

    # 时间范围
    if '评论时间' in df.columns and not df['评论时间'].empty:
        min_time = df['评论时间'].min()
        max_time = df['评论时间'].max()
        print(f"\n评论时间范围: {min_time} 至 {max_time}")


def main():
    """主函数"""
    print("=" * 60)
    print("B站视频评论抓取工具 (完整版)")
    print("=" * 60)

    # 获取Cookie
    cookie = get_bilibili_cookie()
    if not cookie:
        print("❌ 未提供Cookie，程序退出")
        return

    # 配置参数
    bvid = input("请输入要抓取评论的B站视频BV号: ").strip()
    if not bvid:
        print("❌ 未提供BV号，程序退出")
        return

    max_pages = 200  # 抓取更多页数获取完整评论
    sort_mode = 0  # 0=按热度排序，2=按时间排序

    print(f"\n目标视频: https://www.bilibili.com/video/{bvid}")
    print(f"抓取页数: {max_pages}")
    print(f"排序方式: {'热度' if sort_mode == 0 else '时间'}")

    # 获取视频ID和标题
    aid, video_title = get_bvid_info(bvid, cookie)
    if not aid:
        print("无法获取视频信息，请检查BV号或网络连接")
        return

    # 抓取评论数据
    all_comments_df = pd.DataFrame()
    total_comments = 0

    # 1. 获取置顶评论
    top_comments = get_top_comments(aid, bvid, cookie)
    if top_comments:
        top_df = parse_comments_to_dataframe(top_comments, is_top=True)
        all_comments_df = pd.concat([all_comments_df, top_df], ignore_index=True)
        print(f"已获取 {len(top_df)} 条置顶评论")

    # 2. 获取普通评论
    for page in range(1, max_pages + 1):
        try:
            start_time = time.time()
            data, page_total = get_comments(aid, bvid, cookie, page, sort_mode)

            # 记录总评论数
            if page == 1 and page_total > 0:
                total_comments = page_total
                print(f"视频总评论数: {total_comments} 条")

            # 如果API返回错误，停止抓取
            if data is None:
                print(f"第 {page} 页获取失败，停止抓取")
                break

            # 解析评论数据
            page_df = parse_comments_to_dataframe(data)

            # 如果本页没有数据，停止抓取
            if page_df.empty:
                print(f"第 {page} 页无评论数据，停止抓取")
                break

            all_comments_df = pd.concat([all_comments_df, page_df], ignore_index=True)
            elapsed = time.time() - start_time

            # 计算进度
            collected = len(all_comments_df)
            progress = min(100, collected / min(total_comments, max_pages * 20) * 100)
            print(f"第 {page} 页处理完成, 获取 {len(page_df)} 条评论, 总进度: {progress:.1f}%, 耗时 {elapsed:.2f} 秒")

            # 随机延迟，避免触发反爬
            delay = random.uniform(1.5, 3.0)
            time.sleep(delay)

            # 每10页保存一次进度
            if page % 10 == 0:
                print(f"已处理 {page} 页，累计 {collected} 条评论，保存临时进度...")
                temp_file = f"temp_{bvid}_page_{page}.xlsx"
                all_comments_df.to_excel(temp_file, index=False)
                print(f"临时进度已保存至: {temp_file}")

        except Exception as e:
            print(f"处理第 {page} 页时出错: {str(e)}")
            # 发生错误时等待更长时间
            time.sleep(5.0)
            continue

    # 检查是否获取到数据
    if all_comments_df.empty:
        print("\n未抓取到任何评论数据，可能原因：")
        print("1. 视频没有评论")
        print("2. API限制未登录用户")
        print("3. 反爬机制阻止了请求")
        print("4. API路径或参数已变更")
        print("5. 提供的Cookie无效或已过期")
        return

    # 添加层级标识列
    all_comments_df.insert(0, '层级标识', all_comments_df['层级'].apply(
        lambda x: "▶" if x == "主评论" else "└└─"
    ))

    # 排序：按点赞数降序排列
    all_comments_df.sort_values(by='点赞数', ascending=False, inplace=True)

    # 保存到Excel
    saved_path = save_to_excel(all_comments_df, bvid, video_title)

    # 打印摘要信息
    print_summary(all_comments_df, total_comments)

    # 完成提示
    if saved_path:
        print("\n" + "=" * 60)
        print("操作完成!")
        print(f"Excel文件已保存至: {os.path.abspath(saved_path)}")

        # 在Windows系统中尝试打开文件
        if sys.platform.startswith('win'):
            try:
                os.startfile(os.path.abspath(saved_path))
                print("已尝试自动打开Excel文件")
            except:
                print("无法自动打开文件，请手动查看")
    else:
        print("保存文件失败，请检查错误信息")

    # 防止PyCharm运行完成后立即关闭窗口
    input("\n按Enter键退出...")


if __name__ == "__main__":
    # 检查openpyxl是否安装
    try:
        import openpyxl
    except ImportError:
        print("未安装 openpyxl，正在尝试安装...")
        try:
            import subprocess

            subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
            import openpyxl

            print("openpyxl 安装成功")
        except Exception as e:
            print(f"安装 openpyxl 失败: {str(e)}")
            print("请手动运行: pip install openpyxl")
            exit(1)

    main()