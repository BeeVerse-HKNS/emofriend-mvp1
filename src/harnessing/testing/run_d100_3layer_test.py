"""D-100 3 Layer Testing Engine — 5 New Engines

CrossCulturalThinkingEngine (R-ERR-081)
SessionContextManager (R-ERR-082)
SupervisorAgent (R-ERR-083)
AbandonmentDetector (R-ERR-084)
FrameworkSelector (R-ERR-085)

L1: 10M cases — fast validation (random parameter combinations)
L2: 100M cases — stress test (edge cases + boundary values)
L3: 1B cases — stability confirmation (convergence check)

Usage:
    python -m harnessing.testing.run_d100_3layer_test --layer L1
    python -m harnessing.testing.run_d100_3layer_test --layer ALL
    python -m harnessing.testing.run_d100_3layer_test --layer L2 --output results.json
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import random
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any

from harnessing.core.abandonment_detector import (
    AbandonmentDetector,
    AbandonmentPattern,
    TaskComplexity,
    TaskRecord,
)
from harnessing.core.cross_cultural_engine import (
    CrossCulturalThinkingEngine,
    CultureSphere,
    ThinkingMethod,
)
from harnessing.core.framework_selector import (
    FrameworkSelector,
    ScenarioType,
)
from harnessing.core.session_context_manager import (
    SessionContext,
    SessionContextManager,
    SessionStatus,
)
from harnessing.core.supervisor_agent import (
    QualityDimension,
    SupervisorAgent,
)

LAYER_SIZES = {"L1": 10_000_000, "L2": 100_000_000, "L3": 1_000_000_000}

SQLITE_ENGINE_RATIO = 0.05

CONVERGENCE_THRESHOLD_L2 = 5.0
CONVERGENCE_THRESHOLD_L3 = 1.0

ALL_THINKING_METHODS = list(ThinkingMethod)
ALL_SCENARIO_TYPES = list(ScenarioType)
ALL_ABANDONMENT_PATTERNS = list(AbandonmentPattern)
ALL_TASK_COMPLEXITIES = list(TaskComplexity)

SCENARIO_KEYWORDS = [
    "策略", "競爭", "系統思維", "去中心化", "團隊管理",
    "產品決策", "邏輯推理", "研發", "學術研究", "產品演進",
    "科學研究", "SWOT", "A/B 測試", "MVP", "YAGNI",
    "數據分析", "用戶研究", "AI 倫理", "市場策略", "架構設計",
]

TASK_NAMES = [
    "開通 YouTube 頻道", "發佈第 1 集影片", "建立知識星球",
    "首次直播帶貨", "評估助理成本", "購買設備升級",
    "A/B 測試方案", "用戶研究計劃", "競爭分析報告",
    "架構設計文檔", "MVP 開發", "市場推廣計劃",
]

OUTPUT_SAMPLES = [
    "", "短", "x" * 50, "x" * 200,
    "步驟一：執行 TODO 項目", "可以運行以下命令",
    "這是一個測試輸出，包含多個關鍵詞和詳細說明",
    "No actionable content here",
]

CULTURE_KEYWORDS = [
    "中國", "chinese", "hong kong", "台灣", "taiwan",
    "american", "european", "japanese", "korean",
    "", "unknown", "印度", "中東",
]

BUDGET_OPTIONS = ["FREE", "LOW", "MEDIUM", "HIGH"]


@dataclass
class EngineTestResult:
    engine: str
    pass_count: int
    total_count: int
    errors: list[str] = field(default_factory=list)
    scenario_details: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def coverage_rate(self) -> float:
        return self.pass_count / self.total_count * 100 if self.total_count > 0 else 0.0


@dataclass
class LayerResult:
    layer: str
    total_count: int
    pass_count: int
    coverage_rate: float
    errors: list[str] = field(default_factory=list)
    execution_time_s: float = 0.0
    engine_results: dict[str, dict[str, Any]] = field(default_factory=dict)


def _run_cross_cultural_batch(args: tuple[int, int, bool]) -> tuple[int, int, list[str], dict[str, dict[str, int]]]:
    batch_size, seed, edge_mode = args
    random.seed(seed)
    engine = CrossCulturalThinkingEngine()
    pass_count = 0
    errors = []
    scenario_details: dict[str, dict[str, int]] = {}

    for i in range(batch_size):
        st = random.randint(0, 4)
        scenario_name = ["get_profile", "recommend_for_scenario", "compare", "get_all_eastern_western", "suggest_for_user_culture"][st]
        if scenario_name not in scenario_details:
            scenario_details[scenario_name] = {"pass": 0, "total": 0}
        scenario_details[scenario_name]["total"] += 1

        try:
            if st == 0:
                method = random.choice(ALL_THINKING_METHODS)
                profile = engine.get_profile(method)
                ok = profile is not None and profile.method == method
            elif st == 1:
                keyword = random.choice(SCENARIO_KEYWORDS) if not edge_mode else ""
                recs = engine.recommend_for_scenario(keyword)
                ok = isinstance(recs, list)
            elif st == 2:
                a = random.choice(ALL_THINKING_METHODS)
                b = random.choice(ALL_THINKING_METHODS)
                comp = engine.compare(a, b)
                ok = comp.method_a == a and comp.method_b == b
            elif st == 3:
                eastern = engine.get_all_eastern_methods()
                western = engine.get_all_western_methods()
                ok = len(eastern) > 0 and len(western) > 0
            else:
                culture = random.choice(CULTURE_KEYWORDS)
                suggestions = engine.suggest_for_user_culture(culture)
                ok = isinstance(suggestions, list)

            if ok:
                pass_count += 1
                scenario_details[scenario_name]["pass"] += 1
        except Exception as e:
            errors.append(str(e)[:200])

    return pass_count, batch_size, errors, scenario_details


def _run_supervisor_batch(args: tuple[int, int, bool]) -> tuple[int, int, list[str], dict[str, dict[str, int]]]:
    batch_size, seed, edge_mode = args
    random.seed(seed)
    agent = SupervisorAgent(
        pass_threshold=random.uniform(50, 90) if edge_mode else 70.0,
        regeneration_threshold=random.uniform(30, 60) if edge_mode else 60.0,
        max_regenerations=random.randint(1, 5) if edge_mode else 3,
    )
    pass_count = 0
    errors = []
    scenario_details: dict[str, dict[str, int]] = {}

    for i in range(batch_size):
        st = random.randint(0, 3)
        scenario_name = ["evaluate_output", "request_regeneration", "detect_deviation", "get_evaluation_history"][st]
        if scenario_name not in scenario_details:
            scenario_details[scenario_name] = {"pass": 0, "total": 0}
        scenario_details[scenario_name]["total"] += 1

        try:
            if st == 0:
                output = random.choice(OUTPUT_SAMPLES)
                criteria = {}
                if edge_mode:
                    criteria = {
                        "required_fields": [f"field_{j}" for j in range(random.randint(0, 5))],
                        "forbidden_keywords": ["bad"],
                        "output_timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                result = agent.evaluate_output(
                    session_id=f"sess_{i}",
                    task=f"task_{i}",
                    output=output,
                    expected_criteria=criteria,
                    regeneration_count=random.randint(0, 5) if edge_mode else 0,
                )
                ok = 0 <= result.overall_score <= 100
            elif st == 1:
                output = random.choice(OUTPUT_SAMPLES)
                result = agent.evaluate_output(session_id=f"sess_{i}", task=f"task_{i}", output=output)
                regen = agent.request_regeneration(result)
                ok = regen["action"] in ("NO_ACTION", "REGENERATE", "ESCALATE_TO_HUMAN")
            elif st == 2:
                keywords = [f"keyword_{j}" for j in range(random.randint(1, 5))]
                output = random.choice(OUTPUT_SAMPLES)
                report = agent.detect_deviation(
                    original_task=f"task with {' '.join(keywords)}",
                    current_output=output,
                    expected_keywords=keywords,
                )
                ok = report.deviation_severity in ("LOW", "MEDIUM", "HIGH")
            else:
                history = agent.get_evaluation_history()
                ok = isinstance(history, list)

            if ok:
                pass_count += 1
                scenario_details[scenario_name]["pass"] += 1
        except Exception as e:
            errors.append(str(e)[:200])

    return pass_count, batch_size, errors, scenario_details


def _run_framework_batch(args: tuple[int, int, bool]) -> tuple[int, int, list[str], dict[str, dict[str, int]]]:
    batch_size, seed, edge_mode = args
    random.seed(seed)
    selector = FrameworkSelector()
    pass_count = 0
    errors = []
    scenario_details: dict[str, dict[str, int]] = {}

    for i in range(batch_size):
        st = random.randint(0, 2)
        scenario_name = ["select_for_scenario", "select_for_requirements", "get_all_options"][st]
        if scenario_name not in scenario_details:
            scenario_details[scenario_name] = {"pass": 0, "total": 0}
        scenario_details[scenario_name]["total"] += 1

        try:
            if st == 0:
                s_type = random.choice(ALL_SCENARIO_TYPES)
                max_opts = random.randint(3, 6) if edge_mode else 3
                rec = selector.select_for_scenario(s_type, max_options=max_opts)
                ok = (
                    rec.scenario == s_type
                    and rec.zero_dependency_option is not None
                    and len(rec.zero_dependency_option.external_dependencies) == 0
                    and len(rec.additional_options) >= 1
                )
            elif st == 1:
                max_users = random.choice([10, 100, 500, 1000, 5000, 10000])
                budget = random.choice(BUDGET_OPTIONS)
                timeline = random.randint(1, 60)
                cross_border = random.random() > 0.5
                offline = random.random() > 0.8 if edge_mode else False
                rec = selector.select_for_requirements(
                    max_users=max_users,
                    budget=budget,
                    timeline_days=timeline,
                    cross_border=cross_border,
                    offline=offline,
                )
                ok = (
                    rec.zero_dependency_option is not None
                    and len(rec.zero_dependency_option.external_dependencies) == 0
                )
            else:
                options = selector.get_all_options()
                ok = len(options) >= 3

            if ok:
                pass_count += 1
                scenario_details[scenario_name]["pass"] += 1
        except Exception as e:
            errors.append(str(e)[:200])

    return pass_count, batch_size, errors, scenario_details


def _run_session_ctx_batch(
    batch_size: int, seed: int, db_path: str, edge_mode: bool = False
) -> tuple[int, int, list[str], dict[str, dict[str, int]]]:
    random.seed(seed)
    mgr = SessionContextManager(db_path=db_path)
    pass_count = 0
    errors = []
    session_ids: list[str] = []
    scenario_details: dict[str, dict[str, int]] = {}

    for i in range(batch_size):
        st = random.randint(0, 6)
        scenario_name = [
            "create_session", "get_session", "get_context", "update_context",
            "pause_session", "serialize_deserialize", "list_sessions",
        ][st]
        if scenario_name not in scenario_details:
            scenario_details[scenario_name] = {"pass": 0, "total": 0}
        scenario_details[scenario_name]["total"] += 1

        try:
            if st == 0:
                meta = {"key": f"val_{i}"} if not edge_mode else {}
                session = mgr.create_session(metadata=meta)
                ok = session.status == SessionStatus.CREATED and len(session.id) > 0
                session_ids.append(session.id)
            elif st == 1 and session_ids:
                sid = random.choice(session_ids)
                s = mgr.get_session(sid)
                ok = s is not None and s.id == sid
            elif st == 2 and session_ids:
                sid = random.choice(session_ids)
                ctx = mgr.get_context(sid)
                ok = ctx is not None and ctx.session_id == sid
            elif st == 3 and session_ids:
                sid = random.choice(session_ids)
                ctx = mgr.get_context(sid)
                if ctx:
                    ctx.state[f"k_{i}"] = f"v_{i}"
                    ctx.add_history({"event": "update", "idx": i})
                    mgr.update_context(ctx)
                    ok = True
                else:
                    ok = False
            elif st == 4 and session_ids:
                sid = random.choice(session_ids)
                ok = mgr.pause_session(sid)
            elif st == 5 and session_ids:
                sid = random.choice(session_ids)
                blob = mgr.serialize_context(sid)
                if blob:
                    restored = mgr.deserialize_context(blob)
                    ok = restored.session_id == sid
                else:
                    ok = True
            else:
                sessions = mgr.list_sessions()
                ok = isinstance(sessions, list)

            if ok:
                pass_count += 1
                scenario_details[scenario_name]["pass"] += 1
        except Exception as e:
            errors.append(str(e)[:200])

    return pass_count, batch_size, errors, scenario_details


def _run_abandonment_batch(
    batch_size: int, seed: int, db_path: str, edge_mode: bool = False
) -> tuple[int, int, list[str], dict[str, dict[str, int]]]:
    random.seed(seed)
    detector = AbandonmentDetector(db_path=db_path, inactivity_days=7)
    pass_count = 0
    errors = []
    task_ids: list[str] = []
    scenario_details: dict[str, dict[str, int]] = {}

    for i in range(batch_size):
        st = random.randint(0, 4)
        scenario_name = [
            "register_task", "get_scenario", "get_all_scenarios",
            "update_task_progress", "detect_abandonment",
        ][st]
        if scenario_name not in scenario_details:
            scenario_details[scenario_name] = {"pass": 0, "total": 0}
        scenario_details[scenario_name]["total"] += 1

        try:
            if st == 0:
                pattern = random.choice(ALL_ABANDONMENT_PATTERNS)
                complexity = random.choice(ALL_TASK_COMPLEXITIES)
                hours = random.uniform(0.5, 100)
                task = TaskRecord(
                    id=f"task_{i}_{seed}",
                    name=random.choice(TASK_NAMES),
                    scenario_code=random.choice(["M1", "M3", "M6", None]),
                    pattern=pattern,
                    complexity=complexity,
                    status=random.choice(["PENDING", "IN_PROGRESS"]),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    last_update=datetime.now(timezone.utc).isoformat(),
                    estimated_hours=hours,
                    progress=random.uniform(0, 1),
                )
                detector.register_task(task)
                task_ids.append(task.id)
                ok = True
            elif st == 1:
                code = random.choice(["M1", "M3", "M6"])
                scenario = detector.get_scenario(code)
                ok = scenario is not None and scenario.code == code
            elif st == 2:
                scenarios = detector.get_all_scenarios()
                ok = len(scenarios) == 3
            elif st == 3 and task_ids:
                tid = random.choice(task_ids)
                progress = random.uniform(0, 1)
                ok = detector.update_task_progress(tid, progress)
            else:
                alerts = detector.detect_abandonment()
                ok = isinstance(alerts, list)

            if ok:
                pass_count += 1
                scenario_details[scenario_name]["pass"] += 1
        except Exception as e:
            errors.append(str(e)[:200])

    return pass_count, batch_size, errors, scenario_details


def _aggregate_results(
    engine_name: str,
    batch_results: list[tuple[int, int, list[str], dict[str, dict[str, int]]]],
) -> EngineTestResult:
    total_pass = 0
    total_count = 0
    all_errors: list[str] = []
    all_scenarios: dict[str, dict[str, int]] = {}

    for p, t, errs, scenarios in batch_results:
        total_pass += p
        total_count += t
        all_errors.extend(errs)
        for s_name, s_data in scenarios.items():
            if s_name not in all_scenarios:
                all_scenarios[s_name] = {"pass": 0, "total": 0}
            all_scenarios[s_name]["pass"] += s_data["pass"]
            all_scenarios[s_name]["total"] += s_data["total"]

    return EngineTestResult(
        engine=engine_name,
        pass_count=total_pass,
        total_count=total_count,
        errors=all_errors[:50],
        scenario_details=all_scenarios,
    )


def _run_layer(
    layer_name: str,
    total_count: int,
    edge_mode: bool = False,
) -> LayerResult:
    start = time.perf_counter()
    ncpu = max(1, cpu_count() - 1)

    sqlite_count = max(1000, int(total_count * SQLITE_ENGINE_RATIO))
    cpu_count_val = max(1, total_count // ncpu // 5) if total_count > ncpu * 5 else max(1, total_count // ncpu)

    cc_args = [(cpu_count_val, i * 1000 + 1, edge_mode) for i in range(ncpu * 5)]
    sv_args = [(cpu_count_val, i * 2000 + 1, edge_mode) for i in range(ncpu * 5)]
    fw_args = [(cpu_count_val, i * 3000 + 1, edge_mode) for i in range(ncpu * 5)]

    with Pool(ncpu) as pool:
        cc_results = pool.map(_run_cross_cultural_batch, cc_args)
        sv_results = pool.map(_run_supervisor_batch, sv_args)
        fw_results = pool.map(_run_framework_batch, fw_args)

    cc_agg = _aggregate_results("CrossCulturalThinkingEngine", cc_results)
    sv_agg = _aggregate_results("SupervisorAgent", sv_results)
    fw_agg = _aggregate_results("FrameworkSelector", fw_results)

    tmpdir = tempfile.mkdtemp()
    try:
        session_db = os.path.join(tmpdir, "sessions.db")
        task_db = os.path.join(tmpdir, "tasks.db")

        sqlite_batch = max(1, sqlite_count // (ncpu * 5))
        sc_results = []
        ab_results = []
        for i in range(ncpu * 5):
            sc_results.append(
                _run_session_ctx_batch(sqlite_batch, i * 4000 + 1, session_db, edge_mode)
            )
            ab_results.append(
                _run_abandonment_batch(sqlite_batch, i * 5000 + 1, task_db, edge_mode)
            )

        sc_agg = _aggregate_results("SessionContextManager", sc_results)
        ab_agg = _aggregate_results("AbandonmentDetector", ab_results)

        gc.collect()
    finally:
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass

    all_engine_results = [cc_agg, sv_agg, fw_agg, sc_agg, ab_agg]
    total_pass = sum(e.pass_count for e in all_engine_results)
    total = sum(e.total_count for e in all_engine_results)
    all_errors = []
    for e in all_engine_results:
        all_errors.extend(e.errors)

    engine_agg: dict[str, dict[str, Any]] = {}
    for e in all_engine_results:
        engine_agg[e.engine] = {
            "pass": e.pass_count,
            "total": e.total_count,
            "coverage_rate": round(e.coverage_rate, 4),
            "scenarios": e.scenario_details,
        }

    elapsed = time.perf_counter() - start
    coverage = total_pass / total * 100 if total > 0 else 0.0

    return LayerResult(
        layer=layer_name,
        total_count=total,
        pass_count=total_pass,
        coverage_rate=coverage,
        errors=all_errors[:50],
        execution_time_s=elapsed,
        engine_results=engine_agg,
    )


def _check_convergence(results: dict[str, LayerResult]) -> dict[str, Any]:
    convergence = {"overall": "UNKNOWN", "details": {}}

    if "L1" in results and "L2" in results:
        l1_rate = results["L1"].coverage_rate
        l2_rate = results["L2"].coverage_rate
        delta_l2 = abs(l2_rate - l1_rate)
        l2_ok = delta_l2 < CONVERGENCE_THRESHOLD_L2
        convergence["details"]["L2_vs_L1"] = {
            "l1_rate": l1_rate,
            "l2_rate": l2_rate,
            "delta": delta_l2,
            "threshold": CONVERGENCE_THRESHOLD_L2,
            "converged": l2_ok,
        }

    if "L2" in results and "L3" in results:
        l2_rate = results["L2"].coverage_rate
        l3_rate = results["L3"].coverage_rate
        delta_l3 = abs(l3_rate - l2_rate)
        l3_ok = delta_l3 < CONVERGENCE_THRESHOLD_L3
        convergence["details"]["L3_vs_L2"] = {
            "l2_rate": l2_rate,
            "l3_rate": l3_rate,
            "delta": delta_l3,
            "threshold": CONVERGENCE_THRESHOLD_L3,
            "converged": l3_ok,
        }

    l2_ok = convergence["details"].get("L2_vs_L1", {}).get("converged", False)
    l3_ok = convergence["details"].get("L3_vs_L2", {}).get("converged", False)
    if "L1" in results and "L2" in results and "L3" in results:
        convergence["overall"] = "CONVERGED" if (l2_ok and l3_ok) else "NOT_CONVERGED"
    elif "L1" in results and "L2" in results:
        convergence["overall"] = "PARTIAL_L2" if l2_ok else "NOT_CONVERGED"

    return convergence


def _layer_result_to_dict(lr: LayerResult) -> dict[str, Any]:
    return {
        "layer": lr.layer,
        "total_count": lr.total_count,
        "pass_count": lr.pass_count,
        "coverage_rate": round(lr.coverage_rate, 4),
        "execution_time_s": round(lr.execution_time_s, 2),
        "errors": lr.errors[:20],
        "engine_results": {
            eng: {
                "pass": data["pass"],
                "total": data["total"],
                "coverage_rate": round(data["coverage_rate"], 4),
                "scenarios": {
                    s: {"pass": v["pass"], "total": v["total"]}
                    for s, v in data["scenarios"].items()
                },
            }
            for eng, data in lr.engine_results.items()
        },
    }


def main():
    parser = argparse.ArgumentParser(description="D-100 3 Layer Testing — 5 New Engines")
    parser.add_argument(
        "--layer",
        choices=["L1", "L2", "L3", "ALL"],
        default="ALL",
        help="測試層級：L1=10M, L2=100M, L3=1B, ALL=全部（預設 ALL）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="結果輸出路徑（預設 data/d100_3layer_test_results.json）",
    )
    args = parser.parse_args()

    layers_to_run = ["L1", "L2", "L3"] if args.layer == "ALL" else [args.layer]

    print("=" * 60)
    print("D-100 3 Layer Testing — 5 新引擎")
    print("=" * 60)
    print(f"層級：{', '.join(layers_to_run)}")
    print(f"CPU 核心數：{cpu_count()}")
    print()

    results: dict[str, LayerResult] = {}

    for layer_name in layers_to_run:
        total = LAYER_SIZES[layer_name]
        edge_mode = layer_name in ("L2", "L3")
        print(f"[{layer_name}] 開始測試 — 目標 {total:,} cases {'(邊界模式)' if edge_mode else ''}")
        lr = _run_layer(layer_name, total, edge_mode=edge_mode)
        results[layer_name] = lr
        print(f"[{layer_name}] 完成 — 覆蓋率 {lr.coverage_rate:.2f}% "
              f"({lr.pass_count:,}/{lr.total_count:,}) — 耗時 {lr.execution_time_s:.2f}s")
        for eng, data in lr.engine_results.items():
            print(f"  {eng}: {data['coverage_rate']:.2f}% ({data['pass']}/{data['total']})")
        if lr.errors:
            print(f"  錯誤數量：{len(lr.errors)}（只顯示前 5 個）")
            for e in lr.errors[:5]:
                print(f"    - {e[:100]}")
        print()

    convergence = _check_convergence(results)
    print("收斂分析：")
    print(f"  整體狀態：{convergence['overall']}")
    for key, detail in convergence["details"].items():
        print(f"  {key}: delta={detail['delta']:.4f}% "
              f"(閾值 {detail['threshold']}%) → {'✅ 收斂' if detail['converged'] else '❌ 未收斂'}")
    print()

    output_path = args.output or str(
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "d100_3layer_test_results.json"
    )
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    output_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "layers_run": layers_to_run,
        "convergence": convergence,
        "results": {name: _layer_result_to_dict(lr) for name, lr in results.items()},
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"結果已保存至：{output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
