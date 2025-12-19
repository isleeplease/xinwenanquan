import os
import time
import json
import random
import csv
import re
import math
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service

# ============== 全局配置 ==============
DEBUG_MODE = True
RESULTS_PER_KEYWORD = 100  # 每个关键词抓取100个视频
START_DATE = "2025-10-14"  # 开始日期
END_DATE = "2025-11-09"    # 结束日期
KEYWORDS = ["哔哩哔哩英雄联盟赛事"]    # 在这里填写UP主的名字作为关键词
COLLECT_DETAILED_STATS = True
MAX_RETRIES = 3  # 最大重试次数
MAX_PAGES = 50  # B站最大分页数
PER_PAGE = 30  # 每页视频数
# 配置本地chromedriver路径（用户需自行修改为实际路径）
CHROMEDRIVER_PATH = r"C:\Users\here\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"  # 您下载的ChromeDriver路径


# ============== 浏览器初始化 ==============
def init_browser():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在配置浏览器选项...")
    options = webdriver.ChromeOptions()

    # 优化设置
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在初始化浏览器驱动...")
    try:
        # 使用用户配置的chromedriver路径
        if not os.path.exists(CHROMEDRIVER_PATH):
            raise FileNotFoundError(f"ChromeDriver未找到，请检查路径: {CHROMEDRIVER_PATH}")

        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)

        driver.set_page_load_timeout(60)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ WebDriver特征已隐藏")
        return driver
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 浏览器初始化失败: {str(e)}")
        raise


# ============== 登录管理 ==============
def check_login_status(driver):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 访问空间页面验证登录状态")
    try:
        driver.get("https://space.bilibili.com")
        WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".header-avatar, .h-avatar, .avatar"))
        )
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 通过头像元素验证登录状态")
        return True
    except TimeoutException:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 登录状态验证失败")
        return False


def load_cookies(driver):
    try:
        driver.get("https://www.bilibili.com")
        time.sleep(3)

        # 提示用户输入cookie字符串
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 请粘贴B站的完整Cookie（包含所有键值对）:")
        cookie_str = input("> ").strip()

        # 解析cookie字符串为字典列表
        cookies = []
        for item in cookie_str.split('; '):
            if '=' in item:
                name, value = item.split('=', 1)  # 只分割第一个等号
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.bilibili.com'  # 设置为B站主域名
                })

        # 添加cookie到浏览器
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 添加Cookie失败: {cookie['name']} - {str(e)}")

        driver.refresh()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Cookies已成功应用")
        return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 加载Cookies失败: {str(e)}")
        return False


# ============== 数据清洗函数 ==============
def clean_number(text):
    if not text or text == "未知":
        return "0"
    try:
        if "万" in text:
            num_match = re.search(r'(\d+\.?\d*)万', text)
            if num_match:
                num = float(num_match.group(1)) * 10000
                return str(int(num))
        num_match = re.search(r'\d+', text)
        return num_match.group(0) if num_match else "0"
    except:
        return "0"


# ============== URL获取增强方法 ==============
def get_video_url(item, driver, debug_idx=None):
    """多重方法获取视频URL"""
    href = None
    try:
        title_link = item.find_element(By.CSS_SELECTOR, ".bili-video-card__info--tit")
        href = title_link.get_attribute("href")
        if href and "bilibili.com/video/" in href:
            return href
    except:
        pass

    try:
        cover_link = item.find_element(By.CSS_SELECTOR, ".bili-video-card__image")
        href = cover_link.get_attribute("href")
        if href and "bilibili.com/video/" in href:
            return href
    except:
        pass

    try:
        card_container = item.find_element(By.XPATH, "./ancestor::a")
        href = card_container.get_attribute("href")
        if href and "bilibili.com/video/" in href:
            return href
    except:
        pass

    try:
        js_script = "return arguments[0].querySelector('[data-loc-id]').getAttribute('data-loc-id');"
        loc_id = driver.execute_script(js_script, item)
        if loc_id:
            return f"https://www.bilibili.com/video/{loc_id}"
    except:
        pass

    try:
        bvid_element = item.find_element(By.CSS_SELECTOR, "[href*='BV']")
        bvid = re.search(r'BV\w+', bvid_element.get_attribute("href")).group(0)
        if bvid:
            return f"https://www.bilibili.com/video/{bvid}"
    except:
        pass

    try:
        title_text = item.get_attribute("title")
        if "BV" in title_text:
            bv_match = re.search(r'BV\w+', title_text)
            if bv_match:
                return f"https://www.bilibili.com/video/{bv_match.group(0)}"
    except:
        pass

    if DEBUG_MODE and debug_idx is not None:
        try:
            # 移除截图相关代码
            with open(f"url_failed_{debug_idx}.html", "w", encoding="utf-8") as f:
                f.write(item.get_attribute("outerHTML"))
        except:
            pass

    return None


