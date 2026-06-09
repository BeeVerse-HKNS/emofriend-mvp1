"""
Cognitive Architecture Extension (D-100)
2026-06-03 Daily Learning Cycle

擴展 UnifiedCognitiveArchitecture 整合 5 個新引擎：
1. CrossCulturalThinkingEngine (R-ERR-081)
2. SessionContextManager (R-ERR-082)
3. SupervisorAgent (R-ERR-083)
4. AbandonmentDetector (R-ERR-084)
5. FrameworkSelector (R-ERR-085)

採用「擴展模式」而非「直接修改」，避免破壞現有架構。

信心等級：🔍 已研究（D-100 Daily Learning）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from harnessing.core.abandonment_detector import (
    AbandonmentDetector,
    AbandonmentPattern,
    TaskRecord,
)
from harnessing.core.cross_cultural_engine import (
    CrossCulturalThinkingEngine,
)
from harnessing.core.framework_selector import (
    FrameworkRecommendation,
    FrameworkSelector,
    ScenarioType,
)
from harnessing.core.session_context_manager import (
    Session,
    SessionContext,
    SessionContextManager,
)
from harnessing.core.supervisor_agent import (
    EvaluationResult,
    SupervisorAgent,
)


class ExtendedEngine(str, Enum):
    """5 個擴展引擎"""
    CROSS_CULTURAL = "cross_cultural"
    SESSION_CONTEXT = "session_context"
    SUPERVISOR = "supervisor"
    ABANDONMENT = "abandonment"
    FRAMEWORK = "framework"


@dataclass
class ExtendedEngineOutput:
    """擴展引擎嘅輸出"""
    engine_name: str
    output_data: dict[str, Any]
    confidence: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source_rule: str = ""  # 對應嘅 error-rule


@dataclass
class CognitiveExtensionResult:
    """認知架構擴展結果"""
    task: str
    engine_outputs: list[ExtendedEngineOutput]
    cross_cultural_recommendations: list[str] = field(default_factory=list)
    framework_recommendation: Optional[FrameworkRecommendation] = None
    abandonment_alerts: list[str] = field(default_factory=list)
    supervisor_evaluation: Optional[EvaluationResult] = None
    session_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CognitiveArchitectureExtension:
    """認知架構擴展 — 整合 D-100 嘅 5 個新引擎

    採用策略模式 + 依賴注入，可獨立使用每個引擎。
    """

    def __init__(self, db_dir: str = "data") -> None:
        self.db_dir = db_dir
        self.cross_cultural = CrossCulturalThinkingEngine()
        self.session_manager = SessionContextManager(
            db_path=f"{db_dir}/sessions.db"
        )
        self.supervisor = SupervisorAgent()
        self.abandonment = AbandonmentDetector(
            db_path=f"{db_dir}/tasks.db"
        )
        self.framework = FrameworkSelector()

    def get_engine_health(self) -> dict[str, dict[str, Any]]:
        """獲取所有引擎嘅健康狀態"""
        return {
            ExtendedEngine.CROSS_CULTURAL.value: {
                "status": "OK",
                "methods_loaded": len(self.cross_cultural._profiles),
                "source_rule": "R-ERR-081",
            },
            ExtendedEngine.SESSION_CONTEXT.value: {
                "status": "OK",
                "db_path": str(self.session_manager.db_path),
                "source_rule": "R-ERR-082",
            },
            ExtendedEngine.SUPERVISOR.value: {
                "status": "OK",
                "pass_threshold": self.supervisor.pass_threshold,
                "max_regenerations": self.supervisor.max_regenerations,
                "source_rule": "R-ERR-083",
            },
            ExtendedEngine.ABANDONMENT.value: {
                "status": "OK",
                "scenarios": [s.code for s in self.abandonment.get_all_scenarios()],
                "inactivity_days": self.abandonment.inactivity_days,
                "source_rule": "R-ERR-084",
            },
            ExtendedEngine.FRAMEWORK.value: {
                "status": "OK",
                "options_count": len(self.framework.get_all_options()),
                "zero_dependency_options": sum(
                    1 for o in self.framework.get_all_options() if not o.external_dependencies
                ),
                "source_rule": "R-ERR-085",
            },
        }

    def think_cross_cultural(self, scenario: str, user_culture: str = "中國") -> ExtendedEngineOutput:
        """執行跨文化思維分析"""
        self.framework.select_for_scenario(ScenarioType.RAPID_PROTOTYPE)
        method_profiles = self.cross_cultural.recommend_for_scenario(scenario)
        culture_specific = self.cross_cultural.suggest_for_user_culture(user_culture)
        return ExtendedEngineOutput(
            engine_name=ExtendedEngine.CROSS_CULTURAL.value,
            output_data={
                "scenario": scenario,
                "user_culture": user_culture,
                "method_recommendations": [
                    {"method": p.method.value, "use_cases": p.use_cases}
                    for p in method_profiles
                ],
                "culture_specific_methods": [
                    {"method": p.method.value, "culture": p.culture_sphere.value}
                    for p in culture_specific
                ],
            },
            confidence=0.85,
            source_rule="R-ERR-081",
        )

    def create_session(self, metadata: Optional[dict[str, Any]] = None) -> tuple[Session, SessionContext]:
        """建立 Session + Context（封裝 Session-Context 分離）"""
        session = self.session_manager.create_session(metadata)
        context = self.session_manager.get_context(session.id)
        if context is None:
            context = SessionContext(session_id=session.id)
        return session, context

    def supervised_evaluate(
        self,
        session_id: str,
        task: str,
        output: Any,
        criteria: Optional[dict[str, Any]] = None,
    ) -> EvaluationResult:
        """執行監督評估"""
        return self.supervisor.evaluate_output(
            session_id=session_id,
            task=task,
            output=output,
            expected_criteria=criteria,
        )

    def select_framework(
        self,
        scenario: ScenarioType,
        max_options: int = 3,
    ) -> FrameworkRecommendation:
        """執行場景化框架選型"""
        return self.framework.select_for_scenario(scenario, max_options)

    def detect_abandonment(self) -> list[Any]:
        """執行半途而廢偵測"""
        return self.abandonment.detect_abandonment()

    def register_task(
        self,
        task_id: str,
        name: str,
        scenario_code: Optional[str] = None,
        estimated_hours: float = 4.0,
    ) -> TaskRecord:
        """註冊任務（自動判斷複雜度）"""
        complexity = self.abandonment.estimate_complexity(estimated_hours)
        pattern = AbandonmentPattern.STARTED_NO_FOLLOWUP
        now = datetime.now(timezone.utc).isoformat()
        task = TaskRecord(
            id=task_id,
            name=name,
            scenario_code=scenario_code,
            pattern=pattern,
            complexity=complexity,
            status="IN_PROGRESS",
            created_at=now,
            last_update=now,
            estimated_hours=estimated_hours,
            progress=0.0,
        )
        self.abandonment.register_task(task)
        return task

    def full_think(
        self,
        task: str,
        scenario: Optional[str] = None,
        user_culture: str = "中國",
        framework_scenario: Optional[ScenarioType] = None,
    ) -> CognitiveExtensionResult:
        """完整思考 — 整合所有 5 個引擎"""
        outputs = []

        # 1. 跨文化思維
        if scenario:
            outputs.append(self.think_cross_cultural(scenario, user_culture))

        # 2. 框架選型
        framework_rec = None
        if framework_scenario:
            framework_rec = self.select_framework(framework_scenario)
            outputs.append(
                ExtendedEngineOutput(
                    engine_name=ExtendedEngine.FRAMEWORK.value,
                    output_data={
                        "scenario": framework_scenario.value,
                        "zero_dependency": framework_rec.zero_dependency_option.name,
                        "additional": [o.name for o in framework_rec.additional_options],
                    },
                    confidence=0.90,
                    source_rule="R-ERR-085",
                )
            )

        # 3. 半途而廢偵測
        alerts = self.abandonment.detect_abandonment()
        outputs.append(
            ExtendedEngineOutput(
                engine_name=ExtendedEngine.ABANDONMENT.value,
                output_data={
                    "alerts_count": len(alerts),
                    "alerts": [
                        {"task_id": a.task_id, "action": a.action.value}
                        for a in alerts
                    ],
                },
                confidence=0.95,
                source_rule="R-ERR-084",
            )
        )

        # 4. Session-Context 演示
        demo_session, demo_context = self.create_session({"task": task})
        outputs.append(
            ExtendedEngineOutput(
                engine_name=ExtendedEngine.SESSION_CONTEXT.value,
                output_data={
                    "session_id": demo_session.id,
                    "session_status": demo_session.status.value,
                    "context_history_length": len(demo_context.history),
                },
                confidence=1.0,
                source_rule="R-ERR-082",
            )
        )

        return CognitiveExtensionResult(
            task=task,
            engine_outputs=outputs,
            cross_cultural_recommendations=[
                f"{p.method.value}：{p.decision_style}"
                for p in self.cross_cultural.recommend_for_scenario(scenario or "策略")
            ],
            framework_recommendation=framework_rec,
            abandonment_alerts=[a.message for a in alerts],
            session_id=demo_session.id,
        )
