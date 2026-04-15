#!/usr/bin/env python3
"""
小红书MCP - 命令行入口
"""
import argparse
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import XiaohongshuPipeline


def main():
    parser = argparse.ArgumentParser(
        description="小红书MCP - AI爆文生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 快速生成
  python main.py "AI效率工具"
  
  # 指定风格和受众
  python main.py "职场穿搭" --style "时尚穿搭" --audience "职场女性"
  
  # 生成并发布为草稿
  python main.py "学习方法" --publish --draft
        """
    )
    
    # 必需参数
    parser.add_argument(
        "keywords",
        type=str,
        help="主题关键词（如：AI工具、职场穿搭、学习方法）"
    )
    
    # 可选参数
    parser.add_argument(
        "--style",
        type=str,
        default="干货分享",
        help="笔记风格（默认：干货分享）"
    )
    
    parser.add_argument(
        "--audience",
        type=str,
        default="年轻女性",
        help="目标受众（默认：年轻女性）"
    )
    
    parser.add_argument(
        "--images",
        type=int,
        default=1,
        help="图片数量（默认：1张封面图）"
    )
    
    parser.add_argument(
        "--publish",
        action="store_true",
        help="发布到小红书"
    )
    
    parser.add_argument(
        "--draft",
        action="store_true",
        help="保存为草稿（与--publish一起使用）"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径"
    )
    
    args = parser.parse_args()
    
    # 创建流水线
    pipeline = XiaohongshuPipeline(config_path=args.config)
    
    # 运行
    result = pipeline.run(
        keywords=args.keywords,
        target_audience=args.audience,
        style=args.style,
        image_count=args.images,
        publish=args.publish,
        save_as_draft=args.draft if args.publish else True
    )
    
    # 输出结果
    if result.get("error"):
        print(f"\n❌ 错误: {result['error']}")
        sys.exit(1)
    else:
        print(f"\n✅ 成功生成笔记!")
        print(f"标题: {result['note']['title']}")
        print(f"图片: {len(result.get('images', []))} 张")
        sys.exit(0)


if __name__ == "__main__":
    main()