# ============== 通过API获取统计数据 ==============
def get_video_stats_by_api(href, driver):
    """通过B站API获取视频统计数据"""
    stats = {
        "播放量": "0", "弹幕数": "0", "点赞数": "0",
        "投币数": "0", "收藏量": "0", "转发数": "0", "评论数": "0",
        "发布时间": ""  # 新增字段，用于存储精确时间
    }

    try:
        # 从URL中提取bv_id
        bv_match = re.search(r'video/(BV\w+)', href)
        if not bv_match: return stats

        # 构建API URL
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv_match.group(1)}"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌐 访问视频统计API: {api_url}")

        # 使用临时标签页访问API
        original_window = driver.current_window_handle
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])

        driver.get(api_url)

        # 等待响应加载
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )

            # 解析JSON响应
            pre_element = driver.find_element(By.TAG_NAME, "pre")
            api_data = json.loads(pre_element.text)

            # 提取统计数据
            if api_data.get("code") == 0 and api_data.get("data"):
                data = api_data["data"]
                stat = data.get("stat", {})

                # 提取精确发布时间
                pubdate_timestamp = data.get("pubdate")
                if pubdate_timestamp:
                    pubdate_dt = datetime.fromtimestamp(pubdate_timestamp)
                    stats["发布时间"] = pubdate_dt.strftime("%Y-%m-%d %H:%M:%S")

                # 更新统计数据
                stats.update({
                    "播放量": str(stat.get("view", "0")),
                    "弹幕数": str(stat.get("danmaku", "0")),
                    "点赞数": str(stat.get("like", "0")),
                    "投币数": str(stat.get("coin", "0")),
                    "收藏量": str(stat.get("favorite", "0")),
                    "转发数": str(stat.get("share", "0")),
                    "评论数": str(stat.get("reply", "0"))
                })
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ API视频统计数据获取成功")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ API返回错误: {api_data.get('message')}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ API数据处理失败: {str(e)}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ API访问失败: {str(e)}")
    finally:
        # 关闭API标签页并切换回原窗口
        if len(driver.window_handles) > 1 and driver.current_window_handle != original_window:
            driver.close()
            driver.switch_to.window(original_window)

        return stats


def get_comments_by_api(href, driver):
    """通过API获取评论数"""
    try:
        # 从URL中提取bv_id
        bv_match = re.search(r'video/(BV\w+)', href)
        if not bv_match:
            return "0"
        bv_id = bv_match.group(1)

        # 构建API URL
        api_url = f"https://api.bilibili.com/x/v2/reply/main?type=1&oid={bv_id}&sort=0"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌐 访问评论API: {api_url}")

        # 使用临时标签页访问API
        original_window = driver.current_window_handle
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])

        driver.get(api_url)

        # 等待响应加载
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )

            # 解析JSON响应
            pre_element = driver.find_element(By.TAG_NAME, "pre")
            api_data = json.loads(pre_element.text)

            # 提取评论数
            if api_data.get("code") == 0 and api_data.get("data"):
                count = str(api_data["data"].get("cursor", {}).get("all_count", "0"))
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ API评论数获取成功: {count}")
                return count
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ API返回错误: {api_data.get('message')}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ API数据处理失败: {str(e)}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ API访问失败: {str(e)}")
    finally:
        # 关闭API标签页并切换回原窗口
        if len(driver.window_handles) > 1 and driver.current_window_handle != original_window:
            driver.close()
            driver.switch_to.window(original_window)

        return "0"


