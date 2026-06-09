from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class TokenCount:
    chinese: int
    english_chars: int
    total: int


@dataclass
class EffectivenessReport:
    total_chars: int
    useful_chars: int
    noise_chars: int
    effectiveness: float


class TokenVisibilityReporter:
    FOOTER_TEMPLATE = "📊 [Token Stats] Input: {input} | Output: {output} | Total: {total} | Effectiveness: {eff:.2f}"
    CN_TOKEN_RATIO = 1
    EN_CHARS_PER_TOKEN = 4
    USEFUL_PATTERNS = (
        r"[A-Za-z0-9]",
        r"[\u4e00-\u9fff]",
        r"[一-鿿]",
    )
    NOISE_PATTERNS = (
        r"\s{2,}",
        r"[^\x00-\x7f\u4e00-\u9fff]",
    )

    def __init__(self) -> None:
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_wrap_calls = 0
        self._total_effectiveness_sum = 0.0
        self._effectiveness_samples = 0

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        chinese = sum(1 for c in text if self._is_chinese(c))
        non_chinese = len(text) - chinese
        tokens = chinese * self.CN_TOKEN_RATIO + (non_chinese + self.EN_CHARS_PER_TOKEN - 1) // self.EN_CHARS_PER_TOKEN
        return int(tokens)

    def count_tokens_detailed(self, text: str) -> TokenCount:
        if not text:
            return TokenCount(chinese=0, english_chars=0, total=0)
        chinese = sum(1 for c in text if self._is_chinese(c))
        non_chinese = len(text) - chinese
        en_tokens = (non_chinese + self.EN_CHARS_PER_TOKEN - 1) // self.EN_CHARS_PER_TOKEN
        return TokenCount(
            chinese=chinese * self.CN_TOKEN_RATIO,
            english_chars=en_tokens,
            total=chinese * self.CN_TOKEN_RATIO + en_tokens,
        )

    def compute_effectiveness(self, output_text: str) -> float:
        if not output_text:
            return 0.0
        total = len(output_text)
        useful = self._count_useful_chars(output_text)
        noise = self._count_noise_chars(output_text)
        adjusted_useful = max(0, useful - noise)
        ratio = adjusted_useful / total if total else 0.0
        ratio = max(0.0, min(1.0, ratio))
        self._total_effectiveness_sum += ratio
        self._effectiveness_samples += 1
        return round(ratio, 4)

    def compute_effectiveness_detailed(self, output_text: str) -> EffectivenessReport:
        if not output_text:
            return EffectivenessReport(total_chars=0, useful_chars=0, noise_chars=0, effectiveness=0.0)
        total = len(output_text)
        useful = self._count_useful_chars(output_text)
        noise = self._count_noise_chars(output_text)
        adjusted_useful = max(0, useful - noise)
        ratio = max(0.0, min(1.0, adjusted_useful / total)) if total else 0.0
        return EffectivenessReport(
            total_chars=total,
            useful_chars=useful,
            noise_chars=noise,
            effectiveness=round(ratio, 4),
        )

    def format_footer(self, input_tokens: int, output_tokens: int) -> str:
        total = input_tokens + output_tokens
        if total == 0:
            eff = 0.0
        else:
            sample_text = f"in:{input_tokens} out:{output_tokens}"
            eff = self.compute_effectiveness(sample_text)
        return self.FOOTER_TEMPLATE.format(
            input=input_tokens,
            output=output_tokens,
            total=total,
            eff=eff,
        )

    def wrap_response(self, content: str, input_text: str = "") -> str:
        in_tokens = self.count_tokens(input_text)
        out_tokens = self.count_tokens(content)
        footer = self.format_footer(in_tokens, out_tokens)
        self._total_input_tokens += in_tokens
        self._total_output_tokens += out_tokens
        self._total_wrap_calls += 1
        sep = "\n\n" if content and not content.endswith("\n") else "\n"
        return f"{content}{sep}{footer}"

    def format_summary_table(self) -> str:
        avg_eff = (
            self._total_effectiveness_sum / self._effectiveness_samples
            if self._effectiveness_samples
            else 0.0
        )
        lines = [
            "| Metric | Value |",
            "| --- | --- |",
            f"| Total wrap calls | {self._total_wrap_calls} |",
            f"| Total input tokens | {self._total_input_tokens} |",
            f"| Total output tokens | {self._total_output_tokens} |",
            f"| Avg effectiveness | {avg_eff:.4f} |",
        ]
        return "\n".join(lines)

    def _is_chinese(self, ch: str) -> bool:
        cp = ord(ch)
        return (
            0x4E00 <= cp <= 0x9FFF
            or 0x3400 <= cp <= 0x4DBF
            or 0xF900 <= cp <= 0xFAFF
        )

    def _count_useful_chars(self, text: str) -> int:
        count = 0
        for pat in self.USEFUL_PATTERNS:
            count += len(re.findall(pat, text))
        return count

    def _count_noise_chars(self, text: str) -> int:
        count = 0
        for pat in self.NOISE_PATTERNS:
            count += len(re.findall(pat, text))
        return count

    def stats(self) -> Dict[str, object]:
        avg_eff = (
            self._total_effectiveness_sum / self._effectiveness_samples
            if self._effectiveness_samples
            else 0.0
        )
        return {
            "wrap_calls": self._total_wrap_calls,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "avg_effectiveness": round(avg_eff, 4),
            "effectiveness_samples": self._effectiveness_samples,
        }
