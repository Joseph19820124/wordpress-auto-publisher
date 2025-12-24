"""
AI Agent 资讯自动获取器
从多个RSS源获取AI/Agent相关新闻
"""

import feedparser
import requests
from datetime import datetime, timedelta
from typing import Optional
import re
import html
from dataclasses import dataclass
import hashlib


@dataclass
class NewsItem:
    title: str
    link: str
    summary: str
    source: str
    published: datetime

    @property
    def id(self) -> str:
        """生成唯一ID用于去重"""
        return hashlib.md5(self.link.encode()).hexdigest()[:12]


class AINewsFetcher:
    """AI Agent 新闻获取器"""

    # AI/Agent 相关的RSS源
    RSS_SOURCES = {
        # 英文源
        "Hacker News (AI)": "https://hnrss.org/newest?q=AI+agent+OR+LLM+OR+GPT+OR+Claude",
        "MIT Tech Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "OpenAI Blog": "https://openai.com/blog/rss.xml",
        "Google AI Blog": "https://blog.google/technology/ai/rss/",
        "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
        "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",

        # 中文源
        "机器之心": "https://rsshub.app/jiqizhixin",
        "量子位": "https://rsshub.app/qbitai",
        "AI科技评论": "https://rsshub.app/leiphone/category/ai",
    }

    # 关键词过滤 (必须包含至少一个)
    KEYWORDS = [
        "agent", "ai agent", "llm", "gpt", "claude", "gemini",
        "langchain", "autogpt", "chatgpt", "copilot",
        "大模型", "智能体", "AI助手", "人工智能",
        "anthropic", "openai", "机器人", "自动化"
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; AINewsFetcher/1.0)"
        })

    def fetch_rss(self, url: str, source_name: str) -> list[NewsItem]:
        """获取单个RSS源的新闻"""
        items = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:  # 每个源最多20条
                # 解析发布时间
                published = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])

                # 清理摘要
                summary = ""
                if hasattr(entry, 'summary'):
                    summary = self._clean_html(entry.summary)[:500]
                elif hasattr(entry, 'description'):
                    summary = self._clean_html(entry.description)[:500]

                items.append(NewsItem(
                    title=entry.get('title', 'Untitled'),
                    link=entry.get('link', ''),
                    summary=summary,
                    source=source_name,
                    published=published
                ))
        except Exception as e:
            print(f"获取 {source_name} 失败: {e}")

        return items

    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        text = html.unescape(text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _is_relevant(self, item: NewsItem) -> bool:
        """检查新闻是否与AI Agent相关"""
        text = f"{item.title} {item.summary}".lower()
        return any(kw.lower() in text for kw in self.KEYWORDS)

    def fetch_all(self, hours: int = 24) -> list[NewsItem]:
        """
        获取所有源的新闻

        Args:
            hours: 只获取最近N小时的新闻

        Returns:
            按时间排序的新闻列表
        """
        all_items = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        print(f"正在获取最近 {hours} 小时的AI Agent资讯...")

        for source_name, url in self.RSS_SOURCES.items():
            print(f"  获取: {source_name}")
            items = self.fetch_rss(url, source_name)

            # 过滤时间和相关性
            for item in items:
                if item.published >= cutoff_time and self._is_relevant(item):
                    all_items.append(item)

        # 去重 (按链接)
        seen = set()
        unique_items = []
        for item in all_items:
            if item.id not in seen:
                seen.add(item.id)
                unique_items.append(item)

        # 按时间排序
        unique_items.sort(key=lambda x: x.published, reverse=True)

        print(f"共获取 {len(unique_items)} 条相关资讯")
        return unique_items

    def format_as_blog_post(
        self,
        items: list[NewsItem],
        max_items: int = 15,
        date: datetime = None
    ) -> tuple[str, str, str]:
        """
        将新闻格式化为博客文章

        Returns:
            (title, content, excerpt)
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y年%m月%d日")
        title = f"AI Agent 每日资讯 - {date_str}"

        # 按来源分组
        by_source = {}
        for item in items[:max_items]:
            if item.source not in by_source:
                by_source[item.source] = []
            by_source[item.source].append(item)

        # 生成HTML内容
        content_parts = [
            f"<p>今日精选 <strong>{len(items[:max_items])}</strong> 条 AI Agent 领域重要资讯。</p>",
            "<hr />"
        ]

        for source, source_items in by_source.items():
            content_parts.append(f"<h2>{source}</h2>")
            content_parts.append("<ul>")

            for item in source_items:
                time_str = item.published.strftime("%H:%M")
                content_parts.append(
                    f'<li><strong><a href="{item.link}" target="_blank">{item.title}</a></strong>'
                    f'<br /><small>{time_str}</small>'
                )
                if item.summary:
                    content_parts.append(f"<p>{item.summary[:200]}...</p>")
                content_parts.append("</li>")

            content_parts.append("</ul>")

        content_parts.append("<hr />")
        content_parts.append(
            f"<p><em>本文由 AI Agent 资讯聚合系统自动生成，更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</em></p>"
        )

        content = "\n".join(content_parts)
        excerpt = f"AI Agent 领域 {date_str} 资讯汇总，共 {len(items[:max_items])} 条精选内容。"

        return title, content, excerpt


# 使用示例
if __name__ == "__main__":
    fetcher = AINewsFetcher()

    # 获取最近24小时的新闻
    items = fetcher.fetch_all(hours=24)

    if items:
        # 格式化为博客文章
        title, content, excerpt = fetcher.format_as_blog_post(items)

        print(f"\n标题: {title}")
        print(f"摘要: {excerpt}")
        print(f"\n内容预览:\n{content[:1000]}...")
    else:
        print("没有获取到相关资讯")
