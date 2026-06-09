from __future__ import annotations

import json
import os
import random
import structlog
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .base_engine import BaseInventionEngine
from .base_invention_engine import InventionResult, ConfidenceLevel
from .invention_registry import InventionRegistry
from .combined_synergy_discovery import CombinedSynergyDiscoveryEngine
from .sci_001_quantum_superposition import QuantumSuperpositionInvention
from .sci_002_emergence_detector import EmergenceDetector
from .sci_003_entropy_aware_design import EntropyAwareDesign
from .sci_004_field_theoretic import FieldTheoreticInvention
from .sci_005_symmetry_breaking import SymmetryBreakingCreativity
from .ewf_001_quantum_zen import QuantumZenCognition
from .ewf_002_iching_systems import IChingSystemsThinking
from .ewf_003_suntzu_evolutionary import SunTzuEvolutionaryStrategy
from .ewf_004_dao_emergence import DaoEmergenceFramework
from .ewf_005_pratitya_causal import PratityaCausalReasoning

logger = structlog.get_logger()

INVENTION_CATEGORIES = [
    "decision_making",
    "system_analysis",
    "strategic_planning",
    "creative_generation",
    "causal_reasoning",
]

INVENTION_TARGET_MAP: dict[str, list[str]] = {
    "decision_making": ["SCI-001", "EWF-001"],
    "system_analysis": ["SCI-002", "SCI-003", "EWF-002"],
    "strategic_planning": ["EWF-003", "EWF-004"],
    "creative_generation": ["SCI-004", "SCI-005"],
    "causal_reasoning": ["EWF-005", "SCI-001", "SCI-003"],
}


@dataclass
class TestScenario:
    scenario_id: str
    category: str
    context: dict
    expected_type: str


@dataclass
class LayerTestResult:
    layer: str
    total_scenarios: int
    passed: int
    failed: int
    pass_rate: float
    duration_ms: float
    details: list[dict]


@dataclass
class CombinedTestResult:
    l1_result: Optional[LayerTestResult]
    l2_result: Optional[LayerTestResult]
    l3_result: Optional[LayerTestResult]
    converged: bool
    convergence_rate: float


class ScenarioGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def generate(self, count: int) -> list[TestScenario]:
        scenarios: list[TestScenario] = []
        for _ in range(count):
            category = random.choice(INVENTION_CATEGORIES)
            target_inventions = INVENTION_TARGET_MAP[category]
            target = random.choice(target_inventions)
            context = self._make_context(target)
            self._counter += 1
            scenarios.append(TestScenario(
                scenario_id=f"SCN-{self._counter:06d}",
                category=category,
                context=context,
                expected_type=target,
            ))
        return scenarios

    def _make_context(self, invention_id: str) -> dict[str, Any]:
        if invention_id == "SCI-001":
            return {"hypotheses": [
                {"id": f"H{i}", "content": f"hypothesis_{i}", "evidence": random.random()}
                for i in range(random.randint(2, 6))
            ]}
        if invention_id == "SCI-002":
            return {"skills": [
                {"name": f"skill_{i}", "features": [random.random() for _ in range(3)]}
                for i in range(random.randint(2, 5))
            ]}
        if invention_id == "SCI-003":
            return {"system_data": {
                "code_complexity": random.random(),
                "dependency_count": random.random(),
                "config_drift": random.random(),
                "test_coverage": random.random(),
                "doc_freshness": random.random(),
                "api_stability": random.random(),
            }}
        if invention_id == "SCI-004":
            return {"skills": [
                {"name": f"s{i}", "center": [random.random(), random.random()], "amplitude": random.uniform(0.5, 2.0)}
                for i in range(random.randint(2, 4))
            ]}
        if invention_id == "SCI-005":
            return {"solution": [random.randint(1, 10) for _ in range(random.randint(3, 6))]}
        if invention_id == "EWF-001":
            return {"decision": {
                "evidence_level": random.random(),
                "attachment_level": random.random(),
                "time_invested": random.random(),
                "emotional_language": random.random(),
                "commitment_signals": random.random(),
                "skill_level": random.random(),
                "challenge_level": random.random(),
            }}
        if invention_id == "EWF-002":
            return {"system_metrics": {
                "growth": random.random(),
                "stability": random.random(),
                "complexity": random.random(),
                "momentum": random.random(),
                "cohesion": random.random(),
                "openness": random.random(),
            }}
        if invention_id == "EWF-003":
            return {"competition": {
                "factors": {
                    "dao": random.random(),
                    "tian": random.random(),
                    "di": random.random(),
                    "jiang": random.random(),
                    "fa": random.random(),
                },
                "strategies": {"cooperate": random.random(), "defect": random.random(), "adapt": random.random()},
                "rounds": random.randint(5, 15),
            }}
        if invention_id == "EWF-004":
            return {"system_state": {
                "complexity": random.random(),
                "stability": random.random(),
                "adaptability": random.random(),
                "emergence_potential": random.random(),
            }}
        if invention_id == "EWF-005":
            return {"variables": [
                {"name": chr(65 + i), "type": random.choice(["cause", "effect", "mediator"])}
                for i in range(random.randint(3, 6))
            ]}
        return {}