# ============== 详情页数据采集 ==============
def get_video_details(href, driver):
    """获取视频详情数据"""
    details = {
        "播放量": "0", "弹幕数": "0", "点赞数": "0",
        "投币数": "0", "收藏量": "0", "转发数": "0", "评论数": "0",
        "发布时间": ""  # 新增字段，用于存储精确时间
    }

    if not COLLECT_DETAILED_STATS or not href or href == "未知":
        return details

    # 优先使用API获取数据
    api_stats = get_video_stats_by_api(href, driver)
    if any(value != "0" for value in api_stats.values()):
        details = api_stats
        return details

    # API失败时使用页面解析方法
    original_window = driver.current_window_handle
    try:
        # 打开新标签页
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌐 访问视频详情页: {href[:60]}...")
        driver.get(href)

        # 等待页面基本加载
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 详情页框架已加载")

        # 1. 获取精确发布时间
        try:
            # 方法1：通过meta标签获取
            pubdate_element = driver.find_element(By.CSS_SELECTOR, "meta[itemprop='datePublished']")
            pubdate_str = pubdate_element.get_attribute("content")
            if pubdate_str:
                # 转换格式：2025-03-24T12:34:56+08:00 -> 2025-03-24 12:34:56
                pubdate_str = pubdate_str.replace("T", " ").split("+")[0]
                details["发布时间"] = pubdate_str
        except:
            try:
                # 方法2：通过发布时间元素获取
                pubdate_element = driver.find_element(By.CSS_SELECTOR,
                                                      ".video-info .video-info-detail .video-info-ctime")
                pubdate_str = pubdate_element.text.strip()
                if pubdate_str:
                    details["发布时间"] = pubdate_str
            except:
                pass

        # 2. 播放量
        try:
            play_element = driver.find_element(By.CSS_SELECTOR, ".view-text, .video-info-views .item")
            details["播放量"] = clean_number(play_element.text.strip())
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 播放量提取失败: {str(e)}")

        # 3. 弹幕数
        try:
            danmaku_element = driver.find_element(By.CSS_SELECTOR, ".dm-text, .video-info-danmaku .item")
            details["弹幕数"] = clean_number(danmaku_element.text.strip())
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 弹幕数提取失败: {str(e)}")

        # 4. 点赞数
        try:
            like_element = driver.find_element(By.CSS_SELECTOR, ".video-like-info, .ops .like")
            details["点赞数"] = clean_number(like_element.text.strip())
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 点赞数提取失败: {str(e)}")

        # 5. 投币数
        try:
            coin_element = driver.find_element(By.CSS_SELECTOR, ".video-coin-info, .ops .coin")
            details["投币数"] = clean_number(coin_element.text.strip())
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 投币数提取失败: {str(e)}")

        # 6. 收藏量
        try:
            collect_element = driver.find_element(By.CSS_SELECTOR, ".video-fav-info, .ops .collect")
            details["收藏量"] = clean_number(collect_element.text.strip())
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 收藏量提取失败: {str(e)}")

        # 7. 转发数 - 三重方法获取
        try:
            # 方法1：用户提供的精确XPath
            share_element = driver.find_element(By.XPATH,
                                                "/html/body/div[2]/div[2]/div[1]/div[3]/div[1]/div/div[4]/div/span/div[2]/div/span")
            details["转发数"] = clean_number(share_element.text.strip())
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 转发数（方法1）获取成功")
        except Exception as e1:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 转发数方法1失败: {str(e1)}")
            try:
                # 方法2：相对定位方法
                share_element = driver.find_element(By.CSS_SELECTOR,
                                                    "div.tool-bar div:nth-child(4) .share-num, .ops .share")
                details["转发数"] = clean_number(share_element.text.strip())
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 转发数（方法2）获取成功")
            except Exception as e2:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 转发数方法2失败: {str(e2)}")
                try:
                    # 方法3：文本内容定位
                    share_element = driver.find_element(By.XPATH,
                                                        "//span[contains(text(),'转发')]/following-sibling::span")
                    details["转发数"] = clean_number(share_element.text.strip())
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 转发数（方法3）获取成功")
                except Exception as e3:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 所有转发数方法失败")

        # 8. 评论数 - 通过API获取
        details["评论数"] = get_comments_by_api(href, driver)

        # 打印获取的数据
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 获取详情数据: "
              f"播放={details['播放量']} "
              f"弹幕={details['弹幕数']} "
              f"点赞={details['点赞数']} "
              f"投币={details['投币数']} "
              f"收藏={details['收藏量']} "
              f"转发={details['转发数']} "
              f"评论={details['评论数']}")

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 获取详情数据失败: {str(e)}")
    finally:
        # 关闭详情页标签
        if len(driver.window_handles) > 1 and driver.current_window_handle != original_window:
            driver.close()
            driver.switch_to.window(original_window)
        time.sleep(1)

    return details


# ============== 错误处理函数 ==============
def handle_extraction_error(e, item, driver, keyword, idx):
    """统一处理视频提取错误"""
    error_type = type(e).__name__

    if "NoSuchElement" in error_type:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 元素未找到: {str(e)}")
        # 如果是发布时间元素未找到，尝试其他方法
        if "date" in str(e):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 发布时间元素未找到，尝试API获取")
            return "retry"  # 重试时尝试API获取
        return "retry"  # 立即重试

    elif "Timeout" in error_type:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 操作超时: {str(e)}")
        return "wait_and_retry"  # 增加等待时间后重试

    elif "WebDriver" in error_type:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 浏览器错误: {str(e)}")
        return "restart_browser"  # 重启浏览器

    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 未知错误: {str(e)}")
        return "skip"  # 跳过当前视频


