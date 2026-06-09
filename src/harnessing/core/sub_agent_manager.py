"""Sub-Agent Manager — Unified coordinator for all sub-projects/sub-agents.

Integrates discovery, registration, health monitoring, and task coordination
across the Harnessing ecosystem.

Components:
  1. SubAgentInfo       — Dataclass representing a single sub-agent.
  2. SubAgentRegistry   — In-memory registry with query and persistence.
  3. SubAgentHealthMonitor — Health scoring based on filesystem heuristics.
  4. SubAgentCoordinator   — Task routing via EmoGlyphFlowGraph.
  5. SubAgentManager        — Main entry point with auto-discovery.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from harnessing.core.emoglyph_flow_graph import EmoGlyphFlowGraph

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SubAgentInfo
# ---------------------------------------------------------------------------

@dataclass
class SubAgentInfo:
    """Metadata and status for a single sub-agent / sub-project."""

    id: str
    name: str
    path: str
    stack: str  # Python / Node / Streamlit / etc.
    status: str  # active / inactive / archived / unknown
    deploy_target: str
    health_score: float  # 0–100
    last_scanned: str
    capabilities: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "stack": self.stack,
            "status": self.status,
            "deploy_target": self.deploy_target,
            "health_score": self.health_score,
            "last_scanned": self.last_scanned,
            "capabilities": list(self.capabilities),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SubAgentInfo:
        return cls(
            id=data["id"],
            name=data["name"],
            path=data["path"],
            stack=data.get("stack", "unknown"),
            status=data.get("status", "unknown"),
            deploy_target=data.get("deploy_target", ""),
            health_score=float(data.get("health_score", 0.0)),
            last_scanned=data.get("last_scanned", ""),
            capabilities=list(data.get("capabilities", [])),
            errors=list(data.get("errors", [])),
        )


# ---------------------------------------------------------------------------
# SubAgentRegistry
# ---------------------------------------------------------------------------

class SubAgentRegistry:
    """In-memory registry of sub-agents with query helpers and persistence."""

    def __init__(self) -> None:
        self._agents: Dict[str, SubAgentInfo] = {}

    # -- mutation -----------------------------------------------------------

    def register(self, info: SubAgentInfo) -> None:
        self._agents[info.id] = info
        logger.info("registry_register id=%s name=%s", info.id, info.name)

    def unregister(self, id: str) -> None:
        removed = self._agents.pop(id, None)
        if removed is not None:
            logger.info("registry_unregister id=%s name=%s", id, removed.name)
        else:
            logger.warning("registry_unregister_not_found id=%s", id)

    # -- query --------------------------------------------------------------

    def get(self, id: str) -> Optional[SubAgentInfo]:
        return self._agents.get(id)

    def list_all(self) -> List[SubAgentInfo]:
        return list(self._agents.values())

    def list_by_status(self, status: str) -> List[SubAgentInfo]:
        return [a for a in self._agents.values() if a.status == status]

    def list_by_stack(self, stack: str) -> List[SubAgentInfo]:
        return [a for a in self._agents.values() if a.stack.lower() == stack.lower()]

    def search(self, capability: str) -> List[SubAgentInfo]:
        cap_lower = capability.lower()
        return [
            a for a in self._agents.values()
            if any(cap_lower in c.lower() for c in a.capabilities)
        ]

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {aid: info.to_dict() for aid, info in self._agents.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SubAgentRegistry:
        registry = cls()
        for aid, info_data in data.items():
            registry.register(SubAgentInfo.from_dict(info_data))
        return registry

    # -- file persistence ---------------------------------------------------

    def save(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("registry_saved path=%s agents=%d", path, len(self._agents))

    @classmethod
    def load(cls, path: str) -> SubAgentRegistry:
        p = Path(path)
        if not p.exists():
            logger.warning("registry_load_file_not_found path=%s", path)
            return cls()
        data = json.loads(p.read_text(encoding="utf-8"))
        registry = cls.from_dict(data)
        logger.info("registry_loaded path=%s agents=%d", path, len(registry._agents))
        return registry

    def __len__(self) -> int:
        return len(self._agents)


# ---------------------------------------------------------------------------
# SubAgentHealthMonitor
# ---------------------------------------------------------------------------

class SubAgentHealthMonitor:
    """Scores sub-agent health based on filesystem heuristics.

    Checks (each contributes to the score):
      - Path exists                              +20
      - AGENTS.md exists                         +20
      - requirements.txt / package.json exists   +15
      - No ImportError patterns in source        +15
      - No silent except patterns in source      +15
      - Deployment config present                +15
    """

    MAX_SCORE = 100.0

    def check_health(self, info: SubAgentInfo) -> float:
        score = 0.0
        errors: List[str] = []
        project_path = Path(info.path)

        # 1. Path exists (+20)
        if project_path.exists():
            score += 20
        else:
            errors.append("project_path_missing")

        # 2. AGENTS.md exists (+20)
        agents_md = project_path / "AGENTS.md"
        if agents_md.exists():
            score += 20
        else:
            errors.append("agents_md_missing")

        # 3. requirements.txt / package.json exists (+15)
        has_deps = (project_path / "requirements.txt").exists() or (project_path / "package.json").exists()
        if has_deps:
            score += 15
        else:
            errors.append("dependency_file_missing")

        # 4. No ImportError patterns (+15)
        import_errors = self._count_pattern(project_path, r"ImportError")
        if import_errors == 0:
            score += 15
        else:
            errors.append(f"import_error_patterns:{import_errors}")

        # 5. No silent except patterns (+15)
        silent_excepts = self._count_pattern(project_path, r"except\s*:")
        if silent_excepts == 0:
            score += 15
        else:
            errors.append(f"silent_except_patterns:{silent_excepts}")

        # 6. Deployment config present (+15)
        has_deploy = any(
            (project_path / f).exists()
            for f in ("railway.toml", "Dockerfile", "deploy.py", "vercel.json", ".github/workflows", "Procfile")
        )
        if has_deploy:
            score += 15
        else:
            errors.append("deployment_config_missing")

        info.health_score = min(score, self.MAX_SCORE)
        info.errors = errors
        info.last_scanned = datetime.now().isoformat()
        logger.info(
            "health_check id=%s score=%.1f errors=%s",
            info.id, info.health_score, errors,
        )
        return info.health_score

    def scan_all(self, registry: SubAgentRegistry) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for info in registry.list_all():
            scores[info.id] = self.check_health(info)
        logger.info("health_scan_all total=%d", len(scores))
        return scores

    def get_critical(self, registry: SubAgentRegistry) -> List[SubAgentInfo]:
        """Return agents with health_score < 30."""
        return [a for a in registry.list_all() if a.health_score < 30]

    def get_at_risk(self, registry: SubAgentRegistry) -> List[SubAgentInfo]:
        """Return agents with health_score between 30 and 70 (inclusive)."""
        return [a for a in registry.list_all() if 30 <= a.health_score <= 70]

    # -- helpers ------------------------------------------------------------

    def _count_pattern(self, project_path: Path, pattern: str) -> int:
        if not project_path.exists():
            return 0
        count = 0
        try:
            for py_file in project_path.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    count += len(re.findall(pattern, content))
                except Exception:
                    continue
        except Exception:
            pass
        return count


# ---------------------------------------------------------------------------
# SubAgentCoordinator
# ---------------------------------------------------------------------------

class SubAgentCoordinator:
    """Routes tasks to appropriate sub-agents via EmoGlyphFlowGraph."""

    def __init__(self) -> None:
        self._efg = EmoGlyphFlowGraph()
        self._assignments: Dict[str, Dict[str, Any]] = {}
        self._dependencies: Dict[str, List[str]] = {}

    def coordinate(self, task: str, registry: SubAgentRegistry) -> Dict[str, Any]:
        """Determine which sub-agents to involve for a given task."""
        agents = registry.list_all()
        if not agents:
            return {"task": task, "assigned": [], "flow": None}

        # Build a situation descriptor from the task and available agents
        situation = self._infer_situation(task, agents)
        context = {"task": task, "agents": [a.to_dict() for a in agents]}

        flow_result = self._efg.run(situation, context)

        # Select agents whose capabilities match the task keywords
        assigned = self._select_agents(task, agents)

        result = {
            "task": task,
            "assigned": [a.id for a in assigned],
            "flow_patterns": flow_result.get("current", {}).get("patterns", []),
            "flow_passed": flow_result.get("resonance", {}).get("passed", False),
        }
        logger.info(
            "coordinate task='%s' assigned=%d patterns=%s",
            task, len(assigned), result["flow_patterns"],
        )
        return result

    def assign_task(self, task: str, agent_id: str) -> Dict[str, Any]:
        """Assign a specific task to a specific agent."""
        assignment = {
            "task": task,
            "agent_id": agent_id,
            "assigned_at": datetime.now().isoformat(),
            "status": "assigned",
        }
        self._assignments[f"{agent_id}:{task}"] = assignment
        logger.info("assign_task agent=%s task='%s'", agent_id, task)
        return assignment

    def broadcast_task(self, task: str) -> Dict[str, Dict[str, Any]]:
        """Broadcast a task to all known agents."""
        results: Dict[str, Dict[str, Any]] = {}
        for key, assignment in self._assignments.items():
            agent_id = key.split(":")[0]
            results[agent_id] = {
                "task": task,
                "agent_id": agent_id,
                "assigned_at": datetime.now().isoformat(),
                "status": "broadcast",
            }
        logger.info("broadcast_task task='%s' recipients=%d", task, len(results))
        return results

    def get_dependencies(self, agent_id: str) -> List[str]:
        """Return the list of agent IDs that *agent_id* depends on."""
        return list(self._dependencies.get(agent_id, []))

    def set_dependencies(self, agent_id: str, depends_on: List[str]) -> None:
        self._dependencies[agent_id] = list(depends_on)

    # -- helpers ------------------------------------------------------------

    def _infer_situation(self, task: str, agents: List[SubAgentInfo]) -> Dict[str, Any]:
        task_lower = task.lower()
        urgency = "high" if any(w in task_lower for w in ("urgent", "critical", "asap", "fix")) else "medium"
        complexity = "high" if len(agents) > 5 else "medium" if len(agents) > 2 else "low"
        domain = "creative" if any(w in task_lower for w in ("design", "content", "creative")) else \
                 "realtime" if any(w in task_lower for w in ("monitor", "stream", "realtime")) else "general"
        quality = any(w in task_lower for w in ("quality", "review", "audit", "verify"))
        return {
            "urgency": urgency,
            "complexity": complexity,
            "domain": domain,
            "quality_required": quality,
            "stakeholders": min(len(agents), 10),
        }

    def _select_agents(self, task: str, agents: List[SubAgentInfo]) -> List[SubAgentInfo]:
        task_lower = task.lower()
        task_words = set(re.findall(r"\w+", task_lower))
        scored: List[tuple] = []
        for agent in agents:
            if agent.status != "active":
                continue
            cap_words: set[str] = set()
            for cap in agent.capabilities:
                cap_words.update(re.findall(r"\w+", cap.lower()))
            overlap = len(task_words & cap_words)
            if overlap > 0:
                scored.append((overlap, agent))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [agent for _, agent in scored]


# ---------------------------------------------------------------------------
# SubAgentManager — Main entry point
# ---------------------------------------------------------------------------

class SubAgentManager:
    """Unified entry point for sub-agent discovery, health, and coordination."""

    DEFAULT_PROJECTS_DIR = "projects"

    def __init__(self, projects_dir: str = "projects") -> None:
        self._projects_dir = projects_dir
        self._registry = SubAgentRegistry()
        self._health_monitor = SubAgentHealthMonitor()
        self._coordinator = SubAgentCoordinator()
        logger.info("sub_agent_manager_initialized projects_dir=%s", projects_dir)

    # -- discovery ----------------------------------------------------------

    def auto_discover(self) -> int:
        """Scan the projects directory and register all sub-agents.

        Returns the number of newly registered agents.
        """
        projects_path = Path(self._projects_dir)
        if not projects_path.exists():
            logger.warning("auto_discover_projects_dir_not_found path=%s", self._projects_dir)
            return 0

        count = 0
        for item in sorted(projects_path.iterdir()):
            if not item.is_dir():
                continue
            # Skip directories that are clearly not sub-projects
            if item.name.startswith(".") or item.name == "__pycache__":
                continue

            agent_id = item.name
            existing = self._registry.get(agent_id)
            if existing is not None:
                continue

            info = self._build_agent_info(item)
            self._registry.register(info)
            count += 1

        logger.info("auto_discover_complete registered=%d total=%d", count, len(self._registry))
        return count

    # -- accessors ----------------------------------------------------------

    def get_registry(self) -> SubAgentRegistry:
        return self._registry

    def get_health_monitor(self) -> SubAgentHealthMonitor:
        return self._health_monitor

    def get_coordinator(self) -> SubAgentCoordinator:
        return self._coordinator

    # -- health check -------------------------------------------------------

    def run_health_check(self) -> Dict[str, Any]:
        scores = self._health_monitor.scan_all(self._registry)
        critical = self._health_monitor.get_critical(self._registry)
        at_risk = self._health_monitor.get_at_risk(self._registry)
        result = {
            "total_agents": len(self._registry),
            "scores": scores,
            "critical_count": len(critical),
            "at_risk_count": len(at_risk),
            "critical": [a.id for a in critical],
            "at_risk": [a.id for a in at_risk],
        }
        logger.info(
            "health_check_complete total=%d critical=%d at_risk=%d",
            result["total_agents"], result["critical_count"], result["at_risk_count"],
        )
        return result

    # -- dashboard ----------------------------------------------------------

    def get_dashboard_data(self) -> Dict[str, Any]:
        agents = self._registry.list_all()
        status_counts: Dict[str, int] = {}
        stack_counts: Dict[str, int] = {}
        total_health = 0.0
        for a in agents:
            status_counts[a.status] = status_counts.get(a.status, 0) + 1
            stack_counts[a.stack] = stack_counts.get(a.stack, 0) + 1
            total_health += a.health_score

        avg_health = total_health / len(agents) if agents else 0.0
        critical = self._health_monitor.get_critical(self._registry)
        at_risk = self._health_monitor.get_at_risk(self._registry)

        return {
            "total_agents": len(agents),
            "status_distribution": status_counts,
            "stack_distribution": stack_counts,
            "average_health": round(avg_health, 1),
            "critical_agents": [a.to_dict() for a in critical],
            "at_risk_agents": [a.to_dict() for a in at_risk],
            "agents": [a.to_dict() for a in agents],
        }

    # -- helpers ------------------------------------------------------------

    def _build_agent_info(self, project_path: Path) -> SubAgentInfo:
        name = project_path.name
        stack = self._detect_stack(project_path)
        status = self._detect_status(project_path)
        deploy_target = self._detect_deploy_target(project_path)
        capabilities = self._extract_capabilities(project_path)

        return SubAgentInfo(
            id=name,
            name=name,
            path=str(project_path),
            stack=stack,
            status=status,
            deploy_target=deploy_target,
            health_score=0.0,
            last_scanned="",
            capabilities=capabilities,
            errors=[],
        )

    def _detect_stack(self, project_path: Path) -> str:
        if (project_path / "requirements.txt").exists() or (project_path / "pyproject.toml").exists():
            # Check for Streamlit
            req = project_path / "requirements.txt"
            if req.exists():
                try:
                    content = req.read_text(encoding="utf-8", errors="ignore").lower()
                    if "streamlit" in content:
                        return "Streamlit"
                except Exception:
                    pass
            return "Python"
        if (project_path / "package.json").exists():
            return "Node"
        if (project_path / "App.js").exists():
            return "React Native"
        if (project_path / "manifest.json").exists():
            return "Chrome Extension"
        # Check for static site
        if (project_path / "index.html").exists() or (project_path / "site").is_dir():
            return "Static"
        return "unknown"

    def _detect_status(self, project_path: Path) -> str:
        name_lower = project_path.name.lower()
        if "archived" in name_lower:
            return "archived"
        agents_md = project_path / "AGENTS.md"
        if not agents_md.exists():
            return "unknown"
        # Check last modification time
        try:
            latest_mtime: Optional[float] = None
            for f in project_path.rglob("*"):
                if f.is_file() and not f.name.startswith("."):
                    mtime = f.stat().st_mtime
                    if latest_mtime is None or mtime > latest_mtime:
                        latest_mtime = mtime
            if latest_mtime is not None:
                days_since = (datetime.now().timestamp() - latest_mtime) / 86400
                if days_since > 30:
                    return "inactive"
                return "active"
        except Exception:
            pass
        return "unknown"

    def _detect_deploy_target(self, project_path: Path) -> str:
        if (project_path / "railway.toml").exists():
            return "Railway"
        if (project_path / "Dockerfile").exists():
            return "Docker"
        if (project_path / "vercel.json").exists():
            return "Vercel"
        if (project_path / "Procfile").exists():
            return "Heroku"
        if (project_path / ".github").is_dir():
            return "GitHub Actions"
        return "local"

    def _extract_capabilities(self, project_path: Path) -> List[str]:
        capabilities: List[str] = []
        agents_md = project_path / "AGENTS.md"
        if agents_md.exists():
            try:
                content = agents_md.read_text(encoding="utf-8", errors="ignore")
                # Extract capability-like lines from AGENTS.md
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("- ") and len(line) > 3:
                        cap = line.lstrip("- ").strip()
                        if 3 < len(cap) < 80:
                            capabilities.append(cap)
            except Exception:
                pass
        # Infer from key files
        if (project_path / "app.py").exists():
            capabilities.append("web_app")
        if (project_path / "api").is_dir() or (project_path / "src" / project_path.name / "api").is_dir():
            capabilities.append("api")
        if any((project_path / f).exists() for f in ("qa_test.py", "qa_check.py", "tests")):
            capabilities.append("testing")
        return capabilities[:20]


# ---------------------------------------------------------------------------
# main() demo
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

    # Resolve projects directory relative to this file's location
    this_dir = Path(__file__).resolve().parent
    root_dir = this_dir.parent.parent.parent  # src/harnessing/core -> repo root
    projects_dir = str(root_dir / "projects")

    manager = SubAgentManager(projects_dir=projects_dir)

    # --- Auto-discover ---
    print("=" * 70)
    print("  Sub-Agent Manager — Auto-Discovery & Health Check")
    print("=" * 70)

    registered = manager.auto_discover()
    print(f"\n  Registered {registered} sub-agents from: {projects_dir}")

    # --- Health check ---
    print("\n--- Health Check ---")
    health = manager.run_health_check()
    print(f"  Total agents : {health['total_agents']}")
    print(f"  Critical     : {health['critical_count']}  {health['critical']}")
    print(f"  At-risk      : {health['at_risk_count']}  {health['at_risk']}")

    # --- Dashboard summary ---
    print("\n--- Dashboard Summary ---")
    dashboard = manager.get_dashboard_data()
    print(f"  Total agents     : {dashboard['total_agents']}")
    print(f"  Avg health score : {dashboard['average_health']}")
    print(f"  Status breakdown : {dashboard['status_distribution']}")
    print(f"  Stack breakdown  : {dashboard['stack_distribution']}")

    # --- Per-agent details ---
    print("\n--- Agent Details ---")
    for agent_data in dashboard["agents"]:
        score = agent_data["health_score"]
        icon = "🔴" if score < 30 else "🟡" if score <= 70 else "🟢"
        print(
            f"  {icon} {agent_data['id']:<30} "
            f"stack={agent_data['stack']:<12} "
            f"status={agent_data['status']:<10} "
            f"health={score:>5.1f}  "
            f"deploy={agent_data['deploy_target']}"
        )
        if agent_data["errors"]:
            print(f"     errors: {', '.join(agent_data['errors'])}")

    # --- Critical / At-risk detail ---
    if dashboard["critical_agents"]:
        print("\n--- Critical Agents (score < 30) ---")
        for a in dashboard["critical_agents"]:
            print(f"  🔴 {a['id']}: score={a['health_score']:.1f} errors={a['errors']}")

    if dashboard["at_risk_agents"]:
        print("\n--- At-Risk Agents (score 30-70) ---")
        for a in dashboard["at_risk_agents"]:
            print(f"  🟡 {a['id']}: score={a['health_score']:.1f} errors={a['errors']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
