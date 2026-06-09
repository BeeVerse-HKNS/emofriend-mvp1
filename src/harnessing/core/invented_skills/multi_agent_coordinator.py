from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = structlog.get_logger()


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class ConflictType(Enum):
    RESOURCE = "resource"
    DEPENDENCY = "dependency"
    PRIORITY = "priority"
    OUTPUT = "output"


@dataclass
class Agent:
    id: str
    name: str
    capabilities: list[str]
    current_load: float = 0.0
    max_capacity: float = 1.0

    @property
    def available_capacity(self) -> float:
        return max(0.0, self.max_capacity - self.current_load)


@dataclass
class Task:
    id: str
    name: str
    required_capabilities: list[str]
    priority: int = 5
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: str | None = None
    dependencies: list[str] = field(default_factory=list)
    result: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conflict:
    id: str
    conflict_type: ConflictType
    agents: list[str]
    tasks: list[str]
    description: str
    resolution: str | None = None


class CommunicationProtocol:
    def __init__(self):
        self._message_queue: dict[str, list[dict[str, Any]]] = {}
        self._broadcast_history: list[dict[str, Any]] = []

    def send(self, from_agent: str, to_agent: str, message: dict[str, Any]) -> str:
        message_id = str(uuid4())
        full_message = {
            "id": message_id,
            "from": from_agent,
            "to": to_agent,
            "content": message,
            "timestamp": self._get_timestamp()
        }
        if to_agent not in self._message_queue:
            self._message_queue[to_agent] = []
        self._message_queue[to_agent].append(full_message)
        return message_id

    def broadcast(self, from_agent: str, message: dict[str, Any]) -> str:
        message_id = str(uuid4())
        full_message = {
            "id": message_id,
            "from": from_agent,
            "to": "all",
            "content": message,
            "timestamp": self._get_timestamp()
        }
        self._broadcast_history.append(full_message)
        return message_id

    def receive(self, agent_id: str) -> list[dict[str, Any]]:
        messages = self._message_queue.get(agent_id, [])
        self._message_queue[agent_id] = []
        return messages

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


class TaskDistributor:
    def __init__(self):
        self._agents: dict[str, Agent] = {}
        self._tasks: dict[str, Task] = {}
        self._assignment_history: list[dict[str, Any]] = []

    def register_agent(self, agent: Agent) -> None:
        self._agents[agent.id] = agent

    def add_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    def distribute(self) -> dict[str, str]:
        assignments = {}
        pending_tasks = [
            t for t in self._tasks.values()
            if t.status == TaskStatus.PENDING and self._dependencies_met(t)
        ]
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)
        for task in pending_tasks:
            best_agent = self._find_best_agent(task)
            if best_agent:
                task.assigned_agent = best_agent.id
                task.status = TaskStatus.ASSIGNED
                best_agent.current_load += 0.1
                assignments[task.id] = best_agent.id
                self._assignment_history.append({
                    "task_id": task.id,
                    "agent_id": best_agent.id,
                    "timestamp": self._get_timestamp()
                })
        return assignments

    def _find_best_agent(self, task: Task) -> Agent | None:
        candidates = [
            agent for agent in self._agents.values()
            if self._can_handle(agent, task) and agent.available_capacity > 0
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda a: a.current_load)
        return candidates[0]

    def _can_handle(self, agent: Agent, task: Task) -> bool:
        return all(cap in agent.capabilities for cap in task.required_capabilities)

    def _dependencies_met(self, task: Task) -> bool:
        for dep_id in task.dependencies:
            dep_task = self._tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


class ConflictResolver:
    def __init__(self):
        self._conflicts: list[Conflict] = []
        self._resolution_strategies = {
            ConflictType.RESOURCE: self._resolve_resource_conflict,
            ConflictType.DEPENDENCY: self._resolve_dependency_conflict,
            ConflictType.PRIORITY: self._resolve_priority_conflict,
            ConflictType.OUTPUT: self._resolve_output_conflict,
        }

    def detect(self, agents: dict[str, Agent], tasks: dict[str, Task]) -> list[Conflict]:
        conflicts = []
        conflicts.extend(self._detect_resource_conflicts(agents, tasks))
        conflicts.extend(self._detect_dependency_conflicts(tasks))
        self._conflicts.extend(conflicts)
        return conflicts

    def resolve(self, conflict: Conflict) -> str:
        strategy = self._resolution_strategies.get(conflict.conflict_type)
        if strategy:
            resolution = strategy(conflict)
            conflict.resolution = resolution
            return resolution
        return "no_resolution_available"

    def _detect_resource_conflicts(self, agents: dict[str, Agent], tasks: dict[str, Task]) -> list[Conflict]:
        conflicts = []
        overloaded = [a for a in agents.values() if a.current_load > a.max_capacity]
        for agent in overloaded:
            conflict = Conflict(
                id=str(uuid4()),
                conflict_type=ConflictType.RESOURCE,
                agents=[agent.id],
                tasks=[t.id for t in tasks.values() if t.assigned_agent == agent.id],
                description=f"Agent {agent.name} is overloaded"
            )
            conflicts.append(conflict)
        return conflicts

    def _detect_dependency_conflicts(self, tasks: dict[str, Task]) -> list[Conflict]:
        conflicts = []
        for task in tasks.values():
            if task.status == TaskStatus.IN_PROGRESS:
                for dep_id in task.dependencies:
                    dep_task = tasks.get(dep_id)
                    if dep_task and dep_task.status == TaskStatus.FAILED:
                        conflict = Conflict(
                            id=str(uuid4()),
                            conflict_type=ConflictType.DEPENDENCY,
                            agents=[],
                            tasks=[task.id, dep_id],
                            description=f"Task {task.name} depends on failed task {dep_task.name}"
                        )
                        conflicts.append(conflict)
        return conflicts

    def _resolve_resource_conflict(self, conflict: Conflict) -> str:
        return "redistribute_tasks"

    def _resolve_dependency_conflict(self, conflict: Conflict) -> str:
        return "skip_dependent_task"

    def _resolve_priority_conflict(self, conflict: Conflict) -> str:
        return "reorder_by_priority"

    def _resolve_output_conflict(self, conflict: Conflict) -> str:
        return "merge_or_select_latest"


