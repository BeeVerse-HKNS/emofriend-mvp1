from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .base_engine import BaseInventionEngine
from .base_invention_engine import ConfidenceLevel, InventionResult

logger = structlog.get_logger()


@dataclass
class EmergentCause:
    cause_id: str
    description: str
    irreducibility_score: float
    contributing_factors: list[str]


@dataclass
class CausalEstimate:
    effect: float
    confidence: float
    method: str
    assumptions: list[str]


@dataclass
class _Node:
    name: str
    type: str


@dataclass
class _Edge:
    source: str
    target: str
    base_weight: float
    context_fn: Optional[Callable[[dict], float]]


class CyclicCausalGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, _Node] = {}
        self._edges: list[_Edge] = []
        self._adj: dict[str, list[_Edge]] = {}
        self._radj: dict[str, list[_Edge]] = {}

    def add_node(self, name: str, type: str) -> None:
        self._nodes[name] = _Node(name=name, type=type)
        if name not in self._adj:
            self._adj[name] = []
        if name not in self._radj:
            self._radj[name] = []

    def add_edge(
        self,
        source: str,
        target: str,
        weight: float,
        context_fn: Optional[Callable[[dict], float]] = None,
    ) -> None:
        edge = _Edge(source=source, target=target, base_weight=weight, context_fn=context_fn)
        self._edges.append(edge)
        self._adj.setdefault(source, []).append(edge)
        self._radj.setdefault(target, []).append(edge)

    def get_cycles(self) -> list[list[str]]:
        visited: set[str] = set()
        stack: list[str] = []
        stack_set: set[str] = set()
        cycles: list[list[str]] = []

        def _dfs(node: str) -> None:
            visited.add(node)
            stack.append(node)
            stack_set.add(node)
            for edge in self._adj.get(node, []):
                if edge.target in stack_set:
                    idx = stack.index(edge.target)
                    cycles.append(list(stack[idx:]) + [edge.target])
                elif edge.target not in visited:
                    _dfs(edge.target)
            stack.pop()
            stack_set.discard(node)

        for n in self._nodes:
            if n not in visited:
                _dfs(n)
        return cycles

    def get_ancestors(self, node: str) -> list[str]:
        ancestors: list[str] = []
        visited: set[str] = set()

        def _walk(n: str) -> None:
            for edge in self._radj.get(n, []):
                if edge.source not in visited:
                    visited.add(edge.source)
                    ancestors.append(edge.source)
                    _walk(edge.source)

        _walk(node)
        return ancestors

    def get_descendants(self, node: str) -> list[str]:
        descendants: list[str] = []
        visited: set[str] = set()

        def _walk(n: str) -> None:
            for edge in self._adj.get(n, []):
                if edge.target not in visited:
                    visited.add(edge.target)
                    descendants.append(edge.target)
                    _walk(edge.target)

        _walk(node)
        return descendants

    @property
    def nodes(self) -> dict[str, _Node]:
        return self._nodes

    @property
    def edges(self) -> list[_Edge]:
        return self._edges


class ContextDependentWeights:
    def __init__(self) -> None:
        self._context: dict[str, Any] = {}

    def compute_weight(self, edge: _Edge, context: dict[str, Any]) -> float:
        merged = {**self._context, **context}
        if edge.context_fn is not None:
            try:
                modifier = edge.context_fn(merged)
            except Exception:
                modifier = 1.0
            return edge.base_weight * modifier
        return edge.base_weight

    def update_context(self, new_context: dict[str, Any]) -> None:
        self._context.update(new_context)


