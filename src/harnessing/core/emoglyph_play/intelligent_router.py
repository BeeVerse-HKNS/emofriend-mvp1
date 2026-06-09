"""
IntelligentSkillRouter — 智能路由器

用 EmoGlyph Play LSP 4步流程替代关键词匹配：

  [L1 Pulse]    感知用户意图信号（不只是关键词，是场景）
  [L2 Current]  分析情境 → 构建技能假设
  [L3 Construct] 推荐技能 + 解释原因
  [L4 Enactive]  记录推荐，等待用户反馈
  [L5 Resonance] 如果用户拒绝，降低该技能置信度

旧方式（关键词匹配）：
  "我的缓存太慢了" → [] (无匹配) ❌

新方式（智能路由）：
  "我的缓存太慢了" → redis-development (0.85, "缓存性能问题通常需要 Redis 优化") ✅
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .domain_map import DomainMap
from .lsp_ai_engine import LSPEngine, LSPStage, PlaySession, PlayerType
from .situation_analyzer import Situation, SituationAnalyzer
from .lsp_ai_engine import LSPPlayerTypeDetector


# ── 推荐结果 ───────────────────────────────────────────────────────

@dataclass
class SkillRecommendation:
    """单个技能推荐。"""

    skill_name: str
    confidence: float
    reason: str  # 人类语言解释（Rule 86）
    domain: str = ""
    source: str = "intelligent"  # "intelligent" | "keyword_fallback"


@dataclass
class IntelligentRouteResult:
    """智能路由的完整结果。"""

    recommended_skills: list[SkillRecommendation] = field(default_factory=list)
    situation: Situation = field(default_factory=Situation)
    player_type: PlayerType = PlayerType.EXPLORER
    lsp_session_id: str = ""
    formula_score: float = 0.0
    explanation: str = ""  # Rule 86: 人类语言解释
    fallback_used: bool = False


# ── 反馈追踪器 ─────────────────────────────────────────────────────

class FeedbackTracker:
    """追踪用户对推荐的反馈，用于学习。"""

    def __init__(self) -> None:
        self._history: dict[str, dict[str, Any]] = {}  # skill_name → {accepted, rejected, last_used}

    def record(self, skill_name: str, accepted: bool) -> None:
        """记录用户是否接受了推荐。"""
        if skill_name not in self._history:
            self._history[skill_name] = {"accepted": 0, "rejected": 0, "last_used": ""}
        entry = self._history[skill_name]
        if accepted:
            entry["accepted"] += 1
        else:
            entry["rejected"] += 1
        entry["last_used"] = datetime.utcnow().isoformat()

    def get_confidence_adjustment(self, skill_name: str) -> float:
        """根据历史反馈返回置信度调整值。"""
        entry = self._history.get(skill_name)
        if not entry:
            return 0.0
        total = entry["accepted"] + entry["rejected"]
        if total == 0:
            return 0.0
        acceptance_rate = entry["accepted"] / total
        # 高接受率 +0.1，低接受率 -0.2
        if acceptance_rate > 0.7:
            return 0.1
        if acceptance_rate < 0.3:
            return -0.2
        return 0.0

    def get_stats(self) -> dict[str, dict[str, Any]]:
        """返回所有反馈统计。"""
        return dict(self._history)


# ── 意图 → 技能领域映射 ────────────────────────────────────────────

_INTENT_DOMAIN_HINTS: dict[str, list[str]] = {
    "create": ["content_creation", "design_ui", "documentation"],
    "fix": ["data_analysis", "testing", "devops"],
    "research": ["research", "data_analysis"],
    "deploy": ["devops"],
    "design": ["design_ui", "content_creation"],
    "test": ["testing", "browser_automation"],
    "optimize": ["data_analysis", "devops"],
}


# ── IntelligentSkillRouter ─────────────────────────────────────────

class IntelligentSkillRouter:
    """智能路由器 — 用 EmoGlyph Play LSP 4步流程替代关键词匹配。"""

    def __init__(
        self,
        domain_map: DomainMap | None = None,
        situation_analyzer: SituationAnalyzer | None = None,
        feedback_tracker: FeedbackTracker | None = None,
    ) -> None:
        self.domain_map = domain_map or DomainMap()
        self.analyzer = situation_analyzer or SituationAnalyzer(self.domain_map)
        self.feedback = feedback_tracker or FeedbackTracker()
        self._lsp_engine = LSPEngine()

    def route(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> IntelligentRouteResult:
        """用 EmoGlyph Play LSP 4步流程路由技能。

        Parameters
        ----------
        prompt : str
            用户输入。
        context : dict | None
            额外上下文。

        Returns
        -------
        IntelligentRouteResult
            包含推荐技能、情境分析、人类语言解释。
        """
        if context is None:
            context = {}

        # ── L1 Pulse: 感知意图信号 ──────────────────────────────
        situation = self._pulse_stage(prompt, context)

        # ── L2 Current: 构建技能假设 ────────────────────────────
        candidates = self._build_stage(situation)

        # ── L3 Construct: 生成推荐 + 解释 ───────────────────────
        recommendations = self._share_stage(candidates, situation)

        # ── L4 Enactive: 记录推荐 ───────────────────────────────
        session_id = self._reflect_stage(prompt, situation, recommendations)

        # ── L5 Resonance: 共鸣检查 ──────────────────────────────
        formula_score = self._resonance_check(situation, recommendations)

        # 生成人类语言解释（Rule 86）
        explanation = self._generate_explanation(situation, recommendations)

        return IntelligentRouteResult(
            recommended_skills=recommendations,
            situation=situation,
            player_type=situation.player_type,
            lsp_session_id=session_id,
            formula_score=formula_score,
            explanation=explanation,
            fallback_used=False,
        )

    # ── L1 Pulse: 感知意图信号 ──────────────────────────────────

    def _pulse_stage(
        self, prompt: str, context: dict[str, Any]
    ) -> Situation:
        """L1 Pulse — 感知用户的意图信号，不只是关键词。"""
        return self.analyzer.analyze(prompt, context)

    # ── L2 Current: 构建技能假设 ────────────────────────────────

    def _build_stage(self, situation: Situation) -> list[tuple[str, float, str]]:
        """L2 Current — 根据情境构建技能假设。

        Returns
        -------
        list[tuple[str, float, str]]
            [(skill_name, base_confidence, domain_name), ...]
        """
        candidates: list[tuple[str, float, str]] = []
        seen: set[str] = set()

        # 1. 从匹配的领域获取技能
        for domain_name, domain_conf in situation.matched_domains:
            skills = self.domain_map.get_skills_for_domain(domain_name)
            for skill_name in skills:
                if skill_name in seen:
                    continue
                seen.add(skill_name)

                # 基础置信度 = 领域置信度
                confidence = domain_conf

                # 意图匹配加分
                intent_domains = _INTENT_DOMAIN_HINTS.get(situation.intent, [])
                if domain_name in intent_domains:
                    confidence += 0.15

                # 地理匹配加分
                domain_entry = self.domain_map.domain_info(domain_name)
                if domain_entry and domain_entry.geo in (situation.geo, "any"):
                    confidence += 0.1

                # 反馈调整
                feedback_adj = self.feedback.get_confidence_adjustment(skill_name)
                confidence += feedback_adj

                confidence = round(min(max(confidence, 0.0), 1.0), 4)
                candidates.append((skill_name, confidence, domain_name))

        # 2. 如果没有匹配领域，尝试意图推断
        if not candidates and situation.intent != "create":
            intent_domains = _INTENT_DOMAIN_HINTS.get(situation.intent, [])
            for domain_name in intent_domains:
                skills = self.domain_map.get_skills_for_domain(domain_name)
                for skill_name in skills:
                    if skill_name in seen:
                        continue
                    seen.add(skill_name)
                    candidates.append((skill_name, 0.4, domain_name))

        # 按置信度排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    # ── L3 Construct: 生成推荐 + 解释 ──────────────────────────

    def _share_stage(
        self,
        candidates: list[tuple[str, float, str]],
        situation: Situation,
    ) -> list[SkillRecommendation]:
        """L3 Construct — 生成推荐列表 + 人类语言解释。"""
        recommendations: list[SkillRecommendation] = []

        for skill_name, confidence, domain_name in candidates:
            # 生成推荐原因
            reason = self._generate_reason(skill_name, domain_name, situation)

            rec = SkillRecommendation(
                skill_name=skill_name,
                confidence=confidence,
                reason=reason,
                domain=domain_name,
                source="intelligent",
            )
            recommendations.append(rec)

        return recommendations

    # ── L4 Enactive: 记录推荐 ──────────────────────────────────

    def _reflect_stage(
        self,
        prompt: str,
        situation: Situation,
        recommendations: list[SkillRecommendation],
    ) -> str:
        """L4 Enactive — 记录推荐到 LSP 会话。"""
        session = self._lsp_engine.start_session(prompt)

        # Build step: 记录技能假设
        hypothesis = f"Based on {situation.domain} domain ({situation.geo}), recommend {len(recommendations)} skills"
        self._lsp_engine.build(
            session.session_id, hypothesis, confidence=situation.domain_confidence
        )

        # Share step: 记录推荐
        skill_names = [r.skill_name for r in recommendations[:5]]
        narrative = f"Recommended skills: {', '.join(skill_names)}"
        self._lsp_engine.share(session.session_id, narrative, confidence=0.7)

        # Reflect step: 记录学习
        learning = f"Situation: {situation.summary()}, top skill: {recommendations[0].skill_name if recommendations else 'none'}"
        self._lsp_engine.reflect(session.session_id, learning, surprise_score=0.2)

        return session.session_id

    # ── L5 Resonance: 共鸣检查 ─────────────────────────────────

    def _resonance_check(
        self,
        situation: Situation,
        recommendations: list[SkillRecommendation],
    ) -> float:
        """L5 Resonance — 检查推荐质量。

        使用 Play Formula 的简化版本：
        score = (domain_confidence × intent_confidence) + (player_match × 0.2) - (low_confidence_penalty)
        """
        if not recommendations:
            return 0.0

        # 领域置信度
        domain_conf = situation.domain_confidence

        # 意图置信度
        intent_conf = situation.intent_confidence

        # 玩家类型匹配度
        player_conf = situation.player_confidence

        # 低置信度惩罚（推荐中置信度 < 0.5 的比例）
        low_conf_ratio = sum(1 for r in recommendations if r.confidence < 0.5) / max(len(recommendations), 1)

        score = (domain_conf * intent_conf) + (player_conf * 0.2) - (low_conf_ratio * 0.3)
        return round(min(max(score, 0.0), 1.0), 4)

    # ── 人类语言解释生成 ────────────────────────────────────────

    def _generate_reason(
        self, skill_name: str, domain_name: str, situation: Situation
    ) -> str:
        """生成推荐原因的人类语言解释。"""
        # 领域描述
        domain_entry = self.domain_map.domain_info(domain_name)
        domain_desc = domain_entry.description if domain_entry else domain_name

        # 地理环境说明
        geo_label = {"china": "中国", "global": "国际", "any": "通用"}.get(situation.geo, situation.geo)

        # 意图说明
        intent_label = {
            "create": "创建", "fix": "修复", "research": "研究",
            "deploy": "部署", "design": "设计", "test": "测试",
            "optimize": "优化",
        }.get(situation.intent, situation.intent)

        return f"{geo_label}{intent_label}场景，{domain_desc}，推荐 {skill_name}"

    def _generate_explanation(
        self, situation: Situation, recommendations: list[SkillRecommendation]
    ) -> str:
        """生成完整的人类语言解释（Rule 86）。"""
        if not recommendations:
            return f"未找到匹配的技能。情境：{situation.summary()}"

        top_skills = recommendations[:3]
        skill_descriptions = []
        for rec in top_skills:
            skill_descriptions.append(f"  - {rec.skill_name}（置信度 {rec.confidence:.0%}）：{rec.reason}")

        return (
            f"情境分析：{situation.summary()}\n"
            f"推荐 {len(recommendations)} 个技能：\n"
            + "\n".join(skill_descriptions)
        )

    # ── 公开辅助方法 ────────────────────────────────────────────

    def record_feedback(self, skill_name: str, accepted: bool) -> None:
        """记录用户对推荐的反馈。"""
        self.feedback.record(skill_name, accepted)

    def get_feedback_stats(self) -> dict[str, dict[str, Any]]:
        """获取反馈统计。"""
        return self.feedback.get_stats()