class ResultAggregator:
    def __init__(self):
        self._results: dict[str, Any] = {}
        self._aggregation_strategies: dict[str, callable] = {}

    def collect(self, task_id: str, result: Any) -> None:
        self._results[task_id] = result

    def aggregate(self, task_ids: list[str], strategy: str = "combine") -> dict[str, Any]:
        results_to_aggregate = {
            tid: self._results.get(tid)
            for tid in task_ids
            if tid in self._results
        }
        if strategy == "combine":
            return {"combined": results_to_aggregate}
        elif strategy == "merge":
            merged = {}
            for result in results_to_aggregate.values():
                if isinstance(result, dict):
                    merged.update(result)
            return merged
        elif strategy == "list":
            return {"results": list(results_to_aggregate.values())}
        return results_to_aggregate

    def get_result(self, task_id: str) -> Any:
        return self._results.get(task_id)


class MultiAgentCoordinator:
    def __init__(self) -> None:
        self._formula = "A * C + G / S"
        self._capability = "multi_agent_coordinator"
        self._id = "INV-008"
        self.communication = CommunicationProtocol()
        self.distributor = TaskDistributor()
        self.conflict_resolver = ConflictResolver()
        self.result_aggregator = ResultAggregator()

    def analyze(
        self,
        agents: list[dict[str, Any]],
        tasks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        try:
            for agent_data in agents:
                agent = Agent(
                    id=agent_data.get("id", str(uuid4())),
                    name=agent_data.get("name", "Unknown"),
                    capabilities=agent_data.get("capabilities", []),
                    current_load=agent_data.get("current_load", 0.0),
                    max_capacity=agent_data.get("max_capacity", 1.0)
                )
                self.distributor.register_agent(agent)
            for task_data in tasks:
                task = Task(
                    id=task_data.get("id", str(uuid4())),
                    name=task_data.get("name", "Unknown"),
                    required_capabilities=task_data.get("required_capabilities", []),
                    priority=task_data.get("priority", 5),
                    dependencies=task_data.get("dependencies", [])
                )
                self.distributor.add_task(task)
            assignments = self.distributor.distribute()
            conflicts = self.conflict_resolver.detect(
                self.distributor._agents,
                self.distributor._tasks
            )
            resolved = []
            for conflict in conflicts:
                resolution = self.conflict_resolver.resolve(conflict)
                resolved.append({"conflict_id": conflict.id, "resolution": resolution})
            result = {
                "assignments": assignments,
                "total_agents": len(self.distributor._agents),
                "total_tasks": len(self.distributor._tasks),
                "assigned_tasks": len(assignments),
                "conflicts_detected": len(conflicts),
                "conflicts_resolved": len(resolved),
                "resolution_details": resolved
            }
            logger.info(
                "multi_agent_coordinator_success",
                capability=self._capability,
                assigned=len(assignments)
            )
            return {"status": "success", "capability": self._capability, "result": result, "formula": self._formula}
        except Exception as exc:
            logger.error("multi_agent_coordinator_failed", capability=self._capability, error=str(exc))
            return {"status": "error", "capability": self._capability, "error": str(exc)}

    def execute(
        self,
        agents: list[dict[str, Any]],
        tasks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self.analyze(agents, tasks)

    def send_message(self, from_agent: str, to_agent: str, message: dict[str, Any]) -> str:
        return self.communication.send(from_agent, to_agent, message)

    def broadcast_message(self, from_agent: str, message: dict[str, Any]) -> str:
        return self.communication.broadcast(from_agent, message)

    def collect_result(self, task_id: str, result: Any) -> None:
        self.result_aggregator.collect(task_id, result)

    def get_aggregated_results(self, task_ids: list[str]) -> dict[str, Any]:
        return self.result_aggregator.aggregate(task_ids)


if __name__ == "__main__":
    coordinator = MultiAgentCoordinator()
    test_agents = [
        {"id": "agent1", "name": "Coder", "capabilities": ["coding", "testing"], "max_capacity": 1.0},
        {"id": "agent2", "name": "Reviewer", "capabilities": ["review", "testing"], "max_capacity": 1.0},
        {"id": "agent3", "name": "Deployer", "capabilities": ["deploy"], "max_capacity": 1.0},
    ]
    test_tasks = [
        {"id": "task1", "name": "Write code", "required_capabilities": ["coding"], "priority": 8},
        {"id": "task2", "name": "Test code", "required_capabilities": ["testing"], "priority": 7},
        {"id": "task3", "name": "Review code", "required_capabilities": ["review"], "priority": 6},
        {"id": "task4", "name": "Deploy", "required_capabilities": ["deploy"], "priority": 5},
    ]
    result = coordinator.analyze(test_agents, test_tasks)
    print(f"Status: {result['status']}")
    print(f"Assigned tasks: {result['result']['assigned_tasks']}")
    print(f"Assignments: {result['result']['assignments']}")
    print(f"Conflicts: {result['result']['conflicts_detected']}")
    msg_id = coordinator.send_message("agent1", "agent2", {"type": "task_complete", "task": "task1"})
    print(f"Message sent: {msg_id}")
    assert result["status"] == "success"
    assert result["result"]["assigned_tasks"] == 4
    print("All tests passed!")