class EmergentCauseDetector:
    def __init__(self, threshold: float = 0.3) -> None:
        self._threshold = threshold

    def detect(
        self,
        graph: CyclicCausalGraph,
        node: str,
        context: dict[str, Any],
    ) -> list[EmergentCause]:
        ancestors = graph.get_ancestors(node)
        if not ancestors:
            return []

        weight_engine = ContextDependentWeights()
        weight_engine.update_context(context)

        individual_effects: dict[str, float] = {}
        for anc in ancestors:
            total = 0.0
            for edge in graph._radj.get(node, []):
                if edge.source == anc:
                    total += weight_engine.compute_weight(edge, context)
            for edge in graph._adj.get(anc, []):
                if edge.target != node:
                    for inner in graph._radj.get(node, []):
                        if inner.source == edge.target:
                            total += weight_engine.compute_weight(inner, context) * 0.5
            individual_effects[anc] = total

        sum_individual = sum(individual_effects.values())

        total_combined = 0.0
        for edge in graph._radj.get(node, []):
            total_combined += weight_engine.compute_weight(edge, context)

        cycles = graph.get_cycles()
        cycle_boost = 0.0
        for cycle in cycles:
            if node in cycle:
                cycle_boost += 0.1 * len(cycle)

        observed_effect = total_combined + cycle_boost
        irreducibility = abs(observed_effect - sum_individual) / max(abs(observed_effect), 1e-9)

        results: list[EmergentCause] = []
        if irreducibility > self._threshold:
            results.append(
                EmergentCause(
                    cause_id=f"emergent_{node}",
                    description=f"Emergent causal effect at {node} exceeding sum of individual causes",
                    irreducibility_score=round(irreducibility, 4),
                    contributing_factors=ancestors,
                )
            )

        for cycle in cycles:
            if node in cycle and len(cycle) > 2:
                cycle_id = "_".join(cycle[:-1])
                cycle_irreducibility = 0.5 + 0.1 * len(cycle)
                if cycle_irreducibility > self._threshold:
                    results.append(
                        EmergentCause(
                            cause_id=f"cyclic_{cycle_id}",
                            description=f"Cyclic feedback loop: {' → '.join(cycle)}",
                            irreducibility_score=round(min(cycle_irreducibility, 1.0), 4),
                            contributing_factors=cycle[:-1],
                        )
                    )

        return results


class CyclicDoCalculus:
    def do_intervention(
        self,
        graph: CyclicCausalGraph,
        node: str,
        value: float,
    ) -> CyclicCausalGraph:
        new_graph = CyclicCausalGraph()
        for n, nd in graph.nodes.items():
            new_graph.add_node(n, nd.type)
        for edge in graph.edges:
            if edge.target == node:
                continue
            new_graph.add_edge(
                edge.source,
                edge.target,
                edge.base_weight,
                edge.context_fn,
            )
        new_graph.add_node(node, graph.nodes[node].type)
        return new_graph

    def estimate_effect(
        self,
        graph: CyclicCausalGraph,
        treatment: str,
        outcome: str,
        context: dict[str, Any],
    ) -> CausalEstimate:
        intervened = self.do_intervention(graph, treatment, 1.0)

        weight_engine = ContextDependentWeights()
        weight_engine.update_context(context)

        descendants = intervened.get_descendants(treatment)
        if outcome not in descendants and outcome != treatment:
            return CausalEstimate(
                effect=0.0,
                confidence=0.0,
                method="cyclic_do_calculus",
                assumptions=["no_causal_path"],
            )

        path_weight = 0.0
        visited: set[str] = set()
        queue: list[tuple[str, float]] = [(treatment, 1.0)]
        while queue:
            current, accumulated = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current == outcome and current != treatment:
                path_weight += accumulated
                continue
            for edge in intervened._adj.get(current, []):
                w = weight_engine.compute_weight(edge, context)
                queue.append((edge.target, accumulated * w))

        cycles = graph.get_cycles()
        cycle_factor = 1.0
        for cycle in cycles:
            if treatment in cycle and outcome in cycle:
                cycle_factor *= 1.1

        effect = path_weight * cycle_factor

        confidence = min(0.95, 0.5 + 0.1 * len(descendants))
        if cycles:
            confidence *= 0.9

        assumptions = [
            "cyclic_graph_structure",
            "context_dependent_weights",
            "feedback_loops_accounted",
        ]
        if cycles:
            assumptions.append("cycle_convergence_assumed")

        return CausalEstimate(
            effect=round(effect, 6),
            confidence=round(confidence, 4),
            method="cyclic_do_calculus",
            assumptions=assumptions,
        )


