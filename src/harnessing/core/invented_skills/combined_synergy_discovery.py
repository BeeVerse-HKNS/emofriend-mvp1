from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Optional

from .base_engine import BaseInventionEngine
from .base_invention_engine import InventionResult, ConfidenceLevel
from .invention_registry import InventionRegistry

logger = structlog.get_logger()


@dataclass
class SynergyDiscovery:
    pair: tuple[str, str]
    synergy_type: str
    strength: float
    combined_formula: str
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class NewInventionCandidate:
    candidate_id: str
    formula: str
    source_synergies: list[str]
    description: str
    test_results: Optional[dict[str, Any]] = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNCERTAIN
    promoted: bool = False


@dataclass
class SynergyNetwork:
    nodes: list[str]
    edges: list[SynergyDiscovery]
    new_candidates: list[NewInventionCandidate]
    total_synergies: int = 0
    avg_strength: float = 0.0
    strongest_synergy: Optional[SynergyDiscovery] = None


class CombinedSynergyDiscoveryEngine:
    SYNERGY_THRESHOLD = 0.5
    PROMOTION_THRESHOLD = 0.8

    def __init__(self, registry: Optional[InventionRegistry] = None):
        self.registry = registry or InventionRegistry.get_instance()
        self._synergy_cache: list[SynergyDiscovery] = []
        self._candidate_cache: list[NewInventionCandidate] = []

    def discover_synergies(self, scenarios: list[dict[str, Any]]) -> list[SynergyDiscovery]:
        engines = self.registry.get_all()
        if len(engines) < 2:
            return []

        synergies = []
        engine_ids = list(engines.keys())

        for e1_id, e2_id in combinations(engine_ids, 2):
            e1 = engines[e1_id]
            e2 = engines[e2_id]

            if e2_id not in e1.get_synergy_partners() and e1_id not in e2.get_synergy_partners():
                continue

            combined_results = []
            for scenario in scenarios:
                try:
                    r1 = e1.execute(scenario)
                    r2 = e2.execute(scenario)
                    combined_results.append((r1, r2))
                except Exception:
                    continue

            if not combined_results:
                continue

            strength = self._compute_synergy_strength(combined_results)
            synergy_type = self._classify_synergy(e1_id, e2_id, combined_results)

            if strength >= self.SYNERGY_THRESHOLD:
                discovery = SynergyDiscovery(
                    pair=(e1_id, e2_id),
                    synergy_type=synergy_type,
                    strength=strength,
                    combined_formula=f"({e1.operator} ⊗ {e2.operator})",
                    description=f"{e1.name} + {e2.name}: {synergy_type} synergy (strength={strength:.2f})",
                    evidence={"scenarios_tested": len(scenarios), "avg_strength": strength},
                )
                synergies.append(discovery)
                logger.info("synergy_discovered", pair=(e1_id, e2_id), type=synergy_type, strength=strength)

        self._synergy_cache = synergies
        return synergies

    def generate_new_inventions(self, synergies: list[SynergyDiscovery]) -> list[NewInventionCandidate]:
        candidates = []
        for i, synergy in enumerate(synergies):
            if synergy.strength < self.PROMOTION_THRESHOLD:
                continue

            candidate = NewInventionCandidate(
                candidate_id=f"CAND-{i+1:03d}",
                formula=synergy.combined_formula,
                source_synergies=[f"{synergy.pair[0]}+{synergy.pair[1]}"],
                description=f"New invention from {synergy.description}",
                confidence=ConfidenceLevel.INFERRED,
            )
            candidates.append(candidate)
            logger.info("new_candidate_generated", candidate_id=candidate.candidate_id, formula=candidate.formula)

        self._candidate_cache = candidates
        return candidates

    def test_new_invention(self, candidate: NewInventionCandidate, scenarios: list[dict]) -> dict[str, Any]:
        source_ids = candidate.source_synergies[0].split("+")
        engines = self.registry.get_all()

        source_engines = [engines.get(sid) for sid in source_ids if sid in engines]
        if not source_engines:
            candidate.test_results = {"status": "failed", "reason": "source engines not found"}
            return candidate.test_results

        passed = 0
        total = len(scenarios)
        for scenario in scenarios:
            try:
                results = [e.execute(scenario) for e in source_engines]
                if all(r.is_valid() for r in results):
                    passed += 1
            except Exception:
                continue

        pass_rate = passed / max(total, 1)
        candidate.test_results = {
            "status": "passed" if pass_rate >= 0.7 else "failed",
            "pass_rate": pass_rate,
            "scenarios_tested": total,
        }
        candidate.confidence = ConfidenceLevel.VERIFIED if pass_rate >= 0.9 else (
            ConfidenceLevel.RESEARCHED if pass_rate >= 0.7 else ConfidenceLevel.INFERRED
        )

        if pass_rate >= 0.7:
            candidate.promoted = True

        return candidate.test_results

    def get_synergy_network(self) -> SynergyNetwork:
        synergies = self._synergy_cache
        candidates = self._candidate_cache

        nodes = list(self.registry.get_all().keys())
        avg_strength = sum(s.strength for s in synergies) / max(len(synergies), 1)
        strongest = max(synergies, key=lambda s: s.strength) if synergies else None

        return SynergyNetwork(
            nodes=nodes,
            edges=synergies,
            new_candidates=candidates,
            total_synergies=len(synergies),
            avg_strength=avg_strength,
            strongest_synergy=strongest,
        )

    def _compute_synergy_strength(self, combined_results: list[tuple[InventionResult, InventionResult]]) -> float:
        if not combined_results:
            return 0.0

        valid_pairs = sum(1 for r1, r2 in combined_results if r1.is_valid() and r2.is_valid())
        synergy_indicators = 0

        for r1, r2 in combined_results:
            if not r1.is_valid() or not r2.is_valid():
                continue
            if r1.synergy_detected and r2.invention_id in r1.synergy_detected:
                synergy_indicators += 1
            if r2.synergy_detected and r1.invention_id in r2.synergy_detected:
                synergy_indicators += 1
            shared_keys = set(r1.output.keys()) & set(r2.output.keys())
            if shared_keys:
                synergy_indicators += len(shared_keys) * 0.5

        base = valid_pairs / max(len(combined_results), 1)
        bonus = min(synergy_indicators / max(len(combined_results) * 2, 1), 1.0)
        return min(base * 0.6 + bonus * 0.4, 1.0)

    def _classify_synergy(self, e1_id: str, e2_id: str, results: list) -> str:
        e1_partners = []
        e2_partners = []

        engines = self.registry.get_all()
        if e1_id in engines:
            e1_partners = engines[e1_id].get_synergy_partners()
        if e2_id in engines:
            e2_partners = engines[e2_id].get_synergy_partners()

        if e2_id in e1_partners and e1_id in e2_partners:
            return "complementary"
        elif e2_id in e1_partners or e1_id in e2_partners:
            return "dependent"
        else:
            return "amplifying"
