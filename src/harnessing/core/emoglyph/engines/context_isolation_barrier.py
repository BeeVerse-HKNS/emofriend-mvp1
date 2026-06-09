"""ContextIsolationBarrier — 上下文隔離屏障

EmoGlyph Parallel Workspace 上下文隔離引擎。
防止 Root Workspace 與 Sub-Folder Workspace 之間的上下文交叉污染。

公式：ParallelWork = ⊕(Root, Sub) × Bridge - ContextLeak
本引擎實作 - ContextLeak 部分，確保 Sub-Agent 回傳結果不洩漏敏感上下文，
同時 Root 指令不會將 Root 專屬資訊洩漏給 Sub-Agent。

核心能力：
1. filter_result — 從 Sub-Agent 結果中剝離 BLOCKED 類型資訊
2. validate_instruction — 確保指令不會將 Root 上下文洩漏給 Sub-Agent
3. serialize_result — 將 Sub-Agent 輸出壓縮為緊湊格式，截斷過長摘要
4. check_leakage — 掃描結果中的潛在上下文洩漏模式

資訊分類策略：
- ALLOWED：操作狀態、結果摘要（≤500 tokens）、錯誤訊息、修改檔案路徑、時間戳、子項目名稱
- BLOCKED：完整檔案內容、會話歷史、內部狀態、上下文視窗內容、環境變數、憑證
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InformationType(Enum):
    """Information type classification for barrier policy."""

    # ALLOWED types — safe to cross the barrier
    OPERATION_STATUS = "operation_status"
    RESULT_SUMMARY = "result_summary"
    ERROR_MESSAGES = "error_messages"
    MODIFIED_FILE_PATHS = "modified_file_paths"
    TIMESTAMP = "timestamp"
    SUBPROJECT_NAME = "subproject_name"

    # BLOCKED types — must not cross the barrier
    FULL_FILE_CONTENTS = "full_file_contents"
    SESSION_HISTORY = "session_history"
    INTERNAL_STATE = "internal_state"
    CONTEXT_WINDOW_CONTENT = "context_window_content"
    ENVIRONMENT_VARIABLES = "environment_variables"
    CREDENTIALS = "credentials"


@dataclass
class BarrierPolicy:
    """Defines which information types are allowed or blocked across the isolation barrier.

    The default policy follows the ParallelWork formula:
        ParallelWork = ⊕(Root, Sub) × Bridge - ContextLeak

    ALLOWED types pass through the bridge; BLOCKED types are subtracted
    as ContextLeak to prevent cross-contamination.
    """

    allowed: set[InformationType] = field(default_factory=lambda: {
        InformationType.OPERATION_STATUS,
        InformationType.RESULT_SUMMARY,
        InformationType.ERROR_MESSAGES,
        InformationType.MODIFIED_FILE_PATHS,
        InformationType.TIMESTAMP,
        InformationType.SUBPROJECT_NAME,
    })

    blocked: set[InformationType] = field(default_factory=lambda: {
        InformationType.FULL_FILE_CONTENTS,
        InformationType.SESSION_HISTORY,
        InformationType.INTERNAL_STATE,
        InformationType.CONTEXT_WINDOW_CONTENT,
        InformationType.ENVIRONMENT_VARIABLES,
        InformationType.CREDENTIALS,
    })

    def is_allowed(self, info_type: InformationType) -> bool:
        return info_type in self.allowed

    def is_blocked(self, info_type: InformationType) -> bool:
        return info_type in self.blocked


# Keys in a raw result dict that map to each InformationType
_RESULT_KEY_MAP: dict[str, InformationType] = {
    "operation_status": InformationType.OPERATION_STATUS,
    "status": InformationType.OPERATION_STATUS,
    "success": InformationType.OPERATION_STATUS,
    "result_summary": InformationType.RESULT_SUMMARY,
    "summary": InformationType.RESULT_SUMMARY,
    "error_messages": InformationType.ERROR_MESSAGES,
    "errors": InformationType.ERROR_MESSAGES,
    "error": InformationType.ERROR_MESSAGES,
    "modified_file_paths": InformationType.MODIFIED_FILE_PATHS,
    "changed_files": InformationType.MODIFIED_FILE_PATHS,
    "timestamp": InformationType.TIMESTAMP,
    "created_at": InformationType.TIMESTAMP,
    "subproject_name": InformationType.SUBPROJECT_NAME,
    "project_name": InformationType.SUBPROJECT_NAME,
    "full_file_contents": InformationType.FULL_FILE_CONTENTS,
    "file_contents": InformationType.FULL_FILE_CONTENTS,
    "content": InformationType.FULL_FILE_CONTENTS,
    "session_history": InformationType.SESSION_HISTORY,
    "history": InformationType.SESSION_HISTORY,
    "messages": InformationType.SESSION_HISTORY,
    "internal_state": InformationType.INTERNAL_STATE,
    "state": InformationType.INTERNAL_STATE,
    "context_window_content": InformationType.CONTEXT_WINDOW_CONTENT,
    "context": InformationType.CONTEXT_WINDOW_CONTENT,
    "environment_variables": InformationType.ENVIRONMENT_VARIABLES,
    "env": InformationType.ENVIRONMENT_VARIABLES,
    "environ": InformationType.ENVIRONMENT_VARIABLES,
    "credentials": InformationType.CREDENTIALS,
    "secrets": InformationType.CREDENTIALS,
    "tokens": InformationType.CREDENTIALS,
    "api_keys": InformationType.CREDENTIALS,
}

# Patterns that indicate credential leakage
_CREDENTIAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|password|passwd)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)sk-[A-Za-z0-9]{20,}"),  # OpenAI-style keys
    re.compile(r"(?i)AKIA[A-Z0-9]{16}"),  # AWS-style keys
]

# Patterns that indicate environment variable leakage
_ENV_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\b[A-Z_]{3,}\s*=\s*[\w/\.\-]+"),
    re.compile(r"(?i)(PATH|HOME|USER|SHELL|JAVA_HOME|NODE_ENV|PYTHONPATH)\s*="),
]

# Approximate tokens per character ratio for truncation
_CHARS_PER_TOKEN = 4


class ContextIsolationBarrier:
    """Prevents context cross-contamination between Root and Sub-Folder workspaces.

    Implements the - ContextLeak component of:
        ParallelWork = ⊕(Root, Sub) × Bridge - ContextLeak

    This barrier ensures:
    - Sub-Agent results only expose ALLOWED information types
    - Root instructions do not carry Root-specific context into Sub-Agents
    - Results are compact and fit within token budgets
    - Potential leakage patterns are detected and reported
    """

    def __init__(self, policy: BarrierPolicy | None = None):
        self.policy = policy or BarrierPolicy()

    # ------------------------------------------------------------------
    # 1. filter_result
    # ------------------------------------------------------------------

    def filter_result(self, raw_result: dict) -> dict:
        """Strip BLOCKED information from a Sub-Agent result.

        Only keys whose mapped InformationType is in the ALLOWED set are
        retained.  Unknown keys (not in _RESULT_KEY_MAP) are dropped by
        default to enforce a deny-by-default posture.

        Args:
            raw_result: The raw dictionary returned by a Sub-Agent.

        Returns:
            A filtered dictionary containing only ALLOWED information.
        """
        filtered: dict[str, Any] = {}
        for key, value in raw_result.items():
            info_type = _RESULT_KEY_MAP.get(key)
            if info_type is not None and self.policy.is_allowed(info_type):
                filtered[key] = value
        return filtered

    # ------------------------------------------------------------------
    # 2. validate_instruction
    # ------------------------------------------------------------------

    def validate_instruction(
        self,
        instruction: str,
        context_pack: dict,
    ) -> tuple[bool, str]:
        """Ensure an instruction does not leak Root context to a Sub-Agent.

        Checks both the instruction text and the context_pack for:
        - Credential patterns (API keys, tokens, passwords)
        - Root session state references
        - Environment variables that belong to Root

        Args:
            instruction: The instruction string to send to a Sub-Agent.
            context_pack: Additional context dictionary attached to the instruction.

        Returns:
            A tuple of (is_valid, reason).  is_valid is True when no leakage
            is detected; False with a descriptive reason otherwise.
        """
        # Check instruction text for credential patterns
        for pattern in _CREDENTIAL_PATTERNS:
            match = pattern.search(instruction)
            if match:
                return (False, f"Instruction contains credential pattern: '{match.group()}'")

        # Check instruction text for environment variable patterns
        for pattern in _ENV_PATTERNS:
            match = pattern.search(instruction)
            if match:
                return (False, f"Instruction contains environment variable pattern: '{match.group()}'")

        # Check instruction text for root session references
        root_session_indicators = [
            "root_session",
            "root_context",
            "root_state",
            "main_session",
            "main_context",
        ]
        instruction_lower = instruction.lower()
        for indicator in root_session_indicators:
            if indicator in instruction_lower:
                return (False, f"Instruction references root session state: '{indicator}'")

        # Check context_pack for blocked keys
        for key in context_pack:
            info_type = _RESULT_KEY_MAP.get(key)
            if info_type is not None and self.policy.is_blocked(info_type):
                return (False, f"Context pack contains blocked key: '{key}' (type: {info_type.value})")

        # Check context_pack values for credential patterns
        for key, value in context_pack.items():
            value_str = str(value)
            for pattern in _CREDENTIAL_PATTERNS:
                match = pattern.search(value_str)
                if match:
                    return (False, f"Context pack key '{key}' contains credential pattern: '{match.group()}'")

        return (True, "Instruction validated — no leakage detected")

    # ------------------------------------------------------------------
    # 3. serialize_result
    # ------------------------------------------------------------------

    def serialize_result(
        self,
        raw_result: dict,
        max_tokens: int = 500,
    ) -> dict:
        """Convert a Sub-Agent output to a compact, serialized format.

        Steps:
        1. Filter out BLOCKED keys (via filter_result).
        2. Truncate any string values that exceed the token budget.
        3. Convert non-serializable values to their string representation.

        Args:
            raw_result: The raw dictionary returned by a Sub-Agent.
            max_tokens: Maximum approximate token count for string values.

        Returns:
            A compact dictionary suitable for crossing the barrier.
        """
        filtered = self.filter_result(raw_result)
        max_chars = max_tokens * _CHARS_PER_TOKEN

        serialized: dict[str, Any] = {}
        for key, value in filtered.items():
            if isinstance(value, str):
                serialized[key] = self._truncate_string(value, max_chars)
            elif isinstance(value, list):
                serialized[key] = self._truncate_list(value, max_chars)
            elif isinstance(value, dict):
                serialized[key] = self._truncate_dict(value, max_chars)
            else:
                serialized[key] = value

        return serialized

    # ------------------------------------------------------------------
    # 4. check_leakage
    # ------------------------------------------------------------------

    def check_leakage(self, result: dict) -> list[str]:
        """Scan a result dictionary for potential context leakage patterns.

        Detects:
        - File contents exceeding 100 lines (likely full_file_contents)
        - Environment variable patterns
        - Credential patterns (API keys, tokens, passwords)
        - Blocked keys present in the result

        Args:
            result: The result dictionary to scan.

        Returns:
            A list of human-readable leakage warnings.  Empty if clean.
        """
        warnings: list[str] = []

        for key, value in result.items():
            # Check for blocked keys
            info_type = _RESULT_KEY_MAP.get(key)
            if info_type is not None and self.policy.is_blocked(info_type):
                warnings.append(f"Blocked key present: '{key}' (type: {info_type.value})")

            value_str = str(value)

            # Check for large file contents (> 100 lines)
            if isinstance(value, str):
                line_count = value.count("\n") + 1
                if line_count > 100:
                    warnings.append(
                        f"Key '{key}' contains {line_count} lines — likely full file contents (max 100)"
                    )

            # Check for credential patterns
            for pattern in _CREDENTIAL_PATTERNS:
                match = pattern.search(value_str)
                if match:
                    warnings.append(
                        f"Key '{key}' contains credential pattern: '{match.group()}'"
                    )
                    break  # one warning per key for credentials

            # Check for environment variable patterns
            for pattern in _ENV_PATTERNS:
                match = pattern.search(value_str)
                if match:
                    warnings.append(
                        f"Key '{key}' contains environment variable pattern: '{match.group()}'"
                    )
                    break  # one warning per key for env vars

            # Check for nested dicts/lists with blocked content
            if isinstance(value, dict):
                nested_warnings = self._check_nested_leakage(key, value)
                warnings.extend(nested_warnings)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        nested_warnings = self._check_nested_leakage(f"{key}[{i}]", item)
                        warnings.extend(nested_warnings)

        return warnings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate_string(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + f"... [truncated, {len(text)} total chars]"

    @staticmethod
    def _truncate_list(items: list, max_chars: int) -> list:
        result: list[Any] = []
        current_chars = 0
        for item in items:
            item_str = str(item)
            if current_chars + len(item_str) > max_chars:
                result.append(f"... [truncated, {len(items) - len(result)} items omitted]")
                break
            result.append(item)
            current_chars += len(item_str)
        return result

    @staticmethod
    def _truncate_dict(d: dict, max_chars: int) -> dict:
        result: dict[str, Any] = {}
        current_chars = 0
        for key, value in d.items():
            entry_str = str(value)
            if current_chars + len(entry_str) > max_chars:
                result["_truncated"] = True
                break
            result[key] = value
            current_chars += len(entry_str)
        return result

    def _check_nested_leakage(self, parent_key: str, nested: dict) -> list[str]:
        warnings: list[str] = []
        for key, value in nested.items():
            full_key = f"{parent_key}.{key}"
            info_type = _RESULT_KEY_MAP.get(key)
            if info_type is not None and self.policy.is_blocked(info_type):
                warnings.append(f"Blocked key in nested dict: '{full_key}' (type: {info_type.value})")

            value_str = str(value)
            for pattern in _CREDENTIAL_PATTERNS:
                match = pattern.search(value_str)
                if match:
                    warnings.append(
                        f"Nested key '{full_key}' contains credential pattern: '{match.group()}'"
                    )
                    break

            for pattern in _ENV_PATTERNS:
                match = pattern.search(value_str)
                if match:
                    warnings.append(
                        f"Nested key '{full_key}' contains environment variable pattern: '{match.group()}'"
                    )
                    break

            if isinstance(value, str):
                line_count = value.count("\n") + 1
                if line_count > 100:
                    warnings.append(
                        f"Nested key '{full_key}' contains {line_count} lines — likely full file contents"
                    )
        return warnings
