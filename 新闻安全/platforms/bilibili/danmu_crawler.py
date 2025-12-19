import asyncio
import aiohttp
import random
import xml.etree.ElementTree as ET
import pandas as pd
import os
import time
import datetime
import numpy as np


def get_random_user_agent():
    """生成随机的 User-Agent"""
    browsers = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
    ]
    return random.choice(browsers)


async def fetch_cid(bvid):
    """获取视频的 CID（弹幕 ID）"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"

    headers = {
        "User-Agent": get_random_user_agent(),
        "Referer": f"https://www.bilibili.com/video/{bvid}",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "DNT": "1"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            if response.status != 200:
                error_msg = f"获取CID失败: 状态码 {response.status}"
                print(error_msg)
                raise ValueError(error_msg)

            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                content = await response.text()
                error_msg = f"获取CID失败: 非JSON响应 ({content_type})"
                print(f"{error_msg}\n响应内容: {content[:300]}")
                raise ValueError(error_msg)

            data = await response.json()
            if data.get("code") == 0:
                return data["data"]["cid"]
            else:
                error_msg = f"获取CID失败: {data.get('message', '未知错误')}"
                print(error_msg)
                raise ValueError(error_msg)


async def fetch_danmu(cid):
    """根据 CID 获取弹幕，并提取时间点和弹幕内容"""
    url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"

    headers = {
        "User-Agent": get_random_user_agent(),
        "Referer": "https://www.bilibili.com",
        "Origin": "https://www.bilibili.com",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "DNT": "1"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            if response.status != 200:
                error_msg = f"获取弹幕失败: 状态码 {response.status}"
                print(error_msg)
                raise ValueError(error_msg)

            content = await response.text(encoding='utf-8')

            # 使用XML解析器解析弹幕数据
            try:
                root = ET.fromstring(content)
            except ET.ParseError:
                # 尝试修复XML格式错误
                content = content.replace('</i>', '').replace('</d>', '')
                root = ET.fromstring(content)

            # 创建一个列表来存储弹幕数据 (时间点, 弹幕内容)
            danmu_data = []

            # 遍历所有<d>标签
            for d in root.findall('d'):
                # 解析弹幕属性 (p属性包含时间等信息)
                p_attr = d.get('p').split(',')
                if len(p_attr) >= 5:  # 确保有足够的字段
                    try:
                        # 第一个属性是弹幕在视频中出现的时间点（秒）
                        time_point = float(p_attr[0])

                        # 新增：解析发送时间（第5个字段是Unix时间戳）
                        send_timestamp = int(p_attr[4])
                        # 转换为可读的日期时间格式
                        send_time = datetime.datetime.fromtimestamp(send_timestamp).strftime('%Y-%m-%d %H:%M:%S')

                        # 添加弹幕数据（包含发送时间）
                        danmu_data.append((time_point, d.text, send_time))
                    except (ValueError, IndexError) as e:
                        # 忽略无法解析的弹幕
                        print(f"解析弹幕失败: {e}")
                        continue

            # 按照时间点排序
            danmu_data.sort(key=lambda x: x[0])

            return danmu_data

def format_time(total_seconds):
    """将秒数格式化为 '时:分:秒' 形式"""
    # 计算小时、分钟和秒
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds_remaining = total_seconds % 60

    # 格式化为 "时:分:秒"
    return f"{hours}:{minutes:02d}:{seconds_remaining:02d}"


def save_to_excel(df, filename):
    """保存DataFrame到Excel文件，兼容不同pandas版本"""
    try:
        # 尝试较新的保存方法
        df.to_excel(filename, index=False, engine='openpyxl')
        return True
    except TypeError:
        # 如果失败，尝试旧版保存方法
        try:
            df.to_excel(filename, index=False)
            return True
        except Exception as e:
            print(f"保存Excel文件失败: {e}")
            return False


async def fetch_and_save_danmu(bvid):
    """获取并保存弹幕到Excel文件，按秒分组显示"""
    try:
        print(f"开始获取视频 {bvid} 的弹幕...")
        start_time = time.time()

        # 获取视频CID
        cid = await fetch_cid(bvid)
        print(f"获取到视频CID: {cid}")

        # 获取弹幕数据 (包含时间点和内容)
        danmu_data = await fetch_danmu(cid)
        print(f"成功获取到 {len(danmu_data)} 条弹幕")

        # 创建DataFrame
        df = pd.DataFrame(danmu_data, columns=['时间点(秒)', '弹幕内容', '发送时间'])

        # 添加整数秒列用于分组
        df['整数秒'] = df['时间点(秒)'].apply(lambda x: int(float(x)))

        # 计算每秒弹幕数量
        danmu_counts = df['整数秒'].value_counts().to_dict()

        # 添加格式化时间列
        df['时间点(格式化)'] = df['整数秒'].apply(
            lambda sec: f"{format_time(sec)} (共{danmu_counts.get(sec, 0)}条)"
        )

        # 重新排列列顺序（包含整数秒列）
        df = df[['时间点(秒)', '整数秒', '时间点(格式化)', '弹幕内容', '发送时间']]

        # 为每个时间点添加分组标识（每个时间点的第一条弹幕）
        # 使用shift来检测时间点变化
        df['新时间点'] = df['整数秒'] != df['整数秒'].shift(1)
        # 第一条记录总是新时间点
        if not df.empty:  # 添加空DataFrame检查
            df.loc[df.index[0], '新时间点'] = True

        # 删除临时列
        df = df.drop(columns=['整数秒'])

        # 保存到Excel文件
        excel_filename = f"danmu_{bvid}.xlsx"

        if save_to_excel(df, excel_filename):
            elapsed = time.time() - start_time
            print(f"\n所有弹幕已保存到 {excel_filename}")
            print(f"文件包含 {len(df)} 条弹幕记录")
            print(f"处理耗时: {elapsed:.2f}秒")
            print("列标题: 时间点(秒), 时间点(格式化), 弹幕内容, 发送时间")
            print("提示: 时间点(格式化)列在每个新时间点的第一条弹幕显示一次")

            # 打开Excel文件（如果系统支持）
            if os.name == 'nt':  # Windows系统
                try:
                    os.startfile(excel_filename)
                except:
                    print("无法自动打开Excel文件，请手动打开查看")

            return True
        else:
            print("保存Excel文件失败")
            return False

    except Exception as e:
        print(f"获取弹幕失败: {e}")
        return False


async def process_multiple_bvids(bvid_list):
    """批量处理多个BV号"""
    total = len(bvid_list)
    success_count = 0

    print(f"\n{'=' * 50}")
    print(f"开始批量处理 {total} 个视频")
    print(f"{'=' * 50}\n")

    for i, bvid in enumerate(bvid_list, 1):
        print(f"\n[进度 {i}/{total}] 处理视频: {bvid}")
        result = await fetch_and_save_danmu(bvid)

        if result:
            success_count += 1
            print(f"√ 视频 {bvid} 处理成功")
        else:
            print(f"× 视频 {bvid} 处理失败")

        # 添加请求间隔避免触发反爬
        if i < total:
            delay = random.uniform(1.5, 3.5)
            print(f"等待 {delay:.1f} 秒后继续...")
            await asyncio.sleep(delay)

    print(f"\n{'=' * 50}")
    print(f"批量处理完成! 成功: {success_count}/{total}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    # 在这里替换为您要爬取的BV号列表
    target_bvids = [
        "BV1example123",  # 请替换为实际的BV号
        # 可以添加更多BV号，例如：
        # "BV1example456",
        # "BV1example789"
    ]

    print("B站弹幕爬取程序启动...")

    # 根据输入类型自动选择处理模式
    if isinstance(target_bvids, list) and len(target_bvids) > 1:
        asyncio.run(process_multiple_bvids(target_bvids))
    elif isinstance(target_bvids, list) and len(target_bvids) == 1:
        asyncio.run(fetch_and_save_danmu(target_bvids[0]))
    else:
        print("错误: 请输入有效的BV号列表")