from __future__ import annotations

import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
from litellm import completion

logger = structlog.get_logger()

OLLAMA_BASE = "http://localhost:11434"
MODEL_FAST = "ollama/qwen3:4b"
MODEL_STANDARD = "ollama/qwen3:8b"


@dataclass
class ScanResult:
    content: str
    model_used: str
    tokens_per_second: float
    scan_type: str
    timestamp: datetime
    needs_cloud_verification: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class LocalScanner:
    def __init__(self, ollama_base: str = OLLAMA_BASE) -> None:
        self._ollama_base = ollama_base
        self._last_model: str | None = None

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._ollama_base}/")
            urllib.request.urlopen(req, timeout=2)
            return True
        except Exception:
            return False

    def _call_ollama(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> tuple[str, float]:
        try:
            start = time.time()
            response = completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_base=self._ollama_base,
            )
            elapsed = time.time() - start
            content = response.choices[0].message.content or ""
            usage = response.usage
            total_tokens = usage.total_tokens if usage else 0
            tokens_per_second = total_tokens / elapsed if elapsed > 0 else 0.0
            self._last_model = model
            return content, tokens_per_second
        except Exception as exc:
            logger.error("ollama_call_failed", model=model, error=str(exc))
            raise

    def scan_code(self, code: str, scan_type: str = "general") -> ScanResult:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a code scanner. Analyze the following code "
                    "for bugs, security issues, and improvements. Be concise."
                ),
            },
            {"role": "user", "content": code},
        ]
        content, tps = self._call_ollama(messages, MODEL_STANDARD)
        return ScanResult(
            content=content,
            model_used=MODEL_STANDARD,
            tokens_per_second=tps,
            scan_type=scan_type,
            timestamp=datetime.now(),
            needs_cloud_verification=True,
        )

    def scan_text(self, text: str, task: str = "analyze") -> ScanResult:
        messages = [
            {
                "role": "system",
                "content": "You are a text analyzer. Analyze the following text. Be concise.",
            },
            {"role": "user", "content": text},
        ]
        content, tps = self._call_ollama(messages, MODEL_STANDARD)
        return ScanResult(
            content=content,
            model_used=MODEL_STANDARD,
            tokens_per_second=tps,
            scan_type=task,
            timestamp=datetime.now(),
            needs_cloud_verification=True,
        )

    def classify(self, content: str, categories: list[str]) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    f"Classify the following content into one of these "
                    f"categories: {categories}. Reply with only the category name."
                ),
            },
            {"role": "user", "content": content},
        ]
        try:
            result, _ = self._call_ollama(messages, MODEL_FAST)
            return result.strip()
        except Exception:
            return "unknown"

    def extract_keywords(self, text: str) -> list[str]:
        messages = [
            {
                "role": "system",
                "content": "Extract key terms from the following text. Return as comma-separated list.",
            },
            {"role": "user", "content": text},
        ]
        try:
            result, _ = self._call_ollama(messages, MODEL_FAST)
            return [kw.strip() for kw in result.split(",") if kw.strip()]
        except Exception:
            return []

    def quick_check(self, content: str) -> ScanResult:
        messages = [
            {
                "role": "system",
                "content": "Quick check: Is this content problematic? Reply YES or NO with brief reason.",
            },
            {"role": "user", "content": content},
        ]
        content, tps = self._call_ollama(messages, MODEL_FAST)
        return ScanResult(
            content=content,
            model_used=MODEL_FAST,
            tokens_per_second=tps,
            scan_type="quick_check",
            timestamp=datetime.now(),
            needs_cloud_verification=False,
        )

    def get_loaded_model(self) -> str | None:
        return self._last_model
