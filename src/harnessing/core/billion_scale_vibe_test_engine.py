"""
BillionScaleVibeCodingTestEngine
1B Vibe Coding 情景測試引擎

公式：F² + C * R
- F = Formula（公式思維）
- C = Creativity（創意）
- R = Reasoning（推理）

解決痛點：
- Rule 38：樣本量充足規則（≥1,000,000）
- Rule 56：發明測試先行協議（≥10M cases）
- Rule 59：三輪擴展協議（10M → 100M → 1B → 10B）
- Rule 58：數據決定方向協議
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class PainpointCategory(Enum):
    WESTERN_LLM = "western_llm"
    CHINA_LLM = "china_llm"
    WESTERN_AGENTIC_AI = "western_agentic_ai"
    CHINA_AGENTIC_AI = "china_agentic_ai"
    HARNESSING_DIFFICULTIES = "harnessing_difficulties"


class CapabilityDimension(Enum):
    KNOWLEDGE = "K"
    REASONING = "R"
    CREATIVITY = "C"
    MEMORY = "M"
    SELF_HEALING = "S"
    GUARDRAILS = "G"
    AUTOMATION = "A"
    PREDICTION = "P"
    FORMULA = "F"
    HARDWARE = "H"


class FormulaOperator(Enum):
    UNION = "+"
    DIFFERENCE = "-"
    CROSS = "*"
    SPECIALIZE = "/"
    SELF_IMPROVE = "sq"
    DECOMPOSE = "sqrt"
    AMPLIFY = "^"
    ABSTRACT = "log"


class ConfidenceLevel(Enum):
    VERIFIED = "verified"
    RESEARCHED = "researched"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


class TaskType(Enum):
    CODING = "coding"
    CONTENT_CREATION = "content_creation"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class TestLayer(Enum):
    L1_QUICK_SCAN = "l1"
    L2_STRESS_TEST = "l2"
    L3_STABILITY = "l3"


@dataclass
class Painpoint:
    id: str
    painpoint: str
    severity: str
    dimension: str
    frequency: str
    category: PainpointCategory
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "painpoint": self.painpoint,
            "severity": self.severity,
            "dimension": self.dimension,
            "frequency": self.frequency,
            "category": self.category.value,
        }


@dataclass
class InventedSkill:
    id: str
    name: str
    formula: str
    dimensions: List[CapabilityDimension]
    painpoints_addressed: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "formula": self.formula,
            "dimensions": [d.value for d in self.dimensions],
            "painpoints_addressed": self.painpoints_addressed,
        }


@dataclass
class TestScenario:
    scenario_id: str
    painpoint: Optional[Painpoint]
    skill: Optional[InventedSkill]
    dimensions: List[CapabilityDimension]
    operators: List[FormulaOperator]
    confidence: ConfidenceLevel
    task_type: TaskType
    complexity: float
    expected_pass: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "painpoint": self.painpoint.to_dict() if self.painpoint else None,
            "skill": self.skill.to_dict() if self.skill else None,
            "dimensions": [d.value for d in self.dimensions],
            "operators": [op.value for op in self.operators],
            "confidence": self.confidence.value,
            "task_type": self.task_type.value,
            "complexity": self.complexity,
            "expected_pass": self.expected_pass,
            "metadata": self.metadata,
        }


@dataclass
class ScenarioResult:
    scenario_id: str
    passed: bool
    actual_output: Any
    expected_output: Any
    execution_time_ms: float
    token_count: int
    error: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNCERTAIN
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "passed": self.passed,
            "actual_output": str(self.actual_output)[:500] if self.actual_output else None,
            "expected_output": str(self.expected_output)[:500] if self.expected_output else None,
            "execution_time_ms": self.execution_time_ms,
            "token_count": self.token_count,
            "error": self.error,
            "confidence": self.confidence.value,
        }


@dataclass
class LayerTestResult:
    layer: TestLayer
    total_scenarios: int
    passed: int
    failed: int
    coverage_rate: float
    execution_time_s: float
    results: List[ScenarioResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer.value,
            "total_scenarios": self.total_scenarios,
            "passed": self.passed,
            "failed": self.failed,
            "coverage_rate": self.coverage_rate,
            "execution_time_s": self.execution_time_s,
            "results_count": len(self.results),
        }


@dataclass
class BenchmarkMetrics:
    scenario_pass_rate: float = 0.0
    painpoint_coverage_rate: float = 0.0
    rule_application_rate: float = 0.0
    research_success_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    token_efficiency: float = 0.0
    total_scenarios: int = 0
    total_passed: int = 0
    total_failed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_pass_rate": self.scenario_pass_rate,
            "painpoint_coverage_rate": self.painpoint_coverage_rate,
            "rule_application_rate": self.rule_application_rate,
            "research_success_rate": self.research_success_rate,
            "avg_response_time_ms": self.avg_response_time_ms,
            "token_efficiency": self.token_efficiency,
            "total_scenarios": self.total_scenarios,
            "total_passed": self.total_passed,
            "total_failed": self.total_failed,
        }


@dataclass
class ImprovementSuggestion:
    direction: str
    formula: str
    expected_effect: float
    confidence: ConfidenceLevel
    rationale: str
    affected_painpoints: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "formula": self.formula,
            "expected_effect": self.expected_effect,
            "confidence": self.confidence.value,
            "rationale": self.rationale,
            "affected_painpoints": self.affected_painpoints,
        }


class ScenarioGenerator:
    """
    ScenarioGenerator - 生成測試情景
    
    覆蓋維度：
    - 48 Vibe Coding 痛點（來自 painpoints_research.json）
    - 15 發明技能
    - 10 能力維度（K/R/C/M/S/G/A/P/F/H）
    - 8 公式運算符
    - 3 信心等級
    - 多種任務類型
    """
    
    VIBE_CODING_PAINPOINTS = [
        "short_term_memory", "single_solution", "too_fast_execution",
        "external_dependency", "ignoring_phase_outputs", "overconfidence",
        "hallucination_disguise", "scope_creep", "over_engineering",
        "ignoring_user_intent", "security_blind_spots", "missing_feedback_loops",
        "unnecessary_manual_approval", "requesting_manual_deletion",
        "rules_only_specific_scenarios", "requesting_manual_copy",
        "human_ai_understanding_gap", "api_integration_failures",
        "dom_change_fixes", "scattered_credentials", "too_many_dependencies",
        "unified_error_handling", "language_inconsistency", "acting_without_research",
        "system_limits_blocking", "output_without_qa", "supply_chain_risks",
        "environmental_hazards", "privacy_leaks", "insufficient_recovery",
        "timing_conflicts", "missing_compliance", "lack_self_improvement",
        "guardrail_conflicts", "coverage_gap_neglect", "generic_skills_not_deep",
        "cross_domain_no_synergy", "single_module_limit", "research_not_verified",
        "formula_for_selection", "invention_not_tested", "high_coverage_stop",
        "waiting_user_approval", "few_round_expansion", "sandbox_not_synced",
        "leaving_todos", "simplifying_prompt", "capability_gap_not_detected",
    ]
    
    INVENTED_SKILLS = [
        {"id": "INV-001", "name": "AdaptiveContextManager", "formula": "log(M*K) + A"},
        {"id": "INV-002", "name": "PredictiveMemoryPreloader", "formula": "P*M + K"},
        {"id": "INV-003", "name": "CrossDomainKnowledgeBridge", "formula": "K*K + log(A)"},
        {"id": "INV-004", "name": "IntentDrivenExecutor", "formula": "R*A - G"},
        {"id": "INV-005", "name": "SelfOptimizingPipeline", "formula": "sq(A) + S"},
        {"id": "INV-006", "name": "GuardrailAwareGenerator", "formula": "C*G + R"},
        {"id": "INV-007", "name": "HierarchicalKnowledgeIndexer", "formula": "log(K) + M"},
        {"id": "INV-008", "name": "ProactiveErrorPreventer", "formula": "P*S + G"},
        {"id": "INV-009", "name": "ContextualSkillRouter", "formula": "R/A + K"},
        {"id": "INV-010", "name": "FeedbackAmplifier", "formula": "sq(F) + M"},
        {"id": "INV-011", "name": "HardwareAwareScheduler", "formula": "H*A + P"},
        {"id": "INV-012", "name": "KnowledgeGraphBuilder", "formula": "K^R + M"},
        {"id": "INV-013", "name": "AdaptiveGuardTuner", "formula": "G/S + R"},
        {"id": "INV-014", "name": "MultiModalReasoner", "formula": "R*C + K"},
        {"id": "INV-015", "name": "ContinuousLearner", "formula": "log(S) + M*K"},
    ]
    
    def __init__(self, painpoints_data: Optional[Dict[str, Any]] = None):
        self.painpoints_data = painpoints_data
        self.painpoints: List[Painpoint] = []
        self.skills: List[InventedSkill] = []
        self._load_data()
    
    def _load_data(self):
        if self.painpoints_data:
            self._parse_painpoints_data()
        else:
            self._generate_default_painpoints()
        
        self._generate_skills()
    
    def _parse_painpoints_data(self):
        if not self.painpoints_data or "painpoints" not in self.painpoints_data:
            self._generate_default_painpoints()
            return
        
        for category_name, category_data in self.painpoints_data["painpoints"].items():
            try:
                category = PainpointCategory(category_name)
            except ValueError:
                continue
            
            for item in category_data.get("items", []):
                painpoint = Painpoint(
                    id=item.get("id", "UNKNOWN"),
                    painpoint=item.get("painpoint", ""),
                    severity=item.get("severity", "medium"),
                    dimension=item.get("dimension", "unknown"),
                    frequency=item.get("frequency", "medium"),
                    category=category,
                )
                self.painpoints.append(painpoint)
    
    def _generate_default_painpoints(self):
        for i, pp_name in enumerate(self.VIBE_CODING_PAINPOINTS):
            painpoint = Painpoint(
                id=f"HD-{i+1:03d}",
                painpoint=pp_name.replace("_", " "),
                severity="high" if i < 20 else "medium",
                dimension="memory" if i < 10 else "reasoning" if i < 20 else "planning",
                frequency="high",
                category=PainpointCategory.HARNESSING_DIFFICULTIES,
            )
            self.painpoints.append(painpoint)
    
    def _generate_skills(self):
        for skill_data in self.INVENTED_SKILLS:
            dimensions = self._parse_formula_dimensions(skill_data["formula"])
            skill = InventedSkill(
                id=skill_data["id"],
                name=skill_data["name"],
                formula=skill_data["formula"],
                dimensions=dimensions,
                painpoints_addressed=[],
            )
            self.skills.append(skill)
    
    def _parse_formula_dimensions(self, formula: str) -> List[CapabilityDimension]:
        dimensions = []
        dim_map = {
            "K": CapabilityDimension.KNOWLEDGE,
            "R": CapabilityDimension.REASONING,
            "C": CapabilityDimension.CREATIVITY,
            "M": CapabilityDimension.MEMORY,
            "S": CapabilityDimension.SELF_HEALING,
            "G": CapabilityDimension.GUARDRAILS,
            "A": CapabilityDimension.AUTOMATION,
            "P": CapabilityDimension.PREDICTION,
            "F": CapabilityDimension.FORMULA,
            "H": CapabilityDimension.HARDWARE,
        }
        for char in formula:
            if char in dim_map and dim_map[char] not in dimensions:
                dimensions.append(dim_map[char])
        return dimensions if dimensions else [CapabilityDimension.KNOWLEDGE]
    
    def generate_scenarios(
        self,
        num_scenarios: int = 10_000_000,
        include_painpoints: bool = True,
        include_skills: bool = True,
        seed: Optional[int] = None,
    ) -> List[TestScenario]:
        """
        生成測試情景
        
        使用採樣策略生成大量情景，確保覆蓋所有維度
        """
        if seed is not None:
            random.seed(seed)
        
        scenarios = []
        scenario_id = 0
        
        dimension_values = list(CapabilityDimension)
        operator_values = list(FormulaOperator)
        confidence_values = list(ConfidenceLevel)
        task_values = list(TaskType)
        
        if include_painpoints:
            for painpoint in self.painpoints:
                for _ in range(max(1, num_scenarios // len(self.painpoints) // 10)):
                    dimensions = random.sample(
                        dimension_values, 
                        k=min(3, len(dimension_values))
                    )
                    operators = random.sample(
                        operator_values,
                        k=min(2, len(operator_values))
                    )
                    
                    scenario = TestScenario(
                        scenario_id=f"SC-{scenario_id:08d}",
                        painpoint=painpoint,
                        skill=None,
                        dimensions=dimensions,
                        operators=operators,
                        confidence=random.choice(confidence_values),
                        task_type=random.choice(task_values),
                        complexity=random.uniform(0.1, 1.0),
                        expected_pass=True,
                        metadata={"generation": "painpoint_based"},
                    )
                    scenarios.append(scenario)
                    scenario_id += 1
                    
                    if len(scenarios) >= num_scenarios:
                        return scenarios[:num_scenarios]
        
        if include_skills:
            for skill in self.skills:
                for _ in range(max(1, num_scenarios // len(self.skills) // 10)):
                    operators = random.sample(
                        operator_values,
                        k=min(2, len(operator_values))
                    )
                    
                    scenario = TestScenario(
                        scenario_id=f"SC-{scenario_id:08d}",
                        painpoint=None,
                        skill=skill,
                        dimensions=skill.dimensions,
                        operators=operators,
                        confidence=random.choice(confidence_values),
                        task_type=random.choice(task_values),
                        complexity=random.uniform(0.1, 1.0),
                        expected_pass=True,
                        metadata={"generation": "skill_based"},
                    )
                    scenarios.append(scenario)
                    scenario_id += 1
                    
                    if len(scenarios) >= num_scenarios:
                        return scenarios[:num_scenarios]
        
        while len(scenarios) < num_scenarios:
            dimensions = random.sample(
                dimension_values,
                k=random.randint(1, min(5, len(dimension_values)))
            )
            operators = random.sample(
                operator_values,
                k=random.randint(1, min(4, len(operator_values)))
            )
            
            scenario = TestScenario(
                scenario_id=f"SC-{scenario_id:08d}",
                painpoint=random.choice(self.painpoints) if self.painpoints else None,
                skill=random.choice(self.skills) if self.skills else None,
                dimensions=dimensions,
                operators=operators,
                confidence=random.choice(confidence_values),
                task_type=random.choice(task_values),
                complexity=random.uniform(0.1, 1.0),
                expected_pass=True,
                metadata={"generation": "random"},
            )
            scenarios.append(scenario)
            scenario_id += 1
        
        return scenarios[:num_scenarios]
    
    def generate_stratified_sample(
        self,
        total_scenarios: int,
        strata: Dict[str, float],
    ) -> Dict[str, List[TestScenario]]:
        """
        生成分層採樣
        
        Args:
            total_scenarios: 總情景數
            strata: 各層比例，如 {"painpoint": 0.4, "skill": 0.3, "random": 0.3}
        """
        result = {}
        
        for stratum_name, proportion in strata.items():
            num = int(total_scenarios * proportion)
            
            if stratum_name == "painpoint":
                scenarios = self.generate_scenarios(
                    num_scenarios=num,
                    include_painpoints=True,
                    include_skills=False,
                )
            elif stratum_name == "skill":
                scenarios = self.generate_scenarios(
                    num_scenarios=num,
                    include_painpoints=False,
                    include_skills=True,
                )
            else:
                scenarios = self.generate_scenarios(
                    num_scenarios=num,
                    include_painpoints=True,
                    include_skills=True,
                )
            
            result[stratum_name] = scenarios
        
        return result


class ThreeLayerTestingFramework:
    """
    ThreeLayerTestingFramework - 三層測試框架
    
    L1 (10M cases) - Quick scan，識別明顯問題
    L2 (100M cases) - Stress test，發現邊界問題
    L3 (1B cases) - Stability confirmation，統計顯著性
    
    遵循 Rule 59：三輪擴展協議
    """
    
    LAYER_CONFIGS = {
        TestLayer.L1_QUICK_SCAN: {
            "name": "L1 Quick Scan",
            "target_cases": 10_000_000,
            "sample_rate": 1.0,
            "parallel_workers": 4,
            "batch_size": 100_000,
        },
        TestLayer.L2_STRESS_TEST: {
            "name": "L2 Stress Test",
            "target_cases": 100_000_000,
            "sample_rate": 0.1,
            "parallel_workers": 8,
            "batch_size": 1_000_000,
        },
        TestLayer.L3_STABILITY: {
            "name": "L3 Stability",
            "target_cases": 1_000_000_000,
            "sample_rate": 0.01,
            "parallel_workers": 16,
            "batch_size": 10_000_000,
        },
    }
    
    def __init__(
        self,
        scenario_generator: ScenarioGenerator,
        executor: Optional[Callable] = None,
    ):
        self.generator = scenario_generator
        self.executor = executor or self._default_executor
        self.layer_results: Dict[TestLayer, LayerTestResult] = {}
        self.checkpoint_file: Optional[Path] = None
    
    def _default_executor(self, scenario: TestScenario) -> ScenarioResult:
        """
        默認執行器 - 模擬測試執行
        """
        start_time = time.time()
        
        pass_probability = 0.85
        if scenario.painpoint:
            if scenario.painpoint.severity == "critical":
                pass_probability = 0.7
            elif scenario.painpoint.severity == "high":
                pass_probability = 0.8
        
        if scenario.skill:
            pass_probability += 0.05
        
        passed = random.random() < pass_probability
        
        execution_time = random.uniform(10, 100)
        token_count = random.randint(100, 1000)
        
        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            passed=passed,
            actual_output={"result": "pass" if passed else "fail"},
            expected_output={"result": "pass"},
            execution_time_ms=execution_time,
            token_count=token_count,
            confidence=scenario.confidence,
        )
    
    def run_layer(
        self,
        layer: TestLayer,
        scenarios: Optional[List[TestScenario]] = None,
        num_scenarios: Optional[int] = None,
        checkpoint: Optional[Dict[str, Any]] = None,
    ) -> LayerTestResult:
        """
        執行單層測試
        """
        config = self.LAYER_CONFIGS[layer]
        start_time = time.time()
        
        if scenarios is None:
            target = num_scenarios or config["target_cases"]
            sample_size = int(target * config["sample_rate"])
            scenarios = self.generator.generate_scenarios(num_scenarios=sample_size)
        
        if checkpoint:
            scenarios = scenarios[checkpoint.get("processed", 0):]
        
        results: List[ScenarioResult] = []
        passed = 0
        failed = 0
        
        batch_size = config["batch_size"]
        workers = config["parallel_workers"]
        
        for i in range(0, len(scenarios), batch_size):
            batch = scenarios[i:i + batch_size]
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_scenario = {
                    executor.submit(self.executor, scenario): scenario
                    for scenario in batch
                }
                
                for future in as_completed(future_to_scenario):
                    try:
                        result = future.result()
                        results.append(result)
                        if result.passed:
                            passed += 1
                        else:
                            failed += 1
                    except Exception as e:
                        failed += 1
                        results.append(ScenarioResult(
                            scenario_id=future_to_scenario[future].scenario_id,
                            passed=False,
                            actual_output=None,
                            expected_output=None,
                            execution_time_ms=0,
                            token_count=0,
                            error=str(e),
                        ))
        
        total = len(scenarios)
        coverage_rate = passed / total if total > 0 else 0.0
        execution_time = time.time() - start_time
        
        layer_result = LayerTestResult(
            layer=layer,
            total_scenarios=total,
            passed=passed,
            failed=failed,
            coverage_rate=coverage_rate,
            execution_time_s=execution_time,
            results=results,
        )
        
        self.layer_results[layer] = layer_result
        return layer_result
    
    def run_all_layers(
        self,
        l1_scenarios: int = 10_000_000,
        l2_scenarios: int = 100_000_000,
        l3_scenarios: int = 1_000_000_000,
        resume_from_checkpoint: bool = False,
    ) -> Dict[TestLayer, LayerTestResult]:
        """
        執行所有三層測試
        
        遵循 Rule 59：三輪擴展協議
        """
        checkpoint = None
        if resume_from_checkpoint and self.checkpoint_file:
            checkpoint = self._load_checkpoint()
        
        l1_result = self.run_layer(
            TestLayer.L1_QUICK_SCAN,
            num_scenarios=l1_scenarios,
            checkpoint=checkpoint.get("l1") if checkpoint else None,
        )
        
        l2_result = self.run_layer(
            TestLayer.L2_STRESS_TEST,
            num_scenarios=l2_scenarios,
            checkpoint=checkpoint.get("l2") if checkpoint else None,
        )
        
        l3_result = self.run_layer(
            TestLayer.L3_STABILITY,
            num_scenarios=l3_scenarios,
            checkpoint=checkpoint.get("l3") if checkpoint else None,
        )
        
        self._save_checkpoint()
        
        return {
            TestLayer.L1_QUICK_SCAN: l1_result,
            TestLayer.L2_STRESS_TEST: l2_result,
            TestLayer.L3_STABILITY: l3_result,
        }
    
    def _save_checkpoint(self):
        if not self.checkpoint_file:
            return
        
        checkpoint_data = {
            "timestamp": datetime.now().isoformat(),
            "layers": {},
        }
        
        for layer, result in self.layer_results.items():
            checkpoint_data["layers"][layer.value] = {
                "processed": result.total_scenarios,
                "passed": result.passed,
                "failed": result.failed,
            }
        
        try:
            with open(self.checkpoint_file, "w") as f:
                json.dump(checkpoint_data, f)
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")
    
    def _load_checkpoint(self) -> Optional[Dict[str, Any]]:
        if not self.checkpoint_file or not self.checkpoint_file.exists():
            return None
        
        try:
            with open(self.checkpoint_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return None
    
    def check_convergence(self) -> Tuple[bool, float]:
        """
        檢查三層結果是否收斂
        
        收斂條件：連續三層覆蓋率變化 <1%
        """
        if len(self.layer_results) < 3:
            return False, 0.0
        
        rates = [
            self.layer_results[TestLayer.L1_QUICK_SCAN].coverage_rate,
            self.layer_results[TestLayer.L2_STRESS_TEST].coverage_rate,
            self.layer_results[TestLayer.L3_STABILITY].coverage_rate,
        ]
        
        diff1 = abs(rates[1] - rates[0])
        diff2 = abs(rates[2] - rates[1])
        
        converged = diff1 < 0.01 and diff2 < 0.01
        final_rate = rates[-1]
        
        return converged, final_rate


class BeeVerseBenchmark:
    """
    BeeVerseBenchmark - 性能指標追蹤
    
    追蹤指標：
    - Scenario pass rate（情景通過率）
    - Painpoint coverage rate（痛點覆蓋率）
    - Rule application rate（規則應用率）
    - Research success rate（研究成功率）
    - Average response time（平均響應時間）
    - Token efficiency（Token 效率）
    """
    
    def __init__(self):
        self.metrics = BenchmarkMetrics()
        self.painpoint_results: Dict[str, List[bool]] = {}
        self.rule_applications: Dict[str, int] = {}
        self.research_results: List[bool] = []
        self.response_times: List[float] = []
        self.token_counts: List[int] = []
    
    def update_from_results(self, results: List[ScenarioResult]):
        """
        從測試結果更新指標
        """
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        
        self.metrics.total_scenarios += len(results)
        self.metrics.total_passed += passed
        self.metrics.total_failed += failed
        
        for result in results:
            self.response_times.append(result.execution_time_ms)
            self.token_counts.append(result.token_count)
        
        self._recalculate_metrics()
    
    def track_painpoint(self, painpoint_id: str, passed: bool):
        """
        追蹤痛點解決情況
        """
        if painpoint_id not in self.painpoint_results:
            self.painpoint_results[painpoint_id] = []
        self.painpoint_results[painpoint_id].append(passed)
        self._recalculate_metrics()
    
    def track_rule_application(self, rule_id: str):
        """
        追蹤規則應用
        """
        self.rule_applications[rule_id] = self.rule_applications.get(rule_id, 0) + 1
        self._recalculate_metrics()
    
    def track_research_result(self, success: bool):
        """
        追蹤研究結果
        """
        self.research_results.append(success)
        self._recalculate_metrics()
    
    def _recalculate_metrics(self):
        """
        重新計算所有指標
        """
        if self.metrics.total_scenarios > 0:
            self.metrics.scenario_pass_rate = (
                self.metrics.total_passed / self.metrics.total_scenarios
            )
        
        if self.painpoint_results:
            resolved = sum(
                1 for results in self.painpoint_results.values()
                if any(results)
            )
            self.metrics.painpoint_coverage_rate = resolved / len(self.painpoint_results)
        
        if self.rule_applications:
            total_applications = sum(self.rule_applications.values())
            unique_rules = len(self.rule_applications)
            self.metrics.rule_application_rate = unique_rules / max(1, total_applications / 10)
        
        if self.research_results:
            self.metrics.research_success_rate = (
                sum(self.research_results) / len(self.research_results)
            )
        
        if self.response_times:
            self.metrics.avg_response_time_ms = (
                sum(self.response_times) / len(self.response_times)
            )
        
        if self.token_counts:
            total_tokens = sum(self.token_counts)
            if self.metrics.total_passed > 0:
                self.metrics.token_efficiency = self.metrics.total_passed / max(1, total_tokens / 1000)
    
    def get_metrics(self) -> BenchmarkMetrics:
        return self.metrics
    
    def get_report(self) -> Dict[str, Any]:
        """
        生成基準報告
        """
        return {
            "metrics": self.metrics.to_dict(),
            "painpoint_summary": {
                pid: {"resolved": any(results), "attempts": len(results)}
                for pid, results in self.painpoint_results.items()
            },
            "top_rules": sorted(
                self.rule_applications.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
            "research_stats": {
                "total": len(self.research_results),
                "successful": sum(self.research_results),
            },
        }


class ImprovementAnalyzer:
    """
    ImprovementAnalyzer - 分析測試結果生成改進建議
    
    使用公式思維法生成改進方向
    """
    
    def __init__(self):
        self.failed_scenarios: List[TestScenario] = []
        self.failure_patterns: Dict[str, int] = {}
    
    def analyze(
        self,
        layer_results: Dict[TestLayer, LayerTestResult],
        scenarios: List[TestScenario],
    ) -> List[ImprovementSuggestion]:
        """
        分析測試結果，生成改進建議
        """
        suggestions = []
        
        self._identify_failed_scenarios(layer_results, scenarios)
        self._analyze_failure_patterns()
        
        suggestions.extend(self._generate_dimension_suggestions())
        suggestions.extend(self._generate_operator_suggestions())
        suggestions.extend(self._generate_painpoint_suggestions())
        suggestions.extend(self._generate_skill_suggestions())
        
        return sorted(suggestions, key=lambda x: x.expected_effect, reverse=True)
    
    def _identify_failed_scenarios(
        self,
        layer_results: Dict[TestLayer, LayerTestResult],
        scenarios: List[TestScenario],
    ):
        """
        識別失敗的情景
        """
        self.failed_scenarios = []
        
        scenario_map = {s.scenario_id: s for s in scenarios}
        
        for layer_result in layer_results.values():
            for result in layer_result.results:
                if not result.passed and result.scenario_id in scenario_map:
                    self.failed_scenarios.append(scenario_map[result.scenario_id])
    
    def _analyze_failure_patterns(self):
        """
        分析失敗模式
        """
        self.failure_patterns = {}
        
        for scenario in self.failed_scenarios:
            if scenario.painpoint:
                key = f"painpoint:{scenario.painpoint.dimension}"
                self.failure_patterns[key] = self.failure_patterns.get(key, 0) + 1
            
            for dim in scenario.dimensions:
                key = f"dimension:{dim.value}"
                self.failure_patterns[key] = self.failure_patterns.get(key, 0) + 1
            
            for op in scenario.operators:
                key = f"operator:{op.value}"
                self.failure_patterns[key] = self.failure_patterns.get(key, 0) + 1
    
    def _generate_dimension_suggestions(self) -> List[ImprovementSuggestion]:
        """
        基於維度生成改進建議
        """
        suggestions = []
        
        dimension_failures = {
            k: v for k, v in self.failure_patterns.items()
            if k.startswith("dimension:")
        }
        
        if not dimension_failures:
            return suggestions
        
        worst_dim = max(dimension_failures.items(), key=lambda x: x[1])
        dim_name = worst_dim[0].split(":")[1]
        
        dim_map = {
            "K": CapabilityDimension.KNOWLEDGE,
            "R": CapabilityDimension.REASONING,
            "C": CapabilityDimension.CREATIVITY,
            "M": CapabilityDimension.MEMORY,
            "S": CapabilityDimension.SELF_HEALING,
            "G": CapabilityDimension.GUARDRAILS,
            "A": CapabilityDimension.AUTOMATION,
            "P": CapabilityDimension.PREDICTION,
            "F": CapabilityDimension.FORMULA,
            "H": CapabilityDimension.HARDWARE,
        }
        
        if dim_name in dim_map:
            target_dim = dim_map[dim_name]
            
            suggestions.append(ImprovementSuggestion(
                direction=f"增強 {target_dim.name} 能力",
                formula=f"sq({target_dim.value})",
                expected_effect=0.15,
                confidence=ConfidenceLevel.INFERRED,
                rationale=f"維度 {target_dim.name} 失敗率最高 ({worst_dim[1]} 次)",
                affected_painpoints=[s.painpoint.id for s in self.failed_scenarios[:10] if s.painpoint],
            ))
        
        return suggestions
    
    def _generate_operator_suggestions(self) -> List[ImprovementSuggestion]:
        """
        基於運算符生成改進建議
        """
        suggestions = []
        
        operator_failures = {
            k: v for k, v in self.failure_patterns.items()
            if k.startswith("operator:")
        }
        
        if not operator_failures:
            return suggestions
        
        worst_op = max(operator_failures.items(), key=lambda x: x[1])
        op_name = worst_op[0].split(":")[1]
        
        op_map = {
            "+": "聯合",
            "-": "差異",
            "*": "交叉",
            "/": "專門化",
            "sq": "自我改善",
            "sqrt": "分解",
            "^": "放大",
            "log": "抽象",
        }
        
        if op_name in op_map:
            suggestions.append(ImprovementSuggestion(
                direction=f"優化 {op_map[op_name]} 運算符",
                formula=f"log(K) {op_name} S",
                expected_effect=0.10,
                confidence=ConfidenceLevel.INFERRED,
                rationale=f"運算符 {op_map[op_name]} 失敗率最高 ({worst_op[1]} 次)",
                affected_painpoints=[],
            ))
        
        return suggestions
    
    def _generate_painpoint_suggestions(self) -> List[ImprovementSuggestion]:
        """
        基於痛點生成改進建議
        """
        suggestions = []
        
        painpoint_failures: Dict[str, int] = {}
        for scenario in self.failed_scenarios:
            if scenario.painpoint:
                pid = scenario.painpoint.id
                painpoint_failures[pid] = painpoint_failures.get(pid, 0) + 1
        
        if not painpoint_failures:
            return suggestions
        
        top_failures = sorted(painpoint_failures.items(), key=lambda x: x[1], reverse=True)[:5]
        
        for pid, count in top_failures:
            suggestions.append(ImprovementSuggestion(
                direction=f"解決痛點 {pid}",
                formula="S + G + R",
                expected_effect=0.05 * (count / max(painpoint_failures.values())),
                confidence=ConfidenceLevel.INFERRED,
                rationale=f"痛點 {pid} 失敗 {count} 次",
                affected_painpoints=[pid],
            ))
        
        return suggestions
    
    def _generate_skill_suggestions(self) -> List[ImprovementSuggestion]:
        """
        基於技能生成改進建議
        """
        suggestions = []
        
        skill_coverage: Dict[str, int] = {}
        for scenario in self.failed_scenarios:
            if scenario.skill:
                sid = scenario.skill.id
                skill_coverage[sid] = skill_coverage.get(sid, 0) + 1
        
        if not skill_coverage:
            return suggestions
        
        worst_skills = sorted(skill_coverage.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for sid, count in worst_skills:
            suggestions.append(ImprovementSuggestion(
                direction=f"改進技能 {sid}",
                formula="sq(S) + K",
                expected_effect=0.08,
                confidence=ConfidenceLevel.INFERRED,
                rationale=f"技能 {sid} 覆蓋不足 ({count} 次失敗)",
                affected_painpoints=[],
            ))
        
        return suggestions


class BillionScaleVibeCodingTestEngine:
    """
    BillionScaleVibeCodingTestEngine - 1B Vibe Coding 情景測試引擎
    
    公式：F² + C * R
    
    主要組件：
    - ScenarioGenerator：生成測試情景
    - ThreeLayerTestingFramework：三層測試框架
    - BeeVerseBenchmark：性能指標追蹤
    - ImprovementAnalyzer：改進建議生成
    
    遵循規則：
    - Rule 38：樣本量充足規則
    - Rule 56：發明測試先行協議
    - Rule 58：數據決定方向協議
    - Rule 59：三輪擴展協議
    """
    
    def __init__(
        self,
        painpoints_data: Optional[Dict[str, Any]] = None,
        executor: Optional[Callable] = None,
        checkpoint_dir: Optional[Path] = None,
    ):
        self.scenario_generator = ScenarioGenerator(painpoints_data)
        self.testing_framework = ThreeLayerTestingFramework(
            self.scenario_generator,
            executor,
        )
        self.benchmark = BeeVerseBenchmark()
        self.improvement_analyzer = ImprovementAnalyzer()
        
        self.checkpoint_dir = checkpoint_dir or Path("data/billion_scale_checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.all_scenarios: List[TestScenario] = []
        self.layer_results: Dict[TestLayer, LayerTestResult] = {}
    
    def run_quick_test(
        self,
        num_scenarios: int = 1_000_000,
    ) -> Dict[str, Any]:
        """
        快速測試 - 用於開發驗證
        """
        logger.info(f"Running quick test with {num_scenarios:,} scenarios")
        
        self.all_scenarios = self.scenario_generator.generate_scenarios(num_scenarios)
        
        l1_result = self.testing_framework.run_layer(
            TestLayer.L1_QUICK_SCAN,
            scenarios=self.all_scenarios[:num_scenarios],
        )
        
        self.layer_results = {TestLayer.L1_QUICK_SCAN: l1_result}
        self.benchmark.update_from_results(l1_result.results)
        
        return self._generate_report("quick_test")
    
    def run_full_test(
        self,
        l1_scenarios: int = 10_000_000,
        l2_scenarios: int = 100_000_000,
        l3_scenarios: int = 1_000_000_000,
        resume: bool = False,
    ) -> Dict[str, Any]:
        """
        完整測試 - 三層全部執行
        
        遵循 Rule 59：三輪擴展協議
        """
        logger.info("Starting full billion-scale test")
        
        strata = {"painpoint": 0.4, "skill": 0.3, "random": 0.3}
        stratified = self.scenario_generator.generate_stratified_sample(
            l1_scenarios,
            strata,
        )
        
        self.all_scenarios = []
        for scenarios in stratified.values():
            self.all_scenarios.extend(scenarios)
        
        self.layer_results = self.testing_framework.run_all_layers(
            l1_scenarios=l1_scenarios,
            l2_scenarios=l2_scenarios,
            l3_scenarios=l3_scenarios,
            resume_from_checkpoint=resume,
        )
        
        for layer_result in self.layer_results.values():
            self.benchmark.update_from_results(layer_result.results)
        
        converged, final_rate = self.testing_framework.check_convergence()
        
        return self._generate_report(
            "full_test",
            converged=converged,
            final_rate=final_rate,
        )
    
    def run_three_round_expansion(
        self,
        initial_scenarios: int = 10_000_000,
    ) -> Dict[str, Any]:
        """
        三輪擴展測試
        
        遵循 Rule 59：10M → 100M → 1B → 10B
        """
        logger.info("Starting three-round expansion test")
        
        rounds = [
            ("Round 1", initial_scenarios),
            ("Round 2", initial_scenarios * 10),
            ("Round 3", initial_scenarios * 100),
        ]
        
        round_results = []
        
        for round_name, num_scenarios in rounds:
            logger.info(f"Running {round_name} with {num_scenarios:,} scenarios")
            
            scenarios = self.scenario_generator.generate_scenarios(num_scenarios)
            result = self.testing_framework.run_layer(
                TestLayer.L1_QUICK_SCAN,
                scenarios=scenarios,
            )
            
            self.benchmark.update_from_results(result.results)
            round_results.append({
                "round": round_name,
                "scenarios": num_scenarios,
                "coverage_rate": result.coverage_rate,
                "passed": result.passed,
                "failed": result.failed,
            })
        
        rates = [r["coverage_rate"] for r in round_results]
        converged = all(abs(rates[i+1] - rates[i]) < 0.01 for i in range(len(rates) - 1))
        
        return {
            "test_type": "three_round_expansion",
            "rounds": round_results,
            "converged": converged,
            "final_coverage_rate": rates[-1],
            "benchmark": self.benchmark.get_report(),
        }
    
    def analyze_and_suggest(self) -> List[ImprovementSuggestion]:
        """
        分析結果並生成改進建議
        """
        return self.improvement_analyzer.analyze(
            self.layer_results,
            self.all_scenarios,
        )
    
    def _generate_report(
        self,
        test_type: str,
        converged: bool = False,
        final_rate: float = 0.0,
    ) -> Dict[str, Any]:
        """
        生成測試報告
        """
        report = {
            "test_type": test_type,
            "timestamp": datetime.now().isoformat(),
            "formula": "F² + C * R",
            "layers": {
                layer.value: result.to_dict()
                for layer, result in self.layer_results.items()
            },
            "benchmark": self.benchmark.get_report(),
            "converged": converged,
            "final_coverage_rate": final_rate,
            "total_scenarios": len(self.all_scenarios),
            "painpoints_covered": len(set(
                s.painpoint.id for s in self.all_scenarios if s.painpoint
            )),
            "skills_tested": len(set(
                s.skill.id for s in self.all_scenarios if s.skill
            )),
        }
        
        if converged:
            report["improvement_suggestions"] = [
                s.to_dict() for s in self.analyze_and_suggest()[:10]
            ]
        
        return report
    
    def save_report(self, report: Dict[str, Any], filepath: Optional[Path] = None):
        """
        保存報告到文件
        """
        if filepath is None:
            filepath = self.checkpoint_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report saved to {filepath}")
        return filepath
    
    def integrate_with_formula_coverage(
        self,
        formula_engine: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        整合 FormulaDrivenUniversalCoverage
        
        使用公式思維法分析測試結果
        """
        try:
            from .formula_driven_universal_coverage import (
                FormulaDrivenUniversalCoverage,
                FormulaOperator as FDFormulaOperator,
                FormulaNode,
                FormulaResult,
            )
            
            if formula_engine is None:
                formula_engine = FormulaDrivenUniversalCoverage()
            
            coverage_analysis = {
                "dimensions": {},
                "operators": {},
                "formulas": [],
            }
            
            for dim in CapabilityDimension:
                dim_scenarios = [
                    s for s in self.all_scenarios
                    if dim in s.dimensions
                ]
                if dim_scenarios:
                    passed = sum(
                        1 for r in self.layer_results.get(TestLayer.L1_QUICK_SCAN, LayerTestResult(TestLayer.L1_QUICK_SCAN, 0, 0, 0, 0.0, 0.0)).results
                        if r.passed and any(
                            s.scenario_id == r.scenario_id and dim in s.dimensions
                            for s in dim_scenarios
                        )
                    )
                    coverage_analysis["dimensions"][dim.value] = {
                        "total": len(dim_scenarios),
                        "passed": passed,
                        "rate": passed / len(dim_scenarios) if dim_scenarios else 0.0,
                    }
            
            for op in FormulaOperator:
                op_scenarios = [
                    s for s in self.all_scenarios
                    if op in s.operators
                ]
                if op_scenarios:
                    passed = sum(
                        1 for r in self.layer_results.get(TestLayer.L1_QUICK_SCAN, LayerTestResult(TestLayer.L1_QUICK_SCAN, 0, 0, 0, 0.0, 0.0)).results
                        if r.passed and any(
                            s.scenario_id == r.scenario_id and op in s.operators
                            for s in op_scenarios
                        )
                    )
                    coverage_analysis["operators"][op.value] = {
                        "total": len(op_scenarios),
                        "passed": passed,
                        "rate": passed / len(op_scenarios) if op_scenarios else 0.0,
                    }
            
            return {
                "integration": "formula_driven_universal_coverage",
                "coverage_analysis": coverage_analysis,
                "benchmark": self.benchmark.get_report(),
            }
            
        except ImportError as e:
            logger.warning(f"FormulaDrivenUniversalCoverage not available: {e}")
            return {"integration": "failed", "error": str(e)}
    
    def integrate_with_local_llm_research(
        self,
        research_bridge: Optional[Any] = None,
        query: str = "vibe coding painpoints",
    ) -> Dict[str, Any]:
        """
        整合 LocalLLMResearchBridge
        
        使用本地 LLM 研究增強測試分析
        """
        try:
            from .local_llm_research_bridge import LocalLLMResearchBridge
            
            if research_bridge is None:
                research_bridge = LocalLLMResearchBridge()
            
            research_results = []
            
            failed_painpoints = set()
            for scenario in self.all_scenarios:
                if scenario.painpoint:
                    for layer_result in self.layer_results.values():
                        for result in layer_result.results:
                            if not result.passed and result.scenario_id == scenario.scenario_id:
                                failed_painpoints.add(scenario.painpoint.painpoint)
            
            if failed_painpoints:
                research_query = f"Research solutions for: {', '.join(list(failed_painpoints)[:5])}"
                try:
                    research_result = research_bridge.research(research_query)
                    research_results.append({
                        "query": research_query,
                        "result": research_result,
                    })
                except Exception as e:
                    logger.warning(f"Research failed: {e}")
            
            return {
                "integration": "local_llm_research_bridge",
                "research_results": research_results,
                "failed_painpoints_count": len(failed_painpoints),
            }
            
        except ImportError as e:
            logger.warning(f"LocalLLMResearchBridge not available: {e}")
            return {"integration": "failed", "error": str(e)}
    
    def run_integrated_analysis(
        self,
        use_formula_coverage: bool = True,
        use_local_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        運行整合分析
        
        結合所有整合組件進行全面分析
        """
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "base_report": self._generate_report("integrated_analysis"),
            "integrations": {},
        }
        
        if use_formula_coverage:
            analysis["integrations"]["formula_coverage"] = self.integrate_with_formula_coverage()
        
        if use_local_llm:
            analysis["integrations"]["local_llm_research"] = self.integrate_with_local_llm_research()
        
        suggestions = self.analyze_and_suggest()
        analysis["improvement_suggestions"] = [s.to_dict() for s in suggestions[:10]]
        
        return analysis


def run_billion_scale_test(
    painpoints_file: Optional[str] = None,
    quick_mode: bool = True,
    num_scenarios: int = 1_000_000,
) -> Dict[str, Any]:
    """
    運行 Billion Scale 測試
    
    Args:
        painpoints_file: 痛點數據文件路徑
        quick_mode: 是否使用快速模式
        num_scenarios: 快速模式下的情景數
    
    Returns:
        測試報告
    """
    painpoints_data = None
    if painpoints_file:
        try:
            with open(painpoints_file, "r", encoding="utf-8") as f:
                painpoints_data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load painpoints file: {e}")
    
    engine = BillionScaleVibeCodingTestEngine(painpoints_data=painpoints_data)
    
    if quick_mode:
        report = engine.run_quick_test(num_scenarios)
    else:
        report = engine.run_full_test()
    
    return report


if __name__ == "__main__":
    import sys
    
    quick_mode = "--full" not in sys.argv
    num_scenarios = 1_000_000
    
    for arg in sys.argv:
        if arg.startswith("--scenarios="):
            num_scenarios = int(arg.split("=")[1])
    
    painpoints_file = "data/painpoints_research.json"
    
    report = run_billion_scale_test(
        painpoints_file=painpoints_file,
        quick_mode=quick_mode,
        num_scenarios=num_scenarios,
    )
    
    print(json.dumps(report, indent=2, ensure_ascii=False))
