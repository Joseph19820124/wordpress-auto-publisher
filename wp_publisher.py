"""
WordPress REST API Publisher
用于自动发布AI Agent资讯博客
"""

import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class WordPressPublisher:
    def __init__(
        self,
        site_url: str = None,
        username: str = None,
        app_password: str = None
    ):
        """
        初始化WordPress发布器

        Args:
            site_url: WordPress站点URL (如: https://wordpress-bitnami-production.up.railway.app)
            username: WordPress用户名
            app_password: Application Password (在WordPress后台生成)
        """
        self.site_url = (site_url or os.getenv("WP_SITE_URL", "")).rstrip("/")
        self.username = username or os.getenv("WP_USERNAME")
        self.app_password = app_password or os.getenv("WP_APP_PASSWORD")
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self.auth = HTTPBasicAuth(self.username, self.app_password)

    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            response = requests.get(
                f"{self.api_base}/users/me",
                auth=self.auth,
                timeout=10
            )
            if response.status_code == 200:
                user = response.json()
                print(f"连接成功! 当前用户: {user['name']}")
                return True
            else:
                print(f"连接失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"连接错误: {e}")
            return False

    def create_post(
        self,
        title: str,
        content: str,
        status: str = "publish",
        categories: list[int] = None,
        tags: list[int] = None,
        excerpt: str = None,
        featured_image_id: int = None,
        slug: str = None
    ) -> dict:
        """
        创建新文章

        Args:
            title: 文章标题
            content: 文章内容 (支持HTML)
            status: 发布状态 (publish/draft/pending/private)
            categories: 分类ID列表
            tags: 标签ID列表
            excerpt: 文章摘要
            featured_image_id: 特色图片ID
            slug: 文章别名/URL

        Returns:
            创建的文章信息
        """
        data = {
            "title": title,
            "content": content,
            "status": status,
        }

        if categories:
            data["categories"] = categories
        if tags:
            data["tags"] = tags
        if excerpt:
            data["excerpt"] = excerpt
        if featured_image_id:
            data["featured_media"] = featured_image_id
        if slug:
            data["slug"] = slug

        response = requests.post(
            f"{self.api_base}/posts",
            auth=self.auth,
            json=data,
            timeout=30
        )

        if response.status_code == 201:
            post = response.json()
            print(f"文章发布成功: {post['link']}")
            return post
        else:
            raise Exception(f"发布失败: {response.status_code} - {response.text}")

    def create_category(self, name: str, slug: str = None, description: str = None) -> dict:
        """创建分类"""
        data = {"name": name}
        if slug:
            data["slug"] = slug
        if description:
            data["description"] = description

        response = requests.post(
            f"{self.api_base}/categories",
            auth=self.auth,
            json=data,
            timeout=10
        )

        if response.status_code == 201:
            return response.json()
        elif response.status_code == 400 and "term_exists" in response.text:
            # 分类已存在，获取现有的
            return self.get_category_by_name(name)
        else:
            raise Exception(f"创建分类失败: {response.text}")

    def get_category_by_name(self, name: str) -> Optional[dict]:
        """根据名称获取分类"""
        response = requests.get(
            f"{self.api_base}/categories",
            params={"search": name},
            auth=self.auth,
            timeout=10
        )
        if response.status_code == 200:
            categories = response.json()
            for cat in categories:
                if cat["name"].lower() == name.lower():
                    return cat
        return None

    def create_tag(self, name: str, slug: str = None) -> dict:
        """创建标签"""
        data = {"name": name}
        if slug:
            data["slug"] = slug

        response = requests.post(
            f"{self.api_base}/tags",
            auth=self.auth,
            json=data,
            timeout=10
        )

        if response.status_code == 201:
            return response.json()
        elif response.status_code == 400 and "term_exists" in response.text:
            return self.get_tag_by_name(name)
        else:
            raise Exception(f"创建标签失败: {response.text}")

    def get_tag_by_name(self, name: str) -> Optional[dict]:
        """根据名称获取标签"""
        response = requests.get(
            f"{self.api_base}/tags",
            params={"search": name},
            auth=self.auth,
            timeout=10
        )
        if response.status_code == 200:
            tags = response.json()
            for tag in tags:
                if tag["name"].lower() == name.lower():
                    return tag
        return None

    def upload_image(self, image_path: str, alt_text: str = None) -> dict:
        """
        上传图片到媒体库

        Args:
            image_path: 图片文件路径
            alt_text: 图片替代文本

        Returns:
            上传的媒体信息
        """
        filename = os.path.basename(image_path)

        # 确定MIME类型
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        ext = os.path.splitext(filename)[1].lower()
        mime_type = mime_types.get(ext, "application/octet-stream")

        with open(image_path, "rb") as f:
            response = requests.post(
                f"{self.api_base}/media",
                auth=self.auth,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": mime_type
                },
                data=f,
                timeout=60
            )

        if response.status_code == 201:
            media = response.json()
            if alt_text:
                # 更新alt文本
                requests.post(
                    f"{self.api_base}/media/{media['id']}",
                    auth=self.auth,
                    json={"alt_text": alt_text},
                    timeout=10
                )
            print(f"图片上传成功: {media['source_url']}")
            return media
        else:
            raise Exception(f"上传失败: {response.text}")

    def batch_publish(self, posts: list[dict]) -> list[dict]:
        """
        批量发布文章

        Args:
            posts: 文章列表，每个文章是一个字典，包含title, content等字段

        Returns:
            发布成功的文章列表
        """
        results = []
        for i, post_data in enumerate(posts, 1):
            try:
                print(f"发布第 {i}/{len(posts)} 篇: {post_data.get('title', 'Untitled')}")
                result = self.create_post(**post_data)
                results.append(result)
            except Exception as e:
                print(f"发布失败: {e}")
                results.append({"error": str(e), "title": post_data.get("title")})

        success_count = len([r for r in results if "error" not in r])
        print(f"\n发布完成: {success_count}/{len(posts)} 篇成功")
        return results


# 使用示例
if __name__ == "__main__":
    # 初始化发布器
    publisher = WordPressPublisher()

    # 测试连接
    if not publisher.test_connection():
        print("请检查 .env 文件中的配置")
        exit(1)

    # 创建AI Agent分类
    ai_category = publisher.create_category(
        name="AI Agent",
        slug="ai-agent",
        description="AI Agent相关资讯"
    )
    print(f"分类ID: {ai_category['id']}")

    # 创建标签
    tags = []
    for tag_name in ["AI", "Agent", "LLM", "资讯"]:
        tag = publisher.create_tag(tag_name)
        tags.append(tag["id"])

    # 发布示例文章
    post = publisher.create_post(
        title="AI Agent每日资讯 - " + datetime.now().strftime("%Y-%m-%d"),
        content="""
        <h2>今日要闻</h2>
        <p>这是一篇关于AI Agent的资讯文章...</p>

        <h3>1. 重要更新</h3>
        <p>内容描述...</p>

        <h3>2. 行业动态</h3>
        <p>更多内容...</p>
        """,
        status="publish",
        categories=[ai_category["id"]],
        tags=tags,
        excerpt="AI Agent领域最新动态汇总"
    )

    print(f"\n文章链接: {post['link']}")
