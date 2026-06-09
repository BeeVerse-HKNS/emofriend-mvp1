"""
StatusDashboard - Master Agent 狀態儀表板

功能：
1. CLI 儀表板（Rich 格式化輸出）
2. Markdown 報告生成
3. JSON 狀態輸出（供其他引擎使用）

公式：log(M) + K — 抽象化監控 + 知識整合

相關規則：Rule 67 (Master Orchestrator 調度規則)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .project_scanner import ProjectScanner, SubProject


class StatusDashboard:
    """
    Master Agent 狀態儀表板

    提供多種格式嘅狀態視覺化輸出。
    """

    def __init__(self, scanner: ProjectScanner):
        self.scanner = scanner

    def render_cli(self) -> str:
        projects = self.scanner.scan_all()
        summary = self.scanner.get_summary()

        lines: list[str] = []
        lines.append("┌" + "─" * 68 + "┐")
        lines.append("│" + "Harnessing Master Agent Dashboard".center(68) + "│")
        lines.append("├" + "─" * 68 + "┤")
        lines.append("│ {:<36} {:<8} {:<8} {:<14} │".format("Project", "Status", "Progress", "Last Update"))
        lines.append("├" + "─" * 68 + "┤")

        for p in sorted(projects, key=lambda x: x.name):
            status_icon = self._get_status_icon(p.status.value)
            agents_icon = "✓" if p.has_agents_md else "✗"
            progress_str = f"{p.progress:.0f}%" if p.progress > 0 else "-"
            update_str = self._format_date(p.last_update)

            display_name = p.name[:34] if len(p.name) > 34 else p.name
            lines.append(
                "│ {} {:<33} {} {:<7} {:<14} │".format(
                    status_icon, display_name, agents_icon, progress_str, update_str
                )
            )

        lines.append("├" + "─" * 68 + "┤")
        summary_line = "Summary: {} projects, {} with AGENTS.md, {} active".format(
            summary["total_projects"],
            summary["with_agents_md"],
            summary["active_projects"],
        )
        lines.append("│" + summary_line.ljust(68) + "│")
        lines.append("└" + "─" * 68 + "┘")

        return "\n".join(lines)

    def render_markdown(self, title: str = "Harnessing 子項目狀態報告") -> str:
        projects = self.scanner.scan_all()
        summary = self.scanner.get_summary()

        lines: list[str] = []
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"> **生成時間**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        lines.append("## 統計摘要")
        lines.append("")
        lines.append(f"- **總子項目**：{summary['total_projects']}")
        lines.append(f"- **有 AGENTS.md**：{summary['with_agents_md']}（{summary['with_agents_md'] / max(summary['total_projects'], 1) * 100:.1f}%）")
        lines.append(f"- **缺少 AGENTS.md**：{summary['without_agents_md']}")
        lines.append(f"- **活躍項目**：{summary['active_projects']}")
        lines.append(f"- **停滯項目**：{summary['stalled_projects']}")
        lines.append("")

        lines.append("## 項目類型分佈")
        lines.append("")
        lines.append("| 類型 | 數量 |")
        lines.append("|------|------|")
        for ptype, count in sorted(summary["type_distribution"].items(), key=lambda x: -x[1]):
            lines.append(f"| {ptype} | {count} |")
        lines.append("")

        lines.append("## 子項目清單")
        lines.append("")
        lines.append("| 子項目 | 狀態 | 進度 | AGENTS.md | 最後更新 |")
        lines.append("|--------|------|------|-----------|----------|")

        for p in sorted(projects, key=lambda x: x.name):
            status_icon = self._get_status_icon(p.status.value)
            agents_icon = "✅" if p.has_agents_md else "❌"
            progress_str = f"{p.progress:.0f}%" if p.progress > 0 else "-"
            update_str = self._format_date(p.last_update) if p.last_update else "-"
            lines.append(f"| {p.name} | {status_icon} {p.status.value} | {progress_str} | {agents_icon} | {update_str} |")

        lines.append("")

        stalled = self.scanner.find_stalled_projects()
        if stalled:
            lines.append("## ⚠️ 停滯項目")
            lines.append("")
            for p in stalled:
                days = (datetime.now() - p.last_update).days if p.last_update else 0
                lines.append(f"- **{p.name}**：最後更新 {days} 天前")
            lines.append("")

        missing = self.scanner.find_missing_agents_md()
        if missing:
            lines.append("## ❌ 缺少 AGENTS.md")
            lines.append("")
            lines.append(", ".join([f"`{p.name}`" for p in missing]))
            lines.append("")
            lines.append("**建議**：為這些項目創建 AGENTS.md 以啟用記憶追蹤。")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*由 Master Agent StatusDashboard 自動生成*")

        return "\n".join(lines)

    def render_json(self) -> str:
        projects = self.scanner.scan_all()
        summary = self.scanner.get_summary()

        return json.dumps(
            {
                "generated_at": datetime.now().isoformat(),
                "summary": summary,
                "projects": [p.to_dict() for p in projects],
            },
            indent=2,
            ensure_ascii=False,
        )

    def save_report(self, output_path: Path | str, format: str = "markdown") -> Path:
        output_path = Path(output_path)

        if format == "markdown" or output_path.suffix == ".md":
            content = self.render_markdown()
        elif format == "json" or output_path.suffix == ".json":
            content = self.render_json()
        else:
            content = self.render_cli()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        return output_path

    def generate_daily_report(self, output_dir: Path | str) -> Path:
        output_dir = Path(output_dir)
        today = datetime.now().strftime("%Y-%m-%d")
        output_path = output_dir / f"daily-report-{today}.md"

        projects = self.scanner.scan_all()

        lines: list[str] = []
        lines.append(f"# Harnessing 每日進度報告 — {today}")
        lines.append("")

        active_projects = [p for p in projects if p.status.value == "active"]
        if active_projects:
            lines.append("## 活躍項目")
            lines.append("")
            for p in active_projects:
                lines.append(f"- **{p.name}**：{p.description[:50]}...")
            lines.append("")

        stalled_projects = self.scanner.find_stalled_projects(days_threshold=7)
        if stalled_projects:
            lines.append("## 停滯項目")
            lines.append("")
            for p in stalled_projects:
                days = (datetime.now() - p.last_update).days if p.last_update else 0
                lines.append(f"- **{p.name}**：最後更新 {days} 天前，建議檢查")
            lines.append("")

        missing_agents = self.scanner.find_missing_agents_md()
        if missing_agents:
            lines.append("## 缺少 AGENTS.md")
            lines.append("")
            lines.append(", ".join([f"`{p.name}`" for p in missing_agents]))
            lines.append("")

        lines.append("## 建議行動")
        lines.append("")
        action_num = 1
        if missing_agents:
            lines.append(f"{action_num}. 為缺少 AGENTS.md 的項目創建記憶文件")
            action_num += 1
        if stalled_projects:
            lines.append(f"{action_num}. 檢查停滯項目原因")
            action_num += 1
        for p in active_projects[:3]:
            if p.pending_tasks > 0:
                lines.append(f"{action_num}. {p.name} 有 {p.pending_tasks} 個待辦事項")
                action_num += 1

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*由 Master Agent 自動生成*")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")

        return output_path

    def _get_status_icon(self, status: str) -> str:
        icons = {
            "active": "🟢",
            "stalled": "🟡",
            "completed": "✅",
            "error": "🔴",
            "unknown": "⚪",
        }
        return icons.get(status, "⚪")

    def _format_date(self, dt: datetime | None) -> str:
        if dt is None:
            return "-"
        return dt.strftime("%Y-%m-%d")


def create_dashboard(root_path: Path | str) -> StatusDashboard:
    from .project_scanner import ProjectScanner

    scanner = ProjectScanner(root_path)
    return StatusDashboard(scanner)


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    dashboard = create_dashboard(root)

    print(dashboard.render_cli())
    print()

    report_path = Path(root) / "data" / "project-status-report.md"
    dashboard.save_report(report_path)
    print(f"報告已保存到：{report_path}")
