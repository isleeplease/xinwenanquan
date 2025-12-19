
from dotenv import load_dotenv
import os


def load_config():
    """加载环境变量配置"""
    load_dotenv()  # 从.env文件加载

    return {
        'youtube_api_key': os.getenv('YOUTUBE_API_KEY'),
        'REDDIT_CLIENT_ID':os.getenv('REDDIT_CLIENT_ID'),
        'REDDIT_CLIENT_SECRET':os.getenv('REDDIT_CLIENT_SECRET'),
        'REDDIT_USER_AGENT':os.getenv('REDDIT_USER_AGENT')
    }