# ============== 带重试的视频信息提取 ==============
def extract_video_info_with_retry(item, driver, keyword, idx, max_retries=MAX_RETRIES):
    """带重试机制的视频信息提取"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 尝试 #{attempt} 提取视频 {idx + 1}")
            result = extract_video_info(item, driver, keyword, idx)
            if result:
                # 检查是否包含发布时间
                if not result.get("发布时间"):
                    # 如果没有发布时间，尝试从详情页获取
                    href = result.get("URL")
                    if href and href != "未知":
                        details = get_video_details(href, driver)
                        if details.get("发布时间"):
                            result["发布时间"] = details["发布时间"]
                return result
        except Exception as e:
            # 使用统一错误处理
            action = handle_extraction_error(e, item, driver, keyword, idx)

            # 根据错误处理建议执行相应操作
            if action == "retry":
                # 立即重试
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 立即重试...")
                continue
            elif action == "wait_and_retry":
                # 增加等待时间后重试
                sleep_time = min(2 ** attempt, 30)  # 最大30秒
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ 等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            elif action == "restart_browser":
                # 重启浏览器 - 需要上层函数处理
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 需要重启浏览器")
                return "restart_browser"
            else:  # skip
                # 跳过当前视频
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏩ 跳过当前视频")
                break

    # 所有重试失败后记录错误
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 视频提取失败: 超过最大重试次数")

    # 移除截图相关代码
    if DEBUG_MODE:
        try:
            card_html = item.get_attribute("outerHTML")
            with open(f"failed_video_{keyword}_{idx}.html", "w", encoding="utf-8") as f:
                f.write(card_html)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📝 保存失败卡片HTML")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 保存调试信息失败: {str(e)}")

    return None


# ============== 视频卡片信息提取 ==============
def extract_video_info(item, driver, keyword, idx):
    """从视频卡片提取基础信息"""
    try:
        # 基础信息
        try:
            title = item.find_element(By.CSS_SELECTOR, ".bili-video-card__info--tit").text.strip()
        except:
            title = "无标题"

        # 使用增强版URL获取方法
        href = get_video_url(item, driver, debug_idx=f"{keyword}_{idx}")

        # 日期提取 - 精确到秒
        try:
            # 获取完整的日期时间字符串
            date_element = item.find_element(By.CSS_SELECTOR, ".bili-video-card__info--date")
            date_str = date_element.text.strip().replace("· ", "")

            # 检查是否包含时间部分
            if ":" not in date_str:
                # 如果没有时间部分，尝试获取更精确的时间
                try:
                    # 方法1：使用title属性获取精确时间
                    date_str = date_element.get_attribute("title")
                    if not date_str or ":" not in date_str:
                        # 方法2：使用JavaScript获取精确时间
                        date_str = driver.execute_script(
                            "return arguments[0].querySelector('.bili-video-card__info--date').getAttribute('data-time');",
                            item
                        )
                        if date_str:
                            # 将时间戳转换为日期时间格式
                            date_dt = datetime.fromtimestamp(int(date_str))
                            date_str = date_dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
        except:
            date_str = "未知日期"

        # UP主提取
        try:
            up_element = item.find_element(By.CSS_SELECTOR, ".bili-video-card__info--author")
            up_name = up_element.text.strip()
        except:
            up_name = "未知UP主"

        # BV号提取
        bv_id = "未知"
        try:
            if href and "video/BV" in href:
                bv_match = re.search(r'video/(BV\w+)', href)
                bv_id = bv_match.group(1) if bv_match else href.split("/")[-1].split("?")[0]
        except:
            pass

        # 构建基础数据
        video_data = {
            "标题": title,
            "URL": href or "未知",
            "BV号": bv_id,
            "发布时间": date_str,  # 现在包含精确时间
            "UP主": up_name
        }

        # 获取详细统计数据
        if COLLECT_DETAILED_STATS and href and href != "未知":
            details = get_video_details(href, driver)
            video_data.update(details)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 跳过详情页采集，URL无效")

        return video_data
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 视频信息提取失败: {str(e)}")
        return None


# ============== 核心搜索功能 ==============
def search_bilibili(keyword, driver, max_results=RESULTS_PER_KEYWORD):
    """支持分页抓取的核心搜索函数"""
    try:
        # 计算时间范围
        start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")
        end_dt = datetime.strptime(END_DATE, "%Y-%m-%d")
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp()) + 86399

        # 计算总页数
        total_pages = min(MAX_PAGES, math.ceil(max_results / PER_PAGE))

        all_results = []
        for page in range(1, total_pages + 1):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📄 处理第 {page} 页")

            # 构建搜索URL
            params = {
                "keyword": keyword,
                "order": "pubdate",
                "page": page,
                "pubtime_begin_s": start_ts,
                "pubtime_end_s": end_ts
            }
            search_url = "https://search.bilibili.com/all?" + urlencode(params)

            # 访问搜索页
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌐 访问搜索页: {search_url[:80]}...")
            driver.get(search_url)

            # 等待结果加载
            try:
                WebDriverWait(driver, 30).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".bili-video-card"))
                )
            except TimeoutException:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 页面加载超时，继续下一页")
                continue

            # 获取视频卡片
            video_items = driver.find_elements(By.CSS_SELECTOR, ".bili-video-card")
            if not video_items:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 未找到视频卡片，停止分页")
                break

            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔎 找到 {len(video_items)} 个视频卡片")

            # 处理当前页的每个视频
            page_results = []
            for i in range(len(video_items)):
                try:
                    # 使用带重试的视频提取
                    result = extract_video_info_with_retry(
                        video_items[i], driver, keyword, i
                    )

                    if result == "restart_browser":
                        # 重启浏览器
                        driver.quit()
                        driver = init_browser()
                        if load_cookies(driver) and check_login_status(driver):
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 浏览器重启成功")
                        else:
                            return all_results
                        # 重新获取当前页
                        driver.get(search_url)
                        video_items = driver.find_elements(By.CSS_SELECTOR, ".bili-video-card")
                        continue

                    if result:
                        page_results.append(result)
                        current_count = len(all_results) + len(page_results)
                        print(
                            f"[{datetime.now().strftime('%H:%M:%S')}] 🎬 已获取视频 {current_count}/{max_results}: {result['标题'][:20]}...")
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 视频 {i + 1} 提取失败")

                    # 随机延迟
                    time.sleep(random.uniform(1.0, 3.0))
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 处理视频失败: {str(e)}")

            # 添加到总结果
            all_results.extend(page_results)

            # 达到目标数量则停止
            if len(all_results) >= max_results:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 已达到目标数量 {max_results}")
                break

            # 翻页延迟
            sleep_time = random.uniform(3.0, 8.0)
            time.sleep(sleep_time)

        return all_results[:max_results]
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 搜索过程出错: {str(e)}")
        return []


# ============== 数据保存 ==============
def save_to_csv(data, filename="bilibili_data.csv"):
    if not data:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 无数据可保存")
        return False

    # 创建字段列表 - 确保包含"发布时间"字段
    fieldnames = [
        "标题", "URL", "BV号", "发布时间", "UP主",
        "播放量", "弹幕数", "点赞数", "投币数", "收藏量", "转发数", "评论数"
    ]

    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # 确保每行数据包含所有字段
            for row in data:
                # 创建临时字典确保所有字段都存在
                temp_row = {field: "" for field in fieldnames}
                temp_row.update(row)
                writer.writerow(temp_row)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 数据已保存到 {filename}")

        # 打印CSV内容预览
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📄 CSV内容预览:")
        with open(filename, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i < 5:
                    print(line.strip())
                elif i == 5:
                    print("...")
                    break

        return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ 保存数据失败: {str(e)}")
        return False


# ============== 主函数 ==============
def main():
    print("=" * 60)
    print("🚀 B站视频搜索数据采集工具 (900视频版)")
    print("=" * 60)

    start_time = time.time()
    driver = None

    try:
        driver = init_browser()

        if load_cookies(driver) and check_login_status(driver):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 通过Cookies登录成功")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔑 需要手动登录B站账号...")
            driver.get("https://passport.bilibili.com/login")
            input("请在浏览器中登录B站账户，然后在此按回车键继续...")

            if not check_login_status(driver):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 登录验证失败，退出程序")
                return

        all_data = []
        for keyword in KEYWORDS:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 开始处理关键词: {keyword}")
            data = search_bilibili(keyword, driver)
            if data:
                all_data.extend(data)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 关键词 '{keyword}' 获取到 {len(data)} 条视频数据")

        if all_data:
            save_to_csv(all_data, f"bilibili_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

        elapsed = time.time() - start_time
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 采集完成! 耗时: {elapsed:.1f}秒")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 共获取 {len(all_data)} 条视频数据")

    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⛔ 用户中断操作!")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 主程序出错: {str(e)}")
    finally:
        if driver:
            try:
                driver.quit()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚫 浏览器已关闭")
            except:
                pass


if __name__ == "__main__":
    main()