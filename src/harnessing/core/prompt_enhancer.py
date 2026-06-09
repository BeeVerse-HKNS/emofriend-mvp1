from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from harnessing.core.skill_router import SkillRouter

logger = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_AGENTS_MD_PATH = _PROJECT_ROOT / "AGENTS.md"

_INTENT_PATTERNS: list[dict[str, str]] = [
    {"pattern": "build|create|implement|add|develop", "intent": "create"},
    {"pattern": "fix|bug|debug|repair|patch", "intent": "fix"},
    {"pattern": "refactor|improve|optimize|enhance|upgrade", "intent": "improve"},
    {"pattern": "research|investigate|analyze|study|explore", "intent": "research"},
    {"pattern": "test|verify|validate|check|qa", "intent": "verify"},
    {"pattern": "delete|remove|clean|purge", "intent": "delete"},
    {"pattern": "deploy|publish|release|launch", "intent": "deploy"},
    {"pattern": "explain|describe|clarify|what is|how does", "intent": "understand"},
    {"pattern": "review|audit|assess|evaluate", "intent": "review"},
    {"pattern": "design|plan|architect|spec", "intent": "design"},
    {"pattern": "email|outlook|graph api|office 365", "intent": "email_agent"},
    {"pattern": "linkedin|profile|resume|skill", "intent": "linkedin_builder"},
    {"pattern": "esg|audit report|annual report|compliance", "intent": "audit_engine"},
    {"pattern": "voice order|pos|restaurant|menu", "intent": "voice_order"},
]

_REQUIREMENT_KEYWORDS: dict[str, list[str]] = {
    "scope": ["feature", "function", "module", "component", "system", "tool", "script"],
    "constraint": ["must", "should", "need", "require", "without", "no external"],
    "output": ["generate", "produce", "create", "return", "output", "result"],
    "quality": ["test", "verify", "validate", "qa", "ruff", "lint"],
    "integration": ["integrate", "connect", "combine", "sync", "link"],
    "sub_project": [
        "email-agent", "linkedin-builder", "audit-engine",
        "voice-order", "audit-platform", "business-plan",
        "python-for-kids",
    ],
}

_CONFIDENCE_MARKERS = {
    "✅": "已驗證",
    "🔍": "已研究",
    "⚠️": "推測",
    "❌": "不確定",
}

_PHASE_MAP = {
    "Phase 1": "知識庫 + 基礎設施 + 自我約束",
    "Phase 2": "內容創作系統",
    "Phase 3": "MVP 實作",
}


@dataclass
class EnhancedPrompt:
    raw_prompt: str
    intent: str = ""
    context: str = ""
    requirements: list[str] = field(default_factory=list)
    relevant_skills: list[dict[str, Any]] = field(default_factory=list)
    project_phase: str = ""
    confidence: str = "⚠️ 推測"
    enhanced_text: str = ""


class PromptEnhancer:
    def __init__(
        self,
        skill_router: SkillRouter | None = None,
        agents_md_path: Path | None = None,
    ) -> None:
        self.skill_router = skill_router or SkillRouter()
        self.agents_md_path = agents_md_path or _AGENTS_MD_PATH
        self._context_cache: str | None = None

    def enhance(self, raw_prompt: str) -> EnhancedPrompt:
        intent = self._extract_intent(raw_prompt)
        context = self._get_project_context()
        requirements = self._extract_requirements(raw_prompt)
        skills = self._get_relevant_skills(raw_prompt)
        phase = self._get_current_phase()
        confidence = self._assess_confidence(raw_prompt)
        enhanced = self._generate_enhanced(
            raw_prompt, intent, context, requirements, skills, phase, confidence
        )

        result = EnhancedPrompt(
            raw_prompt=raw_prompt,
            intent=intent,
            context=context,
            requirements=requirements,
            relevant_skills=skills,
            project_phase=phase,
            confidence=confidence,
            enhanced_text=enhanced,
        )

        logger.info(
            "prompt_enhanced",
            intent=intent,
            requirements_count=len(requirements),
            skills_count=len(skills),
            confidence=confidence,
        )

        return result

    def _extract_intent(self, prompt: str) -> str:
        import re

        prompt_lower = prompt.lower()
        for entry in _INTENT_PATTERNS:
            if re.search(entry["pattern"], prompt_lower):
                return entry["intent"]
        return "general"

    def _get_project_context(self) -> str:
        if self._context_cache is not None:
            return self._context_cache

        content = self._read_file_safe(self.agents_md_path)
        if not content:
            self._context_cache = "Harnessing: AI OPC Trainer"
            return self._context_cache

        lines = content.split("\n")
        summary_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("**") and "Harnessing" in stripped:
                summary_lines.append(stripped)
            elif stripped.startswith("- **Phase") or stripped.startswith("- **核心"):
                summary_lines.append(stripped)
            if len(summary_lines) >= 5:
                break

        self._context_cache = " | ".join(summary_lines) if summary_lines else "Harnessing: AI OPC Trainer"
        return self._context_cache

    def _extract_requirements(self, prompt: str) -> list[str]:
        prompt_lower = prompt.lower()
        requirements: list[str] = []

        for category, keywords in _REQUIREMENT_KEYWORDS.items():
            matched = [kw for kw in keywords if kw in prompt_lower]
            if matched:
                requirements.append(f"{category}: {', '.join(matched)}")

        return requirements

    def _get_relevant_skills(self, prompt: str) -> list[dict[str, Any]]:
        matches = self.skill_router.get_recommended_skills(prompt, top_n=3)
        return [
            {
                "name": m.skill_name,
                "confidence": m.confidence,
                "reason": m.reason,
            }
            for m in matches
        ]

    def _get_current_phase(self) -> str:
        content = self._read_file_safe(self.agents_md_path)
        if not content:
            return "Phase 2"

        for phase_key, phase_desc in _PHASE_MAP.items():
            if f"{phase_key}" in content and "✅ 完成" in content:
                continue
            if phase_key in content:
                return f"{phase_key}: {phase_desc}"

        return "Phase 2"

    def _assess_confidence(self, prompt: str) -> str:
        vague_indicators = ["maybe", "perhaps", "might", "not sure", "大概", "可能", "應該"]
        specific_indicators = [
            "exactly", "specifically", "must", "require", "明確", "必須",
            "指定", "需求",
        ]

        prompt_lower = prompt.lower()
        has_vague = any(v in prompt_lower for v in vague_indicators)
        has_specific = any(s in prompt_lower for s in specific_indicators)

        if has_specific and not has_vague:
            return "✅ 已驗證"
        elif has_vague and not has_specific:
            return "⚠️ 推測"
        elif has_vague and has_specific:
            return "🔍 已研究"
        else:
            return "🔍 已研究"

    def _generate_enhanced(
        self,
        raw: str,
        intent: str,
        context: str,
        requirements: list[str],
        skills: list[dict[str, Any]],
        phase: str,
        confidence: str,
    ) -> str:
        parts = [
            f"📌 Intent: {intent}",
            f"📋 Context: {phase} | {context}",
        ]

        if requirements:
            parts.append(f"🎯 Requirements: {'; '.join(requirements)}")

        if skills:
            skill_names = ", ".join(s["name"] for s in skills)
            parts.append(f"🔧 Suggested Skills: {skill_names}")

        parts.append(f"📊 Confidence: {confidence}")
        parts.append(f"💬 Original: {raw}")

        return "\n".join(parts)

    def _read_file_safe(self, path: Path) -> str:
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""
