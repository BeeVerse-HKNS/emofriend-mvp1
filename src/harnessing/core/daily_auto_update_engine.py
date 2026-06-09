from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
import yaml

from harnessing.core.beeverse_ollama_sync_engine import BeeVerseOllamaSyncEngine, SyncResult, SyncType

logger = structlog.get_logger()


class FreshnessStatus(Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    OUTDATED = "OUTDATED"


@dataclass
class FileInfo:
    path: Path
    mtime: datetime
    age_days: float
    status: FreshnessStatus
    size_kb: float = 0.0


@dataclass
class UpdateAction:
    action_type: str
    target_path: Path
    description: str
    executed: bool = False
    success: bool = False
    error: str | None = None


@dataclass
class BeeVerseSyncInfo:
    enabled: bool = False
    sync_executed: bool = False
    sync_success: bool = False
    sync_type: str = "none"
    changes_count: int = 0
    sync_duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


@dataclass
class UpdateReport:
    timestamp: str
    files_scanned: int
    files_fresh: int
    files_stale: int
    files_outdated: int
    actions_executed: list[UpdateAction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    beeverse_sync: BeeVerseSyncInfo = field(default_factory=BeeVerseSyncInfo)


class FileFreshnessDetector:
    def __init__(
        self,
        fresh_threshold_days: float = 7.0,
        stale_threshold_days: float = 30.0,
    ) -> None:
        self.fresh_threshold = fresh_threshold_days
        self.stale_threshold = stale_threshold_days

    def get_file_info(self, path: Path) -> FileInfo | None:
        if not path.exists():
            return None
        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime)
        age = datetime.now() - mtime
        age_days = age.total_seconds() / 86400.0
        if age_days < self.fresh_threshold:
            status = FreshnessStatus.FRESH
        elif age_days < self.stale_threshold:
            status = FreshnessStatus.STALE
        else:
            status = FreshnessStatus.OUTDATED
        return FileInfo(
            path=path,
            mtime=mtime,
            age_days=age_days,
            status=status,
            size_kb=stat.st_size / 1024.0,
        )

    def scan_directory(
        self,
        directory: Path,
        pattern: str = "*.md",
        exclude_patterns: list[str] | None = None,
    ) -> list[FileInfo]:
        exclude_patterns = exclude_patterns or []
        results: list[FileInfo] = []
        for file_path in directory.rglob(pattern):
            skip = False
            for excl in exclude_patterns:
                if excl in str(file_path):
                    skip = True
                    break
            if skip:
                continue
            info = self.get_file_info(file_path)
            if info:
                results.append(info)
        return results

    def get_status_distribution(
        self, files: list[FileInfo]
    ) -> dict[FreshnessStatus, int]:
        dist = {s: 0 for s in FreshnessStatus}
        for f in files:
            dist[f.status] += 1
        return dist


class ContentUpdater:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.projects_dir = project_root / "projects"
        self.kb_dir = project_root / "docs" / "knowledge-base"
        self.skills_dir = project_root / "skills"

    def update_agents_md_subproject_index(self) -> UpdateAction:
        agents_path = self.project_root / "AGENTS.md"
        action = UpdateAction(
            action_type="update_agents_index",
            target_path=agents_path,
            description="Update subproject index in AGENTS.md",
        )
        try:
            if not agents_path.exists():
                action.error = "AGENTS.md not found"
                return action
            content = agents_path.read_text(encoding="utf-8")
            projects = self._scan_projects()
            index_table = self._generate_project_table(projects)
            pattern = r"(## 子項目索引\s*\n\s*> 自動掃描.*?\n\n)(\|.*?\n)(\*\*統計\*\*.*?\n)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                new_content = (
                    content[: match.start(2)]
                    + index_table
                    + content[match.end(2) :]
                )
            else:
                action.error = "Could not find subproject index section"
                return action
            agents_path.write_text(new_content, encoding="utf-8")
            action.executed = True
            action.success = True
        except Exception as e:
            action.error = str(e)
        return action

    def update_agents_md_daily_summary(self, summary: dict[str, Any]) -> UpdateAction:
        agents_path = self.project_root / "AGENTS.md"
        action = UpdateAction(
            action_type="update_daily_summary",
            target_path=agents_path,
            description="Update daily summary section in AGENTS.md",
        )
        try:
            if not agents_path.exists():
                action.error = "AGENTS.md not found"
                return action
            content = agents_path.read_text(encoding="utf-8")
            today_str = datetime.now().strftime("%Y-%m-%d")
            summary_block = self._generate_summary_block(summary, today_str)
            pattern = r"(<!-- AUTO-GENERATED: daily-summary\.py -->)(.*?)(<!-- END AUTO-GENERATED -->)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                new_content = (
                    content[: match.start(2)]
                    + "\n"
                    + summary_block
                    + "\n"
                    + content[match.end(2) :]
                )
            else:
                action.error = "Could not find daily summary markers"
                return action
            agents_path.write_text(new_content, encoding="utf-8")
            action.executed = True
            action.success = True
        except Exception as e:
            action.error = str(e)
        return action

    def sync_skill_md(self) -> UpdateAction:
        skill_path = self.skills_dir / "emoglyphplay" / "SKILL.md"
        action = UpdateAction(
            action_type="sync_skill_md",
            target_path=skill_path,
            description="Verify SKILL.md consistency with project_rules.md",
        )
        try:
            if not skill_path.exists():
                action.error = "SKILL.md not found"
                return action
            project_rules_path = self.project_root / ".trae" / "rules" / "project_rules.md"
            if not project_rules_path.exists():
                action.error = "project_rules.md not found"
                return action
            skill_content = skill_path.read_text(encoding="utf-8")
            rules_content = project_rules_path.read_text(encoding="utf-8")
            skill_rule_count = len(re.findall(r"^##\s*規則\s*\d+", skill_content, re.MULTILINE))
            rules_rule_count = len(re.findall(r"^##\s*\d+\.", rules_content, re.MULTILINE))
            if skill_rule_count != rules_rule_count:
                action.error = f"Rule count mismatch: SKILL.md={skill_rule_count}, project_rules.md={rules_rule_count}"
                return action
            action.executed = True
            action.success = True
        except Exception as e:
            action.error = str(e)
        return action

    def update_kb_index(self) -> UpdateAction:
        index_path = self.kb_dir / "00-index.md"
        action = UpdateAction(
            action_type="update_kb_index",
            target_path=index_path,
            description="Update knowledge base index",
        )
        try:
            if not self.kb_dir.exists():
                action.error = "Knowledge base directory not found"
                return action
            kb_files = sorted(
                [f for f in self.kb_dir.glob("*.md") if f.name != "00-index.md"],
                key=lambda x: x.name,
            )
            index_content = self._generate_kb_index_content(kb_files)
            index_path.write_text(index_content, encoding="utf-8")
            action.executed = True
            action.success = True
        except Exception as e:
            action.error = str(e)
        return action

    def update_tasks_md(self, project_name: str) -> UpdateAction:
        project_dir = self.projects_dir / project_name
        tasks_path = project_dir / "tasks.md"
        action = UpdateAction(
            action_type="update_tasks_md",
            target_path=tasks_path,
            description=f"Update tasks.md for {project_name}",
        )
        try:
            if not project_dir.exists():
                action.error = f"Project {project_name} not found"
                return action
            agents_path = project_dir / "AGENTS.md"
            if not agents_path.exists():
                action.error = "AGENTS.md not found in project"
                return action
            content = agents_path.read_text(encoding="utf-8")
            tasks = self._extract_tasks_from_agents(content)
            tasks_content = self._generate_tasks_content(tasks, project_name)
            tasks_path.write_text(tasks_content, encoding="utf-8")
            action.executed = True
            action.success = True
        except Exception as e:
            action.error = str(e)
        return action

    def _scan_projects(self) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        if not self.projects_dir.exists():
            return projects
        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            agents_file = project_dir / "AGENTS.md"
            tasks_file = project_dir / "tasks.md"
            info = {
                "name": project_dir.name,
                "path": str(project_dir),
                "has_agents": agents_file.exists(),
                "has_tasks": tasks_file.exists(),
                "mtime": None,
                "status": "未知",
                "progress": "-",
            }
            if agents_file.exists():
                mtime = datetime.fromtimestamp(agents_file.stat().st_mtime)
                info["mtime"] = mtime
                content = agents_file.read_text(encoding="utf-8")
                status_match = re.search(r"狀態[：:]\s*([^\n|]+)", content)
                if status_match:
                    info["status"] = status_match.group(1).strip()
                progress_match = re.search(r"進度[：:]\s*(\d+/\d+|\d+%)", content)
                if progress_match:
                    info["progress"] = progress_match.group(1)
            projects.append(info)
        return sorted(projects, key=lambda x: x["name"])

    def _generate_project_table(self, projects: list[dict[str, Any]]) -> str:
        lines = ["| 子項目 | 狀態 | 進度 | 最後更新 | AGENTS.md |"]
        lines.append("|--------|------|------|----------|-----------|")
        for p in projects:
            mtime_str = p["mtime"].strftime("%Y-%m-%d") if p["mtime"] else "-"
            agents_link = (
                f"[AGENTS.md](file:///{p['path'].replace(chr(92), '/')}/AGENTS.md)"
                if p["has_agents"]
                else "—"
            )
            lines.append(
                f"| {p['name']} | {p['status']} | {p['progress']} | {mtime_str} | {agents_link} |"
            )
        stats = f"\n**統計**：{len(projects)} 個子項目（{sum(1 for p in projects if p['has_agents'])} 個有 AGENTS.md，{sum(1 for p in projects if p['has_tasks'])} 個有 tasks.md）\n"
        return "\n".join(lines) + stats

    def _generate_summary_block(
        self, summary: dict[str, Any], today_str: str
    ) -> str:
        stats = summary.get("summary", {})
        lines = [
            f"**今日進度**：{stats.get('projects_worked_today', 0)} 個項目修改，{stats.get('files_modified_today', 0)} 個文件修改",
            "",
            f"**關鍵決策**：{stats.get('decisions_today', 0)} 個今日決策",
            "",
            f"**錯誤修復**：{stats.get('total_error_rules', 0)} 條錯誤規則",
            "",
            f"**下一步行動**：（見 decision-log.md）",
        ]
        return "\n".join(lines)

    def _generate_kb_index_content(self, kb_files: list[Path]) -> str:
        lines = [
            "# Knowledge Base Index",
            "",
            f"> 自動生成於 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 文件列表",
            "",
        ]
        for f in kb_files:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            mtime_str = mtime.strftime("%Y-%m-%d")
            lines.append(f"- [{f.name}](./{f.name}) — 更新於 {mtime_str}")
        lines.append("")
        lines.append(f"**總計**：{len(kb_files)} 個知識庫文件")
        return "\n".join(lines)

    def _extract_tasks_from_agents(self, content: str) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        pattern = r"-\s*\[(x| |✅|🔄|⏸️|⏳)\]\s*(.+?)(?=\n|$)"
        for match in re.finditer(pattern, content):
            status_char = match.group(1)
            task_text = match.group(2).strip()
            status = "completed" if status_char in ["x", "✅"] else "pending"
            tasks.append({"status": status, "text": task_text})
        return tasks

    def _generate_tasks_content(
        self, tasks: list[dict[str, Any]], project_name: str
    ) -> str:
        lines = [
            f"# Tasks — {project_name}",
            "",
            f"> 自動生成於 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 任務列表",
            "",
        ]
        for t in tasks:
            checkbox = "[x]" if t["status"] == "completed" else "[ ]"
            lines.append(f"- {checkbox} {t['text']}")
        lines.append("")
        completed = sum(1 for t in tasks if t["status"] == "completed")
        lines.append(f"**進度**：{completed}/{len(tasks)} 完成")
        return "\n".join(lines)