class ThreeLayerTestFramework:
    LAYER_CONFIG: dict[str, int] = {
        "L1": 1000,
        "L2": 10000,
        "L3": 50000,
    }

    def run_layer(
        self,
        layer: str,
        scenarios: list[TestScenario],
        registry: InventionRegistry,
    ) -> LayerTestResult:
        start = time.perf_counter()
        passed = 0
        failed = 0
        details: list[dict] = []
        engines = registry.get_all()

        for scenario in scenarios:
            target = scenario.expected_type
            engine = engines.get(target)
            if engine is None:
                failed += 1
                details.append({
                    "scenario_id": scenario.scenario_id,
                    "target": target,
                    "status": "no_engine",
                })
                continue

            try:
                result = engine.execute(scenario.context)
                is_valid = engine.validate(result)
                if is_valid and result.is_valid():
                    passed += 1
                    details.append({
                        "scenario_id": scenario.scenario_id,
                        "target": target,
                        "status": "passed",
                        "confidence": result.confidence.value,
                    })
                else:
                    failed += 1
                    details.append({
                        "scenario_id": scenario.scenario_id,
                        "target": target,
                        "status": "failed_validation",
                    })
            except Exception as exc:
                failed += 1
                details.append({
                    "scenario_id": scenario.scenario_id,
                    "target": target,
                    "status": "error",
                    "error": str(exc),
                })

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        total = len(scenarios)
        pass_rate = passed / max(total, 1)

        logger.info(
            "layer_completed",
            layer=layer,
            total=total,
            passed=passed,
            failed=failed,
            pass_rate=round(pass_rate, 4),
            duration_ms=round(elapsed_ms, 2),
        )

        return LayerTestResult(
            layer=layer,
            total_scenarios=total,
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            duration_ms=elapsed_ms,
            details=details,
        )

    def run_all(self, registry: InventionRegistry) -> CombinedTestResult:
        generator = ScenarioGenerator()

        l1_scenarios = generator.generate(self.LAYER_CONFIG["L1"])
        l1_result = self.run_layer("L1", l1_scenarios, registry)

        l2_scenarios = generator.generate(self.LAYER_CONFIG["L2"])
        l2_result = self.run_layer("L2", l2_scenarios, registry)

        l3_scenarios = generator.generate(self.LAYER_CONFIG["L3"])
        l3_result = self.run_layer("L3", l3_scenarios, registry)

        converged = self.check_convergence(l2_result, l3_result)
        convergence_rate = abs(l3_result.pass_rate - l2_result.pass_rate)

        logger.info(
            "three_layer_test_complete",
            l1_pass_rate=round(l1_result.pass_rate, 4),
            l2_pass_rate=round(l2_result.pass_rate, 4),
            l3_pass_rate=round(l3_result.pass_rate, 4),
            converged=converged,
            convergence_rate=round(convergence_rate, 6),
        )

        return CombinedTestResult(
            l1_result=l1_result,
            l2_result=l2_result,
            l3_result=l3_result,
            converged=converged,
            convergence_rate=convergence_rate,
        )

    def check_convergence(
        self,
        l2_result: LayerTestResult,
        l3_result: LayerTestResult,
    ) -> bool:
        return abs(l3_result.pass_rate - l2_result.pass_rate) < 0.01