class PratityaCausalReasoning(BaseInventionEngine):
    name = "PratityaCausalReasoning"
    invention_id = "EWF-005"
    operator = "(R * K) ^ C - L"
    formula = "(R * K) ^ C - L → cyclic_causal_graph → context_dependent_weights → emergent_causes"
    category = "EWF"
    description = "Causal reasoning with cyclic dependencies and context-dependent weights, inspired by Buddhist dependent origination"

    def __init__(self) -> None:
        self._graph = CyclicCausalGraph()
        self._weight_engine = ContextDependentWeights()
        self._emergence_detector = EmergentCauseDetector()
        self._do_calculus = CyclicDoCalculus()

    def execute(self, context: dict[str, Any]) -> InventionResult:
        try:
            graph = self._build_graph(context)
            causal_context = context.get("causal_context", {})

            self._weight_engine.update_context(causal_context)

            edge_weights: list[dict[str, Any]] = []
            for edge in graph.edges:
                w = self._weight_engine.compute_weight(edge, causal_context)
                edge_weights.append({
                    "source": edge.source,
                    "target": edge.target,
                    "weight": round(w, 4),
                })

            cycles = graph.get_cycles()

            emergent_causes: list[EmergentCause] = []
            target_nodes = context.get("target_nodes", list(graph.nodes.keys()))
            for node in target_nodes:
                if node in graph.nodes:
                    detected = self._emergence_detector.detect(graph, node, causal_context)
                    emergent_causes.extend(detected)

            causal_estimates: dict[str, CausalEstimate] = {}
            interventions = context.get("interventions", [])
            for iv in interventions:
                treatment = iv.get("treatment", "")
                outcome = iv.get("outcome", "")
                if treatment and outcome and treatment in graph.nodes and outcome in graph.nodes:
                    estimate = self._do_calculus.estimate_effect(
                        graph, treatment, outcome, causal_context,
                    )
                    causal_estimates[f"{treatment}->{outcome}"] = estimate

            output = {
                "nodes": {n: {"type": nd.type} for n, nd in graph.nodes.items()},
                "edge_weights": edge_weights,
                "cycles": cycles,
                "emergent_causes": [
                    {
                        "cause_id": ec.cause_id,
                        "description": ec.description,
                        "irreducibility_score": ec.irreducibility_score,
                        "contributing_factors": ec.contributing_factors,
                    }
                    for ec in emergent_causes
                ],
                "causal_estimates": {
                    k: {
                        "effect": v.effect,
                        "confidence": v.confidence,
                        "method": v.method,
                        "assumptions": v.assumptions,
                    }
                    for k, v in causal_estimates.items()
                },
                "total_nodes": len(graph.nodes),
                "total_edges": len(graph.edges),
                "total_cycles": len(cycles),
                "total_emergent": len(emergent_causes),
            }

            if emergent_causes:
                max_irr = max(ec.irreducibility_score for ec in emergent_causes)
                if max_irr > 0.7:
                    confidence = ConfidenceLevel.VERIFIED
                elif max_irr > 0.5:
                    confidence = ConfidenceLevel.RESEARCHED
                else:
                    confidence = ConfidenceLevel.INFERRED
            elif cycles:
                confidence = ConfidenceLevel.RESEARCHED
            else:
                confidence = ConfidenceLevel.INFERRED

            logger.info(
                "pratitya_causal_analysis_complete",
                invention_id=self.invention_id,
                nodes=len(graph.nodes),
                cycles=len(cycles),
                emergent=len(emergent_causes),
            )

            return InventionResult(
                output=output,
                confidence=confidence,
                synergy_detected=self.get_synergy_partners(),
                invention_id=self.invention_id,
                metadata={"formula": self.formula, "operator": self.operator},
            )

        except Exception as exc:
            logger.error("pratitya_causal_failed", invention_id=self.invention_id, error=str(exc))
            return InventionResult(
                output={"status": "error", "error": str(exc)},
                confidence=ConfidenceLevel.UNCERTAIN,
                invention_id=self.invention_id,
            )

    def validate(self, result: InventionResult) -> bool:
        if not result.output:
            return False
        if result.confidence == ConfidenceLevel.UNCERTAIN:
            return False
        if "error" in result.output:
            return False
        nodes = result.output.get("nodes", {})
        if not nodes:
            return False
        estimates = result.output.get("causal_estimates", {})
        for key, est in estimates.items():
            if est.get("confidence", 0) < 0:
                return False
        return True

    def get_synergy_partners(self) -> list[str]:
        return ["EWF-003", "EWF-002", "SCI-003"]

    def _build_graph(self, context: dict[str, Any]) -> CyclicCausalGraph:
        graph = CyclicCausalGraph()

        causal_graph = context.get("causal_graph", None)
        if causal_graph is not None:
            nodes_data = causal_graph.get("nodes", [])
            edges_data = causal_graph.get("edges", [])
            for nd in nodes_data:
                graph.add_node(
                    nd.get("name", nd.get("id", "")),
                    nd.get("type", "variable"),
                )
            for ed in edges_data:
                context_fn = None
                if "context_fn" in ed and callable(ed["context_fn"]):
                    context_fn = ed["context_fn"]
                graph.add_edge(
                    ed.get("source", ""),
                    ed.get("target", ""),
                    ed.get("weight", 1.0),
                    context_fn,
                )
            return graph

        variables = context.get("variables", [])
        for var in variables:
            name = var.get("name", var.get("id", ""))
            var_type = var.get("type", "variable")
            graph.add_node(name, var_type)

        relations = context.get("relations", [])
        for rel in relations:
            graph.add_edge(
                rel.get("source", ""),
                rel.get("target", ""),
                rel.get("weight", 1.0),
            )

        return graph
