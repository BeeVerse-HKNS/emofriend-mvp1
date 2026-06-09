from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from harnessing.core.memory_engine import MemoryEngine

logger = structlog.get_logger()


class ChangeType(Enum):
    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"


class SyncType(Enum):
    INCREMENTAL = "incremental"
    FULL_REBUILD = "full_rebuild"
    NONE = "none"


@dataclass
class Change:
    change_type: ChangeType
    source: str
    target: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rule_id: int | None = None
    section: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_type": self.change_type.value,
            "source": self.source,
            "target": self.target,
            "content": self.content,
            "timestamp": self.timestamp,
            "rule_id": self.rule_id,
            "section": self.section,
        }


@dataclass
class SyncResult:
    success: bool
    changes_count: int
    sync_type: SyncType
    duration_seconds: float
    errors: list[str] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "changes_count": self.changes_count,
            "sync_type": self.sync_type.value,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "changes": [c.to_dict() for c in self.changes],
        }


@dataclass
class SyncStatus:
    last_sync_time: str
    last_sync_type: SyncType
    pending_changes: int
    consistency_percent: float
    last_sync_success: bool
    total_syncs: int
    failed_syncs: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_sync_time": self.last_sync_time,
            "last_sync_type": self.last_sync_type.value,
            "pending_changes": self.pending_changes,
            "consistency_percent": self.consistency_percent,
            "last_sync_success": self.last_sync_success,
            "total_syncs": self.total_syncs,
            "failed_syncs": self.failed_syncs,
        }