class CombinedTestEngine:
    RESULTS_DIR = os.path.join("data", "invented_formulas")
    RESULTS_FILE = "combined_test_results.json"

    def __init__(self) -> None:
        self._registry: Optional[InventionRegistry] = None
        self._framework = ThreeLayerTestFramework()
        self._synergy_engine: Optional[CombinedSynergyDiscoveryEngine] = None

    def execute(self) -> CombinedTestResult:
        self._registry = InventionRegistry()
        self._register_all_engines()

        combined_result = self._framework.run_all(self._registry)

        self._run_synergy_discovery()

        self._save_results(combined_result)

        logger.info(
            "combined_test_engine_complete",
            converged=combined_result.converged,
            convergence_rate=round(combined_result.convergence_rate, 6),
        )

        return combined_result

    def _register_all_engines(self) -> None:
        engines: list[BaseInventionEngine] = [
            QuantumSuperpositionInvention(),
            EmergenceDetector(),
            EntropyAwareDesign(),
            FieldTheoreticInvention(),
            SymmetryBreakingCreativity(),
            QuantumZenCognition(),
            IChingSystemsThinking(),
            SunTzuEvolutionaryStrategy(),
            DaoEmergenceFramework(),
            PratityaCausalReasoning(),
        ]
        for engine in engines:
            self._registry.register(engine)
        logger.info("all_engines_registered", count=len(engines))

    def _run_synergy_discovery(self) -> None:
        self._synergy_engine = CombinedSynergyDiscoveryEngine(self._registry)
        generator = ScenarioGenerator()
        synergy_scenarios = generator.generate(200)
        scenario_dicts = [s.context for s in synergy_scenarios]
        synergies = self._synergy_engine.discover_synergies(scenario_dicts)
        self._synergy_engine.generate_new_inventions(synergies)
        logger.info("synergy_discovery_complete", synergy_count=len(synergies))

    def _save_results(self, combined_result: CombinedTestResult) -> None:
        results_dir = os.path.abspath(self.RESULTS_DIR)
        os.makedirs(results_dir, exist_ok=True)

        data: dict[str, Any] = {
            "converged": combined_result.converged,
            "convergence_rate": combined_result.convergence_rate,
            "layers": {},
        }

        for label, layer_result in [
            ("L1", combined_result.l1_result),
            ("L2", combined_result.l2_result),
            ("L3", combined_result.l3_result),
        ]:
            if layer_result is None:
                continue
            data["layers"][label] = {
                "total_scenarios": layer_result.total_scenarios,
                "passed": layer_result.passed,
                "failed": layer_result.failed,
                "pass_rate": layer_result.pass_rate,
                "duration_ms": layer_result.duration_ms,
                "details_sample": layer_result.details[:50],
            }

        if self._synergy_engine is not None:
            network = self._synergy_engine.get_synergy_network()
            data["synergy_network"] = {
                "total_synergies": network.total_synergies,
                "avg_strength": network.avg_strength,
                "strongest_synergy": (
                    {
                        "pair": network.strongest_synergy.pair,
                        "type": network.strongest_synergy.synergy_type,
                        "strength": network.strongest_synergy.strength,
                    }
                    if network.strongest_synergy
                    else None
                ),
                "new_candidates": [
                    {
                        "candidate_id": c.candidate_id,
                        "formula": c.formula,
                        "promoted": c.promoted,
                        "confidence": c.confidence.value,
                    }
                    for c in network.new_candidates
                ],
            }

        filepath = os.path.join(results_dir, self.RESULTS_FILE)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        logger.info("results_saved", filepath=filepath)
