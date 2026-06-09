from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = structlog.get_logger()


class EdgeType(Enum):
    CAUSAL = "causal"
    CORRELATION = "correlation"
    SPURIOUS = "spurious"
    UNKNOWN = "unknown"


@dataclass
class CausalNode:
    name: str
    variables: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEdge:
    source: str
    target: str
    edge_type: EdgeType
    strength: float = 1.0
    confidence: float = 0.5


class CausalGraphBuilder:
    def __init__(self):
        self._nodes: dict[str, CausalNode] = {}
        self._edges: list[CausalEdge] = []

    def add_node(self, name: str, variables: list[str] | None = None) -> CausalNode:
        node = CausalNode(name=name, variables=variables or [])
        self._nodes[name] = node
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.UNKNOWN,
        strength: float = 1.0,
        confidence: float = 0.5
    ) -> CausalEdge:
        edge = CausalEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            strength=strength,
            confidence=confidence
        )
        self._edges.append(edge)
        return edge

    def get_graph(self) -> dict[str, Any]:
        return {
            "nodes": {name: {"variables": node.variables, "metadata": node.metadata} for name, node in self._nodes.items()},
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "type": e.edge_type.value,
                    "strength": e.strength,
                    "confidence": e.confidence
                }
                for e in self._edges
            ]
        }

    def find_ancestors(self, node_name: str) -> list[str]:
        ancestors = set()
        to_check = [node_name]
        while to_check:
            current = to_check.pop()
            for edge in self._edges:
                if edge.target == current and edge.source not in ancestors:
                    ancestors.add(edge.source)
                    to_check.append(edge.source)
        return list(ancestors)

    def find_descendants(self, node_name: str) -> list[str]:
        descendants = set()
        to_check = [node_name]
        while to_check:
            current = to_check.pop()
            for edge in self._edges:
                if edge.source == current and edge.target not in descendants:
                    descendants.add(edge.target)
                    to_check.append(edge.target)
        return list(descendants)


class CausalDiscovery:
    def __init__(self, significance_threshold: float = 0.05):
        self.significance_threshold = significance_threshold

    def discover_from_data(self, data: dict[str, list[float]]) -> list[tuple[str, str, float]]:
        discovered_edges = []
        variables = list(data.keys())
        for i, var1 in enumerate(variables):
            for var2 in variables[i+1:]:
                correlation = self._compute_correlation(data[var1], data[var2])
                if abs(correlation) > (1 - self.significance_threshold):
                    discovered_edges.append((var1, var2, abs(correlation)))
        return discovered_edges

    def _compute_correlation(self, x: list[float], y: list[float]) -> float:
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denom_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
        denom_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5
        if denom_x == 0 or denom_y == 0:
            return 0.0
        return numerator / (denom_x * denom_y)

    def distinguish_causal_from_correlation(
        self,
        var1: str,
        var2: str,
        temporal_info: dict[str, int] | None = None,
        domain_knowledge: dict[str, str] | None = None
    ) -> EdgeType:
        if temporal_info:
            if temporal_info.get(var1, 0) < temporal_info.get(var2, 0):
                return EdgeType.CAUSAL
            elif temporal_info.get(var2, 0) < temporal_info.get(var1, 0):
                return EdgeType.CAUSAL
        if domain_knowledge:
            key = f"{var1}->{var2}"
            if key in domain_knowledge:
                return EdgeType.CAUSAL
            key = f"{var2}->{var1}"
            if key in domain_knowledge:
                return EdgeType.CAUSAL
        return EdgeType.CORRELATION


