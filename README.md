# xiaohongshu-viral-notes 🚀

AI驱动的小红书爆款笔记自动化工具。搜索爆文 → 分析特征 → 智能写稿 → 省积分生图 → 发布草稿。

## ✨ 特性

- 🔍 **爆文分析引擎** — 自动搜索同主题高赞文，分析标题/开头/结构/标签策略
- 📝 **AI智能写稿** — 基于竞品洞察，遵循小红书爆文公式生成有干货的笔记
- 🎨 **省积分生图** — 即梦AI生图，自动 9:16→3:4 裁剪为 1080x1440
- 📤 **一键发布** — 支持发布为草稿预览，确认后再公开

## 🛠 安装

### 1. 克隆仓库

```bash
git clone https://github.com/shellery1988/xiaohongshu-viral-notes.git
cd xiaohongshu-viral-notes
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
xhs install-scripts  # 安装 CDP 浏览器自动化脚本
```

### 3. 配置

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml`，填入：
- **智谱AI API Key** — 从 [open.bigmodel.cn](https://open.bigmodel.cn) 获取
- **即梦 sessionid** — 从 jimeng.jianying.com cookies 获取
- **jimeng-free-api 地址** — 本地部署 [jimeng-free-api](https://github.com/LLM-Red-Team/jimeng-free-api)

### 4. 小红书登录

```bash
xhs login --cdp
# 在弹出的 Chrome 窗口中扫码登录
```

## 🚀 使用

### 命令行

```bash
python main.py "AI效率工具"
python main.py "职场穿搭" --style "时尚穿搭" --audience "职场女性"
python main.py "学习方法" --publish --draft
```

### Python API

```python
from src.pipeline import XiaohongshuPipeline

pipeline = XiaohongshuPipeline()
result = pipeline.run(
    keywords="AI效率工具",
    target_audience="职场年轻人",
    style="干货安利",
    image_count=3,
    publish=False
)
```

## 📁 项目结构

```
├── src/
│   ├── search.py        # 搜索 + 爆文分析引擎
│   ├── writer.py        # LLM 智能写稿（两阶段生成）
│   ├── image_gen.py     # 即梦生图（自动裁剪）
│   ├── publisher.py     # 发布到小红书
│   └── pipeline.py      # 完整流水线编排
├── prompts/
│   ├── writer_prompt.md # 写稿系统提示词模板
│   └── image_prompt.md  # 生图提示词模板
├── main.py              # 命令行入口
├── config.yaml.example  # 配置文件模板
└── requirements.txt     # Python 依赖
```

## ⚙️ 依赖

| 依赖 | 用途 |
|------|------|
| [redbook-cli](https://github.com/Youhai020616/xiaohongshu) | 小红书搜索/发布（CDP引擎） |
| [智谱AI GLM](https://open.bigmodel.cn) | AI爆文撰写 |
| [jimeng-free-api](https://github.com/LLM-Red-Team/jimeng-free-api) | 即梦AI图片生成 |
| Google Chrome | CDP 浏览器自动化 |

## 📄 License

[MIT](LICENSE)
