---
name: xiaohongshu-viral-notes
version: 2.2.0
description: AI驱动的小红书爆款笔记自动化工具：搜索爆文 → 分析特征 → 智能写稿 → 省积分生图 → 发布草稿
author: shellery1988
license: MIT
---

# 小红书爆款笔记自动化 🚀

AI驱动的小红书内容自动化工具，完整流水线覆盖从热点搜索到草稿发布的全流程。

## 核心能力

- 🔍 **爆文分析引擎**：自动搜索同主题高赞文，分析标题/开头/结构/标签策略
- 📝 **AI智能写稿**：基于竞品洞察生成有干货的笔记，遵循小红书爆文公式
- 🎨 **精品封面图**：即梦AI生成1张高品质封面，色彩明朗、质感高级、构图大气
- 📤 **一键发布**：支持发布为草稿预览，确认后再公开

## 触发条件

当用户提出以下需求时使用此技能：
- "帮我写一篇小红书笔记"
- "生成小红书爆款笔记"
- "搜索小红书热点/爆文"
- "分析小红书爆文特征"
- "小红书内容创作"
- "帮我发布小红书笔记"

## 前置依赖

### 系统要求
- Python 3.10+
- Google Chrome（用于 CDP 浏览器自动化）

### Python 包
```
redbook-cli>=0.1.0   # 小红书搜索/发布 CLI
playwright>=1.40.0   # 浏览器自动化
pyyaml>=6.0          # 配置文件解析
Pillow>=10.0.0       # 图片裁剪处理
requests>=2.28.0     # HTTP 请求
websockets>=11.0     # CDP WebSocket 连接
```

### 外部服务
- **智谱AI API Key** — AI写稿（从 [open.bigmodel.cn](https://open.bigmodel.cn) 获取）
- **即梦 sessionid** — 图片生成（从 jimeng.jianying.com cookies 获取）
- **即梦 API 服务** — [jimeng-free-api](https://github.com/LLM-Red-Team/jimeng-free-api) 本地部署

## 安装配置

### 1. 安装 Python 依赖

```bash
cd <技能目录>
pip install -r requirements.txt
# 安装 redbook-cli 的 CDP scripts（首次使用必须）
xhs install-scripts
```

### 2. 配置文件

复制配置模板并填入密钥：

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml`：
- `writer.api_key`：智谱AI API Key
- `image_gen.sessionid`：即梦 sessionid
- `image_gen.api_base`：jimeng-free-api 地址（默认 `http://localhost:8000`）

### 3. 小红书登录

```bash
xhs login --cdp
# 在弹出的 Chrome 窗口中扫码登录
```

## 使用方式

### 通过 Pipeline（推荐）

```python
from src.pipeline import XiaohongshuPipeline

pipeline = XiaohongshuPipeline()  # 自动读取技能目录下的 config.yaml
result = pipeline.run(
    keywords="AI效率工具",
    target_audience="职场年轻人",
    style="干货安利",
    image_count=1,
    publish=False
)
```

### 通过命令行

```bash
cd <技能目录>
python main.py "AI效率工具"
python main.py "职场穿搭" --style "时尚穿搭" --audience "职场女性"
python main.py "学习方法" --publish --draft
```

### 单独使用各模块

```python
from src.search import XiaohongshuSearcher
from src.writer import XiaohongshuWriter
from src.image_gen import JimengImageGenerator
from src.publisher import XiaohongshuPublisher

# 搜索爆文
searcher = XiaohongshuSearcher()
hot_posts = searcher.get_trending_posts(topic="AI工具", days=7, min_likes=200)
analysis = searcher.analyze_hot_posts(hot_posts)

# AI写稿
writer = XiaohongshuWriter(api_key="your_key", model="glm-4-plus")
note = writer.generate_post(
    keywords="AI效率工具",
    hot_posts=hot_posts,
    target_audience="职场年轻人",
    style="干货分享",
    image_count=1,
    analysis=analysis,
)

# 生成配图
generator = JimengImageGenerator(sessionid="your_sessionid")
image_results = generator.generate_from_note(note, output_dir="output/images")

# 发布
publisher = XiaohongshuPublisher()
publisher.publish_from_note(note, image_dir="output/images", save_as_draft=True)
```

## 工作流程

```
关键词输入 → 搜索热点 → 爆文分析 → AI撰写(两阶段) → 即梦生图 → 发布草稿
```

1. **搜索热点** → 通过 redbook-cli 搜索关键词，按热度排序
2. **爆文分析** → 分析标题模式、开头钩子、内容结构、标签策略
3. **AI撰写** → 基于分析结果 + 爆文参考，两阶段生成（先正文再封面图描述）
4. **生成封面图** → 即梦AI生成1张精品封面，色彩明朗、质感高级，自动 9:16→3:4 裁剪为 1080x1440
5. **发布草稿** → 通过 redbook-cli 发布到小红书草稿箱

## 内容质量铁律

- 标题严格≤20字
- 禁止"大家好""今天给大家分享"开头
- 禁止编造数据
- 必须有具体操作步骤（干货）
- 必须有互动引导结尾
- 每篇仅1张封面图（精品策略，追求档次和质感）

## 文件结构

```
xiaohongshu-viral-notes/
├── SKILL.md                  # 本文件
├── README.md                 # GitHub 展示页
├── LICENSE                   # MIT 许可证
├── main.py                   # 命令行入口
├── requirements.txt          # Python 依赖
├── config.yaml.example       # 配置文件模板
├── src/
│   ├── __init__.py           # 包导出
│   ├── search.py             # 搜索 + 爆文分析引擎
│   ├── writer.py             # LLM 智能写稿（两阶段生成）
│   ├── image_gen.py          # 即梦生图（自动裁剪）
│   ├── publisher.py          # 发布到小红书
│   └── pipeline.py           # 完整流水线编排
└── prompts/
    ├── writer_prompt.md      # 写稿系统提示词模板
    └── image_prompt.md       # 生图提示词模板
```

## GitHub

https://github.com/shellery1988/xiaohongshu-viral-notes
