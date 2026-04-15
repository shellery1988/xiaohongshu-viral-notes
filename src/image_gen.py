"""
小红书MCP - 即梦图片生成模块
使用 jimeng-free-api 生成高质量配图
支持 jimeng-5.0/4.6/4.5 等模型，每日66次免费
"""
import json
import os
import base64
import time
import urllib.request
import ssl
from typing import Dict, List, Optional
from pathlib import Path


class JimengImageGenerator:
    """即梦图片生成器 - 通过 jimeng-free-api"""
    
    def __init__(
        self,
        sessionid: str = "",
        api_base: str = "http://localhost:8000",
        model: str = "jimeng-5.0"
    ):
        """
        初始化即梦图片生成器
        
        Args:
            sessionid: 即梦 sessionid (从 jimeng.jianying.com cookies 获取)
            api_base: jimeng-free-api 服务地址
            model: 模型名称 (jimeng-5.0, jimeng-4.6, jimeng-4.5 等)
        """
        self.sessionid = sessionid
        self.api_base = api_base
        self.model = model
        
        # SSL上下文
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
    
    def generate_image(
        self,
        prompt: str,
        ratio: str = "3:4",  # 小红书竖版
        resolution: str = "1k",
        negative_prompt: str = "",
        seed: Optional[int] = None
    ) -> Dict:
        """
        生成单张图片
        
        Args:
            prompt: 图片描述提示词
            ratio: 宽高比 (1:1, 3:4, 4:3, 16:9, 9:16)
                   ⚠️ 注意: 即梦API的"3:4"会返回横版，竖版请用"9:16"生成后裁剪
            resolution: 分辨率 (1k, 2k, 4k)
            negative_prompt: 负面提示词
            seed: 随机种子
        
        Returns:
            包含图片数据的字典
        """
        try:
            # 构建请求体
            request_body = {
                "model": self.model,
                "prompt": prompt,
                "n": 1,
                "ratio": ratio,
                "resolution": resolution,
            }
            if negative_prompt:
                request_body["negative_prompt"] = negative_prompt
            if seed:
                request_body["seed"] = seed
            
            body_str = json.dumps(request_body, ensure_ascii=False).encode('utf-8')
            
            # 发送请求
            req = urllib.request.Request(
                f"{self.api_base}/v1/images/generations",
                data=body_str,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.sessionid}",
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
            
            # 解析响应
            if result.get("data") and len(result["data"]) > 0:
                img_data = result["data"][0]
                
                # 获取图片URL
                if img_data.get("url"):
                    # 下载图片
                    img_req = urllib.request.Request(
                        img_data['url'],
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    with urllib.request.urlopen(img_req, timeout=60, context=self.ctx) as img_resp:
                        image_bytes = img_resp.read()
                    
                    return {
                        "success": True,
                        "image_bytes": image_bytes,
                        "image_url": img_data['url'],
                        "prompt": prompt,
                        "model": self.model,
                        "provider": "jimeng",
                        "size": len(image_bytes)
                    }
                elif img_data.get("b64_json"):
                    image_bytes = base64.b64decode(img_data["b64_json"])
                    return {
                        "success": True,
                        "image_bytes": image_bytes,
                        "prompt": prompt,
                        "model": self.model,
                        "provider": "jimeng",
                        "size": len(image_bytes)
                    }
                else:
                    return {"error": f"未知响应格式: {json.dumps(img_data, ensure_ascii=False)[:200]}"}
            else:
                error_msg = result.get("message", "未知错误")
                return {"error": f"即梦API错误: {error_msg}"}
                
        except Exception as e:
            return {"error": f"即梦生图失败: {str(e)}"}
    
    def generate_batch(
        self,
        image_prompts: List[Dict],
        output_dir: str = "output/images",
        auto_crop: bool = True
    ) -> List[Dict]:
        """
        批量生成图片
        
        Args:
            image_prompts: 图片提示词列表，每项包含 index, description, prompt
            output_dir: 输出目录
            auto_crop: 是否自动裁剪为3:4竖版（即梦API的3:4返回横版，需用9:16生成后裁剪）
        
        Returns:
            生成结果列表
        """
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        for i, item in enumerate(image_prompts, 1):
            desc = item.get('description', '')[:30]
            print(f"  生成图片 {i}/{len(image_prompts)}: {desc}...")
            
            # 用9:16生成竖版（3:4参数会返回横版）
            result = self.generate_image(
                prompt=item.get("prompt", ""),
                ratio="9:16"  # 强制使用9:16获取竖版
            )
            
            # 保存图片
            if result.get("success") and result.get("image_bytes"):
                image_path = os.path.join(output_dir, f"jimeng_{i:02d}.png")
                with open(image_path, "wb") as f:
                    f.write(result["image_bytes"])
                
                # 自动裁剪为3:4竖版 (1080x1440)
                if auto_crop:
                    try:
                        from PIL import Image
                        img = Image.open(image_path)
                        w, h = img.size
                        # 9:16 -> 3:4 裁剪
                        target_ratio = 3/4
                        new_w = int(h * target_ratio)
                        left = (w - new_w) // 2
                        img = img.crop((left, 0, left + new_w, h))
                        # 调整到标准小红书尺寸
                        img = img.resize((1080, 1440), Image.LANCZOS)
                        img.save(image_path, "PNG", quality=95)
                        print(f"    已裁剪为1080x1440: {image_path}")
                    except ImportError:
                        print(f"    [WARN] PIL未安装，跳过裁剪")
                    except Exception as e:
                        print(f"    [WARN] 裁剪失败: {e}")
                else:
                    print(f"    已保存: {image_path} ({result.get('size', 0)/1024:.0f} KB)")
                
                result["saved_path"] = image_path
            else:
                print(f"    失败: {result.get('error', '未知错误')}")
            
            results.append(result)
            time.sleep(2)  # 避免请求过快
        
        return results
    
    def generate_from_note(self, note: Dict, output_dir: str = "output/images") -> List[Dict]:
        """根据笔记内容生成配图"""
        images = note.get("images", [])
        if not images:
            return []
        return self.generate_batch(images, output_dir)
    
    def check_status(self) -> Dict:
        """检查API状态和积分"""
        try:
            req = urllib.request.Request(f"{self.api_base}/v1/models")
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                models = [m["id"] for m in result.get("data", []) if "jimeng" in m["id"] and "video" not in m["id"]]
                return {"success": True, "models": models}
        except Exception as e:
            return {"success": False, "error": str(e)}


# 使用示例
if __name__ == "__main__":
    import os
    sessionid = os.environ.get("JIMENG_SESSIONID", "")
    if not sessionid:
        print("请设置环境变量 JIMENG_SESSIONID")
        sys.exit(1)

    gen = JimengImageGenerator(sessionid=sessionid)

    # 检查状态
    status = gen.check_status()
    print(f"可用模型: {status.get('models', [])}")

    # 生成测试图片
    result = gen.generate_image(
        prompt="Modern minimalist office desk, laptop showing AI tools interface, flat illustration, bright colors, Xiaohongshu cover style",
        ratio="3:4"
    )

    if result.get("success"):
        with open("test_jimeng.png", "wb") as f:
            f.write(result["image_bytes"])
        print(f"图片已保存! 大小: {result.get('size', 0)/1024:.0f} KB")
    else:
        print(f"生成失败: {result.get('error')}")
