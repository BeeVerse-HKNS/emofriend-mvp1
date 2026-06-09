from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

BRIDGE_FILENAME = ".harnessing-bridge.md"

VALID_INHERIT_LEVELS = {"MINIMAL", "STANDARD", "FULL"}

AVAILABLE_CONTEXT_AREAS = [
    "rules",
    "decisions",
    "errors",
    "kb",
    "skills",
    "progress",
    "preferences",
]

PROJECT_SYNC_POINTS = {
    "world-cup-2026": {
        "path": "projects/research/world-cup-2026/",
        "description": "World Cup 2026 數據分析同預測系統",
        "context_areas": ["kb", "decisions", "progress"],
        "dependencies": [],
    },
    "audit-platform": {
        "path": "projects/efficiency/audit-platform/",
        "description": "審計 SME 系統平台",
        "context_areas": ["rules", "kb", "progress"],
        "dependencies": ["world-cup-2026"],
    },
    "business-plan": {
        "path": "projects/docs/business-plan/",
        "description": "Business Case Proposal 同商業計劃",
        "context_areas": ["kb", "decisions", "preferences"],
        "dependencies": ["audit-platform"],
    },
}

_ESSENTIAL_TEMPLATE = (
    "[Harnessing Bridge] Master: {master_path}\n"
    "Project: {project_name} | Phase: {current_phase}\n"
    "Core: Agent=Model+Harness | OPC=OnePerson+AI+Harness\n"
    "Formula: log(S+P)+F\u00b2+(C^H) | 8-Layer Spiral | 7 Operators | P0-P3 Priority\n"
    "Rules: 63 rules active | Key: Knowledge-first, Zero-dep, Circular-thinking\n"
    "Progress: {progress_summary}\n"
    "Skills: /harness (rules) | /circularmind (memory+circular)"
)

_BRIDGE_FILE_TEMPLATE = """# Harnessing Bridge

## Configuration

- **master_path**: {master_path}
- **inherit_level**: {inherit_level}
- **focus_areas**: {focus_areas}
- **created_at**: {created_at}
- **last_sync**: {last_sync}

## Available Context Areas

- `rules` — 63 project rules from project_rules.md
- `decisions` — Decision log from data/decision-log.md
- `errors` — Error rules from data/error-rules.yaml
- `kb` — Knowledge base index from docs/knowledge-base/00-index.md
- `skills` — Skill definitions from skills/ directory
- `progress` — Current progress from AGENTS.md
- `preferences` — User preferences from MemoryEngine

## Usage

This bridge file connects this sub-folder to the Harnessing master folder.
The LLM session will automatically inherit context based on `inherit_level`:

- **MINIMAL** (~200 tokens): Project identity + core rules only
- **STANDARD** (~500 tokens): + current progress + key decisions
- **FULL** (~2000 tokens): + knowledge base index + error rules + user preferences

Use `get_on_demand_context(area)` to load specific context areas lazily.
"""


@dataclass
class BridgeConfig:
    master_path: str
    inherit_level: str = "STANDARD"
    focus_areas: list[str] = field(default_factory=lambda: ["rules", "progress"])
    created_at: str = ""
    last_sync: str = ""

    def __post_init__(self) -> None:
        if self.inherit_level not in VALID_INHERIT_LEVELS:
            self.inherit_level = "STANDARD"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.last_sync:
            self.last_sync = self.created_at

    def to_dict(self) -> dict:
        return {
            "master_path": self.master_path,
            "inherit_level": self.inherit_level,
            "focus_areas": list(self.focus_areas),
            "created_at": self.created_at,
            "last_sync": self.last_sync,
        }

    @classmethod
    def from_markdown(cls, content: str) -> Optional["BridgeConfig"]:
        return CrossFolderMemoryBridge._parse_bridge_content(content)


@dataclass
class BridgeValidationResult:
    is_valid: bool = False
    master_found: bool = False
    agents_md_found: bool = False
    bridge_file_found: bool = False
    issues: list[str] = field(default_factory=list)


@dataclass
class ProjectContext:
    project_id: str
    project_path: str
    last_accessed: str
    current_state: str
    context_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_path": self.project_path,
            "last_accessed": self.last_accessed,
            "current_state": self.current_state,
            "context_data": self.context_data,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectContext":
        return cls(
            project_id=data.get("project_id", ""),
            project_path=data.get("project_path", ""),
            last_accessed=data.get("last_accessed", ""),
            current_state=data.get("current_state", ""),
            context_data=data.get("context_data", {}),
        )