class InterventionSimulator:
    def __init__(self, graph_builder: CausalGraphBuilder):
        self.graph = graph_builder

    def intervene(
        self,
        variable: str,
        value: float,
        current_state: dict[str, float]
    ) -> dict[str, float]:
        new_state = dict(current_state)
        new_state[variable] = value
        descendants = self.graph.find_descendants(variable)
        for desc in descendants:
            effect = self._compute_intervention_effect(variable, desc, value, current_state)
            new_state[desc] = current_state.get(desc, 0.0) + effect
        return new_state

    def _compute_intervention_effect(
        self,
        source: str,
        target: str,
        value: float,
        current_state: dict[str, float]
    ) -> float:
        relevant_edges = [
            e for e in self.graph._edges
            if e.source == source and e.target == target
        ]
        if not relevant_edges:
            return 0.0
        total_effect = 0.0
        for edge in relevant_edges:
            if edge.edge_type == EdgeType.CAUSAL:
                total_effect += edge.strength * edge.confidence * value * 0.1
        return total_effect

    def compare_interventions(
        self,
        variable: str,
        values: list[float],
        current_state: dict[str, float]
    ) -> list[dict[str, Any]]:
        results = []
        for value in values:
            new_state = self.intervene(variable, value, current_state)
            results.append({
                "intervention_value": value,
                "resulting_state": new_state,
                "changed_variables": [
                    k for k in new_state
                    if abs(new_state[k] - current_state.get(k, 0.0)) > 0.001
                ]
            })
        return results


class CounterfactualReasoner:
    def __init__(self, graph_builder: CausalGraphBuilder):
        self.graph = graph_builder

    def reason(
        self,
        factual: dict[str, Any],
        counterfactual_condition: dict[str, Any],
        outcome_variable: str
    ) -> dict[str, Any]:
        cf_state = dict(factual)
        for var, value in counterfactual_condition.items():
            cf_state[var] = value
        ancestors = self.graph.find_ancestors(outcome_variable)
        relevant_vars = [v for v in ancestors if v in counterfactual_condition]
        cf_outcome = self._estimate_counterfactual_outcome(
            cf_state,
            outcome_variable,
            relevant_vars
        )
        factual_outcome = factual.get(outcome_variable, 0.0)
        return {
            "factual_outcome": factual_outcome,
            "counterfactual_outcome": cf_outcome,
            "difference": cf_outcome - factual_outcome,
            "intervened_variables": list(counterfactual_condition.keys()),
            "confidence": self._compute_confidence(relevant_vars)
        }

    def _estimate_counterfactual_outcome(
        self,
        state: dict[str, Any],
        outcome_var: str,
        relevant_vars: list[str]
    ) -> float:
        base_value = state.get(outcome_var, 0.0)
        total_adjustment = 0.0
        for var in relevant_vars:
            for edge in self.graph._edges:
                if edge.source == var and edge.target == outcome_var:
                    adjustment = state.get(var, 0.0) * edge.strength * edge.confidence * 0.1
                    total_adjustment += adjustment
        return base_value + total_adjustment

    def _compute_confidence(self, relevant_vars: list[str]) -> float:
        if not relevant_vars:
            return 0.5
        relevant_edges = [
            e for e in self.graph._edges
            if e.source in relevant_vars
        ]
        if not relevant_edges:
            return 0.3
        avg_confidence = sum(e.confidence for e in relevant_edges) / len(relevant_edges)
        return avg_confidence


