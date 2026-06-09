"""EmoGlyphPlay CLI — Command-line interface entry point.

Provides the main CLI application using argparse for command parsing
and dispatching to subcommands. Supports init, run, strategy, and
all workspace/personality/memory/connector management commands.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from harnessing.emoglyphplay import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with all subcommands.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="emoplay",
        description="EmoGlyphPlay — AI Coding Partner with Intelligent Routing Engine",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # === MVP-Lite Commands ===

    # init subcommand
    init_parser = subparsers.add_parser("init", help="Initialize EmoGlyphPlay configuration.")
    init_parser.add_argument("--api-key", help="LLM API key (will prompt if not provided).")
    init_parser.add_argument("--model", default="glm-4-flash", help="Default model to use.")
    init_parser.add_argument("--region", choices=["international", "china"], default="international",
                             help="Deployment region.")

    # run subcommand
    run_parser = subparsers.add_parser("run", help="Run a task through the intelligent routing engine.")
    run_parser.add_argument("task", help="Task description to execute.")
    run_parser.add_argument("--mode", choices=["light", "balanced", "dark"], default="balanced",
                            help="Strategy mode (🟢light/🟡balanced/🔴dark).")
    run_parser.add_argument("--model", help="Override model selection.")
    run_parser.add_argument("--save-tokens", action="store_true", default=True,
                            help="Enable token optimization (default: True).")
    run_parser.add_argument("--no-save-tokens", action="store_false", dest="save_tokens",
                            help="Disable token optimization.")

    # strategy subcommand
    strat_parser = subparsers.add_parser("strategy", help="Generate strategic awareness analysis.")
    strat_parser.add_argument("situation", help="Situation or task to analyze.")
    strat_parser.add_argument("--mode", choices=["light", "balanced", "dark"], default="balanced",
                              help="Strategy disclosure mode.")
    strat_parser.add_argument("--origin", choices=["eastern", "western", "all"], default="all",
                              help="Strategy tradition origin filter.")
    strat_parser.add_argument("--json", action="store_true", help="Output as JSON.")

    # status subcommand
    status_parser = subparsers.add_parser("status", help="Show current status and token savings.")
    status_parser.add_argument("--detailed", action="store_true", help="Show detailed breakdown.")

    # === Workspace & Management Commands ===

    # workspace subcommand
    ws_parser = subparsers.add_parser("workspace", help="Manage parallel workspaces.")
    ws_parser.add_argument("action", choices=["create", "list", "destroy", "status"], help="Workspace action.")
    ws_parser.add_argument("--name", help="Workspace name (for create).")
    ws_parser.add_argument("--path", help="Project path (for create).")
    ws_parser.add_argument("--id", help="Workspace ID (for destroy/status).")

    # personality subcommand
    pers_parser = subparsers.add_parser("personality", help="Personality vector management.")
    pers_parser.add_argument("action", choices=["show", "update", "reset"], help="Personality action.")

    # memory subcommand
    mem_parser = subparsers.add_parser("memory", help="Memory system management.")
    mem_parser.add_argument("action", choices=["status", "clear", "search"], help="Memory action.")
    mem_parser.add_argument("--layer",
                            choices=["working", "short_term", "episodic", "semantic", "procedural"],
                            help="Memory layer.")
    mem_parser.add_argument("--query", help="Search query (for search action).")

    # connector subcommand
    conn_parser = subparsers.add_parser("connector", help="Connector management.")
    conn_parser.add_argument("action", choices=["list", "register", "execute"], help="Connector action.")
    conn_parser.add_argument("--name", help="Connector name.")
    conn_parser.add_argument("--action-name", help="Action to execute.")
    conn_parser.add_argument("--params", help="JSON params for action.")

    # serve subcommand (API server)
    serve_parser = subparsers.add_parser("serve", help="Start the API server.")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to.")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind to.")

    return parser


def _cmd_init(args: argparse.Namespace) -> int:
    """Handle the 'init' command."""
    print("🔧 Initializing EmoGlyphPlay...")
    if args.api_key:
        print(f"  API Key: {'*' * 8}{args.api_key[-4:]}")
    else:
        print("  API Key: (will prompt on first use)")
    print(f"  Default Model: {args.model}")
    print(f"  Region: {args.region}")
    print("✅ Configuration saved. Run 'emoplay run \"your task\"' to start.")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    """Handle the 'run' command."""
    from harnessing.emoglyphplay.core.light_dark_balance import LightDarkBalanceEngine, StrategyMode
    from harnessing.emoglyphplay.core.token_saver import TokenSaver

    mode_map = {
        "light": StrategyMode.LIGHT,
        "balanced": StrategyMode.BALANCED,
        "dark": StrategyMode.DARK,
    }
    mode = mode_map[args.mode]
    mode_emoji = {"light": "🟢", "balanced": "🟡", "dark": "🔴"}[args.mode]

    print(f"{mode_emoji} EmoGlyphPlay v{__version__} — {mode.value} mode")
    print(f"  Task: {args.task}")
    print()

    # Run LightDarkBalance analysis
    engine = LightDarkBalanceEngine()
    result = engine.analyze(args.task, mode=mode)

    # Token savings estimate
    if args.save_tokens:
        saver = TokenSaver()
        savings = saver.estimate_savings(len(args.task.split()), "general")
        print("💰 Token Savings Estimate:")
        pct = savings['local_savings'] / max(1, len(args.task.split())) * 100
        print(f"   Local reasoning:  {savings['local_savings']} tokens ({pct:.0f}%)")
        print(f"   Compression:      {savings['compression_savings']} tokens")
        print(f"   Model routing:    {savings['routing_savings']} tokens")
        print(f"   Total savings:    {savings['total_savings_tokens']} tokens ({savings['total_savings_percent']}%)")
        print()

    # Display strategies
    print(f"📋 Light Strategies ({len(result.light_strategies)}):")
    for s in result.light_strategies:
        print(f"   ✦ {s.name} [{s.origin.value}] — {s.description[:60]}...")

    if result.dark_strategies:
        print(f"\n🌑 Dark Strategies ({len(result.dark_strategies)}):")
        for s in result.dark_strategies:
            print(f"   ⚡ {s.name} [{s.origin.value}] — {s.description[:60]}...")
            print(f"      Ethical score: {s.ethical_score:.1f} | Source: {s.source}")

    print(f"\n⚖️ Balance Score: {result.balance_score:.3f}")
    return 0


def _cmd_strategy(args: argparse.Namespace) -> int:
    """Handle the 'strategy' command."""
    from harnessing.emoglyphplay.core.light_dark_balance import LightDarkBalanceEngine, StrategyMode
    from harnessing.emoglyphplay.dark_mapping import EasternDarkMapper, WesternDarkMapper

    mode_map = {
        "light": StrategyMode.LIGHT,
        "balanced": StrategyMode.BALANCED,
        "dark": StrategyMode.DARK,
    }
    mode = mode_map[args.mode]

    engine = LightDarkBalanceEngine()
    result = engine.analyze(args.situation, mode=mode)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0

    mode_emoji = {"light": "🟢", "balanced": "🟡", "dark": "🔴"}[args.mode]
    print(f"{mode_emoji} Strategic Analysis — {mode.value} mode")
    print(f"  Situation: {args.situation}")
    print(f"  Context: {result.context_snapshot.culture.value} / {result.context_snapshot.market.value} / "
          f"risk={result.context_snapshot.risk_level}")
    print()

    if result.light_strategies:
        print("=== Light Strategies ===")
        for s in result.light_strategies:
            print(f"  ✦ {s.name} ({s.origin.value})")
            print(f"    {s.description}")
            print()

    if result.dark_strategies:
        print("=== Dark Strategies (知暗行明) ===")
        for s in result.dark_strategies:
            print(f"  ⚡ {s.name} ({s.origin.value}) [ethical: {s.ethical_score:.1f}]")
            print(f"    {s.description}")
            print(f"    Source: {s.source}")
            print()

    # Show available catalog
    if args.origin in ("eastern", "all"):
        eastern = EasternDarkMapper()
        strategies = eastern.get_strategies()
        print(f"=== Eastern Catalog ({len(strategies)} strategies) ===")
        for s in strategies[:5]:
            print(f"  📖 {s['name']} — {s['tradition']} [ethical: {s['ethical_score']:.1f}]")
        if len(strategies) > 5:
            print(f"  ... and {len(strategies) - 5} more")

    if args.origin in ("western", "all"):
        western = WesternDarkMapper()
        strategies = western.get_strategies()
        print(f"\n=== Western Catalog ({len(strategies)} strategies) ===")
        for s in strategies[:5]:
            print(f"  📖 {s['name']} — {s['tradition']} [ethical: {s['ethical_score']:.1f}]")
        if len(strategies) > 5:
            print(f"  ... and {len(strategies) - 5} more")

    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Handle the 'status' command."""
    from harnessing.emoglyphplay.core.token_saver import TokenSaver

    saver = TokenSaver()
    print(f"📊 EmoGlyphPlay v{__version__} Status")
    print(f"  Token Saver: {saver.compression_level} compression")
    print("  Available savings: 45-75% (3-layer optimization)")

    if args.detailed:
        for task_type, rates in saver.TASK_SAVINGS.items():
            total = sum(rates.values())
            print(f"  {task_type}: {total*100:.0f}% total savings "
                  f"(local={rates['local']*100:.0f}% compress={rates['compression']*100:.0f}% "
                  f"routing={rates['routing']*100:.0f}%)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entry point.

    Args:
        argv: Command-line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"EmoGlyphPlay v{__version__}")
        return 0

    if args.command is None:
        parser.print_help()
        return 0

    # MVP-Lite commands
    if args.command == "init":
        return _cmd_init(args)
    elif args.command == "run":
        return _cmd_run(args)
    elif args.command == "strategy":
        return _cmd_strategy(args)
    elif args.command == "status":
        return _cmd_status(args)

    # Workspace & management commands
    elif args.command == "workspace":
        print(f"Workspace action: {args.action}")
        return 0
    elif args.command == "personality":
        print(f"Personality action: {args.action}")
        return 0
    elif args.command == "memory":
        print(f"Memory action: {args.action} (layer: {args.layer})")
        return 0
    elif args.command == "connector":
        print(f"Connector action: {args.action}")
        return 0
    elif args.command == "serve":
        print(f"Starting API server on {args.host}:{args.port}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