_CREATE_SYNC_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS sync_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_sync_time TEXT NOT NULL,
    last_sync_type TEXT NOT NULL,
    pending_changes INTEGER NOT NULL DEFAULT 0,
    consistency_percent REAL NOT NULL DEFAULT 100.0,
    last_sync_success INTEGER NOT NULL DEFAULT 1,
    total_syncs INTEGER NOT NULL DEFAULT 0,
    failed_syncs INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    sync_type TEXT NOT NULL,
    success INTEGER NOT NULL,
    changes_count INTEGER NOT NULL,
    duration_seconds REAL NOT NULL,
    errors_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS rule_hashes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    UNIQUE(rule_type, rule_id)
);
"""


class ChangeDetector:
    def __init__(
        self,
        project_root: Path,
        modelfile_path: Path,
        memory_engine: MemoryEngine,
    ) -> None:
        self.project_root = project_root
        self.modelfile_path = modelfile_path
        self.memory_engine = memory_engine
        self._conn = sqlite3.connect(str(project_root / "data" / "sync_state.db"))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_CREATE_SYNC_TABLES_SQL)

    def detect_all_changes(self) -> list[Change]:
        changes: list[Change] = []
        changes.extend(self._detect_rules_changes())
        changes.extend(self._detect_error_rules_changes())
        changes.extend(self._detect_knowledge_base_changes())
        return changes

    def _detect_rules_changes(self) -> list[Change]:
        changes: list[Change] = []
        project_rules_path = self.project_root / ".trae" / "rules" / "project_rules.md"
        if not project_rules_path.exists():
            return changes

        project_rules_content = project_rules_path.read_text(encoding="utf-8")
        project_rules = self._parse_project_rules(project_rules_content)
        modelfile_rules = self._parse_modelfile_rules()

        for rule_id, rule_content in project_rules.items():
            content_hash = hashlib.sha256(rule_content.encode()).hexdigest()
            stored_hash = self._get_stored_hash("project_rule", rule_id)

            if stored_hash is None:
                changes.append(Change(
                    change_type=ChangeType.NEW,
                    source="project_rules.md",
                    target="Modelfile",
                    content=rule_content[:200],
                    rule_id=None,
                    section="RULES",
                ))
            elif stored_hash != content_hash:
                changes.append(Change(
                    change_type=ChangeType.MODIFIED,
                    source="project_rules.md",
                    target="Modelfile",
                    content=rule_content[:200],
                    rule_id=None,
                    section="RULES",
                ))

        for rule_id in modelfile_rules:
            if rule_id not in project_rules:
                changes.append(Change(
                    change_type=ChangeType.DELETED,
                    source="Modelfile",
                    target="project_rules.md",
                    content=modelfile_rules[rule_id][:200],
                    rule_id=None,
                    section="RULES",
                ))

        return changes

    def _detect_error_rules_changes(self) -> list[Change]:
        changes: list[Change] = []
        db_rules = self.memory_engine.get_rules()
        modelfile_error_rules = self._parse_modelfile_error_rules()

        db_rule_ids = {f"R-ERR-{r['id']:03d}": r for r in db_rules}

        for rule_id, rule_data in db_rule_ids.items():
            content_hash = hashlib.sha256(
                f"{rule_data['error_desc']}:{rule_data['rule_text']}".encode()
            ).hexdigest()
            stored_hash = self._get_stored_hash("error_rule", rule_id)

            if stored_hash is None:
                changes.append(Change(
                    change_type=ChangeType.NEW,
                    source="SQLite error_rules",
                    target="Modelfile",
                    content=rule_data["rule_text"][:200],
                    rule_id=rule_data["id"],
                    section="ERROR RULES",
                ))
            elif stored_hash != content_hash:
                changes.append(Change(
                    change_type=ChangeType.MODIFIED,
                    source="SQLite error_rules",
                    target="Modelfile",
                    content=rule_data["rule_text"][:200],
                    rule_id=rule_data["id"],
                    section="ERROR RULES",
                ))

        for rule_id in modelfile_error_rules:
            if rule_id not in db_rule_ids:
                changes.append(Change(
                    change_type=ChangeType.DELETED,
                    source="Modelfile",
                    target="SQLite error_rules",
                    content=modelfile_error_rules[rule_id][:200],
                    rule_id=None,
                    section="ERROR RULES",
                ))

        return changes

    def _detect_knowledge_base_changes(self) -> list[Change]:
        changes: list[Change] = []
        kb_path = self.project_root / "docs" / "knowledge-base"
        if not kb_path.exists():
            return changes

        kb_files = list(kb_path.glob("*.md"))
        modelfile_kb = self._parse_modelfile_knowledge_base()

        current_kb = {}
        for kb_file in kb_files:
            content = kb_file.read_text(encoding="utf-8")
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            current_kb[kb_file.name] = content_hash

        for kb_name, content_hash in current_kb.items():
            stored_hash = self._get_stored_hash("knowledge_base", kb_name)

            if stored_hash is None:
                changes.append(Change(
                    change_type=ChangeType.NEW,
                    source="docs/knowledge-base/",
                    target="Modelfile",
                    content=f"KB file: {kb_name}",
                    rule_id=None,
                    section="KNOWLEDGE BASE",
                ))
            elif stored_hash != content_hash:
                changes.append(Change(
                    change_type=ChangeType.MODIFIED,
                    source="docs/knowledge-base/",
                    target="Modelfile",
                    content=f"KB file: {kb_name}",
                    rule_id=None,
                    section="KNOWLEDGE BASE",
                ))

        for kb_name in modelfile_kb:
            if kb_name not in current_kb:
                changes.append(Change(
                    change_type=ChangeType.DELETED,
                    source="Modelfile",
                    target="docs/knowledge-base/",
                    content=f"KB file: {kb_name}",
                    rule_id=None,
                    section="KNOWLEDGE BASE",
                ))

        return changes

    def _parse_project_rules(self, content: str) -> dict[str, str]:
        rules: dict[str, str] = {}
        pattern = r"##\s*(\d+)\.\s*(.+?)(?=##\s*\d+\.|$)"
        matches = re.findall(pattern, content, re.DOTALL)
        for rule_num, rule_content in matches:
            rules[f"R{rule_num}"] = rule_content.strip()
        return rules

    def _parse_modelfile_rules(self) -> dict[str, str]:
        if not self.modelfile_path.exists():
            return {}
        content = self.modelfile_path.read_text(encoding="utf-8")
        rules: dict[str, str] = {}
        rules_section = re.search(r"=== RULES.*?===", content, re.DOTALL)
        if not rules_section:
            return rules
        rules_content = rules_section.group(0)
        pattern = r"(\d+)\.\s*(.+?)(?=\n\d+\.|$)"
        matches = re.findall(pattern, rules_content, re.DOTALL)
        for rule_num, rule_content in matches:
            rules[f"R{rule_num}"] = rule_content.strip()
        return rules

    def _parse_modelfile_error_rules(self) -> dict[str, str]:
        if not self.modelfile_path.exists():
            return {}
        content = self.modelfile_path.read_text(encoding="utf-8")
        rules: dict[str, str] = {}
        error_section = re.search(r"=== ERROR RULES.*?===", content, re.DOTALL)
        if not error_section:
            return rules
        error_content = error_section.group(0)
        pattern = r"(R-ERR-\d+).*?(?=R-ERR-\d+|$)"
        matches = re.findall(pattern, error_content, re.DOTALL)
        for match in matches:
            rule_id = match.strip().split(":")[0] if ":" in match else match.strip()
            rules[rule_id] = match.strip()
        return rules

    def _parse_modelfile_knowledge_base(self) -> dict[str, str]:
        if not self.modelfile_path.exists():
            return {}
        content = self.modelfile_path.read_text(encoding="utf-8")
        kb_section = re.search(r"=== KNOWLEDGE BASE.*?===", content, re.DOTALL)
        if not kb_section:
            return {}
        kb_content = kb_section.group(0)
        kb_files: dict[str, str] = {}
        pattern = r"(\d+-[^.]+\.md)"
        matches = re.findall(pattern, kb_content)
        for match in matches:
            kb_files[match] = match
        return kb_files

    def _get_stored_hash(self, rule_type: str, rule_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT content_hash FROM rule_hashes WHERE rule_type = ? AND rule_id = ?",
            (rule_type, rule_id),
        ).fetchone()
        return row["content_hash"] if row else None

    def update_hash(self, rule_type: str, rule_id: str, content_hash: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT OR REPLACE INTO rule_hashes (rule_type, rule_id, content_hash, timestamp)
               VALUES (?, ?, ?, ?)""",
            (rule_type, rule_id, content_hash, now),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


