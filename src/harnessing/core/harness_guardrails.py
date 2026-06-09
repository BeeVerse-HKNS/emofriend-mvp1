from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from harnessing.core.memory_engine import MemoryEngine
from harnessing.models.content_models import (
    ComicScript,
    GeneratedAudio,
    GeneratedImage,
    PublishResult,
    TopicProposal,
    VideoOutput,
)

logger = structlog.get_logger()

_BRAND_NAME = "BeeVerse"


class HarnessGuardrails:
    def __init__(self, memory_engine: MemoryEngine):
        self.memory = memory_engine

    def check_feedforward(self, stage: str, data: Any) -> tuple[bool, list[str]]:
        checkers = {
            "research": self._check_research_feedforward,
            "script": self._check_script_feedforward,
            "image": self._check_image_feedforward,
            "audio": self._check_audio_feedforward,
            "video": self._check_video_feedforward,
            "publish": self._check_publish_feedforward,
        }
        checker = checkers.get(stage)
        if not checker:
            return True, []
        return checker(data)

    def check_feedback(self, stage: str, result: Any) -> tuple[bool, list[str]]:
        checkers = {
            "research": self._check_research_feedback,
            "script": self._check_script_feedback,
            "image": self._check_image_feedback,
            "audio": self._check_audio_feedback,
            "video": self._check_video_feedback,
            "publish": self._check_publish_feedback,
        }
        checker = checkers.get(stage)
        if not checker:
            return True, []
        return checker(result)

    def capture_error(self, stage: str, error: Exception, context: dict[str, Any] | None = None) -> None:
        self.memory.save_error_rule(
            error_desc=f"[{stage}] {type(error).__name__}: {error}",
            root_cause=context.get("root_cause", "Unknown") if context else "Unknown",
            rule_text=(
                context.get("rule", f"Handle {type(error).__name__} in {stage} stage")
                if context
                else f"Handle {type(error).__name__} in {stage} stage"
            ),
            rule_source=f"harness_guardrails.py:{stage}",
        )
        logger.error("error_captured", stage=stage, error=str(error))

    def _check_research_feedforward(self, data: Any) -> tuple[bool, list[str]]:
        if not isinstance(data, TopicProposal):
            return False, ["Data must be a TopicProposal"]
        errors: list[str] = []
        if not data.keywords:
            errors.append("Topic must have keywords")
        if data.trend_score < 0.3:
            errors.append(f"Trend score too low: {data.trend_score:.2f} < 0.3")
        if not data.title_en:
            errors.append("English title is required")
        return len(errors) == 0, errors

    def _check_script_feedforward(self, data: Any) -> tuple[bool, list[str]]:
        if not isinstance(data, ComicScript):
            return False, ["Data must be a ComicScript"]
        errors: list[str] = []
        if not data.hook:
            errors.append("Script must have a hook")
        if len(data.scenes) < 3:
            errors.append(f"Script must have at least 3 scenes, got {len(data.scenes)}")
        if not data.cta:
            errors.append("Script must have a CTA")
        if data.total_duration_seconds < 30:
            errors.append(f"Script too short: {data.total_duration_seconds:.0f}s < 30s")
        for scene in data.scenes:
            if not scene.image_prompt:
                errors.append(f"Scene {scene.scene_number} missing image_prompt")
        return len(errors) == 0, errors

    def _check_image_feedforward(self, data: Any) -> tuple[bool, list[str]]:
        if not isinstance(data, list):
            return False, ["Data must be a list of GeneratedImage"]
        errors: list[str] = []
        for img in data:
            if not isinstance(img, GeneratedImage):
                errors.append(f"Item is not a GeneratedImage: {type(img)}")
                continue
            if not img.file_path:
                errors.append(f"Scene {img.scene_number} missing file_path")
        return len(errors) == 0, errors

    def _check_audio_feedforward(self, data: Any) -> tuple[bool, list[str]]:
        if not isinstance(data, list):
            return False, ["Data must be a list of GeneratedAudio"]
        errors: list[str] = []
        for af in data:
            if not isinstance(af, GeneratedAudio):
                errors.append(f"Item is not a GeneratedAudio: {type(af)}")
                continue
            if not af.file_path:
                errors.append(f"Scene {af.scene_number} missing file_path")
        return len(errors) == 0, errors

    def _check_video_feedforward(self, data: Any) -> tuple[bool, list[str]]:
        if not isinstance(data, VideoOutput):
            return False, ["Data must be a VideoOutput"]
        errors: list[str] = []
        if not data.file_path:
            errors.append("Video missing file_path")
        if data.duration_seconds <= 0:
            errors.append(f"Video duration invalid: {data.duration_seconds}")
        return len(errors) == 0, errors

    def _check_publish_feedforward(self, data: Any) -> tuple[bool, list[str]]:
        if not isinstance(data, dict):
            return True, []
        errors: list[str] = []
        title = data.get("title", "")
        if not title:
            errors.append("Title is required for publishing")
        description = data.get("description", "")
        if _BRAND_NAME.lower() not in description.lower():
            errors.append(f"Description must contain brand name: {_BRAND_NAME}")
        tags = data.get("tags", [])
        if len(tags) < 3:
            errors.append(f"At least 3 tags required, got {len(tags)}")
        return len(errors) == 0, errors

    def _check_research_feedback(self, result: Any) -> tuple[bool, list[str]]:
        if not isinstance(result, TopicProposal):
            return True, []
        warnings: list[str] = []
        related = self.memory.search_related(result.title_en, n_results=5)
        recent_similar = [
            r for r in related
            if r.get("metadata", {}).get("type") == "decision"
            and "topic" in r.get("document", "").lower()
        ]
        if len(recent_similar) >= 3:
            warnings.append("Similar topics found in recent decisions — ensure novelty")
        return True, warnings

    def _check_script_feedback(self, result: Any) -> tuple[bool, list[str]]:
        if not isinstance(result, ComicScript):
            return True, []
        warnings: list[str] = []
        hook_keywords = ["how", "why", "what", "secret", "mistake", "never", "always", "驚", "點解", "為何", "為什麼"]
        hook_lower = result.hook.lower()
        if not any(kw in hook_lower for kw in hook_keywords):
            warnings.append("Hook may not be attention-grabbing — consider using question words or strong statements")
        return True, warnings

    def _check_image_feedback(self, result: Any) -> tuple[bool, list[str]]:
        if not isinstance(result, list):
            return True, []
        warnings: list[str] = []
        for img in result:
            if isinstance(img, GeneratedImage) and img.file_path:
                path = Path(img.file_path)
                if path.exists() and path.stat().st_size < 10240:
                    warnings.append(
                        f"Scene {img.scene_number} image file is very small "
                        f"({path.stat().st_size} bytes) — may be blank"
                    )
        return True, warnings

    def _check_audio_feedback(self, result: Any) -> tuple[bool, list[str]]:
        if not isinstance(result, list):
            return True, []
        warnings: list[str] = []
        for af in result:
            if isinstance(af, GeneratedAudio):
                if af.duration_seconds <= 0:
                    warnings.append(f"Scene {af.scene_number} audio duration is 0 — may be silent")
        return True, warnings

    def _check_video_feedback(self, result: Any) -> tuple[bool, list[str]]:
        if not isinstance(result, VideoOutput):
            return True, []
        warnings: list[str] = []
        if result.file_path:
            path = Path(result.file_path)
            if not path.exists():
                warnings.append("Video file does not exist")
        return True, warnings

    def _check_publish_feedback(self, result: Any) -> tuple[bool, list[str]]:
        if not isinstance(result, PublishResult):
            return True, []
        warnings: list[str] = []
        if not result.success:
            warnings.append(f"Publish failed: {result.error_message}")
        if result.success and not result.url:
            warnings.append("Publish succeeded but no URL returned")
        return result.success, warnings