class CausalReasoningEngine:
    def __init__(self) -> None:
        self._formula = "R * K + C ^ H"
        self._capability = "causal_reasoning_engine"
        self._id = "INV-007"
        self.graph_builder = CausalGraphBuilder()
        self.discovery = CausalDiscovery()
        self.intervention = InterventionSimulator(self.graph_builder)
        self.counterfactual = CounterfactualReasoner(self.graph_builder)

    def analyze(
        self,
        data: dict[str, list[float]] | None = None,
        known_relationships: list[dict[str, Any]] | None = None,
        temporal_info: dict[str, int] | None = None,
        domain_knowledge: dict[str, str] | None = None
    ) -> dict[str, Any]:
        try:
            if known_relationships:
                self._build_known_relationships(known_relationships)
            discovered = []
            if data:
                discovered = self.discovery.discover_from_data(data)
                for var1, var2, strength in discovered:
                    edge_type = self.discovery.distinguish_causal_from_correlation(
                        var1, var2, temporal_info, domain_knowledge
                    )
                    self.graph_builder.add_edge(var1, var2, edge_type, strength)
            result = {
                "causal_graph": self.graph_builder.get_graph(),
                "discovered_relationships": len(discovered),
                "causal_edges": sum(
                    1 for e in self.graph_builder._edges
                    if e.edge_type == EdgeType.CAUSAL
                ),
                "correlation_edges": sum(
                    1 for e in self.graph_builder._edges
                    if e.edge_type == EdgeType.CORRELATION
                )
            }
            logger.info(
                "causal_reasoning_engine_success",
                capability=self._capability,
                causal_edges=result["causal_edges"]
            )
            return {"status": "success", "capability": self._capability, "result": result, "formula": self._formula}
        except Exception as exc:
            logger.error("causal_reasoning_engine_failed", capability=self._capability, error=str(exc))
            return {"status": "error", "capability": self._capability, "error": str(exc)}

    def execute(
        self,
        data: dict[str, list[float]] | None = None,
        known_relationships: list[dict[str, Any]] | None = None,
        temporal_info: dict[str, int] | None = None,
        domain_knowledge: dict[str, str] | None = None
    ) -> dict[str, Any]:
        return self.analyze(data, known_relationships, temporal_info, domain_knowledge)

    def simulate_intervention(
        self,
        variable: str,
        value: float,
        current_state: dict[str, float]
    ) -> dict[str, Any]:
        new_state = self.intervention.intervene(variable, value, current_state)
        return {
            "original_state": current_state,
            "intervention": {"variable": variable, "value": value},
            "resulting_state": new_state
        }

    def reason_counterfactual(
        self,
        factual: dict[str, Any],
        counterfactual_condition: dict[str, Any],
        outcome_variable: str
    ) -> dict[str, Any]:
        return self.counterfactual.reason(factual, counterfactual_condition, outcome_variable)

    def _build_known_relationships(self, relationships: list[dict[str, Any]]) -> None:
        for rel in relationships:
            source = rel.get("source")
            target = rel.get("target")
            if source and target:
                self.graph_builder.add_node(source)
                self.graph_builder.add_node(target)
                edge_type_str = rel.get("type", "unknown")
                try:
                    edge_type = EdgeType(edge_type_str)
                except ValueError:
                    edge_type = EdgeType.UNKNOWN
                self.graph_builder.add_edge(
                    source,
                    target,
                    edge_type,
                    rel.get("strength", 1.0),
                    rel.get("confidence", 0.5)
                )


if __name__ == "__main__":
    engine = CausalReasoningEngine()
    known_rels = [
        {"source": "smoking", "target": "lung_cancer", "type": "causal", "strength": 0.8, "confidence": 0.9},
        {"source": "genetics", "target": "lung_cancer", "type": "causal", "strength": 0.3, "confidence": 0.7},
        {"source": "age", "target": "lung_cancer", "type": "causal", "strength": 0.2, "confidence": 0.8},
    ]
    result = engine.analyze(known_relationships=known_rels)
    print(f"Status: {result['status']}")
    print(f"Causal edges: {result['result']['causal_edges']}")
    print(f"Correlation edges: {result['result']['correlation_edges']}")
    intervention_result = engine.simulate_intervention("smoking", 0.0, {"smoking": 1.0, "lung_cancer": 0.5})
    print(f"Intervention result: {intervention_result['resulting_state']}")
    cf_result = engine.reason_counterfactual(
        {"smoking": 1.0, "lung_cancer": 0.5},
        {"smoking": 0.0},
        "lung_cancer"
    )
    print(f"Counterfactual difference: {cf_result['difference']}")
    assert result["status"] == "success"
    assert result["result"]["causal_edges"] == 3
    print("All tests passed!")
