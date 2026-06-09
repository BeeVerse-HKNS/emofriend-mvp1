from __future__ import annotations

import argparse
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

logger = structlog.get_logger()
console = Console()

YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v="
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/channel/"


class VideoMetadata(BaseModel):
    video_id: str
    title: str
    description: str = ""
    published_at: str = ""
    channel_title: str = ""
    tags: list[str] = Field(default_factory=list)
    category_id: str = ""
    duration: str = ""
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0


class ChannelInfo(BaseModel):
    channel_id: str
    title: str
    description: str = ""
    subscriber_count: int = 0
    video_count: int = 0
    view_count: int = 0
    published_at: str = ""


def _parse_iso8601_duration(duration: str) -> str:
    if not duration:
        return ""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return duration
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    return " ".join(parts) if parts else "0s"


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


class YouTubeScanner:
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self._youtube = None
        if api_key:
            try:
                from googleapiclient.discovery import build

                self._youtube = build("youtube", "v3", developerKey=api_key)
                logger.info("youtube_api_initialized")
            except Exception as e:
                logger.error("youtube_api_init_failed", error=str(e))
                self._youtube = None

    def search_channel(self, query: str) -> list[dict]:
        if self._youtube:
            return self._search_channel_api(query)
        return self._search_channel_fallback(query)

    def _search_channel_api(self, query: str) -> list[dict]:
        try:
            request = self._youtube.search().list(
                part="snippet",
                type="channel",
                q=query,
                maxResults=10,
            )
            response = request.execute()
            results: list[dict] = []
            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                results.append({
                    "channel_id": snippet.get("channelId", ""),
                    "title": snippet.get("channelTitle", ""),
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt", ""),
                })
            logger.info("channel_search_api_completed", query=query, count=len(results))
            return results
        except Exception as e:
            logger.error("channel_search_api_failed", error=str(e))
            return self._search_channel_fallback(query)

    def _search_channel_fallback(self, query: str) -> list[dict]:
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgIQAg%3D%3D"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8")

            pattern = r'"channelId":"(UC[^"]+)".*?"title":"([^"]*)"'
            matches = re.findall(pattern, html)
            seen: set[str] = set()
            results: list[dict] = []
            for channel_id, title in matches:
                if channel_id not in seen:
                    seen.add(channel_id)
                    results.append({
                        "channel_id": channel_id,
                        "title": title,
                        "description": "",
                        "published_at": "",
                    })
            logger.info("channel_search_fallback_completed", query=query, count=len(results))
            return results[:10]
        except Exception as e:
            logger.error("channel_search_fallback_failed", error=str(e))
            return []

    def scan_channel(self, channel_id: str, max_results: int = 50) -> list[dict]:
        if not self._youtube:
            logger.error("scan_channel_requires_api_key")
            console.print("[red]Error: YouTube API key is required for channel scanning.[/red]")
            return []

        try:
            channel_info = self._get_channel_info(channel_id)
            video_ids = self._get_channel_video_ids(channel_id, max_results)
            if not video_ids:
                logger.warning("no_videos_found", channel_id=channel_id)
                return []

            videos = self.get_video_details(video_ids)
            logger.info("channel_scan_completed", channel_id=channel_id, count=len(videos))
            return videos
        except Exception as e:
            logger.error("channel_scan_failed", channel_id=channel_id, error=str(e))
            return []

    def _get_channel_info(self, channel_id: str) -> ChannelInfo | None:
        try:
            request = self._youtube.channels().list(part="snippet,statistics", id=channel_id)
            response = request.execute()
            items = response.get("items", [])
            if not items:
                return None
            item = items[0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            return ChannelInfo(
                channel_id=channel_id,
                title=snippet.get("title", ""),
                description=snippet.get("description", ""),
                subscriber_count=_safe_int(stats.get("subscriberCount")),
                video_count=_safe_int(stats.get("videoCount")),
                view_count=_safe_int(stats.get("viewCount")),
                published_at=snippet.get("publishedAt", ""),
            )
        except Exception as e:
            logger.error("get_channel_info_failed", error=str(e))
            return None

    def _get_channel_video_ids(self, channel_id: str, max_results: int) -> list[str]:
        video_ids: list[str] = []
        try:
            request = self._youtube.search().list(
                part="id",
                channelId=channel_id,
                type="video",
                maxResults=min(max_results, 50),
                order="date",
            )
            while request and len(video_ids) < max_results:
                response = request.execute()
                for item in response.get("items", []):
                    video_id = item.get("id", {}).get("videoId", "")
                    if video_id:
                        video_ids.append(video_id)
                next_token = response.get("nextPageToken")
                if next_token and len(video_ids) < max_results:
                    request = self._youtube.search().list(
                        part="id",
                        channelId=channel_id,
                        type="video",
                        maxResults=min(max_results - len(video_ids), 50),
                        order="date",
                        pageToken=next_token,
                    )
                else:
                    break
        except Exception as e:
            logger.error("get_channel_video_ids_failed", error=str(e))
        return video_ids[:max_results]

    def get_video_details(self, video_ids: list[str]) -> list[dict]:
        if not video_ids:
            return []
        if not self._youtube:
            logger.error("get_video_details_requires_api_key")
            return []

        results: list[dict] = []
        batch_size = 50
        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i : i + batch_size]
            try:
                request = self._youtube.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=",".join(batch),
                )
                response = request.execute()
                for item in response.get("items", []):
                    snippet = item.get("snippet", {})
                    content = item.get("contentDetails", {})
                    stats = item.get("statistics", {})
                    meta = VideoMetadata(
                        video_id=item.get("id", ""),
                        title=snippet.get("title", ""),
                        description=snippet.get("description", ""),
                        published_at=snippet.get("publishedAt", ""),
                        channel_title=snippet.get("channelTitle", ""),
                        tags=snippet.get("tags", []) or [],
                        category_id=_safe_str(snippet.get("categoryId")),
                        duration=_parse_iso8601_duration(content.get("duration", "")),
                        view_count=_safe_int(stats.get("viewCount")),
                        like_count=_safe_int(stats.get("likeCount")),
                        comment_count=_safe_int(stats.get("commentCount")),
                    )
                    results.append(meta.model_dump())
            except Exception as e:
                logger.error("get_video_details_batch_failed", error=str(e), batch=i)
        logger.info("video_details_retrieved", count=len(results))
        return results

    def save_to_knowledge_base(self, videos: list[dict], output_path: str) -> None:
        if not videos:
            logger.warning("no_videos_to_save")
            return

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        channel_title = videos[0].get("channel_title", "Unknown Channel")
        channel_id = ""

        first_video = videos[0]
        for v in videos:
            if v.get("description"):
                first_video = v
                break

        lines: list[str] = []
        lines.append(f"# {channel_title} — YouTube Channel Videos")
        lines.append("")
        lines.append("| # | Title | Published | Views | Duration |")
        lines.append("|---|-------|-----------|--------|----------|")
        for idx, video in enumerate(videos, 1):
            title = video.get("title", "").replace("|", "\\|")
            published = video.get("published_at", "")[:10]
            views = video.get("view_count", 0)
            duration = video.get("duration", "")
            vid = video.get("video_id", "")
            link = f"[{title}]({YOUTUBE_VIDEO_URL}{vid})"
            lines.append(f"| {idx} | {link} | {published} | {views:,} | {duration} |")

        lines.append("")
        lines.append("---")
        lines.append("")

        for idx, video in enumerate(videos, 1):
            vid = video.get("video_id", "")
            title = video.get("title", "")
            lines.append(f"## {idx}. {title}")
            lines.append("")
            lines.append(f"- **Video ID**: {vid}")
            lines.append(f"- **URL**: {YOUTUBE_VIDEO_URL}{vid}")
            lines.append(f"- **Published**: {video.get('published_at', '')}")
            lines.append(f"- **Duration**: {video.get('duration', '')}")
            lines.append(f"- **Views**: {video.get('view_count', 0):,}")
            lines.append(f"- **Likes**: {video.get('like_count', 0):,}")
            lines.append(f"- **Comments**: {video.get('comment_count', 0):,}")
            lines.append(f"- **Category ID**: {video.get('category_id', '')}")

            tags = video.get("tags", [])
            if tags:
                lines.append(f"- **Tags**: {', '.join(tags)}")

            description = video.get("description", "")
            if description:
                lines.append("")
                lines.append("### Description")
                lines.append("")
                lines.append(description[:2000])
                if len(description) > 2000:
                    lines.append("\n... (truncated)")
            lines.append("")
            lines.append("---")
            lines.append("")

        output.write_text("\n".join(lines), encoding="utf-8")
        logger.info("knowledge_base_saved", path=str(output), video_count=len(videos))
        console.print(f"[green]Saved {len(videos)} videos to {output}[/green]")


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Channel Scanner for Harnessing")
    parser.add_argument("--api-key", type=str, default="", help="YouTube Data API v3 key")
    parser.add_argument("--channel", type=str, default="", help="Channel name to search for")
    parser.add_argument("--channel-id", type=str, default="", help="YouTube channel ID (UC...)")
    parser.add_argument("--output", type=str, default="docs/knowledge-base/youtube-channel.md", help="Output markdown file path")
    parser.add_argument("--max-results", type=int, default=50, help="Maximum number of videos to retrieve")

    args = parser.parse_args()

    if not args.channel and not args.channel_id:
        console.print("[red]Error: Provide --channel (name) or --channel-id to scan.[/red]")
        return

    scanner = YouTubeScanner(api_key=args.api_key)

    channel_id = args.channel_id

    if args.channel and not channel_id:
        console.print(f"[cyan]Searching for channel: {args.channel}[/cyan]")
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Searching...", total=None)
            results = scanner.search_channel(args.channel)

        if not results:
            console.print("[red]No channels found.[/red]")
            return

        table = Table(title="Channel Search Results")
        table.add_column("#", style="dim")
        table.add_column("Channel ID")
        table.add_column("Title")
        table.add_column("Description", max_width=50)

        for idx, ch in enumerate(results, 1):
            table.add_row(str(idx), ch.get("channel_id", ""), ch.get("title", ""), ch.get("description", "")[:80])

        console.print(table)

        if len(results) == 1:
            channel_id = results[0]["channel_id"]
            console.print(f"[green]Auto-selecting: {results[0]['title']}[/green]")
        else:
            try:
                choice = int(console.input("[bold]Select channel number: [/bold]"))
                if 1 <= choice <= len(results):
                    channel_id = results[choice - 1]["channel_id"]
                else:
                    console.print("[red]Invalid selection.[/red]")
                    return
            except (ValueError, EOFError):
                console.print("[red]Invalid input.[/red]")
                return

    if not channel_id:
        console.print("[red]No channel ID resolved.[/red]")
        return

    console.print(f"[cyan]Scanning channel: {channel_id}[/cyan]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Scanning videos...", total=None)
        videos = scanner.scan_channel(channel_id, max_results=args.max_results)

    if not videos:
        console.print("[yellow]No videos found or API key required.[/yellow]")
        return

    table = Table(title=f"Videos ({len(videos)} found)")
    table.add_column("#", style="dim")
    table.add_column("Title", max_width=40)
    table.add_column("Published")
    table.add_column("Views", justify="right")
    table.add_column("Duration")

    for idx, v in enumerate(videos[:20], 1):
        table.add_row(
            str(idx),
            v.get("title", "")[:40],
            v.get("published_at", "")[:10],
            f"{v.get('view_count', 0):,}",
            v.get("duration", ""),
        )

    console.print(table)
    if len(videos) > 20:
        console.print(f"[dim]... and {len(videos) - 20} more videos[/dim]")

    scanner.save_to_knowledge_base(videos, args.output)


if __name__ == "__main__":
    main()