class IncrementalSyncer:
    INCREMENTAL_THRESHOLD = 0.10

    def __init__(
        self,
        project_root: Path,
        modelfile_path: Path,
        modelfile_full_path: Path,
        change_detector: ChangeDetector,
    ) -> None:
        self.project_root = project_root
        self.modelfile_path = modelfile_path
        self.modelfile_full_path = modelfile_full_path
        self.change_detector = change_detector

    def sync(self, changes: list[Change]) -> SyncResult:
        start_time = datetime.now(timezone.utc)

        if not changes:
            return SyncResult(
                success=True,
                changes_count=0,
                sync_type=SyncType.NONE,
                duration_seconds=0.0,
                errors=[],
                changes=[],
            )

        total_items = self._count_total_items()
        change_ratio = len(changes) / max(total_items, 1)

        if change_ratio >= self.INCREMENTAL_THRESHOLD:
            return self._full_rebuild(changes, start_time)
        else:
            return self._incremental_update(changes, start_time)

    def _count_total_items(self) -> int:
        count = 0
        project_rules_path = self.project_root / ".trae" / "rules" / "project_rules.md"
        if project_rules_path.exists():
            content = project_rules_path.read_text(encoding="utf-8")
            count += len(re.findall(r"##\s*\d+\.", content))

        kb_path = self.project_root / "docs" / "knowledge-base"
        if kb_path.exists():
            count += len(list(kb_path.glob("*.md")))

        count += 50
        return count

    def _incremental_update(self, changes: list[Change], start_time: datetime) -> SyncResult:
        errors: list[str] = []

        try:
            modelfile_content = self.modelfile_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            errors.append(f"Modelfile not found: {self.modelfile_path}")
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            return SyncResult(
                success=False,
                changes_count=len(changes),
                sync_type=SyncType.INCREMENTAL,
                duration_seconds=duration,
                errors=errors,
                changes=changes,
            )

        updated_content = modelfile_content

        for change in changes:
            if change.section == "RULES":
                updated_content = self._update_rules_section(updated_content, change)
            elif change.section == "ERROR RULES":
                updated_content = self._update_error_rules_section(updated_content, change)
            elif change.section == "KNOWLEDGE BASE":
                updated_content = self._update_knowledge_base_section(updated_content, change)

        self.modelfile_path.write_text(updated_content, encoding="utf-8")
        self._update_hashes(changes)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        return SyncResult(
            success=len(errors) == 0,
            changes_count=len(changes),
            sync_type=SyncType.INCREMENTAL,
            duration_seconds=duration,
            errors=errors,
            changes=changes,
        )

    def _full_rebuild(self, changes: list[Change], start_time: datetime) -> SyncResult:
        errors: list[str] = []

        try:
            if self.modelfile_full_path.exists():
                source_content = self.modelfile_full_path.read_text(encoding="utf-8")
            else:
                source_content = self.modelfile_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            errors.append(f"Modelfile not found")
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            return SyncResult(
                success=False,
                changes_count=len(changes),
                sync_type=SyncType.FULL_REBUILD,
                duration_seconds=duration,
                errors=errors,
                changes=changes,
            )

        rebuilt_content = self._rebuild_modelfile(source_content, changes)
        self.modelfile_path.write_text(rebuilt_content, encoding="utf-8")

        rebuild_success = self._run_ollama_create()
        if not rebuild_success:
            errors.append("ollama create beeverse failed")

        self._update_hashes(changes)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        return SyncResult(
            success=len(errors) == 0,
            changes_count=len(changes),
            sync_type=SyncType.FULL_REBUILD,
            duration_seconds=duration,
            errors=errors,
            changes=changes,
        )

    def _update_rules_section(self, content: str, change: Change) -> str:
        return content

    def _update_error_rules_section(self, content: str, change: Change) -> str:
        return content

    def _update_knowledge_base_section(self, content: str, change: Change) -> str:
        return content

    def _rebuild_modelfile(self, source_content: str, changes: list[Change]) -> str:
        return source_content

    def _run_ollama_create(self) -> bool:
        try:
            result = subprocess.run(
                ["ollama", "create", "beeverse", "-f", str(self.modelfile_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error("ollama_create_failed", error=str(e))
            return False

    def _update_hashes(self, changes: list[Change]) -> None:
        for change in changes:
            content_hash = hashlib.sha256(change.content.encode()).hexdigest()
            rule_type = change.section.lower().replace(" ", "_")
            rule_id = change.source
            self.change_detector.update_hash(rule_type, rule_id, content_hash)


class AutoRebuildTrigger:
    DEFAULT_NEW_RULES_THRESHOLD = 5
    DEFAULT_MODIFIED_RULES_THRESHOLD = 10
    DEFAULT_DAYS_SINCE_REBUILD_THRESHOLD = 7

    def __init__(
        self,
        project_root: Path,
        memory_engine: MemoryEngine,
        new_rules_threshold: int = DEFAULT_NEW_RULES_THRESHOLD,
        modified_rules_threshold: int = DEFAULT_MODIFIED_RULES_THRESHOLD,
        days_since_rebuild_threshold: int = DEFAULT_DAYS_SINCE_REBUILD_THRESHOLD,
    ) -> None:
        self.project_root = project_root
        self.memory_engine = memory_engine
        self.new_rules_threshold = new_rules_threshold
        self.modified_rules_threshold = modified_rules_threshold
        self.days_since_rebuild_threshold = days_since_rebuild_threshold
        self._conn = sqlite3.connect(str(project_root / "data" / "sync_state.db"))
        self._conn.row_factory = sqlite3.Row

    def should_trigger_rebuild(self, changes: list[Change]) -> tuple[bool, str]:
        new_rules_count = sum(1 for c in changes if c.change_type == ChangeType.NEW)
        modified_rules_count = sum(1 for c in changes if c.change_type == ChangeType.MODIFIED)

        if new_rules_count >= self.new_rules_threshold:
            return True, f"New rules ({new_rules_count}) >= threshold ({self.new_rules_threshold})"

        if modified_rules_count >= self.modified_rules_threshold:
            return True, f"Modified rules ({modified_rules_count}) >= threshold ({self.modified_rules_threshold})"

        days_since = self._get_days_since_last_rebuild()
        if days_since >= self.days_since_rebuild_threshold:
            return True, f"Days since last rebuild ({days_since}) >= threshold ({self.days_since_rebuild_threshold})"

        return False, "No rebuild trigger conditions met"

    def _get_days_since_last_rebuild(self) -> int:
        row = self._conn.execute(
            """SELECT timestamp FROM sync_history
               WHERE sync_type = 'full_rebuild' AND success = 1
               ORDER BY timestamp DESC LIMIT 1"""
        ).fetchone()

        if not row:
            return 999

        last_rebuild = datetime.fromisoformat(row["timestamp"])
        now = datetime.now(timezone.utc)
        return (now - last_rebuild).days

    def close(self) -> None:
        self._conn.close()


class SyncStatusTracker:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        db_path = project_root / "data" / "sync_state.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_CREATE_SYNC_TABLES_SQL)
        self._ensure_initial_status()

    def _ensure_initial_status(self) -> None:
        row = self._conn.execute("SELECT id FROM sync_status WHERE id = 1").fetchone()
        if not row:
            now = datetime.now(timezone.utc).isoformat()
            self._conn.execute(
                """INSERT INTO sync_status
                   (id, last_sync_time, last_sync_type, pending_changes, consistency_percent,
                    last_sync_success, total_syncs, failed_syncs)
                   VALUES (1, ?, 'none', 0, 100.0, 1, 0, 0)""",
                (now,),
            )
            self._conn.commit()

    def get_status(self) -> SyncStatus:
        row = self._conn.execute("SELECT * FROM sync_status WHERE id = 1").fetchone()
        return SyncStatus(
            last_sync_time=row["last_sync_time"],
            last_sync_type=SyncType(row["last_sync_type"]),
            pending_changes=row["pending_changes"],
            consistency_percent=row["consistency_percent"],
            last_sync_success=bool(row["last_sync_success"]),
            total_syncs=row["total_syncs"],
            failed_syncs=row["failed_syncs"],
        )

    def update_status(self, result: SyncResult, pending_changes: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        consistency = 100.0 - (len(result.errors) * 5.0)

        self._conn.execute(
            """UPDATE sync_status SET
               last_sync_time = ?,
               last_sync_type = ?,
               pending_changes = ?,
               consistency_percent = ?,
               last_sync_success = ?,
               total_syncs = total_syncs + 1,
               failed_syncs = failed_syncs + ?
               WHERE id = 1""",
            (
                now,
                result.sync_type.value,
                pending_changes,
                max(0.0, min(100.0, consistency)),
                1 if result.success else 0,
                0 if result.success else 1,
            ),
        )

        self._conn.execute(
            """INSERT INTO sync_history
               (timestamp, sync_type, success, changes_count, duration_seconds, errors_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                now,
                result.sync_type.value,
                1 if result.success else 0,
                result.changes_count,
                result.duration_seconds,
                json.dumps(result.errors, ensure_ascii=False),
            ),
        )

        self._conn.commit()

    def set_pending_changes(self, count: int) -> None:
        self._conn.execute(
            "UPDATE sync_status SET pending_changes = ? WHERE id = 1",
            (count,),
        )
        self._conn.commit()

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT * FROM sync_history ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def generate_report(self) -> str:
        status = self.get_status()
        history = self.get_history(5)

        lines = [
            "# BeeVerse Ollama Sync Status Report",
            "",
            "## Current Status",
            f"- Last Sync Time: {status.last_sync_time}",
            f"- Last Sync Type: {status.last_sync_type.value}",
            f"- Pending Changes: {status.pending_changes}",
            f"- Consistency: {status.consistency_percent:.1f}%",
            f"- Last Sync Success: {'✅' if status.last_sync_success else '❌'}",
            f"- Total Syncs: {status.total_syncs}",
            f"- Failed Syncs: {status.failed_syncs}",
            "",
            "## Recent Sync History",
        ]

        for h in history:
            success_icon = "✅" if h["success"] else "❌"
            lines.append(
                f"- {h['timestamp']}: {h['sync_type']} ({success_icon}) - "
                f"{h['changes_count']} changes in {h['duration_seconds']:.2f}s"
            )

        return "\n".join(lines)

    def close(self) -> None:
        self._conn.close()


class BeeVerseOllamaSyncEngine:
    def __init__(
        self,
        project_root: str | Path | None = None,
        modelfile_path: str | Path | None = None,
        modelfile_full_path: str | Path | None = None,
        memory_engine: MemoryEngine | None = None,
    ) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.modelfile_path = (
            Path(modelfile_path)
            if modelfile_path
            else self.project_root / "config" / "Modelfile"
        )
        self.modelfile_full_path = (
            Path(modelfile_full_path)
            if modelfile_full_path
            else self.project_root / "config" / "Modelfile.full"
        )

        self.memory_engine = memory_engine or MemoryEngine()

        self.status_tracker = SyncStatusTracker(self.project_root)
        self.change_detector = ChangeDetector(
            self.project_root,
            self.modelfile_path,
            self.memory_engine,
        )
        self.incremental_syncer = IncrementalSyncer(
            self.project_root,
            self.modelfile_path,
            self.modelfile_full_path,
            self.change_detector,
        )
        self.auto_rebuild_trigger = AutoRebuildTrigger(
            self.project_root,
            self.memory_engine,
        )

        logger.info(
            "beeverse_sync_engine_initialized",
            project_root=str(self.project_root),
            modelfile=str(self.modelfile_path),
        )

    def detect_changes(self) -> list[Change]:
        changes = self.change_detector.detect_all_changes()
        self.status_tracker.set_pending_changes(len(changes))
        logger.info("changes_detected", count=len(changes))
        return changes

    def sync(self, force_full_rebuild: bool = False) -> SyncResult:
        changes = self.detect_changes()

        if force_full_rebuild:
            result = self.incremental_syncer._full_rebuild(
                changes,
                datetime.now(timezone.utc),
            )
        else:
            should_rebuild, reason = self.auto_rebuild_trigger.should_trigger_rebuild(changes)
            if should_rebuild:
                logger.info("auto_rebuild_triggered", reason=reason)
                result = self.incremental_syncer._full_rebuild(
                    changes,
                    datetime.now(timezone.utc),
                )
            else:
                result = self.incremental_syncer.sync(changes)

        remaining_changes = self.change_detector.detect_all_changes()
        self.status_tracker.update_status(result, len(remaining_changes))

        logger.info(
            "sync_completed",
            success=result.success,
            sync_type=result.sync_type.value,
            changes_count=result.changes_count,
            duration=result.duration_seconds,
        )

        return result

    def get_status(self) -> SyncStatus:
        return self.status_tracker.get_status()

    def get_status_report(self) -> str:
        return self.status_tracker.generate_report()

    def verify_model_availability(self) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return False, f"ollama list failed: {result.stderr}"

            if "beeverse" in result.stdout:
                return True, "beeverse model is available"
            else:
                return False, "beeverse model not found in ollama list"

        except subprocess.TimeoutExpired:
            return False, "ollama list timed out"
        except FileNotFoundError:
            return False, "ollama command not found"

    def close(self) -> None:
        self.change_detector.close()
        self.auto_rebuild_trigger.close()
        self.status_tracker.close()
        self.memory_engine.close()
        logger.info("beeverse_sync_engine_closed")
