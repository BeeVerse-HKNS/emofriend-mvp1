from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from harnessing.core.formula_operator_architecture import INVENTORY_FACTORS
from harnessing.core.thinking_flow_architecture import LAYER_FACTOR_MAP


@dataclass
class ActionNode:
    id: str
    name: str
    description: str
    status: str = "PENDING"
    dependencies: list[str] = field(default_factory=list)
    affects: list[str] = field(default_factory=list)
    result: Optional[str] = None
    confidence: float = 0.0
    last_modified: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    modification_count: int = 0
    metadata: dict = field(default_factory=dict)
    thinking_layer: Optional[int] = None
    capability_factors: list[str] = field(default_factory=list)
    _result_history: list[dict] = field(default_factory=list)

    def update_result(self, new_result: str, new_confidence: float) -> None:
        if self.result is not None:
            self._result_history.append({
                "result": self.result,
                "confidence": self.confidence,
                "timestamp": self.last_modified,
            })
        self.result = new_result
        self.confidence = max(0.0, min(1.0, new_confidence))
        self.last_modified = datetime.now(timezone.utc).isoformat()
        self.modification_count += 1
        if self.status == "COMPLETED":
            self.status = "NEEDS_REEVALUATION"


@dataclass
class DependencyEdge:
    source: str
    target: str
    edge_type: str = "DEPENDS_ON"
    strength: float = 1.0
    description: str = ""


@dataclass
class RippleEffect:
    origin_action: str
    affected_actions: list[str] = field(default_factory=list)
    propagation_path: list[str] = field(default_factory=list)
    depth: int = 0
    requires_reevaluation: bool = False


@dataclass
class FeedbackLoop:
    nodes: list[str]
    loop_type: str = "REINFORCING"
    strength: float = 0.0
    description: str = ""


@dataclass
class ConvergenceResult:
    is_converged: bool = False
    total_actions: int = 0
    stable_actions: int = 0
    unstable_actions: int = 0
    pending_actions: int = 0
    max_modification_count: int = 0
    feedback_loops: int = 0


@dataclass
class CircularAnalysisResult:
    total_actions: int = 0
    total_dependencies: int = 0
    feedback_loops: list[FeedbackLoop] = field(default_factory=list)
    ripple_effects: list[RippleEffect] = field(default_factory=list)
    convergence: ConvergenceResult = field(default_factory=ConvergenceResult)
    inter_dependency_map: dict[str, list[str]] = field(default_factory=dict)
    critical_actions: list[str] = field(default_factory=list)
    isolated_actions: list[str] = field(default_factory=list)


_WHITE = 0
_GRAY = 1
_BLACK = 2
_MAX_RIPPLE_DEPTH = 10


