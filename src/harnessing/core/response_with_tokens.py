from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .communication_enhancer import CommunicationEnhancer
from .token_visibility_reporter import TokenVisibilityReporter


@dataclass
class WrappedResponse:
    body: str
    footer: str
    combined: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    effectiveness: float
    action_items: List[str] = field(default_factory=list)


class ResponseWithTokens:
    def __init__(
        self,
        enhancer: Optional[CommunicationEnhancer] = None,
        reporter: Optional[TokenVisibilityReporter] = None,
    ) -> None:
        self.enhancer = enhancer or CommunicationEnhancer()
        self.reporter = reporter or TokenVisibilityReporter()
        self._wrap_count = 0

    def wrap(self, content: str, input_text: str = "", title: str = "") -> str:
        wrapped = self.enhancer.wrap_response(content, title=title, include_action_items=True)
        result = self.reporter.wrap_response(wrapped, input_text=input_text)
        self._wrap_count += 1
        return result

    def wrap_detailed(self, content: str, input_text: str = "", title: str = "") -> WrappedResponse:
        in_tokens = self.reporter.count_tokens(input_text)
        wrapped = self.enhancer.wrap_response(content, title=title, include_action_items=True)
        out_tokens = self.reporter.count_tokens(wrapped)
        effectiveness = self.reporter.compute_effectiveness(wrapped)
        footer = self.reporter.format_footer(in_tokens, out_tokens)
        action_items = self.enhancer.extract_action_items(content)
        combined = f"{wrapped}\n\n{footer}"
        self._wrap_count += 1
        return WrappedResponse(
            body=wrapped,
            footer=footer,
            combined=combined,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            total_tokens=in_tokens + out_tokens,
            effectiveness=effectiveness,
            action_items=action_items,
        )

    def demo_footer(self) -> str:
        return self.reporter.format_footer(1234, 567)

    def stats(self) -> Dict[str, object]:
        return {
            "wrap_count": self._wrap_count,
            "enhancer_stats": self.enhancer.stats(),
            "reporter_stats": self.reporter.stats(),
        }
