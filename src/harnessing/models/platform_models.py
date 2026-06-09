from __future__ import annotations

import os

from pydantic import BaseModel


class PlatformConfig(BaseModel):
    platform: str
    enabled: bool = True
    auth_type: str
    api_key: str = ""
    access_token: str = ""
    refresh_token: str = ""
    cookie_data: str = ""
    default_language: str
    default_format: str
    max_duration_seconds: int
    brand_name: str = "BeeVerse Consulting Service Limited"


class YouTubeConfig(PlatformConfig):
    platform: str = "youtube"
    auth_type: str = "oauth2"
    client_id: str = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret: str = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    default_language: str = "zh-HK"
    default_format: str = "16:9"
    max_duration_seconds: int = 900


class DouyinConfig(PlatformConfig):
    platform: str = "douyin"
    auth_type: str = "cookie"
    default_language: str = "zh-CN"
    default_format: str = "9:16"
    max_duration_seconds: int = 60


class BilibiliConfig(PlatformConfig):
    platform: str = "bilibili"
    auth_type: str = "cookie"
    sessdata: str = os.environ.get("BILIBILI_SESSDATA", "")
    default_language: str = "zh-CN"
    default_format: str = "16:9"
    max_duration_seconds: int = 1200


class XiaohongshuConfig(PlatformConfig):
    platform: str = "xiaohongshu"
    auth_type: str = "cookie"
    default_language: str = "zh-CN"
    default_format: str = "3:4"
    max_duration_seconds: int = 180


class WeChatMPConfig(PlatformConfig):
    platform: str = "wechat_mp"
    auth_type: str = "access_token"
    app_id: str = ""
    app_secret: str = ""
    default_language: str = "zh-CN"
    default_format: str = "16:9"
    max_duration_seconds: int = 600


class TikTokConfig(PlatformConfig):
    platform: str = "tiktok"
    auth_type: str = "oauth2"
    client_key: str = ""
    client_secret: str = ""
    default_language: str = "en-US"
    default_format: str = "9:16"
    max_duration_seconds: int = 60


class InstagramConfig(PlatformConfig):
    platform: str = "instagram"
    auth_type: str = "oauth2"
    app_id: str = ""
    app_secret: str = ""
    default_language: str = "en-US"
    default_format: str = "9:16"
    max_duration_seconds: int = 60


class AllPlatformsConfig(BaseModel):
    youtube: YouTubeConfig = YouTubeConfig()
    tiktok: TikTokConfig = TikTokConfig()
    instagram: InstagramConfig = InstagramConfig()
    douyin: DouyinConfig = DouyinConfig()
    bilibili: BilibiliConfig = BilibiliConfig()
    xiaohongshu: XiaohongshuConfig = XiaohongshuConfig()
    wechat_mp: WeChatMPConfig = WeChatMPConfig()
    wechat_video: PlatformConfig = PlatformConfig(
        platform="wechat_video",
        auth_type="cookie",
        default_language="zh-CN",
        default_format="9:16",
        max_duration_seconds=300,
    )
