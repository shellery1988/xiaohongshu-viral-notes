"""
小红书MCP - 发布模块
使用 redbook-cli 发布笔记到小红书草稿箱
"""
import json
import subprocess
import os
from typing import Dict, List, Optional
from pathlib import Path


class XiaohongshuPublisher:
    """小红书发布器"""
    
    def __init__(self, cookie_file: str = "~/.redbook/cookies.json"):
        self.cookie_file = cookie_file
        self._check_installation()
    
    def _check_installation(self):
        """检查 redbook-cli 是否安装"""
        try:
            result = subprocess.run(
                ["xhs", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("redbook-cli 未安装，请运行: pip install redbook-cli")
        except FileNotFoundError:
            raise RuntimeError("redbook-cli 未安装，请运行: pip install redbook-cli")
    
    def publish(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None,
        visibility: str = "public",  # public, private, friends
        save_as_draft: bool = True
    ) -> Dict:
        """
        发布笔记到小红书
        
        Args:
            title: 笔记标题
            content: 笔记正文
            images: 图片文件路径列表
            tags: 标签列表
            visibility: 可见性
            save_as_draft: 是否保存为草稿
        
        Returns:
            发布结果
        """
        # 验证图片文件
        valid_images = self._validate_images(images)
        if not valid_images:
            return {"error": "没有有效的图片文件"}
        
        # 构建发布命令
        cmd = self._build_command(
            title=title,
            content=content,
            images=valid_images,
            tags=tags,
            visibility=visibility,
            save_as_draft=save_as_draft
        )
        
        # 执行发布
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                return {"error": f"发布失败: {result.stderr}"}
            
            return {
                "success": True,
                "output": result.stdout,
                "draft": save_as_draft
            }
            
        except subprocess.TimeoutExpired:
            return {"error": "发布超时"}
        except Exception as e:
            return {"error": f"发布异常: {str(e)}"}
    
    def _build_command(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None,
        visibility: str = "public",
        save_as_draft: bool = True
    ) -> List[str]:
        """构建 redbook-cli 发布命令"""
        
        # 构建发布命令 (CDP模式)
        cmd = [
            "xhs", "publish",
            "-t", title,
            "-c", content,
            "--engine", "cdp",
        ]
        
        # 添加图片
        for img in images:
            cmd.extend(["-i", img])
        
        # 添加标签
        if tags:
            for tag in tags:
                cmd.extend(["--tags", tag])
        
        # 可见性 (CDP模式下可能不生效，需要用户手动修改)
        if visibility != "public":
            cmd.extend(["--visibility", visibility])
        
        # 草稿模式
        if save_as_draft:
            cmd.append("--draft")
        
        return cmd
    
    def _validate_images(self, images: List[str]) -> List[str]:
        """验证图片文件是否存在"""
        valid = []
        for img_path in images:
            expanded_path = os.path.expanduser(img_path)
            if os.path.exists(expanded_path):
                valid.append(expanded_path)
            else:
                print(f"图片不存在: {img_path}")
        return valid
    
    def publish_from_note(
        self,
        note: Dict,
        image_dir: str = "output/images",
        save_as_draft: bool = True
    ) -> Dict:
        """
        从笔记内容发布
        
        Args:
            note: 笔记内容，包含 title, content, tags, images
            image_dir: 图片目录
            save_as_draft: 是否保存为草稿
        
        Returns:
            发布结果
        """
        title = note.get("title", "")
        content = note.get("content", "")
        tags = note.get("tags", [])
        
        # 获取图片文件路径
        images = note.get("images", [])
        image_paths = []
        for img in images:
            if "saved_path" in img:
                image_paths.append(img["saved_path"])
            elif "path" in img:
                image_paths.append(img["path"])
        
        # 如果没有保存的路径，尝试从目录中查找
        if not image_paths:
            image_paths = self._find_images_in_dir(image_dir)
        
        return self.publish(
            title=title,
            content=content,
            images=image_paths,
            tags=tags,
            save_as_draft=save_as_draft
        )
    
    def _find_images_in_dir(self, directory: str) -> List[str]:
        """在目录中查找图片文件"""
        expanded_dir = os.path.expanduser(directory)
        if not os.path.exists(expanded_dir):
            return []
        
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        images = []
        
        for file in os.listdir(expanded_dir):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                images.append(os.path.join(expanded_dir, file))
        
        # 按文件名排序
        images.sort()
        return images
    
    def check_login_status(self) -> bool:
        """检查登录状态 (CDP模式)"""
        try:
            # 尝试搜索来验证登录状态
            result = subprocess.run(
                ["xhs", "search", "测试", "--engine", "cdp", "--limit", "1"],
                capture_output=True,
                text=True,
                timeout=30
            )
            # 如果搜索成功（返回结果或找到0条），说明已登录
            return result.returncode == 0 or "搜索结果" in result.stdout
        except:
            return False
    
    def login(self) -> bool:
        """
        登录小红书
        
        Returns:
            登录是否成功
        """
        try:
            # 运行登录命令（需要用户交互）
            result = subprocess.run(
                ["xhs", "init"],
                timeout=300  # 5分钟超时
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("登录超时")
            return False
        except Exception as e:
            print(f"登录失败: {e}")
            return False


# 使用示例
if __name__ == "__main__":
    publisher = XiaohongshuPublisher()
    
    # 检查登录状态
    if not publisher.check_login_status():
        print("未登录，请先运行: xhs init")
    else:
        # 发布示例
        result = publisher.publish(
            title="测试笔记标题",
            content="这是测试笔记内容",
            images=["output/images/image_01.png"],
            tags=["测试", "小红书"],
            save_as_draft=True
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
