"""EmoGlyph Flow Graph (EFG) — Situation-Driven Dynamic Graph Engine.

Goes beyond linear agent1→agent2→agent3 chains by selecting and composing
execution patterns based on the *situation* (urgency, complexity, domain,
quality requirements, stakeholder count).

5-layer process (Pulse → Current → Construct → Enactive → Resonance):
  1. Pulse:     Analyze the situation dict.
  2. Current:   Select the best FlowPattern(s).
  3. Construct: Assemble a FlowGraph via FlowAssembler.
  4. Enactive:  Execute the graph via FlowExecutor.
  5. Resonance: Evaluate results via FlowEvaluator and feed back.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from harnessing.core.parallelism_governor import Governor
from harnessing.core.sub_agent_pipeline import Pipeline, Task, TaskStatus
from harnessing.core.sub_agent_quorum import Quorum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FlowPattern
# ---------------------------------------------------------------------------

class FlowPattern(Enum):
    """Eight agent coordination patterns, ordered roughly by complexity."""

    SOLO = "solo"
    PIPELINE = "pipeline"
    PARALLEL_FANOUT = "parallel_fanout"
    QUORUM_VOTE = "quorum_vote"
    SUPERVISOR_WORKER = "supervisor_worker"
    ITERATIVE_REFINE = "iterative_refine"
    EVENT_DRIVEN = "event_driven"
    HYBRID = "hybrid"


# ---------------------------------------------------------------------------
# FlowNode / FlowEdge
# ---------------------------------------------------------------------------

@dataclass
class FlowNode:
    """A single agent/task vertex in the flow graph."""

    id: str
    name: str
    pattern: FlowPattern
    callable_fn: Optional[Callable] = None
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pattern": self.pattern.value,
            "config": self.config,
            "metadata": self.metadata,
        }


@dataclass
class FlowEdge:
    """A directed connection between two FlowNodes."""

    source_id: str
    target_id: str
    edge_type: str = "data"  # "data", "control", "feedback"
    condition: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type,
            "has_condition": self.condition is not None,
        }


# ---------------------------------------------------------------------------
# FlowGraph
# ---------------------------------------------------------------------------

class FlowGraph:
    """Dynamic execution graph composed of FlowNodes and FlowEdges."""

    def __init__(self) -> None:
        self.nodes: Dict[str, FlowNode] = {}
        self.edges: List[FlowEdge] = []

    # -- mutation -----------------------------------------------------------

    def add_node(self, node: FlowNode) -> None:
        if node.id in self.nodes:
            raise ValueError(f"node_already_exists id={node.id}")
        self.nodes[node.id] = node
        logger.debug(f"flow_graph_node_added id={node.id} pattern={node.pattern.value}")

    def add_edge(self, edge: FlowEdge) -> None:
        if edge.source_id not in self.nodes:
            raise ValueError(f"edge_source_missing source_id={edge.source_id}")
        if edge.target_id not in self.nodes:
            raise ValueError(f"edge_target_missing target_id={edge.target_id}")
        if edge.source_id == edge.target_id:
            raise ValueError(f"self_loop_not_allowed id={edge.source_id}")
        self.edges.append(edge)
        logger.debug(
            f"flow_graph_edge_added {edge.source_id}→{edge.target_id} type={edge.edge_type}"
        )

    def remove_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            raise KeyError(f"node_not_found id={node_id}")
        del self.nodes[node_id]
        self.edges = [
            e for e in self.edges if e.source_id != node_id and e.target_id != node_id
        ]
        logger.debug(f"flow_graph_node_removed id={node_id}")

    # -- analysis -----------------------------------------------------------

    def _adjacency(self) -> Dict[str, List[str]]:
        adj: Dict[str, List[str]] = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            adj[edge.source_id].append(edge.target_id)
        return adj

    def validate(self) -> List[str]:
        """Return a list of validation issues (empty means valid)."""
        issues: List[str] = []

        # Cycle detection via DFS
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {nid: WHITE for nid in self.nodes}
        stack: List[str] = []

        def _dfs(node: str) -> None:
            color[node] = GRAY
            stack.append(node)
            for neighbor in self._adjacency().get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    cycle = stack[stack.index(neighbor):] + [neighbor]
                    issues.append(f"cycle_detected path={cycle}")
                elif color[neighbor] == WHITE:
                    _dfs(neighbor)
            stack.pop()
            color[node] = BLACK

        for nid in self.nodes:
            if color[nid] == WHITE:
                _dfs(nid)

        # Missing dependency check — edges referencing absent nodes
        for edge in self.edges:
            if edge.source_id not in self.nodes:
                issues.append(f"edge_source_missing source={edge.source_id}")
            if edge.target_id not in self.nodes:
                issues.append(f"edge_target_missing target={edge.target_id}")

        # Orphan nodes (no incoming or outgoing edges)
        connected: Set[str] = set()
        for edge in self.edges:
            connected.add(edge.source_id)
            connected.add(edge.target_id)
        orphans = set(self.nodes.keys()) - connected
        if len(self.nodes) > 1 and orphans:
            issues.append(f"orphan_nodes ids={sorted(orphans)}")

        return issues

    def topological_order(self) -> List[str]:
        """Return execution order; raises ValueError if cycles exist."""
        issues = self.validate()
        cycle_issues = [i for i in issues if "cycle_detected" in i]
        if cycle_issues:
            raise ValueError(cycle_issues[0])

        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        children: Dict[str, List[str]] = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            in_degree[edge.target_id] += 1
            children[edge.source_id].append(edge.target_id)

        queue = sorted([nid for nid, deg in in_degree.items() if deg == 0])
        order: List[str] = []
        while queue:
            current = queue.pop(0)
            order.append(current)
            for child in sorted(children[current]):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(order) != len(self.nodes):
            remaining = set(self.nodes.keys()) - set(order)
            raise ValueError(f"topological_sort_incomplete remaining={remaining}")
        return order

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlowGraph":
        graph = cls()
        for nid, ndata in data.get("nodes", {}).items():
            graph.add_node(
                FlowNode(
                    id=nid,
                    name=ndata.get("name", nid),
                    pattern=FlowPattern(ndata.get("pattern", "solo")),
                    config=ndata.get("config", {}),
                    metadata=ndata.get("metadata", {}),
                )
            )
        for edata in data.get("edges", []):
            graph.add_edge(
                FlowEdge(
                    source_id=edata["source_id"],
                    target_id=edata["target_id"],
                    edge_type=edata.get("edge_type", "data"),
                )
            )
        return graph


# ---------------------------------------------------------------------------
# FlowAssembler
# ---------------------------------------------------------------------------

class FlowAssembler:
    """Assembles a FlowGraph based on a situation descriptor.

    Situation dict keys:
      urgency          — "low" | "medium" | "high"
      complexity       — "low" | "medium" | "high"
      domain           — str  (e.g. "creative", "content", "realtime", "monitoring")
      quality_required — bool
      stakeholders     — int
    """

    CREATIVE_DOMAINS = {"creative", "content"}
    REALTIME_DOMAINS = {"realtime", "monitoring"}

    def assemble(self, situation: Dict[str, Any]) -> FlowGraph:
        """Analyse the situation and return a fully-wired FlowGraph."""
        patterns = self._select_patterns(situation)
        logger.info(f"flow_assembler_selected patterns={[p.value for p in patterns]}")

        if FlowPattern.HYBRID in patterns:
            return self._build_hybrid(situation, patterns)
        if len(patterns) == 1:
            return self._build_single(situation, patterns[0])
        # Multiple non-hybrid patterns → still use HYBRID wrapper
        return self._build_hybrid(situation, patterns)

    # -- pattern selection --------------------------------------------------

    def _select_patterns(self, s: Dict[str, Any]) -> List[FlowPattern]:
        urgency = s.get("urgency", "medium")
        complexity = s.get("complexity", "medium")
        domain = str(s.get("domain", "")).lower()
        quality = bool(s.get("quality_required", False))
        stakeholders = int(s.get("stakeholders", 1))

        matched: List[FlowPattern] = []

        # Rule 1: low urgency + low complexity → SOLO
        if urgency == "low" and complexity == "low":
            matched.append(FlowPattern.SOLO)

        # Rule 2: medium urgency + medium complexity → PIPELINE
        if urgency == "medium" and complexity == "medium":
            matched.append(FlowPattern.PIPELINE)

        # Rule 3: low urgency + high complexity + independent sub-tasks → PARALLEL_FANOUT
        if urgency == "low" and complexity == "high":
            matched.append(FlowPattern.PARALLEL_FANOUT)

        # Rule 4: quality_required + multiple stakeholders → QUORUM_VOTE
        if quality and stakeholders > 1:
            matched.append(FlowPattern.QUORUM_VOTE)

        # Rule 5: quality_required + high complexity → SUPERVISOR_WORKER
        if quality and complexity == "high":
            matched.append(FlowPattern.SUPERVISOR_WORKER)

        # Rule 6: creative / content domain → ITERATIVE_REFINE
        if domain in self.CREATIVE_DOMAINS:
            matched.append(FlowPattern.ITERATIVE_REFINE)

        # Rule 7: realtime / monitoring domain → EVENT_DRIVEN
        if domain in self.REALTIME_DOMAINS:
            matched.append(FlowPattern.EVENT_DRIVEN)

        # Deduplicate while preserving order
        seen: Set[FlowPattern] = set()
        unique: List[FlowPattern] = []
        for p in matched:
            if p not in seen:
                seen.add(p)
                unique.append(p)

        # Multiple conditions met → HYBRID
        if len(unique) > 1:
            if FlowPattern.HYBRID not in seen:
                unique.append(FlowPattern.HYBRID)

        # Fallback: if nothing matched, default to PIPELINE
        if not unique:
            unique.append(FlowPattern.PIPELINE)

        return unique

    # -- graph builders -----------------------------------------------------

    def _build_single(self, situation: Dict[str, Any], pattern: FlowPattern) -> FlowGraph:
        graph = FlowGraph()
        domain = str(situation.get("domain", "general"))

        if pattern == FlowPattern.SOLO:
            node = FlowNode(
                id="solo_agent",
                name="Solo Agent",
                pattern=FlowPattern.SOLO,
                config={"domain": domain},
            )
            graph.add_node(node)

        elif pattern == FlowPattern.PIPELINE:
            steps = ["step_collect", "step_process", "step_deliver"]
            for idx, step_id in enumerate(steps):
                graph.add_node(FlowNode(
                    id=step_id,
                    name=f"Pipeline Step {idx + 1}",
                    pattern=FlowPattern.PIPELINE,
                    config={"step_index": idx, "domain": domain},
                ))
            for i in range(len(steps) - 1):
                graph.add_edge(FlowEdge(source_id=steps[i], target_id=steps[i + 1], edge_type="data"))

        elif pattern == FlowPattern.PARALLEL_FANOUT:
            graph.add_node(FlowNode(id="fanout_merge", name="Merge Agent", pattern=FlowPattern.PARALLEL_FANOUT))
            for i in range(3):
                wid = f"fanout_worker_{i}"
                graph.add_node(FlowNode(id=wid, name=f"Worker {i}", pattern=FlowPattern.PARALLEL_FANOUT))
                graph.add_edge(FlowEdge(source_id=wid, target_id="fanout_merge", edge_type="data"))

        elif pattern == FlowPattern.QUORUM_VOTE:
            graph.add_node(FlowNode(id="quorum_aggregator", name="Vote Aggregator", pattern=FlowPattern.QUORUM_VOTE))
            for i in range(3):
                vid = f"quorum_voter_{i}"
                graph.add_node(FlowNode(id=vid, name=f"Voter {i}", pattern=FlowPattern.QUORUM_VOTE))
                graph.add_edge(FlowEdge(source_id=vid, target_id="quorum_aggregator", edge_type="data"))

        elif pattern == FlowPattern.SUPERVISOR_WORKER:
            graph.add_node(FlowNode(id="supervisor", name="Supervisor", pattern=FlowPattern.SUPERVISOR_WORKER))
            for i in range(2):
                wid = f"worker_{i}"
                graph.add_node(FlowNode(id=wid, name=f"Worker {i}", pattern=FlowPattern.SUPERVISOR_WORKER))
                graph.add_edge(FlowEdge(source_id="supervisor", target_id=wid, edge_type="control"))
                graph.add_edge(FlowEdge(source_id=wid, target_id="supervisor", edge_type="feedback"))

        elif pattern == FlowPattern.ITERATIVE_REFINE:
            graph.add_node(FlowNode(id="refine_creator", name="Creator Agent", pattern=FlowPattern.ITERATIVE_REFINE))
            graph.add_node(FlowNode(id="refine_reviewer", name="Reviewer Agent", pattern=FlowPattern.ITERATIVE_REFINE))
            graph.add_edge(FlowEdge(source_id="refine_creator", target_id="refine_reviewer", edge_type="data"))
            graph.add_edge(FlowEdge(source_id="refine_reviewer", target_id="refine_creator", edge_type="feedback"))

        elif pattern == FlowPattern.EVENT_DRIVEN:
            graph.add_node(FlowNode(id="event_source", name="Event Source", pattern=FlowPattern.EVENT_DRIVEN))
            graph.add_node(FlowNode(id="event_handler", name="Event Handler", pattern=FlowPattern.EVENT_DRIVEN))
            graph.add_node(FlowNode(id="event_sink", name="Event Sink", pattern=FlowPattern.EVENT_DRIVEN))
            graph.add_edge(FlowEdge(source_id="event_source", target_id="event_handler", edge_type="control"))
            graph.add_edge(FlowEdge(source_id="event_handler", target_id="event_sink", edge_type="data"))

        return graph

    def _build_hybrid(self, situation: Dict[str, Any], patterns: List[FlowPattern]) -> FlowGraph:
        """Decompose into sub-graphs, each with its own pattern, linked by a coordinator."""
        graph = FlowGraph()
        graph.add_node(FlowNode(
            id="hybrid_coordinator",
            name="Hybrid Coordinator",
            pattern=FlowPattern.HYBRID,
            config={"sub_patterns": [p.value for p in patterns if p != FlowPattern.HYBRID]},
        ))

        sub_patterns = [p for p in patterns if p != FlowPattern.HYBRID]
        for idx, pat in enumerate(sub_patterns):
            sub_graph = self._build_single(situation, pat)
            # Prefix IDs to avoid collisions across sub-graphs
            prefix = f"sub{idx}_"
            for nid, node in sub_graph.nodes.items():
                prefixed_id = prefix + nid
                node.id = prefixed_id
                node.name = f"[{pat.value}] {node.name}"
                graph.nodes[prefixed_id] = node
            for edge in sub_graph.edges:
                graph.edges.append(FlowEdge(
                    source_id=prefix + edge.source_id,
                    target_id=prefix + edge.target_id,
                    edge_type=edge.edge_type,
                    condition=edge.condition,
                ))
            # Link first node of each sub-graph to coordinator
            first_node_id = prefix + list(sub_graph.nodes.keys())[0]
            graph.edges.append(FlowEdge(
                source_id="hybrid_coordinator",
                target_id=first_node_id,
                edge_type="control",
            ))

        return graph


# ---------------------------------------------------------------------------
# ExecutionStats / EvaluationReport
# ---------------------------------------------------------------------------

@dataclass
class ExecutionStats:
    """Statistics collected during graph execution."""

    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    skipped_nodes: int = 0
    total_duration_seconds: float = 0.0
    max_parallelism: int = 0
    pattern_breakdown: Dict[str, int] = field(default_factory=dict)
    history: deque = field(default_factory=lambda: deque(maxlen=200))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "skipped_nodes": self.skipped_nodes,
            "total_duration_seconds": round(self.total_duration_seconds, 4),
            "max_parallelism": self.max_parallelism,
            "pattern_breakdown": self.pattern_breakdown,
        }


@dataclass
class EvaluationReport:
    """Result of evaluating a flow-graph execution."""

    passed: bool
    completeness: float  # 0.0 – 1.0
    quality_score: float  # 0.0 – 1.0
    timeliness: float  # 0.0 – 1.0
    feedback: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "completeness": round(self.completeness, 4),
            "quality_score": round(self.quality_score, 4),
            "timeliness": round(self.timeliness, 4),
            "feedback": self.feedback,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# FlowExecutor
# ---------------------------------------------------------------------------

class FlowExecutor:
    """Executes a FlowGraph with monitoring, checkpointing, and parallelism."""

    def __init__(
        self,
        governor: Optional[Governor] = None,
        quorum: Optional[Quorum] = None,
        max_workers: Optional[int] = None,
    ) -> None:
        self._governor = governor or Governor(min_concurrent=1, max_concurrent=max_workers or 4)
        self._quorum = quorum or Quorum()
        self._max_workers = max_workers
        self._stats = ExecutionStats()
        logger.info(
            f"flow_executor_initialized max_workers={max_workers}"
        )

    def execute(self, graph: FlowGraph, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all nodes in the graph respecting dependencies and patterns.

        Returns a dict mapping node_id → result value.
        """
        start_time = time.time()
        self._stats = ExecutionStats(total_nodes=len(graph.nodes))

        # Pattern breakdown
        pattern_counts: Dict[str, int] = {}
        for node in graph.nodes.values():
            pattern_counts[node.pattern.value] = pattern_counts.get(node.pattern.value, 0) + 1
        self._stats.pattern_breakdown = pattern_counts

        # Group nodes by pattern for specialised execution
        solo_nodes = [n for n in graph.nodes.values() if n.pattern == FlowPattern.SOLO]
        pipeline_nodes = [n for n in graph.nodes.values() if n.pattern == FlowPattern.PIPELINE]
        fanout_nodes = [n for n in graph.nodes.values() if n.pattern == FlowPattern.PARALLEL_FANOUT]
        quorum_nodes = [n for n in graph.nodes.values() if n.pattern == FlowPattern.QUORUM_VOTE]
        supervisor_nodes = [n for n in graph.nodes.values() if n.pattern == FlowPattern.SUPERVISOR_WORKER]
        refine_nodes = [n for n in graph.nodes.values() if n.pattern == FlowPattern.ITERATIVE_REFINE]
        event_nodes = [n for n in graph.nodes.values() if n.pattern == FlowPattern.EVENT_DRIVEN]
        hybrid_nodes = [n for n in graph.nodes.values() if n.pattern == FlowPattern.HYBRID]

        results: Dict[str, Any] = {}
        completed_ids: Set[str] = set()
        failed_ids: Set[str] = set()

        # --- HYBRID coordinator first ---
        for node in hybrid_nodes:
            try:
                result = self._exec_node(node, context, results)
                results[node.id] = result
                completed_ids.add(node.id)
                self._stats.completed_nodes += 1
            except Exception as exc:
                logger.error(f"flow_executor_hybrid_failed id={node.id} error={exc}")
                results[node.id] = {"error": str(exc)}
                failed_ids.add(node.id)
                self._stats.failed_nodes += 1

        # --- SOLO ---
        for node in solo_nodes:
            try:
                result = self._exec_node(node, context, results)
                results[node.id] = result
                completed_ids.add(node.id)
                self._stats.completed_nodes += 1
            except Exception as exc:
                logger.error(f"flow_executor_solo_failed id={node.id} error={exc}")
                results[node.id] = {"error": str(exc)}
                failed_ids.add(node.id)
                self._stats.failed_nodes += 1

        # --- PIPELINE via existing Pipeline class ---
        if pipeline_nodes:
            pipeline_results = self._exec_pipeline(pipeline_nodes, graph, context, results)
            results.update(pipeline_results)

        # --- PARALLEL_FANOUT ---
        if fanout_nodes:
            fanout_results = self._exec_parallel_fanout(fanout_nodes, context, results)
            results.update(fanout_results)

        # --- QUORUM_VOTE via existing Quorum class ---
        if quorum_nodes:
            quorum_results = self._exec_quorum(quorum_nodes, context, results)
            results.update(quorum_results)

        # --- SUPERVISOR_WORKER ---
        if supervisor_nodes:
            supervisor_results = self._exec_supervisor_worker(supervisor_nodes, graph, context, results)
            results.update(supervisor_results)

        # --- ITERATIVE_REFINE ---
        if refine_nodes:
            refine_results = self._exec_iterative_refine(refine_nodes, graph, context, results)
            results.update(refine_results)

        # --- EVENT_DRIVEN ---
        if event_nodes:
            event_results = self._exec_event_driven(event_nodes, graph, context, results)
            results.update(event_results)

        # Mark any remaining nodes as skipped
        for nid in graph.nodes:
            if nid not in completed_ids and nid not in failed_ids:
                self._stats.skipped_nodes += 1

        self._stats.total_duration_seconds = time.time() - start_time
        self._stats.history.append({
            "timestamp": start_time,
            "total_nodes": self._stats.total_nodes,
            "completed": self._stats.completed_nodes,
            "failed": self._stats.failed_nodes,
            "duration": self._stats.total_duration_seconds,
        })

        logger.info(
            f"flow_executor_complete completed={self._stats.completed_nodes} "
            f"failed={self._stats.failed_nodes} skipped={self._stats.skipped_nodes} "
            f"duration={self._stats.total_duration_seconds:.4f}"
        )
        return results

    # -- individual node execution ------------------------------------------

    def _exec_node(self, node: FlowNode, context: Dict[str, Any], prior_results: Dict[str, Any]) -> Any:
        if node.callable_fn is not None:
            return node.callable_fn(context, prior_results)
        # Default: return a summary dict
        return {
            "node_id": node.id,
            "node_name": node.name,
            "pattern": node.pattern.value,
            "status": "executed",
            "config": node.config,
        }

    # -- PIPELINE -----------------------------------------------------------

    def _exec_pipeline(
        self,
        nodes: List[FlowNode],
        graph: FlowGraph,
        context: Dict[str, Any],
        prior_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        pipeline = Pipeline(max_workers=self._max_workers)
        # Build dependency map from graph edges among pipeline nodes
        node_ids = {n.id for n in nodes}
        for node in nodes:
            deps = [
                e.source_id for e in graph.edges
                if e.target_id == node.id and e.source_id in node_ids and e.source_id != node.id
            ]
            fn = node.callable_fn if node.callable_fn is not None else lambda: {
                "node_id": node.id, "pattern": node.pattern.value, "status": "executed"
            }
            pipeline.add_task(Task(id=node.id, fn=fn, depends_on=deps))

        pipeline_results = pipeline.execute()
        task_results = pipeline.results()
        results: Dict[str, Any] = {}
        for tid, tr in task_results.items():
            if tr.status == TaskStatus.COMPLETED:
                results[tid] = tr.value
                self._stats.completed_nodes += 1
            elif tr.status == TaskStatus.FAILED:
                results[tid] = {"error": tr.error}
                self._stats.failed_nodes += 1
            else:
                results[tid] = {"status": tr.status.value}
                self._stats.skipped_nodes += 1
        return results

    # -- PARALLEL_FANOUT ----------------------------------------------------

    def _exec_parallel_fanout(
        self,
        nodes: List[FlowNode],
        context: Dict[str, Any],
        prior_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        max_parallel = 0

        def _run(node: FlowNode) -> Tuple[str, Any]:
            return node.id, self._exec_node(node, context, prior_results)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {pool.submit(_run, n): n.id for n in nodes}
            active = len(futures)
            if active > max_parallel:
                max_parallel = active
            for future in concurrent.futures.as_completed(futures):
                try:
                    nid, value = future.result()
                    results[nid] = value
                    self._stats.completed_nodes += 1
                except Exception as exc:
                    nid = futures[future]
                    results[nid] = {"error": str(exc)}
                    self._stats.failed_nodes += 1

        if max_parallel > self._stats.max_parallelism:
            self._stats.max_parallelism = max_parallel
        return results

    # -- QUORUM_VOTE --------------------------------------------------------

    def _exec_quorum(
        self,
        nodes: List[FlowNode],
        context: Dict[str, Any],
        prior_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for node in nodes:
            proposal = context.get("proposal", f"vote_on_{node.id}")
            if node.callable_fn is not None:
                try:
                    node_result = self._exec_node(node, context, prior_results)
                    results[node.id] = node_result
                    self._stats.completed_nodes += 1
                except Exception as exc:
                    results[node.id] = {"error": str(exc)}
                    self._stats.failed_nodes += 1
                continue
            # Use Quorum for voting
            decision = self._quorum.decide(proposal)
            results[node.id] = decision.to_dict()
            self._stats.completed_nodes += 1
        return results

    # -- SUPERVISOR_WORKER --------------------------------------------------

    def _exec_supervisor_worker(
        self,
        nodes: List[FlowNode],
        graph: FlowGraph,
        context: Dict[str, Any],
        prior_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        supervisors = [n for n in nodes if "supervisor" in n.id.lower()]
        workers = [n for n in nodes if "supervisor" not in n.id.lower()]

        # Execute supervisor first
        for sup in supervisors:
            try:
                sup_result = self._exec_node(sup, context, prior_results)
                results[sup.id] = sup_result
                self._stats.completed_nodes += 1
            except Exception as exc:
                results[sup.id] = {"error": str(exc)}
                self._stats.failed_nodes += 1

        # Execute workers with governor-controlled concurrency
        for worker in workers:
            acquired = self._governor.acquire(timeout=5.0)
            if not acquired:
                results[worker.id] = {"error": "governor_timeout", "status": "skipped"}
                self._stats.skipped_nodes += 1
                continue
            try:
                worker_result = self._exec_node(worker, context, {**prior_results, **results})
                results[worker.id] = worker_result
                self._stats.completed_nodes += 1
            except Exception as exc:
                results[worker.id] = {"error": str(exc)}
                self._stats.failed_nodes += 1
            finally:
                self._governor.release()

        # Supervisor reviews worker results
        for sup in supervisors:
            if sup.id in results and isinstance(results[sup.id], dict) and "error" not in results[sup.id]:
                results[sup.id]["review"] = {
                    "workers_reviewed": len(workers),
                    "approved": True,
                }

        return results

    # -- ITERATIVE_REFINE ---------------------------------------------------

    def _exec_iterative_refine(
        self,
        nodes: List[FlowNode],
        graph: FlowGraph,
        context: Dict[str, Any],
        prior_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        max_iterations = int(context.get("max_refine_iterations", 3))

        creators = [n for n in nodes if "creator" in n.id.lower()]
        reviewers = [n for n in nodes if "reviewer" in n.id.lower()]

        for creator, reviewer in zip(creators, reviewers):
            draft = None
            for iteration in range(max_iterations):
                # Creator produces / refines
                try:
                    ctx = {**context, "iteration": iteration, "previous_draft": draft}
                    draft = self._exec_node(creator, ctx, prior_results)
                    results[creator.id] = draft
                except Exception as exc:
                    results[creator.id] = {"error": str(exc)}
                    self._stats.failed_nodes += 1
                    break

                # Reviewer evaluates
                try:
                    review = self._exec_node(reviewer, {**ctx, "draft": draft}, prior_results)
                    results[reviewer.id] = review
                except Exception as exc:
                    results[reviewer.id] = {"error": str(exc)}
                    self._stats.failed_nodes += 1
                    break

                # Check if review approves
                if isinstance(review, dict) and review.get("approved", False):
                    logger.info(
                        f"flow_executor_refine_approved creator={creator.id} iteration={iteration}"
                    )
                    break
            else:
                logger.info(
                    f"flow_executor_refine_max_iterations creator={creator.id} iterations={max_iterations}"
                )

            if creator.id not in results or not isinstance(results.get(creator.id), dict) or "error" not in results.get(creator.id, {}):
                self._stats.completed_nodes += 1
            if reviewer.id not in results or not isinstance(results.get(reviewer.id), dict) or "error" not in results.get(reviewer.id, {}):
                self._stats.completed_nodes += 1

        return results

    # -- EVENT_DRIVEN -------------------------------------------------------

    def _exec_event_driven(
        self,
        nodes: List[FlowNode],
        graph: FlowGraph,
        context: Dict[str, Any],
        prior_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        # Build a simple event chain: source → handler → sink
        node_map = {n.id: n for n in nodes}
        for node in nodes:
            # Find outgoing edges from this node
            out_edges = [e for e in graph.edges if e.source_id == node.id and e.target_id in node_map]
            # Check conditional edges
            active_edges = []
            for edge in out_edges:
                if edge.condition is not None:
                    try:
                        if edge.condition(context, prior_results):
                            active_edges.append(edge)
                    except Exception as exc:
                        logger.warning(f"flow_executor_edge_condition_failed edge={edge.source_id}→{edge.target_id} error={exc}")
                else:
                    active_edges.append(edge)

            if node.id not in results:
                try:
                    result = self._exec_node(node, context, prior_results)
                    results[node.id] = result
                    self._stats.completed_nodes += 1
                except Exception as exc:
                    results[node.id] = {"error": str(exc)}
                    self._stats.failed_nodes += 1

            # Propagate events to downstream nodes
            for edge in active_edges:
                target = node_map[edge.target_id]
                if target.id not in results:
                    try:
                        event_ctx = {**context, "event_from": node.id, "event_data": results.get(node.id)}
                        result = self._exec_node(target, event_ctx, {**prior_results, **results})
                        results[target.id] = result
                        self._stats.completed_nodes += 1
                    except Exception as exc:
                        results[target.id] = {"error": str(exc)}
                        self._stats.failed_nodes += 1

        return results

    # -- stats --------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return self._stats.to_dict()


# ---------------------------------------------------------------------------
# FlowEvaluator
# ---------------------------------------------------------------------------

class FlowEvaluator:
    """Evaluates the results of a flow-graph execution.

    Checks:
      - Completeness: did all nodes execute?
      - Quality: supervisor scores if applicable.
      - Timeliness: did execution meet urgency expectations?
    """

    # Urgency → expected max duration (seconds)
    URGENCY_DEADLINES: Dict[str, float] = {
        "high": 5.0,
        "medium": 30.0,
        "low": 120.0,
    }

    def evaluate(
        self,
        results: Dict[str, Any],
        graph: FlowGraph,
        situation: Dict[str, Any],
        exec_stats: ExecutionStats,
    ) -> EvaluationReport:
        """Produce an EvaluationReport from execution results."""
        total = len(graph.nodes)
        completed = exec_stats.completed_nodes
        failed = exec_stats.failed_nodes

        # --- Completeness ---
        completeness = completed / total if total > 0 else 0.0

        # --- Quality ---
        quality_score = self._compute_quality(results, graph)

        # --- Timeliness ---
        urgency = situation.get("urgency", "medium")
        deadline = self.URGENCY_DEADLINES.get(urgency, 30.0)
        timeliness = 1.0 if exec_stats.total_duration_seconds <= deadline else max(
            0.0, deadline / exec_stats.total_duration_seconds
        )

        # --- Overall pass/fail ---
        passed = completeness >= 0.8 and quality_score >= 0.5 and timeliness >= 0.5

        # --- Feedback ---
        feedback_parts: List[str] = []
        if completeness < 0.8:
            feedback_parts.append(
                f"Completeness too low: {completeness:.0%} of nodes completed."
            )
        if quality_score < 0.5:
            feedback_parts.append(
                f"Quality below threshold: {quality_score:.0%}."
            )
        if timeliness < 0.5:
            feedback_parts.append(
                f"Timeliness missed: took {exec_stats.total_duration_seconds:.2f}s "
                f"vs deadline {deadline:.1f}s."
            )
        if not feedback_parts:
            feedback_parts.append("All checks passed.")

        report = EvaluationReport(
            passed=passed,
            completeness=completeness,
            quality_score=quality_score,
            timeliness=timeliness,
            feedback=" ".join(feedback_parts),
            details={
                "total_nodes": total,
                "completed_nodes": completed,
                "failed_nodes": failed,
                "duration_seconds": round(exec_stats.total_duration_seconds, 4),
                "urgency": urgency,
                "deadline_seconds": deadline,
            },
        )
        logger.info(
            f"flow_evaluator_result passed={passed} completeness={completeness:.2f} "
            f"quality={quality_score:.2f} timeliness={timeliness:.2f}"
        )
        return report

    def _compute_quality(self, results: Dict[str, Any], graph: FlowGraph) -> float:
        """Compute a quality score based on supervisor reviews and error rates."""
        supervisor_reviews: List[bool] = []
        error_count = 0
        total = len(results)

        for nid, value in results.items():
            if isinstance(value, dict):
                if "error" in value:
                    error_count += 1
                # Collect supervisor review approvals
                review = value.get("review", {})
                if isinstance(review, dict) and "approved" in review:
                    supervisor_reviews.append(bool(review["approved"]))

        # Base quality from error rate
        error_rate = error_count / total if total > 0 else 0.0
        base_quality = 1.0 - error_rate

        # Boost from supervisor approvals
        if supervisor_reviews:
            approval_rate = sum(supervisor_reviews) / len(supervisor_reviews)
            base_quality = (base_quality + approval_rate) / 2.0

        return max(0.0, min(1.0, base_quality))


# ---------------------------------------------------------------------------
# EmoGlyphFlowGraph — Main Entry Point
# ---------------------------------------------------------------------------

class EmoGlyphFlowGraph:
    """Integrates FlowAssembler + FlowExecutor + FlowEvaluator.

    5-layer process:
      1. Pulse:     Analyze situation.
      2. Current:   Select pattern(s).
      3. Construct: Assemble graph.
      4. Enactive:  Execute with monitoring.
      5. Resonance: Evaluate and feedback.
    """

    def __init__(
        self,
        governor: Optional[Governor] = None,
        quorum: Optional[Quorum] = None,
        max_workers: Optional[int] = None,
    ) -> None:
        self._assembler = FlowAssembler()
        self._executor = FlowExecutor(governor=governor, quorum=quorum, max_workers=max_workers)
        self._evaluator = FlowEvaluator()
        logger.info("emoglyph_flow_graph_initialized")

    def run(self, situation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the full 5-layer process and return comprehensive results."""
        run_id = uuid.uuid4().hex[:12]
        logger.info(f"emoglyph_flow_graph_run_start run_id={run_id}")

        # Layer 1: Pulse — Analyze situation
        pulse = self._pulse(situation)

        # Layer 2: Current — Select pattern(s)
        patterns = self._assembler._select_patterns(situation)
        current = {"patterns": [p.value for p in patterns]}

        # Layer 3: Construct — Assemble graph
        graph = self._assembler.assemble(situation)
        construct = {
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "validation_issues": graph.validate(),
        }

        # Layer 4: Enactive — Execute with monitoring
        results = self._executor.execute(graph, context)
        exec_stats = self._executor.stats()

        # Layer 5: Resonance — Evaluate and feedback
        evaluation = self._evaluator.evaluate(
            results, graph, situation,
            ExecutionStats(**exec_stats) if isinstance(exec_stats, dict) else self._executor._stats,
        )

        output = {
            "run_id": run_id,
            "pulse": pulse,
            "current": current,
            "construct": construct,
            "enactive": {
                "results": results,
                "stats": exec_stats,
            },
            "resonance": evaluation.to_dict(),
        }

        logger.info(
            f"emoglyph_flow_graph_run_complete run_id={run_id} "
            f"passed={evaluation.passed} patterns={current['patterns']}"
        )
        return output

    # -- Layer 1: Pulse -----------------------------------------------------

    @staticmethod
    def _pulse(situation: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the situation and return a summary."""
        return {
            "urgency": situation.get("urgency", "medium"),
            "complexity": situation.get("complexity", "medium"),
            "domain": situation.get("domain", "general"),
            "quality_required": situation.get("quality_required", False),
            "stakeholders": situation.get("stakeholders", 1),
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

    efg = EmoGlyphFlowGraph(max_workers=4)

    demos: List[Dict[str, str]] = [
        {
            "name": "SOLO — low urgency, low complexity",
            "urgency": "low",
            "complexity": "low",
            "domain": "general",
            "quality_required": "false",
            "stakeholders": "1",
        },
        {
            "name": "PIPELINE — medium urgency, medium complexity",
            "urgency": "medium",
            "complexity": "medium",
            "domain": "general",
            "quality_required": "false",
            "stakeholders": "1",
        },
        {
            "name": "PARALLEL_FANOUT — low urgency, high complexity",
            "urgency": "low",
            "complexity": "high",
            "domain": "general",
            "quality_required": "false",
            "stakeholders": "1",
        },
        {
            "name": "QUORUM_VOTE — quality required, multiple stakeholders",
            "urgency": "medium",
            "complexity": "medium",
            "domain": "general",
            "quality_required": "true",
            "stakeholders": "5",
        },
        {
            "name": "SUPERVISOR_WORKER — quality required, high complexity",
            "urgency": "high",
            "complexity": "high",
            "domain": "general",
            "quality_required": "true",
            "stakeholders": "1",
        },
        {
            "name": "ITERATIVE_REFINE — creative domain",
            "urgency": "medium",
            "complexity": "medium",
            "domain": "creative",
            "quality_required": "false",
            "stakeholders": "1",
        },
        {
            "name": "EVENT_DRIVEN — realtime domain",
            "urgency": "high",
            "complexity": "medium",
            "domain": "realtime",
            "quality_required": "false",
            "stakeholders": "1",
        },
        {
            "name": "HYBRID — quality + creative + high complexity",
            "urgency": "low",
            "complexity": "high",
            "domain": "creative",
            "quality_required": "true",
            "stakeholders": "3",
        },
    ]

    for demo in demos:
        name = demo.pop("name")
        print(f"\n{'=' * 60}")
        print(f"  {name}")
        print(f"{'=' * 60}")

        situation = {
            "urgency": demo["urgency"],
            "complexity": demo["complexity"],
            "domain": demo["domain"],
            "quality_required": demo["quality_required"] == "true",
            "stakeholders": int(demo["stakeholders"]),
        }

        output = efg.run(situation, context={"proposal": f"demo for {name}"})

        print(f"  Patterns : {output['current']['patterns']}")
        print(f"  Nodes    : {output['construct']['node_count']}")
        print(f"  Edges    : {output['construct']['edge_count']}")
        print(f"  Passed   : {output['resonance']['passed']}")
        print(f"  Complete : {output['resonance']['completeness']:.0%}")
        print(f"  Quality  : {output['resonance']['quality_score']:.0%}")
        print(f"  Feedback : {output['resonance']['feedback']}")

    # --- Direct FlowGraph / FlowAssembler demo ---
    print(f"\n{'=' * 60}")
    print("  Direct FlowGraph Construction & Validation")
    print(f"{'=' * 60}")

    g = FlowGraph()
    g.add_node(FlowNode(id="a", name="Node A", pattern=FlowPattern.SOLO))
    g.add_node(FlowNode(id="b", name="Node B", pattern=FlowPattern.PIPELINE))
    g.add_node(FlowNode(id="c", name="Node C", pattern=FlowPattern.PIPELINE))
    g.add_edge(FlowEdge(source_id="a", target_id="b", edge_type="data"))
    g.add_edge(FlowEdge(source_id="b", target_id="c", edge_type="data"))

    issues = g.validate()
    order = g.topological_order()
    print(f"  Validation issues : {issues if issues else 'none'}")
    print(f"  Topological order : {order}")

    # Serialization round-trip
    serialized = g.to_dict()
    g2 = FlowGraph.from_dict(serialized)
    print(f"  Round-trip nodes  : {len(g2.nodes)} (expected 3)")
    print(f"  Round-trip edges  : {len(g2.edges)} (expected 2)")


if __name__ == "__main__":
    main()
