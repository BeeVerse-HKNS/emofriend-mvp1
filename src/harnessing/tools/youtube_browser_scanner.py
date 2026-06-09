from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import structlog
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

logger = structlog.get_logger()
console = Console()

HIGH_RELEVANCE = [
    "AI Agent", "Agent", "Harness", "Manus", "n8n", "OPC",
    "自動化", "automation", "MCP", "Claude Code", "Codex",
    "AI 轉型", "AI工具", "AI教學", "智能體", "workflow",
    "Zapier", "OpenClaw", "龍蝦",
]

MEDIUM_RELEVANCE = [
    "ChatGPT", "Claude", "Gemini", "GPT", "AI", "LLM",
    "SEO", "營銷", "marketing", "Perplexity", "DeepSeek",
]


class YouTubeBrowserScanner:
    def __init__(self, headless: bool = True) -> None:
        self.headless = headless

    def scan_channel(self, channel_url: str, max_scrolls: int = 100) -> list[dict]:
        from playwright.sync_api import sync_playwright

        videos: list[dict] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="zh-HK",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            logger.info("navigating_to_channel", url=channel_url)
            page.goto(channel_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            self._dismiss_consent(page)

            try:
                page.wait_for_selector(
                    "ytd-rich-item-renderer",
                    timeout=20000,
                )
            except Exception:
                logger.warning("no_video_elements_found")
                browser.close()
                return videos

            self._scroll_to_bottom(page, max_scrolls)
            videos = self._extract_videos(page)
            browser.close()

        logger.info("scan_completed", video_count=len(videos))
        return videos

    def _dismiss_consent(self, page) -> None:
        consent_selectors = [
            "button.ytp-mdx-privacy-popup-confirm",
            "button[aria-label*='Accept']",
            "button[aria-label*='Reject']",
            "ytd-button-renderer#accept-button button",
            "button.yt-spec-button-shape-next--call-to-action",
        ]
        for sel in consent_selectors:
            try:
                btn = page.query_selector(sel)
                if btn:
                    btn.click()
                    page.wait_for_timeout(1500)
                    logger.info("consent_dialog_dismissed", selector=sel)
                    return
            except Exception:
                continue

    def _scroll_to_bottom(self, page, max_scrolls: int = 100) -> None:
        no_new_count = 0
        prev_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("載入影片中...", total=max_scrolls)

            for i in range(max_scrolls):
                page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                page.wait_for_timeout(2500)

                current_count = page.evaluate(
                    "document.querySelectorAll('ytd-rich-item-renderer').length"
                )

                progress.update(task, advance=1, description=f"載入影片中... ({current_count} 部)")

                if current_count == prev_count:
                    no_new_count += 1
                else:
                    no_new_count = 0

                prev_count = current_count

                if no_new_count >= 8:
                    logger.info("scroll_stopped_no_new_videos", scrolls=i + 1, videos=current_count)
                    break

    def _extract_videos(self, page) -> list[dict]:
        js_extract = """
        () => {
            const videos = [];
            const elements = document.querySelectorAll('ytd-rich-item-renderer');
            elements.forEach(el => {
                try {
                    const titleLink = el.querySelector('a.ytLockupMetadataViewModelTitle');
                    if (!titleLink) return;
                    const title = (titleLink.innerText || '').trim();
                    const href = titleLink.getAttribute('href') || '';
                    const idMatch = href.match(/\\/watch\\?v=([a-zA-Z0-9_-]{11})/);
                    if (!idMatch) return;
                    const videoId = idMatch[1];

                    const metaSpans = el.querySelectorAll('yt-content-metadata-view-model span');
                    let viewCount = '';
                    let publishedTime = '';
                    metaSpans.forEach(span => {
                        const text = (span.innerText || '').trim();
                        if (text.includes('收看') || text.includes('觀看') || text.toLowerCase().includes('views')) {
                            viewCount = text;
                        } else if (text.match(/前|ago|天|週|月|年|小時|分鐘|日/)) {
                            publishedTime = text;
                        }
                    });

                    let duration = '';
                    const durEl = el.querySelector('yt-thumbnail-bottom-overlay-view-model, badge-shape');
                    if (durEl) duration = (durEl.innerText || '').trim();

                    videos.push({title, video_id: videoId, view_count: viewCount, published_time: publishedTime, duration});
                } catch(e) {}
            });
            return videos;
        }
        """
        raw_videos = page.evaluate(js_extract)
        videos: list[dict] = []
        seen_ids: set[str] = set()
        for v in raw_videos:
            if v["video_id"] in seen_ids:
                continue
            seen_ids.add(v["video_id"])
            relevance = self._classify_relevance(v["title"])
            videos.append({
                "title": v["title"],
                "video_id": v["video_id"],
                "url": f"https://www.youtube.com/watch?v={v['video_id']}",
                "view_count": v["view_count"],
                "published_time": v["published_time"],
                "duration": v["duration"],
                "relevance": relevance,
            })
        logger.info("videos_extracted", count=len(videos))
        return videos

    def _classify_relevance(self, title: str) -> str:
        title_lower = title.lower()
        for kw in HIGH_RELEVANCE:
            if kw.lower() in title_lower:
                return "high"
        for kw in MEDIUM_RELEVANCE:
            if kw.lower() in title_lower:
                return "medium"
        return "low"

    def save_to_markdown(self, videos: list[dict], output_path: str, channel_name: str = "") -> None:
        if not videos:
            logger.warning("no_videos_to_save")
            return

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if not channel_name:
            channel_name = "YouTube Channel"

        now = datetime.now().strftime("%Y-%m-%d")
        high_count = sum(1 for v in videos if v["relevance"] == "high")
        medium_count = sum(1 for v in videos if v["relevance"] == "medium")
        low_count = sum(1 for v in videos if v["relevance"] == "low")

        lines: list[str] = []
        lines.append(f"# {channel_name} — 影片目錄")
        lines.append("")
        lines.append(f"> 掃描日期：{now}")
        lines.append("")
        lines.append("## 統計摘要")
        lines.append("")
        lines.append("| 指標 | 數值 |")
        lines.append("|------|------|")
        lines.append(f"| 總影片數 | {len(videos)} |")
        lines.append(f"| ⭐ 高相關 | {high_count} |")
        lines.append(f"| 🟡 中相關 | {medium_count} |")
        lines.append(f"| ⚪ 低相關 | {low_count} |")
        lines.append("")
        lines.append("## 全部影片")
        lines.append("")
        lines.append("| # | 相關度 | 標題 | 發佈時間 | 觀看次數 | 時長 |")
        lines.append("|---|--------|------|----------|----------|------|")

        for idx, v in enumerate(videos, 1):
            title = v["title"].replace("|", "\\|")
            marker = "⭐" if v["relevance"] == "high" else ("🟡" if v["relevance"] == "medium" else "⚪")
            lines.append(
                f"| {idx} | {marker} | [{title}]({v['url']}) | {v['published_time']} | {v['view_count']} | {v['duration']} |"
            )

        high_videos = [v for v in videos if v["relevance"] == "high"]
        if high_videos:
            lines.append("")
            lines.append("## ⭐ 高相關影片詳情")
            lines.append("")
            for idx, v in enumerate(high_videos, 1):
                lines.append(f"### ⭐ {v['title']}")
                lines.append("")
                lines.append(f"- **Video ID**: {v['video_id']}")
                lines.append(f"- **URL**: {v['url']}")
                lines.append(f"- **發佈時間**: {v['published_time']}")
                lines.append(f"- **觀看次數**: {v['view_count']}")
                lines.append(f"- **時長**: {v['duration']}")
                lines.append("")
                lines.append("---")
                lines.append("")

        output.write_text("\n".join(lines), encoding="utf-8")
        logger.info("markdown_saved", path=str(output), video_count=len(videos))
        console.print(f"[green]已儲存 {len(videos)} 部影片至 {output}[/green]")


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Browser Scanner for Harnessing")
    parser.add_argument("--channel-url", type=str, required=True, help="YouTube channel URL")
    parser.add_argument(
        "--output",
        type=str,
        default="docs/research/video-transcripts/ompshek-channel-catalog.md",
        help="Output markdown file path",
    )
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run browser with visible window")
    parser.add_argument("--max-scrolls", type=int, default=100, help="Maximum scroll iterations")

    args = parser.parse_args()

    scanner = YouTubeBrowserScanner(headless=args.headless)

    console.print(f"[cyan]掃描頻道：{args.channel_url}[/cyan]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("啟動瀏覽器...", total=None)
        videos = scanner.scan_channel(args.channel_url, max_scrolls=args.max_scrolls)

    if not videos:
        console.print("[yellow]未找到任何影片[/yellow]")
        return

    table = Table(title=f"掃描結果（{len(videos)} 部影片）")
    table.add_column("#", style="dim")
    table.add_column("相關度")
    table.add_column("標題", max_width=40)
    table.add_column("發佈時間")
    table.add_column("觀看次數")
    table.add_column("時長")

    for idx, v in enumerate(videos[:30], 1):
        marker = "⭐" if v["relevance"] == "high" else ("🟡" if v["relevance"] == "medium" else "⚪")
        table.add_row(
            str(idx),
            marker,
            v["title"][:40],
            v["published_time"],
            v["view_count"],
            v["duration"],
        )

    console.print(table)
    if len(videos) > 30:
        console.print(f"[dim]... 及另外 {len(videos) - 30} 部影片[/dim]")

    scanner.save_to_markdown(videos, args.output)


if __name__ == "__main__":
    main()
