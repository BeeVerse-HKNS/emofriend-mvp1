from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class EnhancementResult:
    original_length: int
    enhanced_length: int
    sections_added: int
    symbols_added: int
    action_items: List[str] = field(default_factory=list)


class CommunicationEnhancer:
    STATUS_SYMBOLS = {
        "success": "✅",
        "failure": "❌",
        "warning": "⚠️",
        "search": "🔍",
        "info": "ℹ️",
        "running": "🔄",
        "complete": "✔️",
    }
    ACTION_KEYWORDS = ("todo", "action", "next", "next step", "follow-up", "follow up", "must do")

    def __init__(self) -> None:
        self._enhance_count = 0
        self._total_added_chars = 0
        self._table_count = 0
        self._action_items_extracted = 0
        self._symbol_count = 0

    def enhance(self, content: str) -> str:
        if not content:
            return ""
        self._enhance_count += 1
        original_len = len(content)
        enhanced = self.add_status_symbols(content)
        symbols_added = self._count_symbols(enhanced) - self._count_symbols(content)
        self._symbol_count += symbols_added
        enhanced = self._ensure_heading(enhanced)
        enhanced = self._ensure_bullet_consistency(enhanced)
        self._total_added_chars += len(enhanced) - original_len
        return enhanced

    def add_status_symbols(self, text: str) -> str:
        if not text:
            return text
        result = text
        result = re.sub(r"(?i)\b(done|success|completed|passed|ok|verified)\b",
                        lambda m: f"{self.STATUS_SYMBOLS['success']} {m.group(0)}", result)
        result = re.sub(r"(?i)\b(fail|failed|error|crash)\b(?!\s*[:：])",
                        lambda m: f"{self.STATUS_SYMBOLS['failure']} {m.group(0)}", result)
        result = re.sub(r"(?i)\b(warn|warning|caution|risky)\b",
                        lambda m: f"{self.STATUS_SYMBOLS['warning']} {m.group(0)}", result)
        result = re.sub(r"(?i)\b(search|research|investigate|find out|look up)\b",
                        lambda m: f"{self.STATUS_SYMBOLS['search']} {m.group(0)}", result)
        return result

    def format_table(self, headers: List[str], rows: List[List[str]]) -> str:
        if not headers:
            return ""
        self._table_count += 1
        norm_rows = [self._normalize_row(r, len(headers)) for r in rows]
        widths = [len(h) for h in headers]
        for r in norm_rows:
            for i, cell in enumerate(r):
                widths[i] = max(widths[i], len(cell))
        lines: List[str] = []
        lines.append(self._format_row(headers, widths))
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for r in norm_rows:
            lines.append(self._format_row(r, widths))
        return "\n".join(lines)

    def _format_row(self, cells: List[str], widths: List[int]) -> str:
        padded = [cells[i].ljust(widths[i]) for i in range(len(cells))]
        return "| " + " | ".join(padded) + " |"

    def _normalize_row(self, row: List[str], expected: int) -> List[str]:
        if len(row) < expected:
            return list(row) + [""] * (expected - len(row))
        if len(row) > expected:
            return row[: expected - 1] + [" ".join(row[expected - 1:])]
        return list(row)

    def extract_action_items(self, content: str) -> List[str]:
        if not content:
            return []
        action_items: List[str] = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            for kw in self.ACTION_KEYWORDS:
                if re.search(rf"^(?:[-*+\d.\s]*){{0,3}}{re.escape(kw)}\b[:：\s\-]", lower) or \
                   re.search(rf"\b{re.escape(kw)}\b\s*[:：]", lower):
                    action_items.append(stripped)
                    break
                if lower.startswith(kw) and len(lower) > len(kw) and lower[len(kw)] in (":", "：", " ", "-", "—"):
                    action_items.append(stripped)
                    break
        self._action_items_extracted += len(action_items)
        return action_items

    def wrap_response(
        self,
        content: str,
        title: str = "",
        include_action_items: bool = True,
    ) -> str:
        enhanced = self.enhance(content)
        pieces: List[str] = []
        if title:
            pieces.append(f"## {title}")
            pieces.append("")
        pieces.append(enhanced)
        if include_action_items:
            items = self.extract_action_items(content)
            if items:
                pieces.append("")
                pieces.append("### Action Items")
                for item in items[:5]:
                    pieces.append(f"- {item}")
        return "\n".join(pieces)

    def _count_symbols(self, text: str) -> int:
        if not text:
            return 0
        return sum(1 for c in text if c in self.STATUS_SYMBOLS.values())

    def _ensure_heading(self, text: str) -> str:
        lines = text.split("\n")
        if not lines:
            return text
        first = lines[0].strip()
        if first.startswith("#") or not first:
            return text
        if len(first) > 80:
            return text
        lines[0] = f"## {first}"
        return "\n".join(lines)

    def _ensure_bullet_consistency(self, text: str) -> str:
        lines = text.split("\n")
        fixed: List[str] = []
        for line in lines:
            stripped = line.lstrip()
            indent_len = len(line) - len(stripped)
            indent = " " * indent_len
            if re.match(r"^[\*]\s+", stripped):
                stripped = "- " + stripped[2:]
            fixed.append(indent + stripped)
        return "\n".join(fixed)

    def stats(self) -> Dict[str, object]:
        return {
            "enhance_count": self._enhance_count,
            "tables_formatted": self._table_count,
            "action_items_extracted": self._action_items_extracted,
            "symbols_added": self._symbol_count,
            "total_added_chars": self._total_added_chars,
        }
