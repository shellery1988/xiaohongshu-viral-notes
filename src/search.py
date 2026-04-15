"""
小红书MCP - 热点搜索模块 + 爆文分析引擎
使用 redbook-cli (xhs) 搜索小红书热点爆文，获取详情，深度分析爆文特征
"""
import json
import re
import subprocess
from typing import List, Dict, Optional
from collections import Counter


class XiaohongshuSearcher:
    """小红书热点搜索引擎 + 爆文分析"""

    def __init__(self, cookie_file: str = "~/.redbook/cookies.json"):
        self.cookie_file = cookie_file
        self._check_installation()

    def _check_installation(self):
        """检查 redbook-cli 是否安装"""
        try:
            result = subprocess.run(
                ["xhs", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("redbook-cli 未安装，请运行: pip install redbook-cli")
        except FileNotFoundError:
            raise RuntimeError("redbook-cli 未安装，请运行: pip install redbook-cli")

    # ============================================================
    # 搜索
    # ============================================================

    def search(
        self, keyword: str, limit: int = 20, sort: str = "general"
    ) -> List[Dict]:
        """
        搜索小红书笔记（返回精简格式：标题、互动数据、ID、token）

        Args:
            keyword: 搜索关键词
            limit: 返回数量
            sort: 排序方式 (general/hot/new)

        Returns:
            笔记列表
        """
        try:
            cmd = [
                "xhs", "search", keyword,
                "--limit", str(limit),
                "--engine", "cdp",
                "--json-output",
            ]
            sort_map = {"general": "综合", "hot": "最多点赞", "new": "最新"}
            if sort in sort_map:
                cmd.extend(["--sort", sort_map[sort]])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                print(f"搜索失败: {result.stderr}")
                return []

            # 跳过非JSON行（如 "ℹ 正在搜索..."）
            raw = self._extract_json(result.stdout)
            if not raw:
                print("搜索结果无有效JSON")
                return []

            data = json.loads(raw)
            feeds = data.get("data", {}).get("feeds", [])
            return self._parse_search_feeds(feeds)

        except subprocess.TimeoutExpired:
            print("搜索超时")
            return []
        except Exception as e:
            print(f"搜索异常: {e}")
            return []

    def _extract_json(self, stdout: str) -> Optional[str]:
        """从stdout中提取JSON部分"""
        lines = stdout.strip().split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                return "\n".join(lines[i:])
        return None

    def _parse_search_feeds(self, feeds: List[Dict]) -> List[Dict]:
        """解析搜索结果feeds为统一格式"""
        parsed = []
        for feed in feeds:
            card = feed.get("noteCard", {})
            interact = card.get("interactInfo", {})
            user = card.get("user", {})

            parsed.append({
                "id": feed.get("id", ""),
                "xsec_token": feed.get("xsecToken", ""),
                "title": card.get("displayTitle", ""),
                "content": "",  # 搜索结果不含正文，需通过detail获取
                "likes": self._safe_int(interact.get("likedCount", 0)),
                "comments": self._safe_int(interact.get("commentCount", 0)),
                "collections": self._safe_int(interact.get("collectedCount", 0)),
                "shares": self._safe_int(interact.get("sharedCount", 0)),
                "tags": [],  # 需通过detail获取
                "author": user.get("nickname", user.get("nickName", "")),
                "note_type": card.get("type", "image"),
                "url": f"https://www.xiaohongshu.com/explore/{feed.get('id', '')}",
                "images": [],
                "has_detail": False,
            })
        return parsed

    def _safe_int(self, val) -> int:
        """安全转整数（xhs返回的互动数据是字符串）"""
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            # 去掉 "1.2w" 这种格式
            val = val.strip()
            if val.endswith("w"):
                try:
                    return int(float(val[:-1]) * 10000)
                except ValueError:
                    return 0
            try:
                return int(val)
            except ValueError:
                return 0
        return 0

    # ============================================================
    # 获取笔记详情（含完整正文）
    # ============================================================

    def get_note_detail(self, note_id: str, xsec_token: str) -> Dict:
        """
        获取单条笔记详情

        Returns:
            包含完整正文、标签、图片等信息的字典
        """
        try:
            cmd = [
                "xhs", "detail", note_id,
                "-t", xsec_token,
                "--engine", "cdp",
                "--json-output",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return {}

            raw = self._extract_json(result.stdout)
            if not raw:
                return {}

            data = json.loads(raw)
            note_data = data.get("data", {}).get("detail", {}).get("note", {})

            if not note_data:
                return {}

            # 解析标签
            tag_list = note_data.get("tagList", [])
            tags = [t.get("name", "") for t in tag_list if t.get("name")]

            # 从desc中提取话题标签（格式: #话题[话题]#）
            desc = note_data.get("desc", "")
            desc_tags = re.findall(r"#([^#\[]+?)(?:\[话题\])?#", desc)
            all_tags = list(dict.fromkeys(tags + desc_tags))  # 去重保序

            # 解析图片
            image_list = note_data.get("imageList", [])
            images = []
            for img in image_list:
                images.append({
                    "url": img.get("urlDefault", ""),
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                })

            interact = note_data.get("interactInfo", {})
            user = note_data.get("user", {})

            return {
                "id": note_id,
                "title": note_data.get("title", ""),
                "content": desc,
                "likes": self._safe_int(interact.get("likedCount", 0)),
                "comments": self._safe_int(interact.get("commentCount", 0)),
                "collections": self._safe_int(interact.get("collectedCount", 0)),
                "shares": self._safe_int(interact.get("shareCount", 0)),
                "tags": all_tags,
                "author": user.get("nickname", ""),
                "note_type": note_data.get("type", "image"),
                "images": images,
                "has_detail": True,
            }

        except Exception as e:
            print(f"获取详情失败 [{note_id}]: {e}")
            return {}

    def fetch_details(self, notes: List[Dict], max_count: int = 10) -> List[Dict]:
        """
        批量获取笔记详情（补充正文和标签）

        Args:
            notes: 搜索结果列表（需含id和xsec_token）
            max_count: 最多获取几条详情

        Returns:
            补充了content和tags的笔记列表
        """
        enriched = []
        count = 0
        for note in notes:
            if count >= max_count:
                enriched.append(note)
                continue

            note_id = note.get("id", "")
            xsec = note.get("xsec_token", "")

            if not note_id or not xsec:
                enriched.append(note)
                continue

            detail = self.get_note_detail(note_id, xsec)
            if detail and detail.get("content"):
                # 合并详情数据
                note.update({
                    "content": detail.get("content", note.get("content", "")),
                    "tags": detail.get("tags", note.get("tags", [])),
                    "images": detail.get("images", note.get("images", [])),
                    "has_detail": True,
                })
                count += 1
                print(f"  ✓ 获取详情 [{count}/{max_count}]: {note.get('title', '')[:30]}")
            else:
                print(f"  ✗ 详情为空: {note.get('title', '')[:30]}")

            enriched.append(note)

        return enriched

    # ============================================================
    # 热门帖子获取（含详情）
    # ============================================================

    def get_trending_posts(
        self, topic: str, days: int = 7, min_likes: int = 200
    ) -> List[Dict]:
        """
        获取指定话题的热门帖子（含完整正文）

        流程: 搜索 → 按热度排序 → 过滤低赞 → 获取top笔记详情
        """
        # 搜索
        notes = self.search(keyword=topic, limit=50, sort="hot")

        # 过滤高互动帖子
        trending = [n for n in notes if n.get("likes", 0) >= min_likes]

        # 如果过滤后太少，取top10
        if len(trending) < 3 and notes:
            trending = sorted(notes, key=lambda x: x.get("likes", 0), reverse=True)[:10]

        trending.sort(key=lambda x: x.get("likes", 0), reverse=True)
        top_notes = trending[:15]

        # 获取top笔记的完整内容
        print(f"  正在获取 {min(len(top_notes), 10)} 篇高赞笔记的详情...")
        enriched = self.fetch_details(top_notes, max_count=10)

        return enriched

    # ============================================================
    # 爆文分析引擎
    # ============================================================

    def analyze_hot_posts(self, hot_posts: List[Dict]) -> Dict:
        """
        深度分析爆文特征，提取可复用的写作模式

        Returns:
            分析结果字典
        """
        if not hot_posts:
            return {"summary": "暂无足够爆文数据进行分析", "top_examples": []}

        # 只分析有完整内容的帖子
        posts_with_content = [p for p in hot_posts if p.get("content")]
        posts_for_analysis = posts_with_content if posts_with_content else hot_posts

        analysis = {
            "title_patterns": self._analyze_titles(posts_for_analysis),
            "hook_styles": self._analyze_hooks(posts_for_analysis),
            "content_structures": self._analyze_content_structure(posts_for_analysis),
            "emoji_patterns": self._analyze_emoji_usage(posts_for_analysis),
            "tag_strategy": self._analyze_tag_strategy(posts_for_analysis),
            "engagement_insights": self._analyze_engagement(posts_for_analysis),
            "top_examples": self._get_top_examples(posts_for_analysis, n=5),
            "summary": "",
        }

        analysis["summary"] = self._generate_analysis_summary(analysis, posts_for_analysis)
        return analysis

    def _analyze_titles(self, posts: List[Dict]) -> List[Dict]:
        """分析标题句式和模式"""
        title_features = []

        for post in posts:
            title = post.get("title", "")
            if not title:
                continue

            features = {
                "text": title,
                "likes": post.get("likes", 0),
                "has_number": bool(re.search(r"\d+", title)),
                "has_emoji": bool(re.search(r"[\U0001F300-\U0001F9FF]", title)),
                "has_question": "?" in title or "？" in title,
                "has_exclamation": "!" in title or "！" in title,
                "has_punctuation": bool(re.search(r"[！？…~]", title)),
                "length": len(title),
            }

            if features["has_number"] and features["has_exclamation"]:
                features["pattern_type"] = "数字冲击型"
            elif features["has_question"]:
                features["pattern_type"] = "疑问钩子型"
            elif features["has_emoji"] and features["length"] <= 15:
                features["pattern_type"] = "Emoji短句型"
            elif features["length"] > 20:
                features["pattern_type"] = "长句信息型"
            else:
                features["pattern_type"] = "简洁直击型"

            title_features.append(features)

        patterns = []
        if title_features:
            pattern_counter = Counter(f["pattern_type"] for f in title_features)
            for pattern_type, count in pattern_counter.most_common(5):
                examples = [f for f in title_features if f["pattern_type"] == pattern_type]
                examples.sort(key=lambda x: x["likes"], reverse=True)
                patterns.append({
                    "type": pattern_type,
                    "count": count,
                    "avg_likes": sum(f["likes"] for f in examples) / len(examples),
                    "best_example": examples[0]["text"] if examples else "",
                    "best_likes": examples[0]["likes"] if examples else 0,
                })
            patterns.sort(key=lambda x: x["avg_likes"], reverse=True)

        return patterns

    def _analyze_hooks(self, posts: List[Dict]) -> List[Dict]:
        """分析开头钩子"""
        hooks = []

        for post in posts:
            content = post.get("content", "")
            if not content:
                continue

            sentences = re.split(r"[。！？\n]", content)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]
            if not sentences:
                continue

            first_sentence = sentences[0]
            hook_type = self._classify_hook(first_sentence)

            hooks.append({
                "text": first_sentence,
                "type": hook_type,
                "likes": post.get("likes", 0),
            })

        hook_types = {}
        for hook in hooks:
            htype = hook["type"]
            if htype not in hook_types:
                hook_types[htype] = {"count": 0, "total_likes": 0, "examples": []}
            hook_types[htype]["count"] += 1
            hook_types[htype]["total_likes"] += hook["likes"]
            hook_types[htype]["examples"].append(hook["text"])

        result = []
        for htype, data in sorted(hook_types.items(), key=lambda x: x[1]["total_likes"], reverse=True):
            result.append({
                "type": htype,
                "count": data["count"],
                "avg_likes": data["total_likes"] / data["count"] if data["count"] else 0,
                "examples": data["examples"][:3],
            })

        return result

    def _classify_hook(self, sentence: str) -> str:
        if re.search(r"(姐妹|兄弟|宝子|家人们|救命|绝了|天呐)", sentence):
            return "情绪共鸣型"
        elif re.search(r"(\d+\s*(个|款|种|步|天|分钟|小时))", sentence):
            return "数字清单型"
        elif re.search(r"(为什么|怎么|如何|到底|凭什么)", sentence):
            return "疑问激发型"
        elif re.search(r"(后悔|早知道|才发现|终于|原来)", sentence):
            return "后悔体/发现体"
        elif re.search(r"(别再|停止|千万别|不要)", sentence):
            return "否定警告型"
        elif re.search(r"(自从|用了|试了|体验了|发现)", sentence):
            return "亲身经历型"
        else:
            return "直叙型"

    def _analyze_content_structure(self, posts: List[Dict]) -> List[Dict]:
        structures = []

        for post in posts:
            content = post.get("content", "")
            if not content or len(content) < 30:
                continue

            lines = [l.strip() for l in content.split("\n") if l.strip()]

            structure = {
                "likes": post.get("likes", 0),
                "total_length": len(content),
                "line_count": len(lines),
                "has_emoji_list": bool(re.search(r"[①②③④⑤❶❷❸❹❺1-9]️⃣|[0-9]+[\.、)]", content)),
                "emoji_count": len(re.findall(r"[\U0001F300-\U0001F9FF]", content)),
                "paragraph_count": len(lines),
                "has_call_to_action": bool(re.search(r"(收藏|点赞|关注|评论|转发|分享).{0,10}(吧|哦|呀|～|~|！)", content)),
            }

            if structure["total_length"] < 200:
                structure["length_type"] = "精简型(<200字)"
            elif structure["total_length"] < 500:
                structure["length_type"] = "适中型(200-500字)"
            elif structure["total_length"] < 800:
                structure["length_type"] = "详细型(500-800字)"
            else:
                structure["length_type"] = "长文型(800字+)"

            structures.append(structure)

        if not structures:
            return []

        length_types = Counter(s["length_type"] for s in structures)
        has_cta = sum(1 for s in structures if s["has_call_to_action"])
        has_list = sum(1 for s in structures if s["has_emoji_list"])
        avg_emoji = sum(s["emoji_count"] for s in structures) / len(structures)
        avg_paragraphs = sum(s["paragraph_count"] for s in structures) / len(structures)
        total = len(structures)

        insights = []
        most_common_length = length_types.most_common(1)[0] if length_types else ("未知", 0)
        insights.append(f"最受欢迎的长度: {most_common_length[0]}（占比{most_common_length[1]/total*100:.0f}%）")
        if has_cta / total > 0.5:
            insights.append(f"超{has_cta/total*100:.0f}%的爆文有互动引导")
        if has_list / total > 0.4:
            insights.append(f"超{has_list/total*100:.0f}%的爆文使用分点列表")
        if avg_emoji > 5:
            insights.append(f"平均{avg_emoji:.0f}个emoji")

        return [{
            "effective_length_types": dict(length_types.most_common()),
            "cta_rate": f"{has_cta}/{total} ({has_cta/total*100:.0f}%)",
            "list_rate": f"{has_list}/{total} ({has_list/total*100:.0f}%)",
            "avg_emoji_count": round(avg_emoji, 1),
            "avg_paragraph_count": round(avg_paragraphs, 1),
            "insight": "；".join(insights),
        }]

    def _analyze_emoji_usage(self, posts: List[Dict]) -> List[Dict]:
        all_emojis = []
        for post in posts:
            content = post.get("content", "") + post.get("title", "")
            all_emojis.extend(re.findall(r"[\U0001F300-\U0001F9FF]", content))
        if not all_emojis:
            return []
        counter = Counter(all_emojis)
        return [{"emoji": e, "count": c} for e, c in counter.most_common(15)]

    def _analyze_tag_strategy(self, posts: List[Dict]) -> Dict:
        all_tags = []
        for post in posts:
            tags = post.get("tags", [])
            if isinstance(tags, list):
                all_tags.extend(tags)
        if not all_tags:
            return {"common_tags": [], "insight": "暂无标签数据"}
        counter = Counter(all_tags)
        common = counter.most_common(10)
        return {
            "common_tags": [{"tag": tag, "count": count} for tag, count in common],
            "total_unique_tags": len(set(all_tags)),
            "insight": f"最常见的标签: {', '.join(t[0] for t in common[:5])}",
        }

    def _analyze_engagement(self, posts: List[Dict]) -> Dict:
        if not posts:
            return {}
        likes = [p.get("likes", 0) for p in posts]
        comments = [p.get("comments", 0) for p in posts]
        collections = [p.get("collections", 0) for p in posts]
        return {
            "post_count": len(posts),
            "avg_likes": round(sum(likes) / len(likes)),
            "max_likes": max(likes),
            "avg_comments": round(sum(comments) / len(comments)),
            "avg_collections": round(sum(collections) / len(collections)),
            "like_collection_ratio": round(sum(collections) / sum(likes), 2) if sum(likes) > 0 else 0,
        }

    def _get_top_examples(self, posts: List[Dict], n: int = 5) -> List[Dict]:
        sorted_posts = sorted(posts, key=lambda x: x.get("likes", 0), reverse=True)
        examples = []
        for post in sorted_posts[:n]:
            examples.append({
                "title": post.get("title", ""),
                "content": post.get("content", ""),
                "likes": post.get("likes", 0),
                "comments": post.get("comments", 0),
                "collections": post.get("collections", 0),
                "tags": post.get("tags", [])[:5],
            })
        return examples

    def _generate_analysis_summary(self, analysis: Dict, posts: List[Dict]) -> str:
        parts = []
        if analysis["title_patterns"]:
            best = analysis["title_patterns"][0]
            parts.append(f"标题: {best['type']}效果最好(平均{best['avg_likes']:.0f}赞)")
        if analysis["hook_styles"]:
            best = analysis["hook_styles"][0]
            parts.append(f"开头: {best['type']}最有效(平均{best['avg_likes']:.0f}赞)")
        if analysis["content_structures"]:
            parts.append(f"结构: {analysis['content_structures'][0].get('insight', '')}")
        if analysis["tag_strategy"].get("insight"):
            parts.append(f"标签: {analysis['tag_strategy']['insight']}")
        return " | ".join(parts) if parts else "分析数据不足"
