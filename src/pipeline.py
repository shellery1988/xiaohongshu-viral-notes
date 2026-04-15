"""
小红书MCP - 完整流水线
整合搜索→爆文分析→撰写→图片生成→发布的完整流程
"""
import json
import os
import time
import yaml
from typing import Dict, List, Optional
from pathlib import Path

from .search import XiaohongshuSearcher
from .writer import XiaohongshuWriter
from .image_gen import JimengImageGenerator
from .publisher import XiaohongshuPublisher


class XiaohongshuPipeline:
    """小红书MCP完整流水线"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)

        self.searcher = XiaohongshuSearcher()
        self.writer = XiaohongshuWriter(
            api_key=self.config.get("writer", {}).get("api_key", ""),
            model=self.config.get("writer", {}).get("model", "glm-4-flash"),
            temperature=self.config.get("writer", {}).get("temperature", 0.9),
            max_tokens=self.config.get("writer", {}).get("max_tokens", 4000),
        )
        self.image_generator = JimengImageGenerator(
            sessionid=self.config.get("image_gen", {}).get("sessionid", ""),
            api_base=self.config.get("image_gen", {}).get("api_base", "http://localhost:8000"),
            model=self.config.get("image_gen", {}).get("model", "jimeng-5.0"),
        )
        self.publisher = XiaohongshuPublisher()

        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """加载配置文件"""
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config.yaml")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"配置文件不存在: {config_path}")
            return {}
        except Exception as e:
            print(f"加载配置失败: {e}")
            return {}

    def run(
        self,
        keywords: str,
        target_audience: str = "年轻女性",
        style: str = "干货分享",
        image_count: int = 1,
        publish: bool = False,
        save_as_draft: bool = True,
    ) -> Dict:
        """
        运行完整流水线

        流程: 搜索热点 → 爆文分析 → AI撰写 → 生成配图 → (发布)
        """
        print("=" * 60)
        print("小红书MCP - AI爆文生成流水线 v2.0")
        print("=" * 60)

        # Step 1: 搜索热点
        print("\n📌 Step 1/4: 搜索热点爆文...")
        hot_posts = self._search_hot_posts(keywords)
        print(f"  找到 {len(hot_posts)} 篇相关热点")

        # Step 2: 爆文分析（新增）
        print("\n🔬 Step 2/4: 深度分析爆文特征...")
        analysis = self._analyze_posts(hot_posts)
        self._print_analysis_summary(analysis)

        # Step 3: 撰写爆文（传入分析结果）
        print("\n📝 Step 3/4: 基于分析撰写爆文笔记...")
        note = self._write_post(
            keywords=keywords,
            hot_posts=hot_posts,
            target_audience=target_audience,
            style=style,
            image_count=image_count,
            analysis=analysis,
        )
        print(f"  标题: {note.get('title', '')}")
        print(f"  正文字数: {len(note.get('content', ''))}字")
        print(f"  标签: {', '.join(note.get('tags', [])[:3])}...")

        # Step 4: 生成图片
        print("\n🎨 Step 4/5: 生成配图...")
        images_dir = str(self.output_dir / "images")
        image_results = self._generate_images(note, images_dir)
        print(f"  生成 {len(image_results)} 张图片")

        note = self._update_note_with_images(note, image_results)

        # Step 5: 发布（可选）
        if publish:
            print("\n🚀 Step 5/5: 发布到小红书...")
            publish_result = self._publish_note(note, save_as_draft)
            status = "草稿已保存" if publish_result.get("success") else "发布失败"
            print(f"  发布状态: {status}")
        else:
            print("\n💾 Step 5/5: 跳过发布（仅生成内容）")
            publish_result = {"skipped": True}

        # 保存完整结果
        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items() if k not in ("image_bytes",)}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            return obj

        clean_result = clean_for_json({
            "keywords": keywords,
            "hot_posts_count": len(hot_posts),
            "analysis_summary": analysis.get("summary", "") if analysis else "",
            "note": note,
            "images": image_results,
            "publish_result": publish_result,
        })

        output_file = self.output_dir / f"note_{keywords[:10]}_{int(time.time())}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(clean_result, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 完成！结果已保存到: {output_file}")
        print(f"\n{'='*60}")
        print("📝 笔记预览:")
        print(f"{'='*60}")
        print(f"标题: {note.get('title', '')}")
        print(f"{'-'*40}")
        print(note.get("content", ""))
        print(f"{'-'*40}")
        print(f"标签: {' '.join('#'+t for t in note.get('tags', []))}")
        print(f"{'='*60}")

        return clean_result

    def _search_hot_posts(self, keywords: str) -> List[Dict]:
        """搜索热点帖子"""
        try:
            return self.searcher.get_trending_posts(
                topic=keywords,
                days=7,
                min_likes=200,  # 降低门槛，确保有足够参考
            )
        except Exception as e:
            print(f"  搜索失败: {e}")
            return []

    def _analyze_posts(self, hot_posts: List[Dict]) -> Dict:
        """爆文分析"""
        try:
            return self.searcher.analyze_hot_posts(hot_posts)
        except Exception as e:
            print(f"  分析失败: {e}")
            return {}

    def _print_analysis_summary(self, analysis: Dict):
        """打印分析摘要"""
        if not analysis:
            print("  ⚠️ 无分析数据")
            return

        summary = analysis.get("summary", "")
        if summary:
            print(f"  📊 {summary}")

        engagement = analysis.get("engagement_insights", {})
        if engagement:
            print(
                f"  📈 数据: {engagement.get('post_count', 0)}篇爆文 | "
                f"平均{engagement.get('avg_likes', 0)}赞 | "
                f"最高{engagement.get('max_likes', 0)}赞"
            )

        patterns = analysis.get("title_patterns", [])
        if patterns:
            best = patterns[0]
            print(f"  🏷️ 最佳标题模式: {best['type']} (平均{best['avg_likes']:.0f}赞)")

        hooks = analysis.get("hook_styles", [])
        if hooks:
            best = hooks[0]
            print(f"  🪝 最佳开头类型: {best['type']} (平均{best['avg_likes']:.0f}赞)")

    def _write_post(
        self,
        keywords: str,
        hot_posts: List[Dict],
        target_audience: str,
        style: str,
        image_count: int,
        analysis: Optional[Dict] = None,
    ) -> Dict:
        """撰写爆文笔记（传入分析结果）"""
        try:
            return self.writer.generate_post(
                keywords=keywords,
                hot_posts=hot_posts,
                target_audience=target_audience,
                style=style,
                image_count=image_count,
                analysis=analysis,
            )
        except Exception as e:
            print(f"  撰写失败: {e}")
            return {
                "title": f"关于{keywords}的分享",
                "content": "内容生成失败，请重试",
                "tags": [keywords],
                "images": [],
            }

    def _generate_images(self, note: Dict, output_dir: str) -> List[Dict]:
        """生成封面图（无描述时自动生成默认描述，仅1张）"""
        # 如果LLM没返回images，用默认封面描述
        if not note.get("images"):
            title = note.get("title", "小红书")[:15]
            note["images"] = [
                {"index": 1, "description": f"封面图：{title}", "prompt": f"minimal elegant scene related to '{title}', warm morning sunlight, soft cream and sage green tones, editorial photography style, centered composition with negative space, natural warm lighting, ultra high quality, 8k, sharp focus, cozy aesthetic"},
            ]
        try:
            return self.image_generator.generate_from_note(note, output_dir)
        except Exception as e:
            print(f"  图片生成失败: {e}")
            return []

    def _update_note_with_images(self, note: Dict, image_results: List[Dict]) -> Dict:
        """更新笔记中的图片路径"""
        images = note.get("images", [])
        for i, result in enumerate(image_results):
            if i < len(images) and "saved_path" in result:
                images[i]["saved_path"] = result["saved_path"]
        note["images"] = images
        return note

    def _publish_note(self, note: Dict, save_as_draft: bool) -> Dict:
        """发布笔记"""
        if not self.publisher.check_login_status():
            return {"error": "未登录小红书，请先运行: xhs init"}

        return self.publisher.publish_from_note(
            note=note,
            image_dir=str(self.output_dir / "images"),
            save_as_draft=save_as_draft,
        )

    def quick_run(self, keywords: str) -> Dict:
        """快速运行（使用默认参数）"""
        return self.run(
            keywords=keywords,
            target_audience="年轻女性",
            style="干货分享",
            image_count=1,
            publish=False,
        )


if __name__ == "__main__":
    pipeline = XiaohongshuPipeline()
    result = pipeline.quick_run("AI效率工具")
    print("\n生成结果预览:")
    print(f"标题: {result['note']['title']}")
    print(f"内容: {result['note']['content'][:200]}...")
