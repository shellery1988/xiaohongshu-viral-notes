"""
小红书MCP - AI爆文撰写模块
接入智谱AI大模型(GLM)，基于爆文分析结果撰写高质量笔记
"""
import json
import os
import time
import urllib.request
import ssl
from typing import Dict, List, Optional
from pathlib import Path


class XiaohongshuWriter:
    """AI爆文撰写器 - 基于爆文分析的智能写作"""

    def __init__(
        self,
        api_key: str = "",
        model: str = "glm-4-flash",
        temperature: float = 0.9,
        max_tokens: int = 4000,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """加载提示词模板"""
        template_path = Path(__file__).parent.parent / "prompts" / "writer_prompt.md"
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return self._get_fallback_prompt()

    def _get_fallback_prompt(self) -> str:
        """降级提示词（极简版）"""
        return """你是一位顶级小红书内容操盘手。

基于以下信息撰写一篇小红书爆文笔记：

关键词: {keywords}
受众: {target_audience}
风格: {style}
参考: {hot_posts_examples}

要求：标题15-25字有吸引力，正文400-700字有干货有情绪，5-8个标签，{image_count}张图描述+英文生图prompt。

输出JSON: {{"title":"...","content":"...","tags":[...],"images":[{{"index":1,"description":"...","prompt":"..."}}]}}"""

    def generate_post(
        self,
        keywords: str,
        hot_posts: List[Dict],
        target_audience: str = "年轻女性",
        style: str = "干货分享",
        image_count: int = 4,
        analysis: Optional[Dict] = None,
    ) -> Dict:
        """
        生成爆文笔记（两阶段生成：先正文，再图片描述）

        Args:
            keywords: 主题关键词
            hot_posts: 热点帖子参考（含完整内容）
            target_audience: 目标受众
            style: 笔记风格
            image_count: 图片数量
            analysis: 爆文分析结果（来自 search.analyze_hot_posts）
        """
        # 阶段1: 生成标题+正文+标签
        print("  阶段1: 生成标题+正文+标签...")
        text_prompt = self._build_text_prompt(
            keywords=keywords,
            hot_posts=hot_posts,
            target_audience=target_audience,
            style=style,
            analysis=analysis,
        )
        note = self._call_llm(text_prompt)

        # 阶段2: 基于正文生成图片描述
        print("  阶段2: 生成配图描述...")
        img_prompt = self._build_image_prompt(note, image_count)
        images = self._call_llm_images(img_prompt)

        if images:
            note["images"] = images

        return note

    def _build_prompt(
        self,
        keywords: str,
        hot_posts: List[Dict],
        target_audience: str,
        style: str,
        image_count: int,
        analysis: Optional[Dict] = None,
    ) -> str:
        """构建完整提示词（兼容旧接口）"""
        return self._build_text_prompt(
            keywords, hot_posts, target_audience, style, analysis
        )

    def _build_text_prompt(
        self,
        keywords: str,
        hot_posts: List[Dict],
        target_audience: str,
        style: str,
        analysis: Optional[Dict] = None,
    ) -> str:
        """构建正文生成提示词（不含图片，减少token）"""
        analysis_summary = self._format_analysis_summary(analysis)
        hot_posts_examples = self._format_hot_posts_examples(hot_posts)
        title_insights = self._format_title_insights(analysis)
        hook_insights = self._format_hook_insights(analysis)
        structure_insights = self._format_structure_insights(analysis)
        tag_insights = self._format_tag_insights(analysis)

        return self.prompt_template.format(
            keywords=keywords,
            target_audience=target_audience,
            style=style,
            image_count=4,  # placeholder, not used in text prompt
            analysis_summary=analysis_summary,
            hot_posts_examples=hot_posts_examples,
            title_insights=title_insights,
            hook_insights=hook_insights,
            structure_insights=structure_insights,
            tag_insights=tag_insights,
        )

    def _build_image_prompt(self, note: Dict, image_count: int = 4) -> str:
        """构建图片描述生成提示词"""
        title = note.get("title", "")
        content = note.get("content", "")[:500]
        tags = note.get("tags", [])

        return f"""根据以下小红书笔记，生成{image_count}张配图的描述和生图prompt。

笔记标题: {title}
笔记内容摘要: {content}
标签: {', '.join(tags[:5])}

请输出JSON数组格式：
[
  {{"index": 1, "description": "封面图：简短中文描述", "prompt": "英文生图prompt 30词内"}},
  {{"index": 2, "description": "配图描述", "prompt": "英文prompt 30词内"}},
  ...
]

要求：
- 封面图要能吸引点击，有标题文字排版空间
- 风格统一：扁平化插画，明亮色彩，小红书爆款风格
- 每个prompt控制在30个英文单词以内
- 直接输出JSON，不要代码块包裹"""

    def _call_llm_images(self, prompt: str) -> List[Dict]:
        """调用LLM生成图片描述"""
        if not self.api_key:
            return []

        try:
            request_body = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1024,
                "stream": False,
            }

            body_str = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                self.api_url,
                data=body_str,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60, context=self.ctx) as resp:
                result = json.loads(resp.read())

            if result.get("choices") and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                return self._parse_images_response(content)

        except Exception as e:
            print(f"  [WARN] 图片描述生成失败: {e}")

        return []

    def _parse_images_response(self, content: str) -> List[Dict]:
        """解析图片描述响应"""
        import re

        # 尝试提取JSON数组
        for pattern in [r'```json\s*\n(.*?)```', r'```\s*\n(.*?)```']:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    pass

        # 直接解析
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass

        # 找 [ 到 ]
        start = content.find('[')
        end = content.rfind(']')
        if start != -1 and end != -1:
            try:
                return json.loads(content[start:end+1])
            except json.JSONDecodeError:
                pass

        return []

    def _format_analysis_summary(self, analysis: Optional[Dict]) -> str:
        """格式化分析总结"""
        if not analysis:
            return "暂无分析数据，请根据经验和关键词自行判断最佳写作策略。"

        summary = analysis.get("summary", "")
        engagement = analysis.get("engagement_insights", {})

        parts = []
        if summary:
            parts.append(f"分析总结: {summary}")
        if engagement:
            parts.append(
                f"数据概览: 共{engagement.get('post_count', 0)}篇爆文，"
                f"平均{engagement.get('avg_likes', 0)}赞，"
                f"最高{engagement.get('max_likes', 0)}赞，"
                f"平均{engagement.get('avg_collections', 0)}收藏"
            )

        return "\n".join(parts) if parts else "暂无分析数据"

    def _format_hot_posts_examples(self, hot_posts: List[Dict]) -> str:
        """格式化高赞案例（适度截断，给正文留token）"""
        if not hot_posts:
            return "暂无高赞案例参考，请自行发挥。"

        examples = []
        for i, post in enumerate(hot_posts[:5], 1):
            title = post.get("title", "无标题")
            content = post.get("content", "无内容")
            # 截断到300字以内，保留关键内容
            if len(content) > 300:
                content = content[:300] + "..."
            likes = post.get("likes", 0)
            collections = post.get("collections", 0)
            tags = post.get("tags", [])
            tags_str = ", ".join(tags[:3]) if tags else "无标签"

            examples.append(
                f"【案例{i}】❤️{likes}赞 ⭐{collections}收藏\n"
                f"标题: {title}\n"
                f"标签: {tags_str}\n"
                f"内容: {content}"
            )

        return "\n\n".join(examples)

    def _format_title_insights(self, analysis: Optional[Dict]) -> str:
        """格式化标题洞察"""
        if not analysis:
            return "无数据"

        patterns = analysis.get("title_patterns", [])
        if not patterns:
            return "无标题数据"

        lines = []
        for p in patterns[:3]:
            lines.append(
                f"- {p['type']}: 平均{p['avg_likes']:.0f}赞 ({p['count']}篇) "
                f"最佳案例: {p['best_example'][:40]}"
            )
        return "\n".join(lines)

    def _format_hook_insights(self, analysis: Optional[Dict]) -> str:
        """格式化开头钩子洞察"""
        if not analysis:
            return "无数据"

        hooks = analysis.get("hook_styles", [])
        if not hooks:
            return "无开头数据"

        lines = []
        for h in hooks[:3]:
            examples = h.get("examples", [])
            example = examples[0][:50] if examples else "无"
            lines.append(
                f"- {h['type']}: 平均{h['avg_likes']:.0f}赞 ({h['count']}篇) "
                f"例: {example}"
            )
        return "\n".join(lines)

    def _format_structure_insights(self, analysis: Optional[Dict]) -> str:
        """格式化内容结构洞察"""
        if not analysis:
            return "无数据"

        structures = analysis.get("content_structures", [])
        if not structures:
            return "无结构数据"

        s = structures[0]
        lines = [
            f"- 有效长度: {s.get('effective_length_types', {})}",
            f"- 互动引导率: {s.get('cta_rate', 'N/A')}",
            f"- 分点列表率: {s.get('list_rate', 'N/A')}",
            f"- 平均emoji数: {s.get('avg_emoji_count', 0)}",
            f"- 平均段落数: {s.get('avg_paragraph_count', 0)}",
            f"- 洞察: {s.get('insight', 'N/A')}",
        ]
        return "\n".join(lines)

    def _format_tag_insights(self, analysis: Optional[Dict]) -> str:
        """格式化标签洞察"""
        if not analysis:
            return "无数据"

        tag_strategy = analysis.get("tag_strategy", {})
        common_tags = tag_strategy.get("common_tags", [])
        if not common_tags:
            return "无标签数据"

        tags = [f"#{t['tag']}({t['count']}次)" for t in common_tags[:8]]
        return f"热门标签: {' '.join(tags)}"

    # ============================================================
    # LLM 调用
    # ============================================================

    def _call_llm(self, prompt: str) -> Dict:
        """调用大模型"""
        if not self.api_key:
            print("  [WARN] 未配置API Key，使用模拟数据")
            return self._mock_response()

        try:
            request_body = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是一位顶级小红书内容操盘手，操盘过1000+篇10w+爆文。"
                            "你的文字有魔力——让人忍不住看完、收藏、转发。\n\n"
                            "【铁律】\n"
                            "1. 严禁以'大家好''今天给大家分享''给大家推荐''最近发现'开头\n"
                            "2. 开头必须是痛点场景、反常识、或亲身经历\n"
                            "3. 必须有情绪起伏，不要平铺直叙\n"
                            "4. 必须有具体干货和实操细节，不要假大空\n"
                            "5. 结尾必须有互动引导\n"
                            "6. 输出纯JSON对象，不要用```json```代码块包裹\n"
                            "7. image prompt控制在30个英文单词以内"
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False,
            }

            body_str = json.dumps(request_body, ensure_ascii=False).encode("utf-8")

            req = urllib.request.Request(
                self.api_url,
                data=body_str,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )

            timeout = 180 if "glm-5" in self.model else 120

            with urllib.request.urlopen(req, timeout=timeout, context=self.ctx) as resp:
                result = json.loads(resp.read())

            if result.get("choices") and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                return self._parse_llm_response(content)
            else:
                print(f"  [ERROR] API返回异常: {json.dumps(result, ensure_ascii=False)[:200]}")
                return self._mock_response()

        except Exception as e:
            print(f"  [ERROR] API调用失败: {e}")
            return self._mock_response()

    def _parse_llm_response(self, content: str) -> Dict:
        """解析LLM返回的JSON（多策略解析）"""
        import re

        # 策略1: 提取 ```json 代码块
        for pattern in [r'```json\s*\n(.*?)```', r'```\s*\n(.*?)```']:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    pass

        # 策略2: 直接解析整个内容
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass

        # 策略3: 找到第一个 { 到最后一个 } 之间的内容
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = content[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 修复未转义的换行符
                try:
                    fixed = re.sub(r'(?<=["\w])\n(?=[^",\]}])', r'\\n', json_str)
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        # 策略4: 截断修复 — 尝试补全不完整的JSON
        if start != -1:
            partial = content[start:]
            # 逐层闭合: 找到最后一个完整的键值对
            for close_attempts in [
                lambda s: s + '"}' ,  # 补 "}"
                lambda s: s + '"}]}' ,  # 补 "]}  }
                lambda s: s + '\n  ]\n}' ,  # 补数组和对象
            ]:
                try:
                    fixed = close_attempts(partial.rstrip('.… \n'))
                    return json.loads(fixed)
                except (json.JSONDecodeError, IndexError):
                    pass

        # 策略5: 正则提取 title 和 content（兜底方案）
        title_match = re.search(r'"title"\s*:\s*"([^"]*)"', content)
        content_match = re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', content, re.DOTALL)
        if title_match and content_match:
            print("  [WARN] 使用正则提取，可能缺少images/tags")
            # 尝试提取tags
            tags_match = re.search(r'"tags"\s*:\s*\[(.*?)\]', content, re.DOTALL)
            tags = []
            if tags_match:
                tags = re.findall(r'"([^"]+)"', tags_match.group(1))

            return {
                "title": title_match.group(1),
                "content": content_match.group(1).replace("\\n", "\n"),
                "tags": tags if tags else [],
                "images": [],
            }

        print(f"  [ERROR] 所有JSON解析策略均失败")
        print(f"  原始内容前500字: {content[:500]}...")
        return self._mock_response()

    def _mock_response(self) -> Dict:
        """模拟响应（降级方案）"""
        return {
            "title": "🔥 效率翻倍！5个AI工具让你告别加班",
            "content": (
                "姐妹们！今天必须分享这几个让我工作效率提升200%的AI神器！😭\n\n"
                "以前每天加班到10点，现在6点准时下班！\n\n"
                "1️⃣ **ChatGPT** - 写文案、做PPT、回复邮件，全能选手\n"
                "2️⃣ **Midjourney** - 做设计再也不用等设计师了\n"
                "3️⃣ **Notion AI** - 整理笔记、写周报，效率拉满\n"
                "4️⃣ **Claude** - 代码审查、技术文档，程序员必备\n"
                "5️⃣ **豆包** - 中文写作、学习辅导，学生党福音\n\n"
                "💡 使用技巧：\n"
                "- 不要直接复制，要根据自己需求调整\n"
                "- 多尝试不同的提示词\n"
                "- 结合多个工具使用效果更佳\n\n"
                "📌 收藏起来慢慢用！有问题评论区问我～"
            ),
            "tags": [
                "AI工具", "效率提升", "职场干货",
                "时间管理", "自律生活", "打工人必备",
            ],
            "images": [
                {
                    "index": 1,
                    "description": "封面图：现代简约办公桌面，5个AI工具logo展示",
                    "prompt": "Modern minimalist office desk, laptop showing 5 AI tool icons, flat illustration, Xiaohongshu cover style, bright warm colors, clean background",
                },
                {
                    "index": 2,
                    "description": "ChatGPT使用界面",
                    "prompt": "ChatGPT conversation interface showing high quality content generation, flat design, clean minimal, bright colors",
                },
                {
                    "index": 3,
                    "description": "效率对比图",
                    "prompt": "Left right comparison, tired overtime work vs happy leaving on time, flat illustration, warm colors, Xiaohongshu style",
                },
                {
                    "index": 4,
                    "description": "工具推荐清单",
                    "prompt": "Modern productivity tools list with icons, flat design, pastel colors, clean layout, Xiaohongshu style",
                },
            ],
        }

    def refine_post(self, post: Dict, feedback: str) -> Dict:
        """根据反馈优化笔记"""
        prompt = f"""请根据以下反馈优化这篇小红书笔记：

## 原始笔记
标题：{post.get('title', '')}
正文：{post.get('content', '')}
标签：{', '.join(post.get('tags', []))}

## 优化反馈
{feedback}

请输出优化后的完整JSON格式笔记。"""

        return self._call_llm(prompt)