class CircularThinkingEngine:
    def __init__(self) -> None:
        self._actions: dict[str, ActionNode] = {}
        self._edges: dict[str, list[DependencyEdge]] = {}
        self._reverse_edges: dict[str, list[DependencyEdge]] = {}
        self._feedback_loops_cache: list[FeedbackLoop] | None = None

    def add_action(self, action: ActionNode) -> None:
        self._actions[action.id] = action
        if action.id not in self._edges:
            self._edges[action.id] = []
        if action.id not in self._reverse_edges:
            self._reverse_edges[action.id] = []
        self._invalidate_cache()

    def add_dependency(
        self,
        source: str,
        target: str,
        edge_type: str = "DEPENDS_ON",
        strength: float = 1.0,
        description: str = "",
    ) -> None:
        if source == target:
            return
        if source not in self._actions or target not in self._actions:
            return

        edge = DependencyEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            strength=strength,
            description=description,
        )
        self._edges.setdefault(source, []).append(edge)

        reverse_edge = DependencyEdge(
            source=target,
            target=source,
            edge_type="AFFECTS",
            strength=strength,
            description=f"Reverse of: {description}" if description else "",
        )
        self._reverse_edges.setdefault(target, []).append(reverse_edge)

        if source not in self._actions[target].dependencies:
            self._actions[target].dependencies.append(source)
        if target not in self._actions[source].affects:
            self._actions[source].affects.append(target)

        if edge_type == "BIDIRECTIONAL":
            rev_edge = DependencyEdge(
                source=target,
                target=source,
                edge_type="BIDIRECTIONAL",
                strength=strength,
                description=description,
            )
            self._edges.setdefault(target, []).append(rev_edge)

            fwd_edge = DependencyEdge(
                source=source,
                target=target,
                edge_type="AFFECTS",
                strength=strength,
                description=f"Reverse of: {description}" if description else "",
            )
            self._reverse_edges.setdefault(source, []).append(fwd_edge)

            if target not in self._actions[source].dependencies:
                self._actions[source].dependencies.append(target)
            if source not in self._actions[target].affects:
                self._actions[target].affects.append(source)

        self._invalidate_cache()

    def remove_action(self, action_id: str) -> None:
        if action_id not in self._actions:
            return

        for edge in list(self._edges.get(action_id, [])):
            target_id = edge.target
            if target_id in self._actions:
                if action_id in self._actions[target_id].dependencies:
                    self._actions[target_id].dependencies.remove(action_id)

        for edge in list(self._reverse_edges.get(action_id, [])):
            source_id = edge.source
            if source_id in self._actions:
                if action_id in self._actions[source_id].affects:
                    self._actions[source_id].affects.remove(action_id)

        for aid in list(self._edges.keys()):
            self._edges[aid] = [e for e in self._edges[aid] if e.target != action_id and e.source != action_id]
        for aid in list(self._reverse_edges.keys()):
            self._reverse_edges[aid] = [e for e in self._reverse_edges[aid] if e.source != action_id and e.target != action_id]

        self._edges.pop(action_id, None)
        self._reverse_edges.pop(action_id, None)
        del self._actions[action_id]
        self._invalidate_cache()

    def get_action(self, action_id: str) -> Optional[ActionNode]:
        return self._actions.get(action_id)

    def get_all_actions(self) -> list[ActionNode]:
        return list(self._actions.values())

    def get_dependencies(self, action_id: str) -> list[DependencyEdge]:
        return list(self._reverse_edges.get(action_id, []))

    def get_affected(self, action_id: str) -> list[DependencyEdge]:
        return list(self._edges.get(action_id, []))

    def detect_feedback_loops(self) -> list[FeedbackLoop]:
        if self._feedback_loops_cache is not None:
            return self._feedback_loops_cache

        loops: list[FeedbackLoop] = []
        color: dict[str, int] = {aid: _WHITE for aid in self._actions}
        path: list[str] = []
        visited_loops: set[frozenset[str]] = set()

        def _dfs(node_id: str) -> None:
            color[node_id] = _GRAY
            path.append(node_id)

            for edge in self._edges.get(node_id, []):
                neighbor = edge.target
                if neighbor not in self._actions:
                    continue

                if color[neighbor] == _GRAY:
                    cycle_start = path.index(neighbor)
                    cycle_nodes = path[cycle_start:]
                    cycle_key = frozenset(cycle_nodes)

                    if cycle_key not in visited_loops:
                        visited_loops.add(cycle_key)

                        cycle_edges: list[DependencyEdge] = []
                        for i in range(len(cycle_nodes)):
                            src = cycle_nodes[i]
                            tgt = cycle_nodes[(i + 1) % len(cycle_nodes)]
                            for e in self._edges.get(src, []):
                                if e.target == tgt:
                                    cycle_edges.append(e)
                                    break

                        all_positive = all(e.strength >= 0 for e in cycle_edges)
                        loop_type = "REINFORCING" if all_positive else "BALANCING"
                        avg_strength = (
                            sum(e.strength for e in cycle_edges) / len(cycle_edges)
                            if cycle_edges
                            else 0.0
                        )

                        loops.append(
                            FeedbackLoop(
                                nodes=list(cycle_nodes),
                                loop_type=loop_type,
                                strength=avg_strength,
                                description=f"{'Reinforcing' if loop_type == 'REINFORCING' else 'Balancing'} loop: {' → '.join(cycle_nodes)} → {cycle_nodes[0]}",
                            )
                        )
                elif color[neighbor] == _WHITE:
                    _dfs(neighbor)

            path.pop()
            color[node_id] = _BLACK

        for aid in self._actions:
            if color[aid] == _WHITE:
                _dfs(aid)

        self._feedback_loops_cache = loops
        return loops

    def propagate_ripple(self, origin_id: str, change_description: str = "") -> list[RippleEffect]:
        if origin_id not in self._actions:
            return []

        effects: list[RippleEffect] = []
        visited: set[str] = {origin_id}
        queue: deque[tuple[str, int, list[str]]] = deque()
        queue.append((origin_id, 0, [origin_id]))

        while queue:
            current_id, depth, path = queue.popleft()
            if depth >= _MAX_RIPPLE_DEPTH:
                continue

            affected_edges = self._edges.get(current_id, [])
            for edge in affected_edges:
                target_id = edge.target
                if target_id not in self._actions:
                    continue
                if target_id in visited and depth > 0:
                    continue

                requires_reeval = (
                    edge.strength >= 0.5
                    and self._actions[target_id].status in ("COMPLETED", "IN_PROGRESS")
                )

                new_path = path + [target_id]
                effects.append(
                    RippleEffect(
                        origin_action=origin_id,
                        affected_actions=[target_id],
                        propagation_path=new_path,
                        depth=depth + 1,
                        requires_reevaluation=requires_reeval,
                    )
                )

                if requires_reeval:
                    self._actions[target_id].status = "NEEDS_REEVALUATION"
                    self._actions[target_id].last_modified = datetime.now(timezone.utc).isoformat()

                visited.add(target_id)
                queue.append((target_id, depth + 1, new_path))

        self._invalidate_cache()
        return effects

    def reevaluate_action(
        self, action_id: str, new_info: str
    ) -> tuple[Optional[ActionNode], list[RippleEffect]]:
        action = self._actions.get(action_id)
        if action is None:
            return None, []

        old_result = action.result
        old_confidence = action.confidence

        action.update_result(
            new_result=f"{old_result or ''} | Updated: {new_info}" if old_result else new_info,
            new_confidence=min(1.0, old_confidence + 0.1),
        )
        action.status = "IN_PROGRESS"

        ripples = self.propagate_ripple(action_id, new_info)

        return action, ripples

    def check_convergence(self) -> ConvergenceResult:
        if not self._actions:
            return ConvergenceResult(is_converged=True)

        stable = sum(1 for a in self._actions.values() if a.status == "COMPLETED")
        unstable = sum(1 for a in self._actions.values() if a.status == "NEEDS_REEVALUATION")
        pending = sum(1 for a in self._actions.values() if a.status == "PENDING")
        max_mod = max((a.modification_count for a in self._actions.values()), default=0)
        loops = self.detect_feedback_loops()

        return ConvergenceResult(
            is_converged=unstable == 0 and pending == 0,
            total_actions=len(self._actions),
            stable_actions=stable,
            unstable_actions=unstable,
            pending_actions=pending,
            max_modification_count=max_mod,
            feedback_loops=len(loops),
        )

    def history_recap(self) -> str:
        if not self._actions:
            return "No actions recorded."

        lines: list[str] = ["=== Circular Thinking History Recap ===", ""]

        sorted_actions = sorted(
            self._actions.values(), key=lambda a: a.last_modified
        )

        for action in sorted_actions:
            lines.append(f"[{action.id}] {action.name}")
            lines.append(f"  Status: {action.status}")
            lines.append(f"  Current Result: {action.result or 'N/A'}")
            lines.append(f"  Confidence: {action.confidence:.2f}")
            lines.append(f"  Modifications: {action.modification_count}")

            if action._result_history:
                lines.append(f"  History ({len(action._result_history)} changes):")
                for i, h in enumerate(action._result_history, 1):
                    result_preview = h["result"][:80] + "..." if len(h.get("result", "") or "") > 80 else (h.get("result") or "N/A")
                    lines.append(f"    {i}. [{h.get('timestamp', 'N/A')[:19]}] conf={h.get('confidence', 0):.2f} → {result_preview}")

            if action.dependencies:
                lines.append(f"  Depends on: {', '.join(action.dependencies)}")
            if action.affects:
                lines.append(f"  Affects: {', '.join(action.affects)}")
            lines.append("")

        loops = self.detect_feedback_loops()
        if loops:
            lines.append(f"Feedback Loops ({len(loops)}):")
            for loop in loops:
                lines.append(f"  {loop.loop_type}: {' → '.join(loop.nodes)} → {loop.nodes[0]} (strength={loop.strength:.2f})")
            lines.append("")

        convergence = self.check_convergence()
        lines.append(f"Convergence: {'YES' if convergence.is_converged else 'NO'} | Stable: {convergence.stable_actions} | Unstable: {convergence.unstable_actions} | Pending: {convergence.pending_actions}")

        return "\n".join(lines)

    def circular_analysis(self) -> CircularAnalysisResult:
        if not self._actions:
            return CircularAnalysisResult()

        total_deps = sum(len(edges) for edges in self._edges.values())
        loops = self.detect_feedback_loops()
        convergence = self.check_convergence()

        inter_dep_map: dict[str, list[str]] = {}
        for aid, action in self._actions.items():
            related = list(set(action.dependencies + action.affects))
            inter_dep_map[aid] = related

        centrality: dict[str, int] = {}
        for aid in self._actions:
            centrality[aid] = len(self._actions[aid].dependencies) + len(self._actions[aid].affects)

        max_centrality = max(centrality.values()) if centrality else 0
        critical = [aid for aid, c in centrality.items() if c == max_centrality and max_centrality > 0]

        isolated = [aid for aid in self._actions if not self._actions[aid].dependencies and not self._actions[aid].affects]

        all_ripples: list[RippleEffect] = []
        for aid in list(self._actions.keys()):
            ripples = self.propagate_ripple(aid)
            all_ripples.extend(ripples)

        return CircularAnalysisResult(
            total_actions=len(self._actions),
            total_dependencies=total_deps,
            feedback_loops=loops,
            ripple_effects=all_ripples,
            convergence=convergence,
            inter_dependency_map=inter_dep_map,
            critical_actions=critical,
            isolated_actions=isolated,
        )

    def visualize_graph(self) -> str:
        if not self._actions:
            return "Empty graph — no actions."

        lines: list[str] = ["=== Circular Dependency Graph ===", ""]

        loops = self.detect_feedback_loops()
        loop_node_set: set[str] = set()
        for loop in loops:
            loop_node_set.update(loop.nodes)

        for aid, action in sorted(self._actions.items()):
            in_loop = " [LOOP]" if aid in loop_node_set else ""
            status_icon = {
                "PENDING": "○",
                "IN_PROGRESS": "◐",
                "COMPLETED": "●",
                "NEEDS_REEVALUATION": "↻",
            }.get(action.status, "?")

            lines.append(f"{status_icon} {aid}: {action.name}{in_loop}")

            for edge in self._edges.get(aid, []):
                edge_icon = {
                    "DEPENDS_ON": "──depends──▶",
                    "AFFECTS": "──affects──▶",
                    "FEEDBACK_LOOP": "──feedback──▶",
                    "BIDIRECTIONAL": "◀──bidir──▶",
                }.get(edge.edge_type, "──▶")

                lines.append(f"  {edge_icon} {edge.target} (strength={edge.strength:.2f})")

        if loops:
            lines.append("")
            lines.append("Feedback Loops:")
            for loop in loops:
                icon = "⟳" if loop.loop_type == "REINFORCING" else "⟲"
                lines.append(f"  {icon} {loop.loop_type}: {' → '.join(loop.nodes)} → {loop.nodes[0]}")

        return "\n".join(lines)

    def get_action_timeline(self) -> list[tuple[str, str, str]]:
        sorted_actions = sorted(
            self._actions.values(), key=lambda a: a.last_modified
        )
        return [(a.last_modified, a.id, a.status) for a in sorted_actions]

    def get_layer_actions(self, layer: int) -> list[ActionNode]:
        if layer < 1 or layer > 8:
            return []
        return [a for a in self._actions.values() if a.thinking_layer == layer]

    def get_factor_actions(self, factor: str) -> list[ActionNode]:
        if factor not in INVENTORY_FACTORS:
            return []
        return [a for a in self._actions.values() if factor in a.capability_factors]

    def _invalidate_cache(self) -> None:
        self._feedback_loops_cache = None