class UpdateReportGenerator:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_json_report(self, report: UpdateReport) -> Path:
        report_path = self.output_dir / "daily_update_report.json"
        data = {
            "timestamp": report.timestamp,
            "files_scanned": report.files_scanned,
            "files_fresh": report.files_fresh,
            "files_stale": report.files_stale,
            "files_outdated": report.files_outdated,
            "actions_executed": [
                {
                    "action_type": a.action_type,
                    "target_path": str(a.target_path),
                    "description": a.description,
                    "executed": a.executed,
                    "success": a.success,
                    "error": a.error,
                }
                for a in report.actions_executed
            ],
            "errors": report.errors,
            "duration_seconds": report.duration_seconds,
            "beeverse_sync": {
                "enabled": report.beeverse_sync.enabled,
                "sync_executed": report.beeverse_sync.sync_executed,
                "sync_success": report.beeverse_sync.sync_success,
                "sync_type": report.beeverse_sync.sync_type,
                "changes_count": report.beeverse_sync.changes_count,
                "sync_duration_seconds": report.beeverse_sync.sync_duration_seconds,
                "errors": report.beeverse_sync.errors,
            },
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return report_path

    def generate_markdown_report(self, report: UpdateReport) -> Path:
        report_path = self.output_dir / "daily_update_report.md"
        lines = [
            f"# 📊 Daily Auto Update Report — {report.timestamp[:10]}",
            "",
            f"> 生成時間: {report.timestamp}",
            f"> 執行耗時: {report.duration_seconds:.2f} 秒",
            "",
            "## 📈 文件狀態分佈",
            "",
            "| 狀態 | 數量 |",
            "|------|------|",
            f"| 🟢 FRESH (< 7 天) | {report.files_fresh} |",
            f"| 🟡 STALE (7-30 天) | {report.files_stale} |",
            f"| 🔴 OUTDATED (> 30 天) | {report.files_outdated} |",
            "",
            f"**總掃描文件**: {report.files_scanned}",
            "",
            "## 🔄 執行動作",
            "",
        ]
        if report.actions_executed:
            for a in report.actions_executed:
                status = "✅" if a.success else "❌"
                lines.append(f"- {status} **{a.action_type}**: {a.description}")
                if a.error:
                    lines.append(f"  - 錯誤: {a.error}")
        else:
            lines.append("*無動作執行*")
        lines.append("")
        lines.append("## 🐝 BeeVerse Ollama Sync")
        lines.append("")
        sync = report.beeverse_sync
        if sync.enabled:
            if sync.sync_executed:
                status = "✅" if sync.sync_success else "❌"
                lines.append(f"- **狀態**: {status} {'成功' if sync.sync_success else '失敗'}")
                lines.append(f"- **同步類型**: {sync.sync_type}")
                lines.append(f"- **變更數量**: {sync.changes_count}")
                lines.append(f"- **同步耗時**: {sync.sync_duration_seconds:.2f} 秒")
                if sync.errors:
                    lines.append("- **錯誤**:")
                    for e in sync.errors:
                        lines.append(f"  - {e}")
            else:
                lines.append("- **狀態**: ⏭️ 未執行")
        else:
            lines.append("- **狀態**: ⏸️ 已停用")
        lines.append("")
        if report.errors:
            lines.append("## ⚠️ 錯誤列表")
            lines.append("")
            for e in report.errors:
                lines.append(f"- {e}")
            lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*此報告由 `DailyAutoUpdateEngine` 自動生成*")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return report_path


class DailyAutoUpdateEngine:
    def __init__(
        self,
        project_root: Path,
        beeverse_sync_enabled: bool = True,
        beeverse_auto_rebuild: bool = True,
    ) -> None:
        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.freshness_detector = FileFreshnessDetector()
        self.content_updater = ContentUpdater(project_root)
        self.report_generator = UpdateReportGenerator(self.data_dir)
        self.beeverse_sync_enabled = beeverse_sync_enabled
        self.beeverse_auto_rebuild = beeverse_auto_rebuild
        self._beeverse_sync_engine: BeeVerseOllamaSyncEngine | None = None

    def _get_beeverse_sync_engine(self) -> BeeVerseOllamaSyncEngine | None:
        if not self.beeverse_sync_enabled:
            return None
        if self._beeverse_sync_engine is None:
            try:
                self._beeverse_sync_engine = BeeVerseOllamaSyncEngine(
                    project_root=self.project_root,
                )
            except Exception as e:
                logger.error("beeverse_sync_engine_init_failed", error=str(e))
                return None
        return self._beeverse_sync_engine

    def _sync_beeverse(self, force_full_rebuild: bool = False) -> BeeVerseSyncInfo:
        info = BeeVerseSyncInfo(enabled=self.beeverse_sync_enabled)
        if not self.beeverse_sync_enabled:
            return info

        engine = self._get_beeverse_sync_engine()
        if engine is None:
            info.errors.append("BeeVerseOllamaSyncEngine initialization failed")
            return info

        info.sync_executed = True
        try:
            result: SyncResult = engine.sync(force_full_rebuild=force_full_rebuild)
            info.sync_success = result.success
            info.sync_type = result.sync_type.value
            info.changes_count = result.changes_count
            info.sync_duration_seconds = result.duration_seconds
            info.errors = result.errors
            logger.info(
                "beeverse_sync_completed",
                success=result.success,
                sync_type=result.sync_type.value,
                changes_count=result.changes_count,
            )
        except Exception as e:
            info.sync_success = False
            info.errors.append(f"BeeVerse sync failed: {e}")
            logger.error("beeverse_sync_exception", error=str(e))

        return info

    def run_full_update(self, force_beeverse_rebuild: bool = False) -> UpdateReport:
        start_time = datetime.now()
        report = UpdateReport(
            timestamp=start_time.isoformat(),
            files_scanned=0,
            files_fresh=0,
            files_stale=0,
            files_outdated=0,
        )
        all_files = self._scan_all_files()
        report.files_scanned = len(all_files)
        dist = self.freshness_detector.get_status_distribution(all_files)
        report.files_fresh = dist[FreshnessStatus.FRESH]
        report.files_stale = dist[FreshnessStatus.STALE]
        report.files_outdated = dist[FreshnessStatus.OUTDATED]
        actions: list[UpdateAction] = []
        action1 = self.content_updater.update_agents_md_subproject_index()
        actions.append(action1)
        if not action1.success and action1.error:
            report.errors.append(f"AGENTS.md index update failed: {action1.error}")
        summary = self._generate_memory_summary()
        action2 = self.content_updater.update_agents_md_daily_summary(summary)
        actions.append(action2)
        if not action2.success and action2.error:
            report.errors.append(f"Daily summary update failed: {action2.error}")
        action3 = self.content_updater.sync_skill_md()
        actions.append(action3)
        if not action3.success and action3.error:
            report.errors.append(f"SKILL.md sync failed: {action3.error}")
        action4 = self.content_updater.update_kb_index()
        actions.append(action4)
        if not action4.success and action4.error:
            report.errors.append(f"KB index update failed: {action4.error}")
        report.actions_executed = actions
        beeverse_sync_info = self._sync_beeverse(force_full_rebuild=force_beeverse_rebuild)
        report.beeverse_sync = beeverse_sync_info
        if beeverse_sync_info.sync_executed and not beeverse_sync_info.sync_success:
            for err in beeverse_sync_info.errors:
                report.errors.append(f"BeeVerse sync: {err}")
        end_time = datetime.now()
        report.duration_seconds = (end_time - start_time).total_seconds()
        self.report_generator.generate_json_report(report)
        self.report_generator.generate_markdown_report(report)
        return report

    def run_quick_update(self) -> UpdateReport:
        start_time = datetime.now()
        report = UpdateReport(
            timestamp=start_time.isoformat(),
            files_scanned=0,
            files_fresh=0,
            files_stale=0,
            files_outdated=0,
        )
        summary = self._generate_memory_summary()
        action = self.content_updater.update_agents_md_daily_summary(summary)
        report.actions_executed = [action]
        if not action.success and action.error:
            report.errors.append(f"Daily summary update failed: {action.error}")
        end_time = datetime.now()
        report.duration_seconds = (end_time - start_time).total_seconds()
        return report

    def _scan_all_files(self) -> list[FileInfo]:
        all_files: list[FileInfo] = []
        md_dirs = [
            self.project_root / "docs",
            self.project_root / "projects",
            self.project_root / "skills",
            self.project_root / ".trae",
        ]
        for d in md_dirs:
            if d.exists():
                files = self.freshness_detector.scan_directory(d)
                all_files.extend(files)
        agents_md = self.project_root / "AGENTS.md"
        info = self.freshness_detector.get_file_info(agents_md)
        if info:
            all_files.append(info)
        return all_files

    def _generate_memory_summary(self) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "summary": {
                "projects_worked_today": 0,
                "files_modified_today": 0,
                "decisions_today": 0,
                "total_error_rules": 0,
                "agents_modified_today": False,
            }
        }
        projects_dir = self.project_root / "projects"
        if projects_dir.exists():
            today = datetime.now().date()
            count = 0
            for p in projects_dir.iterdir():
                if p.is_dir():
                    agents = p / "AGENTS.md"
                    if agents.exists():
                        mtime = datetime.fromtimestamp(agents.stat().st_mtime)
                        if mtime.date() == today:
                            count += 1
            summary["summary"]["projects_worked_today"] = count
        decision_log = self.data_dir / "decision-log.md"
        if decision_log.exists():
            content = decision_log.read_text(encoding="utf-8")
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_decisions = len(re.findall(today_str, content))
            summary["summary"]["decisions_today"] = today_decisions
        error_rules = self.data_dir / "error-rules.yaml"
        if error_rules.exists():
            try:
                with open(error_rules, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                summary["summary"]["total_error_rules"] = len(data)
            except Exception:
                pass
        agents_md = self.project_root / "AGENTS.md"
        if agents_md.exists():
            mtime = datetime.fromtimestamp(agents_md.stat().st_mtime)
            today = datetime.now().date()
            summary["summary"]["agents_modified_today"] = mtime.date() == today
        return summary

    def setup_windows_scheduled_task(
        self,
        task_name: str = "HarnessingDailyAutoUpdate",
        schedule_time: str = "00:30",
    ) -> bool:
        try:
            script_path = self.project_root / "scripts" / "run_daily_auto_update.py"
            if not script_path.exists():
                script_content = f'''#!/usr/bin/env python3
import sys
from pathlib import Path

project_root = Path(r"{self.project_root}")
sys.path.insert(0, str(project_root / "src"))

from harnessing.core.daily_auto_update_engine import DailyAutoUpdateEngine

engine = DailyAutoUpdateEngine(project_root)
report = engine.run_full_update()

print(f"Updated {{report.files_scanned}} files")
print(f"FRESH: {{report.files_fresh}}, STALE: {{report.files_stale}}, OUTDATED: {{report.files_outdated}}")
print(f"Actions: {{len(report.actions_executed)}}")
'''
                script_path.write_text(script_content, encoding="utf-8")
            startup_dir = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            bat_path = startup_dir / f"{task_name}.bat"
            bat_content = f'''@echo off
cd /d "{self.project_root}"
"{sys.executable}" "{script_path}"
'''
            bat_path.write_text(bat_content, encoding="utf-8")
            return True
        except Exception:
            return False


def main() -> int:
    project_root = Path(__file__).parent.parent.parent.parent
    engine = DailyAutoUpdateEngine(project_root)
    print("🔄 執行 Daily Auto Update...")
    print("")
    report = engine.run_full_update()
    print(f"📊 掃描結果:")
    print(f"   - 總文件: {report.files_scanned}")
    print(f"   - 🟢 FRESH: {report.files_fresh}")
    print(f"   - 🟡 STALE: {report.files_stale}")
    print(f"   - 🔴 OUTDATED: {report.files_outdated}")
    print("")
    print(f"🔄 執行動作:")
    for a in report.actions_executed:
        status = "✅" if a.success else "❌"
        print(f"   - {status} {a.action_type}: {a.description}")
        if a.error:
            print(f"      錯誤: {a.error}")
    print("")
    print(f"🐝 BeeVerse Ollama Sync:")
    sync = report.beeverse_sync
    if sync.enabled:
        if sync.sync_executed:
            status = "✅" if sync.sync_success else "❌"
            print(f"   - 狀態: {status} {'成功' if sync.sync_success else '失敗'}")
            print(f"   - 同步類型: {sync.sync_type}")
            print(f"   - 變更數量: {sync.changes_count}")
            print(f"   - 同步耗時: {sync.sync_duration_seconds:.2f} 秒")
            if sync.errors:
                print(f"   - 錯誤: {', '.join(sync.errors)}")
        else:
            print(f"   - 狀態: ⏭️ 未執行")
    else:
        print(f"   - 狀態: ⏸️ 已停用")
    print("")
    print(f"⏱️ 耗時: {report.duration_seconds:.2f} 秒")
    print(f"📄 報告已保存至: {engine.data_dir / 'daily_update_report.json'}")
    return 0 if not report.errors else 1


if __name__ == "__main__":
    sys.exit(main())
