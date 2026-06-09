"""
Master Agent CLI - 命令行界面（增強版）

功能：
- harness scan — 掃描所有子項目
- harness status [project] — 查看狀態
- harness monitor — 啟動監控
- harness report — 生成報告
- harness execute <project> <task> — 執行任務
- harness bugs [project] — Bug 偵測
- harness dashboard — 啟動 Web Dashboard
- harness learn — 觸發自學習
- harness conflicts — 衝突偵測

相關規則：Rule 67-72 (Master Agent 規則)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Harnessing Master Agent - 子項目管理系統（增強版）",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    scan_parser = subparsers.add_parser("scan", help="掃描所有子項目")
    scan_parser.add_argument("--json", action="store_true", help="輸出 JSON 格式")
    scan_parser.add_argument("--output", "-o", type=str, help="輸出文件路徑")

    status_parser = subparsers.add_parser("status", help="查看項目狀態")
    status_parser.add_argument("project", nargs="?", help="項目名稱（可選）")
    status_parser.add_argument("--detailed", "-d", action="store_true", help="顯示詳細信息")

    monitor_parser = subparsers.add_parser("monitor", help="啟動持續監控")
    monitor_parser.add_argument("--interval", "-i", type=int, default=300, help="掃描間隔（秒）")
    monitor_parser.add_argument("--daemon", "-D", action="store_true", help="後台運行")

    report_parser = subparsers.add_parser("report", help="生成進度報告")
    report_parser.add_argument("--daily", action="store_true", help="每日報告")
    report_parser.add_argument("--weekly", action="store_true", help="每週摘要")
    report_parser.add_argument("--output", "-o", type=str, help="輸出文件路徑")

    execute_parser = subparsers.add_parser("execute", help="執行項目任務")
    execute_parser.add_argument("project", help="項目名稱")
    execute_parser.add_argument("task", help="任務類型（read/write/run/test/git）")
    execute_parser.add_argument("--file", "-f", type=str, help="文件路徑")
    execute_parser.add_argument("--args", "-a", type=str, nargs="*", help="額外參數")

    check_parser = subparsers.add_parser("check", help="執行質量檢查")
    check_parser.add_argument("project", help="項目名稱")
    check_parser.add_argument("--lint", action="store_true", help="Lint 檢查")
    check_parser.add_argument("--security", action="store_true", help="安全掃描")
    check_parser.add_argument("--full", action="store_true", help="完整檢查")

    bugs_parser = subparsers.add_parser("bugs", help="Bug 偵測")
    bugs_parser.add_argument("project", nargs="?", help="項目名稱（可選，默認掃描所有）")
    bugs_parser.add_argument("--static", action="store_true", help="靜態分析")
    bugs_parser.add_argument("--git", action="store_true", help="Git 變更分析")
    bugs_parser.add_argument("--deps", action="store_true", help="依賴漏洞掃描")
    bugs_parser.add_argument("--security", action="store_true", help="安全掃描")
    bugs_parser.add_argument("--all", "-a", action="store_true", help="所有檢查")

    dashboard_parser = subparsers.add_parser("dashboard", help="啟動 Web Dashboard")
    dashboard_parser.add_argument("--port", "-p", type=int, default=11436, help="端口號")
    dashboard_parser.add_argument("--no-browser", action="store_true", help="不自動打開瀏覽器")

    learn_parser = subparsers.add_parser("learn", help="觸發自學習")
    learn_parser.add_argument("--dry-run", action="store_true", help="只顯示將要執行的操作")

    conflicts_parser = subparsers.add_parser("conflicts", help="衝突偵測")
    conflicts_parser.add_argument("--deps", action="store_true", help="依賴衝突")
    conflicts_parser.add_argument("--resources", action="store_true", help="資源衝突")
    conflicts_parser.add_argument("--all", "-a", action="store_true", help="所有衝突類型")

    return parser


def cmd_scan(args: argparse.Namespace, root_path: Path) -> int:
    from .project_scanner import ProjectScanner
    from .status_dashboard import StatusDashboard

    scanner = ProjectScanner(root_path)
    dashboard = StatusDashboard(scanner)

    if args.json:
        print(scanner.to_json())
    else:
        print(dashboard.render_cli())

    if args.output:
        output_path = Path(args.output)
        dashboard.save_report(output_path)
        print(f"\n報告已保存到：{output_path}")

    return 0


def cmd_status(args: argparse.Namespace, root_path: Path) -> int:
    from .project_scanner import ProjectScanner

    scanner = ProjectScanner(root_path)

    if args.project:
        project = scanner.scan_single(args.project)
        if not project:
            print(f"❌ 項目未找到：{args.project}")
            return 1

        print(f"\n📋 項目：{project.name}")
        print(f"   類型：{project.project_type.value}")
        print(f"   狀態：{project.status.value}")
        print(f"   進度：{project.progress:.0f}%")
        print(f"   AGENTS.md：{'✅' if project.has_agents_md else '❌'}")
        if project.last_update:
            print(f"   最後更新：{project.last_update.strftime('%Y-%m-%d %H:%M')}")
        print(f"   技術棧：{', '.join(project.tech_stack) or 'N/A'}")

        if args.detailed:
            print(f"\n   描述：{project.description}")
            print(f"   依賴：{len(project.dependencies)} 個")
            print(f"   待辦：{project.pending_tasks} 個")

    else:
        projects = scanner.scan_all()
        summary = scanner.get_summary()

        print(f"\n📊 Harnessing 項目狀態總覽\n")
        print(f"   總項目：{summary['total_projects']}")
        print(f"   有 AGENTS.md：{summary['with_agents_md']}")
        print(f"   活躍項目：{summary['active_projects']}")
        print(f"   停滯項目：{summary['stalled_projects']}")
        print()

        for p in sorted(projects, key=lambda x: x.name):
            status_icon = {"active": "🟢", "stalled": "🟡", "completed": "✅", "unknown": "⚪"}.get(
                p.status.value, "⚪"
            )
            agents_icon = "✓" if p.has_agents_md else "✗"
            print(f"  {status_icon} {p.name:<35} {agents_icon} {p.progress:>5.0f}%")

    return 0


def cmd_monitor(args: argparse.Namespace, root_path: Path) -> int:
    from .project_monitoring_engine import create_monitoring_engine

    def print_alert(alert):
        print(f"[{alert.severity.value.upper()}] {alert.message}")

    engine = create_monitoring_engine(root_path, scan_interval=args.interval, alert_callback=print_alert)

    print(f"🔍 啟動監控引擎（間隔 {args.interval} 秒）...")
    print("按 Ctrl+C 停止\n")

    engine.start()

    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n停止監控...")
        engine.stop()

    return 0


def cmd_report(args: argparse.Namespace, root_path: Path) -> int:
    from .progress_reporter import ProgressReporter

    reporter = ProgressReporter.__new__(ProgressReporter)
    from .project_scanner import ProjectScanner

    scanner = ProjectScanner(root_path)
    reporter.scanner = scanner

    if args.weekly:
        content = reporter.generate_weekly_summary()
    else:
        content = reporter.generate_daily_report()

    print(content)

    if args.output:
        output_path = Path(args.output)
        reporter.save_report(content, output_path)
        print(f"\n報告已保存到：{output_path}")

    return 0


def cmd_execute(args: argparse.Namespace, root_path: Path) -> int:
    from .direct_executor import create_executor

    executor = create_executor(root_path)

    task = args.task.lower()
    project = args.project

    if task == "read":
        if not args.file:
            print("❌ 請指定 --file 參數")
            return 1
        result = executor.read_file(project, args.file)
    elif task == "write":
        if not args.file:
            print("❌ 請指定 --file 參數")
            return 1
        content = sys.stdin.read()
        result = executor.write_file(project, args.file, content)
    elif task == "run":
        if not args.file:
            print("❌ 請指定 --file 參數（腳本路徑）")
            return 1
        result = executor.execute_script(project, args.file, args.args)
    elif task == "test":
        result = executor.run_tests(project, args.file or "tests/")
    elif task == "git":
        git_cmd = args.args[0] if args.args else "status"
        if git_cmd == "status":
            result = executor.git_status(project)
        elif git_cmd == "pull":
            result = executor.git_pull(project)
        else:
            print(f"❌ 不支持嘅 git 命令：{git_cmd}")
            return 1
    else:
        print(f"❌ 未知任務類型：{task}")
        return 1

    print(f"\n📋 執行結果：{result.status.value}")
    if result.output:
        print(result.output[:2000])
    if result.error:
        print(f"\n❌ 錯誤：{result.error}")

    return 0 if result.status.value == "success" else 1


def cmd_check(args: argparse.Namespace, root_path: Path) -> int:
    from .assurance_system import create_assurance_system

    assurance = create_assurance_system(root_path)

    if args.full:
        report = assurance.run_full_check(args.project)
        print(f"\n📊 質量檢查報告：{report.project_name}")
        print(f"   總體狀態：{report.overall_status.value}")
        print(f"   總體分數：{report.overall_score:.1f}%\n")

        for check in report.checks:
            icon = {"pass": "✅", "fail": "❌", "warning": "⚠️", "error": "🔴", "skipped": "⏭️"}.get(
                check.status.value, "❓"
            )
            print(f"  {icon} {check.check_type.value}: {check.message} ({check.score:.1f}%)")
    else:
        if args.lint:
            from .project_scanner import ProjectScanner

            scanner = ProjectScanner(root_path)
            projects = scanner.scan_all()
            project_path = None
            for p in projects:
                if p.name == args.project:
                    project_path = p.path
                    break

            if project_path:
                result = assurance._check_lint(project_path)
                print(f"Lint: {result.status.value} - {result.message}")
            else:
                print(f"❌ 項目未找到：{args.project}")

        if args.security:
            from .project_scanner import ProjectScanner

            scanner = ProjectScanner(root_path)
            projects = scanner.scan_all()
            project_path = None
            for p in projects:
                if p.name == args.project:
                    project_path = p.path
                    break

            if project_path:
                result = assurance._check_security(project_path)
                print(f"Security: {result.status.value} - {result.message}")
                if result.details:
                    for detail in result.details[:10]:
                        print(f"  - {detail.get('file', 'N/A')}: {detail.get('type', 'N/A')}")

    return 0


def cmd_bugs(args: argparse.Namespace, root_path: Path) -> int:
    from .bug_detection_engine import BugDetectionEngine
    from .project_scanner import ProjectScanner

    enable_static = args.static or args.all or (not args.static and not args.git and not args.deps and not args.security)
    enable_git = args.git or args.all
    enable_deps = args.deps or args.all
    enable_security = args.security or args.all

    engine = BugDetectionEngine(
        enable_static=enable_static,
        enable_git=enable_git,
        enable_dependency=enable_deps,
        enable_security=enable_security,
    )

    if args.project:
        project_path = root_path / "projects" / args.project
        if not project_path.exists():
            print(f"❌ 項目未找到：{args.project}")
            return 1

        result = engine.analyze(str(project_path))
        print(f"\n🐛 Bug 偵測報告：{args.project}")
        print(f"   分析器：{', '.join(result.analyzers_run)}")
        print(f"   耗時：{result.duration_seconds:.2f}s\n")

        print(f"   總計：{result.summary['total']} 個問題")
        print(f"   🔴 Critical：{result.summary['critical']}")
        print(f"   🟠 High：{result.summary['high']}")
        print(f"   🟡 Medium：{result.summary['medium']}")
        print(f"   🟢 Low：{result.summary['low']}")
        print(f"   ℹ️ Info：{result.summary['info']}\n")

        for finding in result.findings[:20]:
            sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️"}.get(
                finding.severity.value, "❓"
            )
            location = f"{finding.file_path}:{finding.line_number}" if finding.file_path else "N/A"
            print(f"  {sev_icon} [{finding.category.value}] {finding.title}")
            print(f"     📍 {location}")
            if finding.fix_suggestion:
                print(f"     💡 {finding.fix_suggestion}")
            print()

        recommendations = engine.get_fix_recommendations(result)
        if recommendations:
            print("\n📝 修復建議：\n")
            for i, rec in enumerate(recommendations[:10], 1):
                print(f"  {i}. [{rec['severity']}] {rec['title']}")
                print(f"     → {rec['suggestion']}\n")

    else:
        scanner = ProjectScanner(str(root_path / "projects"))
        projects = scanner.scan_all()

        print(f"\n🐛 Bug 偵測報告（所有項目）\n")

        total_findings = 0
        for project in projects:
            result = engine.analyze(project.path)
            if result.summary['total'] > 0:
                total_findings += result.summary['total']
                print(f"  {project.name}: {result.summary['total']} 個問題")
                print(f"    🔴 {result.summary['critical']} | 🟠 {result.summary['high']} | 🟡 {result.summary['medium']} | 🟢 {result.summary['low']}")

        print(f"\n  總計：{total_findings} 個問題")

    return 0


def cmd_dashboard(args: argparse.Namespace, root_path: Path) -> int:
    from .master_agent_dashboard import MasterAgentDashboard
    from .auto_scan_scheduler import AutoScanScheduler
    from .bug_detection_engine import BugDetectionEngine
    from .project_scanner import ProjectScanner

    scanner = ProjectScanner(str(root_path / "projects"))
    bug_engine = BugDetectionEngine()

    def on_scan(result):
        print(f"[{result.timestamp.strftime('%H:%M:%S')}] 掃描完成：{result.projects_scanned} 個項目")

    auto_scheduler = AutoScanScheduler(
        scan_callback=on_scan,
        interval_seconds=300,
        projects_dir=str(root_path / "projects"),
    )

    dashboard = MasterAgentDashboard(
        auto_scan_scheduler=auto_scheduler,
        bug_detection_engine=bug_engine,
        project_scanner=scanner,
        port=args.port,
    )

    print(f"\n🌐 啟動 Web Dashboard：http://localhost:{args.port}")
    print("   按 Ctrl+C 停止\n")

    auto_scheduler.start()

    if not args.no_browser:
        import webbrowser
        webbrowser.open(f"http://localhost:{args.port}")

    try:
        dashboard.run()
    except KeyboardInterrupt:
        print("\n\n停止 Dashboard...")
        auto_scheduler.stop()

    return 0


def cmd_learn(args: argparse.Namespace, root_path: Path) -> int:
    from .self_learning_loop import SelfLearningLoop

    learning_loop = SelfLearningLoop(
        projects_dir=str(root_path / "projects"),
        master_agents_md=str(root_path / "AGENTS.md"),
        master_decision_log=str(root_path / "data" / "decision-log.md"),
        master_error_rules=str(root_path / "data" / "error-rules.yaml"),
    )

    if args.dry_run:
        print("\n📚 自學習預覽（Dry Run）\n")
        print("  將執行以下操作：")
        print("  1. 掃描所有子項目 AGENTS.md")
        print("  2. 提取新決策、新錯誤規則")
        print("  3. 更新 Master AGENTS.md")
        print("  4. 增強規則庫")
        return 0

    result = learning_loop.learn()

    print("\n📚 自學習結果\n")
    print(f"  子項目掃描：{result.subprojects_scanned} 個")
    print(f"  新決策：{result.new_decisions} 個")
    print(f"  新錯誤規則：{result.new_error_rules} 個")
    print(f"  新模式偵測：{result.new_patterns} 個")
    print(f"  Master AGENTS.md 更新：{'✅' if result.master_md_updated else '❌'}")
    print(f"  規則增強：{result.rules_enhanced} 條\n")

    stats = learning_loop.get_stats()
    print(f"  累計學習次數：{stats['total_learning_sessions']}")
    print(f"  累計決策學習：{stats['total_decisions_learned']}")
    print(f"  累計規則增強：{stats['total_rules_enhanced']}\n")

    return 0


def cmd_conflicts(args: argparse.Namespace, root_path: Path) -> int:
    from .conflict_detector import ConflictDetector

    detector = ConflictDetector(projects_dir=str(root_path / "projects"))
    report = detector.detect()

    print("\n⚡ 衝突偵測報告\n")
    print(f"  總衝突數：{report.total_conflicts}\n")

    if report.by_type:
        print("  按類型：")
        for type_name, count in report.by_type.items():
            print(f"    - {type_name}: {count}")
        print()

    if report.by_severity:
        print("  按嚴重程度：")
        for sev, count in report.by_severity.items():
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(sev, "❓")
            print(f"    - {icon} {sev}: {count}")
        print()

    for conflict in report.conflicts[:20]:
        sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
            conflict.severity.value, "❓"
        )
        print(f"  {sev_icon} [{conflict.conflict_type.value}] {conflict.title}")
        print(f"     項目：{', '.join(conflict.projects_involved)}")
        if conflict.resolution_suggestion:
            print(f"     💡 {conflict.resolution_suggestion}")
        print()

    deps_summary = detector.get_dependency_summary()
    print(f"\n📦 依賴摘要：{deps_summary['total_packages']} 個唯一包\n")

    return 0


def main(args: list[str] | None = None) -> int:
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 0

    root_path = Path.cwd()

    commands = {
        "scan": cmd_scan,
        "status": cmd_status,
        "monitor": cmd_monitor,
        "report": cmd_report,
        "execute": cmd_execute,
        "check": cmd_check,
        "bugs": cmd_bugs,
        "dashboard": cmd_dashboard,
        "learn": cmd_learn,
        "conflicts": cmd_conflicts,
    }

    handler = commands.get(parsed_args.command)
    if handler:
        return handler(parsed_args, root_path)
    else:
        print(f"❌ 未知命令：{parsed_args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
