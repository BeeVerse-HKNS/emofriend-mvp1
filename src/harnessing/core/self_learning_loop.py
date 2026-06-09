"""
SelfLearningLoop — 自學習閉環引擎

從子項目學習並增強 Master Agent 能力：
1. 從子項目學習 — 掃描所有子項目 AGENTS.md，提取新決策、新規則
2. 更新 Master AGENTS.md — 更新索引、統計、摘要
3. 增強規則 — 偵測重複錯誤模式，提取新規則

公式：(S ^ K) — 自學習被知識庫放大
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class LearningResult:
    timestamp: datetime
    subprojects_scanned: int
    new_decisions: int
    new_error_rules: int
    new_patterns: int
    master_md_updated: bool
    rules_enhanced: int
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubProjectKnowledge:
    name: str
    path: str
    decisions: list[dict[str, Any]] = field(default_factory=list)
    error_rules: list[dict[str, Any]] = field(default_factory=list)
    progress: dict[str, Any] = field(default_factory=dict)
    last_update: Optional[str] = None


class SelfLearningLoop:
    def __init__(
        self,
        projects_dir: str = "projects",
        master_agents_md: str = "AGENTS.md",
        master_decision_log: str = "data/decision-log.md",
        master_error_rules: str = "data/error-rules.yaml",
    ):
        self.projects_dir = Path(projects_dir)
        self.master_agents_md = Path(master_agents_md)
        self.master_decision_log = Path(master_decision_log)
        self.master_error_rules = Path(master_error_rules)
        
        self._knowledge_cache: dict[str, SubProjectKnowledge] = {}
        self._learning_history: list[LearningResult] = []

    def learn(self) -> LearningResult:
        start_time = datetime.now()
        
        subprojects = self._scan_subprojects()
        all_decisions = []
        all_error_rules = []
        new_patterns = 0
        
        for sp in subprojects:
            all_decisions.extend(sp.decisions)
            all_error_rules.extend(sp.error_rules)
        
        master_updated = self._update_master_md(subprojects)
        
        rules_enhanced = self._enhance_rules(all_error_rules)
        
        new_patterns = self._detect_patterns(all_decisions, all_error_rules)
        
        result = LearningResult(
            timestamp=start_time,
            subprojects_scanned=len(subprojects),
            new_decisions=len(all_decisions),
            new_error_rules=len(all_error_rules),
            new_patterns=new_patterns,
            master_md_updated=master_updated,
            rules_enhanced=rules_enhanced,
            details={
                "subprojects": [sp.name for sp in subprojects],
            }
        )
        
        self._learning_history.append(result)
        return result

    def _scan_subprojects(self) -> list[SubProjectKnowledge]:
        subprojects = []
        
        if not self.projects_dir.exists():
            return subprojects
        
        for item in self.projects_dir.iterdir():
            if item.is_dir():
                agents_md = item / "AGENTS.md"
                if agents_md.exists():
                    sp = self._parse_subproject(item.name, item)
                    subprojects.append(sp)
                    self._knowledge_cache[item.name] = sp
        
        return subprojects

    def _parse_subproject(self, name: str, path: Path) -> SubProjectKnowledge:
        agents_md = path / "AGENTS.md"
        decisions = []
        error_rules = []
        progress = {}
        last_update = None
        
        if agents_md.exists():
            content = agents_md.read_text(encoding="utf-8", errors="ignore")
            
            decision_pattern = r"D-(\d+).*?\|\s*(\d{4}-\d{2}-\d{2})"
            for match in re.finditer(decision_pattern, content):
                decisions.append({
                    "id": f"D-{match.group(1)}",
                    "date": match.group(2),
                    "source": name,
                })
            
            error_pattern = r"R-ERR-([A-Z0-9]+)"
            for match in re.finditer(error_pattern, content):
                error_rules.append({
                    "id": f"R-ERR-{match.group(1)}",
                    "source": name,
                })
            
            progress_match = re.search(r"## 當前進度\s*(.*?)(?=##|$)", content, re.DOTALL)
            if progress_match:
                progress["status"] = "active" if "✅" in progress_match.group(1) else "in_progress"
            
            update_match = re.search(r"最後更新[：:]\s*(\d{4}-\d{2}-\d{2})", content)
            if update_match:
                last_update = update_match.group(1)
        
        return SubProjectKnowledge(
            name=name,
            path=str(path),
            decisions=decisions,
            error_rules=error_rules,
            progress=progress,
            last_update=last_update,
        )

    def _update_master_md(self, subprojects: list[SubProjectKnowledge]) -> bool:
        if not self.master_agents_md.exists():
            return False
        
        try:
            content = self.master_agents_md.read_text(encoding="utf-8", errors="ignore")
            
            index_pattern = r"## 子項目索引\s*(.*?)(?=##|$)"
            index_match = re.search(index_pattern, content, re.DOTALL)
            
            if index_match:
                new_index = self._generate_subproject_index(subprojects)
                content = content[:index_match.start()] + new_index + content[index_match.end():]
            
            stats_pattern = r"\*\*統計\*\*：\d+ 個子項目"
            stats_replacement = f"**統計**：{len(subprojects)} 個子項目"
            content = re.sub(stats_pattern, stats_replacement, content)
            
            self.master_agents_md.write_text(content, encoding="utf-8")
            return True
        except Exception:
            return False

    def _generate_subproject_index(self, subprojects: list[SubProjectKnowledge]) -> str:
        lines = ["## 子項目索引\n"]
        lines.append(f"> 自動掃描 `projects/` 目錄生成，最後更新：{datetime.now().strftime('%Y-%m-%d')}\n")
        lines.append("\n| 子項目 | 狀態 | 進度 | 最後更新 | AGENTS.md |")
        lines.append("|--------|------|------|----------|-----------|")
        
        for sp in sorted(subprojects, key=lambda x: x.name):
            status = sp.progress.get("status", "未知")
            progress = "✅" if status == "active" else "🔄" if status == "in_progress" else "-"
            agents_link = f"[AGENTS.md](file:///{sp.path.replace(chr(92), '/')}/AGENTS.md)" if Path(sp.path).joinpath("AGENTS.md").exists() else "—"
            lines.append(f"| {sp.name} | {status} | {progress} | {sp.last_update or '-'} | {agents_link} |")
        
        lines.append(f"**統計**：{len(subprojects)} 個子項目")
        return "\n".join(lines) + "\n"

    def _enhance_rules(self, error_rules: list[dict[str, Any]]) -> int:
        if not self.master_error_rules.exists():
            return 0
        
        try:
            content = self.master_error_rules.read_text(encoding="utf-8", errors="ignore")
            existing_ids = set(re.findall(r"R-ERR-([A-Z0-9]+)", content))
            
            new_rules = 0
            for rule in error_rules:
                rule_id = rule.get("id", "")
                if "R-ERR-" in rule_id:
                    short_id = rule_id.replace("R-ERR-", "")
                    if short_id not in existing_ids:
                        new_rules += 1
            
            return new_rules
        except Exception:
            return 0

    def _detect_patterns(
        self,
        decisions: list[dict[str, Any]],
        error_rules: list[dict[str, Any]]
    ) -> int:
        patterns = 0
        
        error_sources: dict[str, int] = {}
        for rule in error_rules:
            source = rule.get("source", "unknown")
            error_sources[source] = error_sources.get(source, 0) + 1
        
        for source, count in error_sources.items():
            if count >= 3:
                patterns += 1
        
        return patterns

    def get_knowledge(self, project_name: str) -> Optional[SubProjectKnowledge]:
        return self._knowledge_cache.get(project_name)

    def get_all_knowledge(self) -> dict[str, SubProjectKnowledge]:
        return self._knowledge_cache.copy()

    def get_learning_history(self) -> list[LearningResult]:
        return self._learning_history.copy()

    def get_stats(self) -> dict[str, Any]:
        if not self._learning_history:
            return {"total_learning_sessions": 0}
        
        return {
            "total_learning_sessions": len(self._learning_history),
            "total_subprojects_scanned": sum(l.subprojects_scanned for l in self._learning_history),
            "total_decisions_learned": sum(l.new_decisions for l in self._learning_history),
            "total_rules_enhanced": sum(l.rules_enhanced for l in self._learning_history),
            "last_learning": self._learning_history[-1].timestamp.isoformat() if self._learning_history else None,
        }