@dataclass
class SharedMemory:
    source_project: str
    target_project: str
    memory_type: str
    memory_key: str
    memory_value: str
    sync_timestamp: str

    def to_dict(self) -> dict:
        return {
            "source_project": self.source_project,
            "target_project": self.target_project,
            "memory_type": self.memory_type,
            "memory_key": self.memory_key,
            "memory_value": self.memory_value,
            "sync_timestamp": self.sync_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SharedMemory":
        return cls(
            source_project=data.get("source_project", ""),
            target_project=data.get("target_project", ""),
            memory_type=data.get("memory_type", ""),
            memory_key=data.get("memory_key", ""),
            memory_value=data.get("memory_value", ""),
            sync_timestamp=data.get("sync_timestamp", ""),
        )


@dataclass
class SyncTimestamp:
    project_id: str
    area: str
    last_sync: str
    checksum: str

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "area": self.area,
            "last_sync": self.last_sync,
            "checksum": self.checksum,
        }


class CrossFolderMemoryBridge:
    def __init__(self, current_dir: str, db_path: Optional[str] = None) -> None:
        self.current_dir = Path(current_dir).resolve()
        self._bridge_config: Optional[BridgeConfig] = None
        self._master_path: Optional[str] = None
        self._agents_md_cache: Optional[str] = None

        if db_path:
            self._db_path = Path(db_path)
        else:
            master = self.detect_master_folder()
            if master:
                self._db_path = Path(master) / "data" / "cross_folder_memory.db"
            else:
                self._db_path = self.current_dir / "data" / "cross_folder_memory.db"

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS project_contexts (
                        project_id TEXT PRIMARY KEY,
                        project_path TEXT NOT NULL,
                        last_accessed TEXT NOT NULL,
                        current_state TEXT NOT NULL,
                        context_data TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS shared_memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_project TEXT NOT NULL,
                        target_project TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        memory_key TEXT NOT NULL,
                        memory_value TEXT NOT NULL,
                        sync_timestamp TEXT NOT NULL,
                        UNIQUE(source_project, target_project, memory_type, memory_key)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sync_timestamps (
                        project_id TEXT NOT NULL,
                        area TEXT NOT NULL,
                        last_sync TEXT NOT NULL,
                        checksum TEXT NOT NULL,
                        PRIMARY KEY (project_id, area)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS project_dependencies (
                        source_project TEXT NOT NULL,
                        target_project TEXT NOT NULL,
                        dependency_type TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (source_project, target_project)
                    )
                """)
                conn.commit()
                logger.debug(f"SQLite database initialized at {self._db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            raise

    def detect_master_folder(self) -> Optional[str]:
        if self._master_path is not None:
            return self._master_path

        candidate = self.current_dir
        while True:
            agents_file = candidate / "AGENTS.md"
            if agents_file.is_file():
                content = self._read_file_safe(agents_file)
                if content and ("Harnessing" in content or "OPC" in content):
                    self._master_path = str(candidate)
                    return self._master_path

            parent = candidate.parent
            if parent == candidate:
                break
            candidate = parent

        self._master_path = None
        return None

    def load_bridge_file(self) -> Optional[BridgeConfig]:
        if self._bridge_config is not None:
            return self._bridge_config

        bridge_path = self.current_dir / BRIDGE_FILENAME
        content = self._read_file_safe(bridge_path)
        if not content:
            return None

        config = self._parse_bridge_content(content)
        if config:
            self._bridge_config = config
            if config.master_path:
                master = Path(config.master_path)
                if master.is_dir():
                    self._master_path = str(master)
        return config

    def create_bridge_file(self, master_path: str, level: str = "STANDARD") -> str:
        if level not in VALID_INHERIT_LEVELS:
            level = "STANDARD"

        now = datetime.now(timezone.utc).isoformat()
        config = BridgeConfig(
            master_path=master_path,
            inherit_level=level,
            focus_areas=["rules", "progress"],
            created_at=now,
            last_sync=now,
        )

        content = _BRIDGE_FILE_TEMPLATE.format(
            master_path=master_path,
            inherit_level=level,
            focus_areas="[" + ", ".join(config.focus_areas) + "]",
            created_at=now,
            last_sync=now,
        )

        bridge_path = self.current_dir / BRIDGE_FILENAME
        bridge_path.write_text(content, encoding="utf-8")

        self._bridge_config = config
        self._master_path = master_path
        return str(bridge_path)

    def inject_context(self, level: str | None = None) -> str:
        config = self.load_bridge_file()
        effective_level = level or (config.inherit_level if config else "STANDARD")
        if effective_level not in VALID_INHERIT_LEVELS:
            effective_level = "STANDARD"

        master = self._resolve_master()
        if not master:
            return ""

        if effective_level == "MINIMAL":
            return self.get_essential_context()
        elif effective_level == "STANDARD":
            essential = self.get_essential_context()
            decisions = self._load_decisions_summary()
            return f"{essential}\n\n{decisions}" if decisions else essential
        else:
            return self.get_full_context()

    def get_essential_context(self) -> str:
        master = self._resolve_master()
        if not master:
            return ""

        agents_content = self._load_agents_md()
        project_name = "Harnessing"
        current_phase = "Phase 1"
        progress_summary = "Knowledge base + Infrastructure + Self-governance complete"

        if agents_content:
            project_name = self._extract_project_name(agents_content)
            current_phase = self._extract_current_phase(agents_content)
            progress_summary = self._extract_progress_summary(agents_content)

        return _ESSENTIAL_TEMPLATE.format(
            master_path=master,
            project_name=project_name,
            current_phase=current_phase,
            progress_summary=progress_summary,
        )

    def get_full_context(self) -> str:
        master = self._resolve_master()
        if not master:
            return ""

        parts: list[str] = [self.get_essential_context()]

        decisions = self._load_decisions_summary()
        if decisions:
            parts.append(f"\n\n--- Decisions ---\n{decisions}")

        errors = self._load_error_rules()
        if errors:
            parts.append(f"\n\n--- Error Rules ---\n{errors}")

        kb_index = self._load_kb_index()
        if kb_index:
            parts.append(f"\n\n--- Knowledge Base Index ---\n{kb_index}")

        preferences = self._load_preferences()
        if preferences:
            parts.append(f"\n\n--- Preferences ---\n{preferences}")

        return "".join(parts)

    def get_on_demand_context(self, area: str) -> str:
        if area not in AVAILABLE_CONTEXT_AREAS:
            return ""

        master = self._resolve_master()
        if not master:
            return ""

        loaders = {
            "rules": self._load_rules,
            "decisions": self._load_decisions_summary,
            "errors": self._load_error_rules,
            "kb": self._load_kb_index,
            "skills": self._load_skills_summary,
            "progress": self._load_progress_detail,
            "preferences": self._load_preferences,
        }

        loader = loaders.get(area)
        if loader:
            return loader()
        return ""

    def list_available_contexts(self) -> list[str]:
        master = self._resolve_master()
        if not master:
            return []

        available: list[str] = []
        master_path = Path(master)

        context_files = {
            "rules": master_path / ".trae" / "rules" / "project_rules.md",
            "decisions": master_path / "data" / "decision-log.md",
            "errors": master_path / "data" / "error-rules.yaml",
            "kb": master_path / "docs" / "knowledge-base" / "00-index.md",
            "skills": master_path / "skills",
            "progress": master_path / "AGENTS.md",
            "preferences": None,
        }

        for area, path in context_files.items():
            if path is None:
                try:
                    from harnessing.core.memory_engine import MemoryEngine
                    available.append(area)
                except Exception:
                    pass
            elif path.exists():
                available.append(area)

        return available

    def validate_bridge(self) -> BridgeValidationResult:
        result = BridgeValidationResult()

        bridge_config = self.load_bridge_file()
        result.bridge_file_found = bridge_config is not None

        master = self._resolve_master()
        result.master_found = master is not None

        if master:
            agents_path = Path(master) / "AGENTS.md"
            result.agents_md_found = agents_path.is_file()
        else:
            result.agents_md_found = False

        issues: list[str] = []
        if not result.bridge_file_found and not result.master_found:
            issues.append("No bridge file found and auto-detection failed — no master folder")
        elif not result.bridge_file_found and result.master_found:
            issues.append("No bridge file — using auto-detected master folder")
        elif result.bridge_file_found and not result.master_found:
            issues.append("Bridge file exists but master_path is invalid or inaccessible")

        if result.master_found and not result.agents_md_found:
            issues.append("Master folder found but AGENTS.md is missing")

        if bridge_config and bridge_config.inherit_level not in VALID_INHERIT_LEVELS:
            issues.append(f"Invalid inherit_level: {bridge_config.inherit_level}")

        result.issues = issues
        result.is_valid = result.master_found and result.agents_md_found and len(issues) == 0

        return result

    def _resolve_master(self) -> Optional[str]:
        if self._master_path:
            return self._master_path

        config = self.load_bridge_file()
        if config and config.master_path:
            master = Path(config.master_path)
            if master.is_dir():
                self._master_path = str(master)
                return self._master_path

        return self.detect_master_folder()

    def _load_agents_md(self) -> Optional[str]:
        if self._agents_md_cache is not None:
            return self._agents_md_cache

        master = self._resolve_master()
        if not master:
            return None

        agents_path = Path(master) / "AGENTS.md"
        content = self._read_file_safe(agents_path)
        if content:
            self._agents_md_cache = content
        return content

    def _load_rules(self) -> str:
        master = self._resolve_master()
        if not master:
            return ""

        rules_path = Path(master) / ".trae" / "rules" / "project_rules.md"
        content = self._read_file_safe(rules_path)
        if not content:
            return ""

        lines = content.split("\n")
        rule_lines: list[str] = []
        for line in lines:
            if line.startswith("## ") and "Rule" not in line and "規則" not in line:
                break
            if line.startswith("## ") or line.startswith("- "):
                rule_lines.append(line)

        return "\n".join(rule_lines[:50])

    def _load_decisions_summary(self) -> str:
        master = self._resolve_master()
        if not master:
            return ""

        decisions_path = Path(master) / "data" / "decision-log.md"
        content = self._read_file_safe(decisions_path)
        if not content:
            return ""

        lines = content.split("\n")
        summary_lines: list[str] = []
        for line in lines:
            if line.startswith("| D-") or line.startswith("## "):
                summary_lines.append(line)
            if len(summary_lines) >= 20:
                break

        return "\n".join(summary_lines)

    def _load_error_rules(self) -> str:
        master = self._resolve_master()
        if not master:
            return ""

        errors_path = Path(master) / "data" / "error-rules.yaml"
        content = self._read_file_safe(errors_path)
        if not content:
            return ""

        lines = content.split("\n")
        return "\n".join(lines[:30])

    def _load_kb_index(self) -> str:
        master = self._resolve_master()
        if not master:
            return ""

        kb_path = Path(master) / "docs" / "knowledge-base" / "00-index.md"
        content = self._read_file_safe(kb_path)
        if not content:
            return ""

        lines = content.split("\n")
        return "\n".join(lines[:30])

    def _load_skills_summary(self) -> str:
        master = self._resolve_master()
        if not master:
            return ""

        skill_path = Path(master) / "skills" / "emoglyphplay" / "SKILL.md"
        content = self._read_file_safe(skill_path)
        if not content:
            return ""

        lines = content.split("\n")
        return "\n".join(lines[:30])

    def _load_progress_detail(self) -> str:
        content = self._load_agents_md()
        if not content:
            return ""

        in_progress = False
        progress_lines: list[str] = []
        for line in content.split("\n"):
            if "## 當前進度" in line or "## Current Progress" in line:
                in_progress = True
                progress_lines.append(line)
                continue
            if in_progress:
                if line.startswith("## ") and "進度" not in line and "Progress" not in line:
                    break
                progress_lines.append(line)
                if len(progress_lines) >= 40:
                    break

        return "\n".join(progress_lines)

    def _load_preferences(self) -> str:
        try:
            from harnessing.core.memory_engine import MemoryEngine

            engine = MemoryEngine()
            prefs = engine.get_preferences()
            engine.close()
            if not prefs:
                return ""
            lines = [f"- {k}: {v}" for k, v in prefs.items()]
            return "\n".join(lines[:20])
        except Exception:
            return ""

    def _extract_project_name(self, agents_content: str) -> str:
        for line in agents_content.split("\n"):
            if "**Harnessing**" in line:
                return "Harnessing"
            if "項目定位" in line or "Project" in line:
                continue
        return "Harnessing"

    def _extract_current_phase(self, agents_content: str) -> str:
        for line in agents_content.split("\n"):
            if "Phase 1" in line and ("✅" in line or "完成" in line):
                return "Phase 1 ✅"
            if "Phase 2" in line and ("🔄" in line or "進行" in line):
                return "Phase 2 🔄"
            if "Phase 3" in line and ("⏸️" in line or "暫停" in line):
                return "Phase 3 ⏸️"
        return "Phase 1"

    def _extract_progress_summary(self, agents_content: str) -> str:
        in_progress = False
        for line in agents_content.split("\n"):
            if "當前焦點" in line or "current focus" in line.lower():
                in_progress = True
                continue
            if in_progress and line.strip().startswith("- **"):
                clean = line.strip().lstrip("- ").strip("*")
                if len(clean) > 80:
                    clean = clean[:77] + "..."
                return clean
        return "Knowledge base + Infrastructure + Self-governance complete"

    @staticmethod
    def _read_file_safe(path: Path) -> Optional[str]:
        try:
            return path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, OSError):
            return None

    @staticmethod
    def _parse_bridge_content(content: str) -> Optional[BridgeConfig]:
        master_path = ""
        inherit_level = "STANDARD"
        focus_areas: list[str] = []
        created_at = ""
        last_sync = ""

        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("- **master_path**"):
                master_path = line.split(":", 1)[1].strip()
            elif line.startswith("- **inherit_level**"):
                inherit_level = line.split(":", 1)[1].strip()
            elif line.startswith("- **focus_areas**"):
                areas_str = line.split(":", 1)[1].strip()
                focus_areas = [
                    a.strip()
                    for a in re.findall(r"\w+", areas_str)
                ]
            elif line.startswith("- **created_at**"):
                created_at = line.split(":", 1)[1].strip()
            elif line.startswith("- **last_sync**"):
                last_sync = line.split(":", 1)[1].strip()

        if not master_path:
            return None

        return BridgeConfig(
            master_path=master_path,
            inherit_level=inherit_level,
            focus_areas=focus_areas,
            created_at=created_at,
            last_sync=last_sync,
        )

    def save_project_context(self, context: ProjectContext) -> bool:
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO project_contexts
                    (project_id, project_path, last_accessed, current_state, context_data)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    context.project_id,
                    context.project_path,
                    context.last_accessed,
                    context.current_state,
                    json.dumps(context.context_data),
                ))
                conn.commit()
                logger.debug(f"Saved project context for {context.project_id}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Failed to save project context: {e}")
            return False

    def load_project_context(self, project_id: str) -> Optional[ProjectContext]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT project_id, project_path, last_accessed, current_state, context_data
                    FROM project_contexts WHERE project_id = ?
                """, (project_id,))
                row = cursor.fetchone()
                if row:
                    return ProjectContext(
                        project_id=row[0],
                        project_path=row[1],
                        last_accessed=row[2],
                        current_state=row[3],
                        context_data=json.loads(row[4]) if row[4] else {},
                    )
                return None
        except sqlite3.Error as e:
            logger.error(f"Failed to load project context: {e}")
            return None

    def save_shared_memory(self, memory: SharedMemory) -> bool:
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO shared_memories
                    (source_project, target_project, memory_type, memory_key, memory_value, sync_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    memory.source_project,
                    memory.target_project,
                    memory.memory_type,
                    memory.memory_key,
                    memory.memory_value,
                    memory.sync_timestamp,
                ))
                conn.commit()
                logger.debug(f"Saved shared memory: {memory.source_project} -> {memory.target_project}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Failed to save shared memory: {e}")
            return False

    def load_shared_memories(self, target_project: str) -> list[SharedMemory]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT source_project, target_project, memory_type, memory_key, memory_value, sync_timestamp
                    FROM shared_memories WHERE target_project = ?
                """, (target_project,))
                rows = cursor.fetchall()
                return [
                    SharedMemory(
                        source_project=row[0],
                        target_project=row[1],
                        memory_type=row[2],
                        memory_key=row[3],
                        memory_value=row[4],
                        sync_timestamp=row[5],
                    )
                    for row in rows
                ]
        except sqlite3.Error as e:
            logger.error(f"Failed to load shared memories: {e}")
            return []

    def save_sync_timestamp(self, sync: SyncTimestamp) -> bool:
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO sync_timestamps
                    (project_id, area, last_sync, checksum)
                    VALUES (?, ?, ?, ?)
                """, (sync.project_id, sync.area, sync.last_sync, sync.checksum))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Failed to save sync timestamp: {e}")
            return False

    def load_sync_timestamp(self, project_id: str, area: str) -> Optional[SyncTimestamp]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT project_id, area, last_sync, checksum
                    FROM sync_timestamps WHERE project_id = ? AND area = ?
                """, (project_id, area))
                row = cursor.fetchone()
                if row:
                    return SyncTimestamp(
                        project_id=row[0],
                        area=row[1],
                        last_sync=row[2],
                        checksum=row[3],
                    )
                return None
        except sqlite3.Error as e:
            logger.error(f"Failed to load sync timestamp: {e}")
            return None

    def recover_context_for_project(self, project_id: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "project_id": project_id,
            "project_context": None,
            "shared_memories": [],
            "dependencies": [],
            "sync_status": {},
        }

        project_context = self.load_project_context(project_id)
        result["project_context"] = project_context.to_dict() if project_context else None

        shared_memories = self.load_shared_memories(project_id)
        result["shared_memories"] = [m.to_dict() for m in shared_memories]

        if project_id in PROJECT_SYNC_POINTS:
            config = PROJECT_SYNC_POINTS[project_id]
            result["dependencies"] = config.get("dependencies", [])

            for area in config.get("context_areas", []):
                sync_ts = self.load_sync_timestamp(project_id, area)
                result["sync_status"][area] = sync_ts.to_dict() if sync_ts else None

        logger.info(f"Recovered context for project: {project_id}")
        return result

    def sync_project_to_project(self, source_id: str, target_id: str, areas: Optional[list[str]] = None) -> bool:
        if source_id not in PROJECT_SYNC_POINTS or target_id not in PROJECT_SYNC_POINTS:
            logger.warning(f"Invalid project IDs for sync: {source_id} -> {target_id}")
            return False

        source_config = PROJECT_SYNC_POINTS[source_id]
        target_config = PROJECT_SYNC_POINTS[target_id]

        if areas is None:
            areas = list(set(source_config.get("context_areas", [])) & set(target_config.get("context_areas", [])))

        master = self._resolve_master()
        if not master:
            logger.error("No master folder found for sync")
            return False

        now = datetime.now(timezone.utc).isoformat()
        success = True

        for area in areas:
            context_value = self.get_on_demand_context(area)
            if not context_value:
                continue

            memory = SharedMemory(
                source_project=source_id,
                target_project=target_id,
                memory_type=area,
                memory_key=f"{source_id}:{area}",
                memory_value=context_value[:10000],
                sync_timestamp=now,
            )

            if not self.save_shared_memory(memory):
                success = False
                continue

            import hashlib
            checksum = hashlib.md5(context_value.encode()).hexdigest()
            sync_ts = SyncTimestamp(
                project_id=target_id,
                area=area,
                last_sync=now,
                checksum=checksum,
            )
            self.save_sync_timestamp(sync_ts)

        logger.info(f"Synced {source_id} -> {target_id} for areas: {areas}")
        return success

    def initialize_project_sync_points(self) -> dict[str, bool]:
        results: dict[str, bool] = {}
        master = self._resolve_master()

        for project_id, config in PROJECT_SYNC_POINTS.items():
            if not master:
                results[project_id] = False
                continue

            project_path = Path(master) / config["path"]
            now = datetime.now(timezone.utc).isoformat()

            context = ProjectContext(
                project_id=project_id,
                project_path=str(project_path),
                last_accessed=now,
                current_state="initialized",
                context_data={"description": config.get("description", "")},
            )

            results[project_id] = self.save_project_context(context)

            if results[project_id]:
                for dep_id in config.get("dependencies", []):
                    self.sync_project_to_project(dep_id, project_id)

        logger.info(f"Initialized {len(results)} project sync points")
        return results

    def get_all_project_contexts(self) -> list[ProjectContext]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT project_id, project_path, last_accessed, current_state, context_data
                    FROM project_contexts
                """)
                rows = cursor.fetchall()
                return [
                    ProjectContext(
                        project_id=row[0],
                        project_path=row[1],
                        last_accessed=row[2],
                        current_state=row[3],
                        context_data=json.loads(row[4]) if row[4] else {},
                    )
                    for row in rows
                ]
        except sqlite3.Error as e:
            logger.error(f"Failed to get all project contexts: {e}")
            return []

    def close(self) -> None:
        pass
