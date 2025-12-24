"""
AI Agent 资讯自动发布系统
每日自动获取AI资讯并发布到WordPress
"""

import os
import sys
from datetime import datetime
from typing import Optional

from news_fetcher import AINewsFetcher
from wp_publisher import WordPressPublisher


class AutoPublisher:
    """自动发布器：获取资讯 -> 格式化 -> 发布到WordPress"""

    def __init__(self):
        self.fetcher = AINewsFetcher()
        self.publisher = WordPressPublisher()
        self.ai_category_id = None
        self.tag_ids = []

    def setup_taxonomy(self):
        """设置分类和标签"""
        # 创建或获取 AI Agent 分类
        category = self.publisher.create_category(
            name="AI Agent",
            slug="ai-agent",
            description="AI Agent 相关资讯"
        )
        self.ai_category_id = category["id"]
        print(f"分类 ID: {self.ai_category_id}")

        # 创建标签
        tag_names = ["AI", "Agent", "LLM", "每日资讯", "人工智能"]
        for name in tag_names:
            tag = self.publisher.create_tag(name)
            self.tag_ids.append(tag["id"])
        print(f"标签 IDs: {self.tag_ids}")

    def publish_daily_news(
        self,
        hours: int = 24,
        max_items: int = 15,
        status: str = "publish"
    ) -> Optional[dict]:
        """
        发布每日资讯

        Args:
            hours: 获取最近N小时的新闻
            max_items: 最多包含多少条新闻
            status: 发布状态 (publish/draft)

        Returns:
            发布的文章信息
        """
        print("=" * 50)
        print(f"AI Agent 每日资讯发布系统")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)

        # 测试连接
        if not self.publisher.test_connection():
            print("WordPress 连接失败，请检查配置")
            return None

        # 设置分类和标签
        self.setup_taxonomy()

        # 获取新闻
        print("\n[1/3] 获取资讯中...")
        items = self.fetcher.fetch_all(hours=hours)

        if not items:
            print("没有获取到相关资讯，跳过发布")
            return None

        # 格式化为博客文章
        print("\n[2/3] 格式化文章...")
        title, content, excerpt = self.fetcher.format_as_blog_post(
            items,
            max_items=max_items
        )

        # 发布到WordPress
        print("\n[3/3] 发布到WordPress...")
        post = self.publisher.create_post(
            title=title,
            content=content,
            excerpt=excerpt,
            status=status,
            categories=[self.ai_category_id],
            tags=self.tag_ids
        )

        print("\n" + "=" * 50)
        print("发布成功!")
        print(f"标题: {title}")
        print(f"链接: {post['link']}")
        print(f"状态: {status}")
        print(f"新闻数: {len(items[:max_items])}")
        print("=" * 50)

        return post

    def publish_multiple(
        self,
        count: int = 10,
        hours_per_batch: int = 24,
        items_per_post: int = 5
    ) -> list[dict]:
        """
        发布多篇资讯文章 (用于批量发布不同主题)

        这个方法将新闻分成多个批次发布

        Args:
            count: 要发布的文章数量
            hours_per_batch: 每批获取多少小时的新闻
            items_per_post: 每篇文章包含多少条新闻

        Returns:
            发布的文章列表
        """
        print(f"批量发布模式: 计划发布 {count} 篇文章")

        if not self.publisher.test_connection():
            print("WordPress 连接失败")
            return []

        self.setup_taxonomy()

        # 获取所有新闻
        all_items = self.fetcher.fetch_all(hours=hours_per_batch * count)

        if len(all_items) < count * items_per_post:
            print(f"新闻数量不足: 获取到 {len(all_items)} 条，需要 {count * items_per_post} 条")
            count = len(all_items) // items_per_post

        results = []
        for i in range(count):
            start_idx = i * items_per_post
            end_idx = start_idx + items_per_post
            batch_items = all_items[start_idx:end_idx]

            if not batch_items:
                break

            # 生成带序号的标题
            date_str = datetime.now().strftime("%Y年%m月%d日")
            title = f"AI Agent 资讯速递 #{i + 1} - {date_str}"

            _, content, excerpt = self.fetcher.format_as_blog_post(
                batch_items,
                max_items=items_per_post
            )

            try:
                post = self.publisher.create_post(
                    title=title,
                    content=content,
                    excerpt=excerpt,
                    status="publish",
                    categories=[self.ai_category_id],
                    tags=self.tag_ids
                )
                results.append(post)
                print(f"  [{i + 1}/{count}] 发布成功: {post['link']}")
            except Exception as e:
                print(f"  [{i + 1}/{count}] 发布失败: {e}")
                results.append({"error": str(e)})

        success_count = len([r for r in results if "error" not in r])
        print(f"\n批量发布完成: {success_count}/{count} 篇成功")
        return results


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Agent 资讯自动发布")
    parser.add_argument(
        "--mode",
        choices=["daily", "batch"],
        default="daily",
        help="发布模式: daily=每日汇总, batch=批量发布"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="获取最近N小时的新闻 (默认24)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="批量模式下发布的文章数量 (默认10)"
    )
    parser.add_argument(
        "--items",
        type=int,
        default=15,
        help="每篇文章包含的新闻数量 (默认15)"
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="发布为草稿而不是直接发布"
    )

    args = parser.parse_args()

    auto = AutoPublisher()

    if args.mode == "daily":
        auto.publish_daily_news(
            hours=args.hours,
            max_items=args.items,
            status="draft" if args.draft else "publish"
        )
    else:
        auto.publish_multiple(
            count=args.count,
            items_per_post=args.items
        )


if __name__ == "__main__":
    main()
