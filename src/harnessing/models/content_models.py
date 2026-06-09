from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Audience(str, Enum):
    KIDS = "kids"
    STUDENTS = "students"
    WORKING = "working"
    ELDERLY = "elderly"


class Language(str, Enum):
    ZH_HK = "zh-HK"
    ZH_CN = "zh-CN"
    EN_US = "en-US"


class Platform(str, Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    XIAOHONGSHU = "xiaohongshu"
    WECHAT_MP = "wechat_mp"
    WECHAT_VIDEO = "wechat_video"


class VideoFormat(str, Enum):
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"
    SQUARE_1_1 = "1:1"
    PORTRAIT_3_4 = "3:4"


class TopicProposal(BaseModel):
    id: str
    title_zh_hk: str
    title_zh_cn: str
    title_en: str
    keywords: list[str]
    target_audience: list[Audience]
    reference_urls: list[str]
    trend_score: float = Field(ge=0.0, le=1.0)
    created_at: datetime


class ComicScene(BaseModel):
    scene_number: int
    description: str
    narration_zh_hk: str
    narration_zh_cn: str
    narration_en: str
    dialogue: list[str]
    image_prompt: str
    duration_seconds: float


class ComicScript(BaseModel):
    id: str
    topic_id: str
    hook: str
    scenes: list[ComicScene]
    cta: str
    total_duration_seconds: float
    language: Language
    created_at: datetime


class GeneratedImage(BaseModel):
    scene_number: int
    file_path: str
    prompt_used: str


class GeneratedAudio(BaseModel):
    scene_number: int
    file_path: str
    voice_name: str
    language: Language
    duration_seconds: float


class VideoOutput(BaseModel):
    id: str
    script_id: str
    platform: Platform
    file_path: str
    duration_seconds: float
    format: VideoFormat
    resolution: str
    has_subtitles: bool = True
    has_bg_music: bool = True


class PublishResult(BaseModel):
    platform: Platform
    video_id: str
    url: str
    published_at: datetime
    success: bool
    error_message: str = ""


class ContentPipelineResult(BaseModel):
    topic: TopicProposal
    script: ComicScript
    images: list[GeneratedImage]
    audio_files: list[GeneratedAudio]
    videos: list[VideoOutput]
    publish_results: list[PublishResult]
