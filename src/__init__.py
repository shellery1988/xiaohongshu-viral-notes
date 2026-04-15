"""
小红书MCP - AI爆文生成器
自动搜索热点、撰写爆文、生成配图、发布笔记
"""

from .search import XiaohongshuSearcher
from .writer import XiaohongshuWriter
from .image_gen import JimengImageGenerator
from .publisher import XiaohongshuPublisher
from .pipeline import XiaohongshuPipeline

__version__ = "2.1.0"
__all__ = [
    "XiaohongshuSearcher",
    "XiaohongshuWriter", 
    "JimengImageGenerator",
    "XiaohongshuPublisher",
    "XiaohongshuPipeline"
]
