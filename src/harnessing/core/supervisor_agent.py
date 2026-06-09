"""
Supervisor Agent (R-ERR-083)
D-100 Daily Learning Cycle 2026-06-03

獨立監督 Agent 監察 worker Agent 嘅產出質量。
基於 ByteDance DeerFlow 2.0 Supervisor 模式 + Anthropic Generator-Evaluator 分離原則。

5 個質量評估維度：
1. 準確性 (Accuracy) — 內容是否正確
2. 完整性 (Completeness) — 是否覆蓋所有要求
3. 時效性 (Timeliness) — 是否符合時間要求
4. 合規性 (Compliance) — 是否符合法規/政策
5. 可執行性 (Actionability) — 結果是否可執行

信心等級：🔍 已研究（基於 ByteDance DeerFlow 2.0 + Anthropic 研究）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional


class QualityDimension(str, Enum):
    """5 個質量評估維度"""
    ACCURACY = "ACCURACY"
    COMPLETENESS = "COMPLETENESS"
    TIMELINESS = "TIMELINESS"
    COMPLIANCE = "COMPLIANCE"
    ACTIONABILITY = "ACTIONABILITY"


@dataclass
class QualityScore:
    """單一維度嘅評分"""
    dimension: QualityDimension
    score: float  # 0-100
    feedback: str = ""
    weight: float = 1.0  # 權重


@dataclass
class EvaluationResult:
    """完整評估結果"""
    session_id: str
    task: str
    output: Any
    scores: list[QualityScore]
    overall_score: float
    passed: bool
    needs_regeneration: bool
    needs_human_intervention: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    regeneration_count: int = 0


@dataclass
class DeviationReport:
    """偏離目標報告"""
    expected_keywords: list[str]
    found_keywords: list[str]
    missing_keywords: list[str]
    semantic_similarity: float  # 0-1
    deviation_severity: str  # LOW / MEDIUM / HIGH
    recommendation: str


# 默認閾值
DEFAULT_PASS_THRESHOLD = 70.0
DEFAULT_REGENERATION_THRESHOLD = 60.0
DEFAULT_MAX_REGENERATIONS = 3


class SupervisorAgent:
    """獨立監督 Agent — 從文字規則升級為可執行代碼 (R-ERR-083)

    整合 R-ERR-077 (Generator-Evaluator 分離) + R-ERR-079 (兩 Strike 規則) + R-ERR-082 (Session-Context)
    """

    def __init__(
        self,
        pass_threshold: float = DEFAULT_PASS_THRESHOLD,
        regeneration_threshold: float = DEFAULT_REGENERATION_THRESHOLD,
        max_regenerations: int = DEFAULT_MAX_REGENERATIONS,
    ) -> None:
        self.pass_threshold = pass_threshold
        self.regeneration_threshold = regeneration_threshold
        self.max_regenerations = max_regenerations
        self._evaluation_history: list[EvaluationResult] = []
        self._evaluators: dict[QualityDimension, Callable[..., QualityScore]] = {
            QualityDimension.ACCURACY: self._default_accuracy_evaluator,
            QualityDimension.COMPLETENESS: self._default_completeness_evaluator,
            QualityDimension.TIMELINESS: self._default_timeliness_evaluator,
            QualityDimension.COMPLIANCE: self._default_compliance_evaluator,
            QualityDimension.ACTIONABILITY: self._default_actionability_evaluator,
        }

    def register_evaluator(self, dimension: QualityDimension, evaluator: Callable[..., QualityScore]) -> None:
        """註冊自定義評估器"""
        self._evaluators[dimension] = evaluator

    def evaluate_output(
        self,
        session_id: str,
        task: str,
        output: Any,
        expected_criteria: Optional[dict[str, Any]] = None,
        regeneration_count: int = 0,
    ) -> EvaluationResult:
        """評估 worker 產出嘅質量"""
        criteria = expected_criteria or {}
        scores = []
        for dimension, evaluator in self._evaluators.items():
            try:
                score = evaluator(output=output, criteria=criteria, dimension=dimension)
                scores.append(score)
            except Exception:
                scores.append(QualityScore(dimension=dimension, score=50.0, feedback="評估失敗，使用默認分數"))

        overall = self._calculate_overall_score(scores)
        passed = overall >= self.pass_threshold
        needs_regen = overall < self.regeneration_threshold
        needs_human = (
            needs_regen and regeneration_count >= self.max_regenerations
        )

        result = EvaluationResult(
            session_id=session_id,
            task=task,
            output=output,
            scores=scores,
            overall_score=overall,
            passed=passed,
            needs_regeneration=needs_regen,
            needs_human_intervention=needs_human,
            regeneration_count=regeneration_count,
        )
        self._evaluation_history.append(result)
        return result

    def request_regeneration(self, result: EvaluationResult) -> dict[str, Any]:
        """請求 worker 重新生成"""
        if not result.needs_regeneration:
            return {"action": "NO_ACTION", "reason": "評估通過，無需重新生成"}

        if result.regeneration_count >= self.max_regenerations:
            return self.escalate_to_human(result)

        return {
            "action": "REGENERATE",
            "regeneration_count": result.regeneration_count + 1,
            "max_attempts": self.max_regenerations,
            "feedback": [f"{s.dimension.value}: {s.score:.1f}/100 — {s.feedback}" for s in result.scores],
            "overall_score": result.overall_score,
        }

    def escalate_to_human(self, result: EvaluationResult) -> dict[str, Any]:
        """升級到人類介入"""
        return {
            "action": "ESCALATE_TO_HUMAN",
            "reason": f"連續 {result.regeneration_count} 次重新生成仍低於閾值",
            "overall_score": result.overall_score,
            "lowest_dimensions": sorted(
                [(s.dimension.value, s.score) for s in result.scores],
                key=lambda x: x[1],
            )[:3],
            "feedback": [f"{s.dimension.value}: {s.score:.1f}/100 — {s.feedback}" for s in result.scores],
        }

    def detect_deviation(
        self,
        original_task: str,
        current_output: Any,
        expected_keywords: Optional[list[str]] = None,
    ) -> DeviationReport:
        """偵測 worker 偏離原定目標"""
        output_text = str(current_output).lower()
        expected = [k.lower() for k in (expected_keywords or [])]
        if not expected:
            return DeviationReport(
                expected_keywords=[],
                found_keywords=[],
                missing_keywords=[],
                semantic_similarity=1.0,
                deviation_severity="LOW",
                recommendation="無預期關鍵詞，無法評估偏離",
            )

        found = [k for k in expected if k in output_text]
        missing = [k for k in expected if k not in output_text]
        coverage = len(found) / len(expected) if expected else 1.0

        # 簡單語義相似度（基於關鍵詞覆蓋率）
        task_words = set(original_task.lower().split())
        output_words = set(output_text.split())
        overlap = len(task_words & output_words)
        similarity = overlap / max(len(task_words), 1)

        if coverage >= 0.8 and similarity >= 0.3:
            severity = "LOW"
            recommendation = "未偏離目標"
        elif coverage >= 0.5:
            severity = "MEDIUM"
            recommendation = f"建議補充關鍵詞：{', '.join(missing)}"
        else:
            severity = "HIGH"
            recommendation = f"嚴重偏離，缺少關鍵詞：{', '.join(missing)}"

        return DeviationReport(
            expected_keywords=expected_keywords or [],
            found_keywords=found,
            missing_keywords=missing,
            semantic_similarity=similarity,
            deviation_severity=severity,
            recommendation=recommendation,
        )

    def _calculate_overall_score(self, scores: list[QualityScore]) -> float:
        """加權計算整體分數"""
        total_weight = sum(s.weight for s in scores)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(s.score * s.weight for s in scores)
        return weighted_sum / total_weight

    # 默認評估器
    def _default_accuracy_evaluator(
        self, output: Any, criteria: dict[str, Any], dimension: QualityDimension
    ) -> QualityScore:
        output_text = str(output)
        if not output_text.strip():
            return QualityScore(dimension=dimension, score=0.0, feedback="輸出為空")
        # 簡單啟發式：非空 + 有一定長度
        length = len(output_text)
        if length < 10:
            return QualityScore(dimension=dimension, score=30.0, feedback="輸出過短")
        if length > 50:
            return QualityScore(dimension=dimension, score=80.0, feedback="輸出有實質內容")
        return QualityScore(dimension=dimension, score=60.0, feedback="輸出基本可接受")

    def _default_completeness_evaluator(
        self, output: Any, criteria: dict[str, Any], dimension: QualityDimension
    ) -> QualityScore:
        required_fields = criteria.get("required_fields", [])
        if not required_fields:
            return QualityScore(dimension=dimension, score=70.0, feedback="無必填欄位要求")
        output_dict = output if isinstance(output, dict) else {}
        present = sum(1 for f in required_fields if f in output_dict)
        score = (present / len(required_fields)) * 100
        fb = f"已覆蓋 {present}/{len(required_fields)} 必填欄位"
        return QualityScore(dimension=dimension, score=score, feedback=fb)

    def _default_timeliness_evaluator(
        self, output: Any, criteria: dict[str, Any], dimension: QualityDimension
    ) -> QualityScore:
        max_age_seconds = criteria.get("max_age_seconds", 3600)
        output_timestamp = criteria.get("output_timestamp")
        if not output_timestamp:
            return QualityScore(dimension=dimension, score=80.0, feedback="無時間戳，默認可接受")
        try:
            ts = datetime.fromisoformat(output_timestamp)
            now = datetime.now(timezone.utc)
            age = (now - ts).total_seconds()
            if age <= max_age_seconds:
                return QualityScore(dimension=dimension, score=100.0, feedback="時效符合要求")
            return QualityScore(dimension=dimension, score=40.0, feedback=f"已過時 {age:.0f} 秒")
        except Exception:
            return QualityScore(dimension=dimension, score=50.0, feedback="時間戳解析失敗")

    def _default_compliance_evaluator(
        self, output: Any, criteria: dict[str, Any], dimension: QualityDimension
    ) -> QualityScore:
        forbidden_keywords = criteria.get("forbidden_keywords", [])
        output_text = str(output).lower()
        violations = [k for k in forbidden_keywords if k.lower() in output_text]
        if violations:
            return QualityScore(dimension=dimension, score=20.0, feedback=f"違規關鍵詞：{', '.join(violations)}")
        return QualityScore(dimension=dimension, score=100.0, feedback="無違規")

    def _default_actionability_evaluator(
        self, output: Any, criteria: dict[str, Any], dimension: QualityDimension
    ) -> QualityScore:
        output_text = str(output)
        actionable_markers = ["TODO", "步驟", "step", "可以", "執行", "運行", "點擊"]
        if any(m.lower() in output_text.lower() for m in actionable_markers):
            return QualityScore(dimension=dimension, score=85.0, feedback="包含可執行指示")
        return QualityScore(dimension=dimension, score=50.0, feedback="缺少明確可執行指示")

    def get_evaluation_history(self) -> list[EvaluationResult]:
        """獲取評估歷史"""
        return list(self._evaluation_history)
