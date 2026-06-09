from __future__ import annotations

import structlog
from typing import Any, Optional

from .base_engine import BaseInventionEngine
from .base_invention_engine import InventionResult

logger = structlog.get_logger()


class InventionRegistry:
    _instance: Optional[InventionRegistry] = None
    _engines: dict[str, BaseInventionEngine]

    def __init__(self) -> None:
        self._engines = {}

    @classmethod
    def get_instance(cls) -> InventionRegistry:
        if cls._instance is None:
            cls._instance = InventionRegistry()
        return cls._instance

    def register(self, engine: BaseInventionEngine) -> None:
        if engine.invention_id in self._engines:
            logger.warning("overwriting_existing_engine", invention_id=engine.invention_id)
        self._engines[engine.invention_id] = engine
        logger.info("engine_registered", invention_id=engine.invention_id, name=engine.name)

    def get(self, invention_id: str) -> Optional[BaseInventionEngine]:
        return self._engines.get(invention_id)

    def get_all(self) -> dict[str, BaseInventionEngine]:
        return dict(self._engines)

    def get_by_category(self, category: str) -> list[BaseInventionEngine]:
        return [e for e in self._engines.values() if e.category == category]

    def get_synergy_network(self) -> dict[str, list[str]]:
        network = {}
        for eid, engine in self._engines.items():
            network[eid] = engine.get_synergy_partners()
        return network

    def execute_all(self, context: dict[str, Any]) -> dict[str, InventionResult]:
        results = {}
        for eid, engine in self._engines.items():
            try:
                results[eid] = engine.execute(context)
            except Exception as e:
                logger.error("engine_execution_failed", invention_id=eid, error=str(e))
        return results

    def list_inventions(self) -> list[dict[str, str]]:
        return [engine.get_info() for engine in self._engines.values()]

    def count(self) -> int:
        return len(self._engines)

    def register_all_builtin_engines(self) -> int:
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

        registered = 0
        for engine in engines:
            if engine.invention_id not in self._engines:
                self.register(engine)
                registered += 1
            else:
                logger.info("engine_already_registered", invention_id=engine.invention_id)

        logger.info("builtin_engines_registered", total=len(engines), newly_registered=registered)
        return registered
