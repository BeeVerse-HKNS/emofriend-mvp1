"""
ProgressReporter - Master Agent 進度報告生成器

功能：
1. 每日報告（Markdown）
2. 每週摘要
3. 自定義報告

公式：log(M) + K — 抽象化監控 + 知識整合

相關規則：Rule 71 (Feedback Loop 規則)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .project_scanner import ProjectScanner, SubProject


class ProgressReporter:
    """
    Master Agent 進度報告生成器
    """

    def __init__(self, scanner: ProjectScanner):
        self.scanner = scanner

    def generate_daily_report(self) -> str:
        projects = self.scanner.scan_all()
        today = datetime.now().strftime("%Y-%m-%d")

        lines: list[str] = []
        lines.append(f"# Harnessing 每日進度報告 — {today}")
        lines.append("")
        lines.append(f"> **生成時間**：{datetime.now().strftime('%H:%M:%S')}")
        lines.append("")

        grouped = self._group_projects(projects)

        if grouped["active"]:
            lines.append("## 🟢 活躍項目")
            lines.append("")
            for group in grouped["active"]:
                lines.append(f"- **{group['display_name']}**：{group['description']}")
                for task in group.get("active_tasks", []):
                    lines.append(f"  - {task}")
            lines.append("")

        if grouped["stalled"]:
            lines.append("## 🟡 停滯項目")
            lines.append("")
            for group in grouped["stalled"]:
                days = group.get("days_stalled", 0)
                lines.append(f"- **{group['display_name']}**：最後更新 {days} 天前")
            lines.append("")

        if grouped["missing_agents"]:
            lines.append("## ❌ 缺少 AGENTS.md")
            lines.append("")
            names = [f"`{p.name}`" for p in grouped["missing_agents"]]
            lines.append(", ".join(names))
            lines.append("")

        lines.append("## 📊 統計摘要")
        lines.append("")
        summary = self.scanner.get_summary()
        lines.append(f"| 指標 | 數值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 總項目 | {summary['total_projects']} |")
        lines.append(f"| 有 AGENTS.md | {summary['with_agents_md']} |")
        lines.append(f"| 活躍項目 | {summary['active_projects']} |")
        lines.append(f"| 停滯項目 | {summary['stalled_projects']} |")
        lines.append("")

        lines.append("## 📝 建議行動")
        lines.append("")
        action_num = 1
        if grouped["missing_agents"]:
            lines.append(f"{action_num}. 為缺少 AGENTS.md 的項目創建記憶文件")
            action_num += 1
        if grouped["stalled"]:
            lines.append(f"{action_num}. 檢查停滯項目原因")
            action_num += 1
        lines.append(f"{action_num}. 繼續活躍項目嘅開發工作")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*由 Master Agent ProgressReporter 自動生成*")

        return "\n".join(lines)

    def generate_weekly_summary(self) -> str:
        projects = self.scanner.scan_all()
        week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        week_end = datetime.now().strftime("%Y-%m-%d")

        lines: list[str] = []
        lines.append(f"# Harnessing 每週摘要 — {week_start} 至 {week_end}")
        lines.append("")

        summary = self.scanner.get_summary()

        lines.append("## 📈 項目概覽")
        lines.append("")
        lines.append(f"- **總項目數**：{summary['total_projects']}")
        lines.append(f"- **活躍項目**：{summary['active_projects']}")
        lines.append(f"- **停滯項目**：{summary['stalled_projects']}")
        lines.append(f"- **完成項目**：{sum(1 for p in projects if p.status.value == 'completed')}")
        lines.append("")

        lines.append("## 📂 項目類型分佈")
        lines.append("")
        for ptype, count in sorted(summary["type_distribution"].items(), key=lambda x: -x[1]):
            lines.append(f"- **{ptype}**：{count} 個")
        lines.append("")

        lines.append("## 🔥 項目分組（按用戶定義）")
        lines.append("")
        grouped = self._group_projects(projects)
        lines.append("| 分組 | 項目 | 狀態 |")
        lines.append("|------|------|------|")
        for group in grouped["all_groups"]:
            names = ", ".join(group["projects"])
            lines.append(f"| {group['display_name']} | {names} | {group['status']} |")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*由 Master Agent 自動生成*")

        return "\n".join(lines)

    def _group_projects(self, projects: list[Any]) -> dict[str, Any]:
        groups: dict[str, list[str]] = {
            "accessible-route": ["accessible-route", "accessible-route-china", "accessible-route-global", "accessible-route-shared"],
            "audit-system": ["automation/audit-engine", "efficiency/audit-platform"],
            "hackathon": ["clawtime-hackathon", "ox-nanssha"],
        }

        grouped_projects: dict[str, list[Any]] = {
            "active": [],
            "stalled": [],
            "missing_agents": [],
            "all_groups": [],
        }

        processed = set()

        for group_name, group_members in groups.items():
            group_projects = [p for p in projects if p.name in group_members]
            if group_projects:
                processed.update(group_members)

                main_project = group_projects[0]
                active_tasks = []
                for p in group_projects:
                    if p.name == "automation/audit-engine":
                        active_tasks.append("Monica 整合開發中")
                    elif p.name == "efficiency/audit-platform":
                        active_tasks.append("v5 版本開發 + 生產部署")

                days_stalled = 0
                if main_project.last_update:
                    days_stalled = (datetime.now() - main_project.last_update).days

                group_info = {
                    "display_name": group_name,
                    "projects": group_members,
                    "description": main_project.description[:50] if main_project.description else "項目分組",
                    "status": main_project.status.value,
                    "active_tasks": active_tasks,
                    "days_stalled": days_stalled,
                }

                grouped_projects["all_groups"].append(group_info)

                if main_project.status.value == "active":
                    grouped_projects["active"].append(group_info)
                elif main_project.status.value == "stalled":
                    grouped_projects["stalled"].append(group_info)

        for p in projects:
            if p.name not in processed:
                if not p.has_agents_md:
                    grouped_projects["missing_agents"].append(p)

        return grouped_projects

    def save_report(self, content: str, output_path: Path | str) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return output_path


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    from .project_scanner import ProjectScanner

    scanner = ProjectScanner(root)
    reporter = ProgressReporter(scanner)

    print(reporter.generate_daily_report())
