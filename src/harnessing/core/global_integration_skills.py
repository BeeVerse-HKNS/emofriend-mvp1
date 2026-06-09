#!/usr/bin/env python3
"""
Global Integration Skills — 全球 AI Agent 最佳實踐整合框架

整合 Phase 3 的全球特色技巧，提供對國際主流框架和最佳實踐的支持。

KB-24 Phase 3 實作內容：
| # | 技巧 | 類別 | 實作方式 |
|---|------|------|---------|
| 1 | Claude Code 架構 | 架構 | ClaudeCodeAdapter |
| 2 | Anthropic Agent SDK | SDK | AnthropicAdapter |
| 3 | Self-Improvement | 學習 | SelfImprovementEngine |
| 4 | Cost Control | 監控 | CostControlSystem |
| 5 | SLA Monitoring | 監控 | SLAMonitor |
| 6 | Observability | 可觀測性 | ObservabilitySystem |
| 7 | Dashboard | 可視化 | SimpleDashboard |
| 8 | Latency Tracking | 監控 | LatencyTracker |

遵循零外部依賴原則
"""

import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    name: str
    type: MetricType
    value: float
    timestamp: str
    tags: Dict[str, str] = field(default_factory=dict)


class SelfImprovementEngine:
    """
    自我改進引擎
    根據歷史表現自動調整策略
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.improvements_dir = self.base_path / "self_improvements"
        self.improvements_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self._rules: List[Dict] = []
        self._history: List[Dict] = []
        self._load_history()

    def _load_history(self) -> None:
        history_path = self.improvements_dir / "history.json"
        if history_path.exists():
            with open(history_path, "r", encoding="utf-8") as f:
                self._history = json.load(f)

    def _save_history(self) -> None:
        history_path = self.improvements_dir / "history.json"
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(self._history, f, indent=2)

    def record_outcome(self, action: str, outcome: str, context: Dict = None) -> None:
        record = {
            "action": action,
            "outcome": outcome,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
        }
        self._history.append(record)
        self._save_history()

        self._analyze_and_generate_rules()

    def _analyze_and_generate_rules(self) -> None:
        recent = self._history[-100:]

        success_actions = [r for r in recent if r["outcome"] == "success"]
        failure_actions = [r for r in recent if r["outcome"] == "failure"]

        if len(recent) >= 10:
            success_rate = len(success_actions) / len(recent)
            if success_rate < 0.5:
                self.logger.warning(f"Success rate below 50%: {success_rate:.1%}")

        if len(failure_actions) >= 3:
            failed_actions = [r["action"] for r in failure_actions[-3:]]
            if len(set(failed_actions)) == 1:
                rule = {
                    "type": "avoid",
                    "action": failed_actions[0],
                    "reason": "Repeated failures detected",
                    "suggestion": "Consider alternative approach",
                    "timestamp": datetime.now().isoformat(),
                }
                self._rules.append(rule)
                self.logger.info(f"Generated improvement rule: {rule}")

    def get_recommended_approach(self, task_type: str) -> Dict:
        successful = [
            r for r in self._history[-50:]
            if r["outcome"] == "success" and r.get("context", {}).get("task_type") == task_type
        ]

        if successful:
            return {
                "recommended": True,
                "based_on": len(successful),
                "actions": [r["action"] for r in successful[:5]],
            }

        return {
            "recommended": False,
            "reason": "No historical data for this task type",
        }

    def get_rules(self) -> List[Dict]:
        return self._rules.copy()

    def get_statistics(self) -> Dict:
        total = len(self._history)
        if total == 0:
            return {"total": 0, "success_rate": 0}

        success = len([r for r in self._history if r["outcome"] == "success"])
        return {
            "total": total,
            "success": success,
            "failure": total - success,
            "success_rate": success / total,
            "rules_generated": len(self._rules),
        }


class CostControlSystem:
    """
    成本控制系統
    追蹤並控制 API 使用成本
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.cost_dir = self.base_path / "cost_control"
        self.cost_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

        self._costs: Dict[str, List[Dict]] = {}
        self._budgets: Dict[str, float] = {}
        self._load_costs()

    def _load_costs(self) -> None:
        costs_path = self.cost_dir / "costs.json"
        if costs_path.exists():
            with open(costs_path, "r", encoding="utf-8") as f:
                self._costs = json.load(f)

    def _save_costs(self) -> None:
        costs_path = self.cost_dir / "costs.json"
        with open(costs_path, "w", encoding="utf-8") as f:
            json.dump(self._costs, f, indent=2)

    def set_budget(self, model: str, daily_budget: float) -> None:
        self._budgets[model] = daily_budget

    def record_cost(self, model: str, cost: float, tokens: int,
                   operation: str = "inference") -> Dict:
        today = datetime.now().strftime("%Y-%m-%d")

        if model not in self._costs:
            self._costs[model] = []
        self._costs[model].append({
            "date": today,
            "cost": cost,
            "tokens": tokens,
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
        })
        self._save_costs()

        daily_spent = self.get_daily_cost(model)
        budget = self._budgets.get(model, float("inf"))

        result = {
            "recorded": True,
            "daily_spent": daily_spent,
            "budget": budget,
            "over_budget": daily_spent > budget,
        }

        if result["over_budget"]:
            self.logger.warning(f"Model {model} over budget: ${daily_spent:.4f} > ${budget:.4f}")

        return result

    def get_daily_cost(self, model: str) -> float:
        today = datetime.now().strftime("%Y-%m-%d")
        costs = self._costs.get(model, [])
        return sum(c["cost"] for c in costs if c["date"] == today)

    def get_monthly_cost(self, model: str) -> float:
        current_month = datetime.now().strftime("%Y-%m")
        costs = self._costs.get(model, [])
        return sum(
            c["cost"] for c in costs
            if c["date"].startswith(current_month)
        )

    def get_cost_breakdown(self) -> Dict:
        breakdown = {}
        for model, costs in self._costs.items():
            total = sum(c["cost"] for c in costs)
            breakdown[model] = {
                "total_cost": total,
                "total_tokens": sum(c["tokens"] for c in costs),
                "request_count": len(costs),
            }
        return breakdown


class SLAMonitor:
    """
    SLA 監控系統
    追蹤服務可用性和響應時間
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.sla_dir = self.base_path / "sla_monitor"
        self.sla_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

        self._sla_targets: Dict[str, Dict] = {}
        self._measurements: Dict[str, List[Dict]] = {}

    def set_sla_target(self, service: str, availability_target: float,
                      latency_p95_target: float) -> None:
        self._sla_targets[service] = {
            "availability": availability_target,
            "latency_p95": latency_p95_target,
        }

    def record_request(self, service: str, success: bool, latency_ms: float) -> None:
        if service not in self._measurements:
            self._measurements[service] = []

        self._measurements[service].append({
            "success": success,
            "latency_ms": latency_ms,
            "timestamp": datetime.now().isoformat(),
        })

        self._cleanup_old_measurements(service)

    def _cleanup_old_measurements(self, service: str) -> None:
        cutoff = datetime.now() - timedelta(days=7)
        self._measurements[service] = [
            m for m in self._measurements[service]
            if datetime.fromisoformat(m["timestamp"]) > cutoff
        ]

    def get_sla_status(self, service: str) -> Dict:
        if service not in self._measurements:
            return {"service": service, "status": "no_data"}

        measurements = self._measurements[service]
        if not measurements:
            return {"service": service, "status": "no_data"}

        total = len(measurements)
        successful = len([m for m in measurements if m["success"]])
        latencies = sorted([m["latency_ms"] for m in measurements])
        p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else 0

        availability = successful / total if total > 0 else 0
        target = self._sla_targets.get(service, {"availability": 0.99, "latency_p95": 1000})

        return {
            "service": service,
            "status": "healthy" if availability >= target["availability"] else "degraded",
            "availability": availability,
            "target_availability": target["availability"],
            "latency_p95": p95_latency,
            "target_latency_p95": target["latency_p95"],
            "total_requests": total,
        }

    def get_all_sla_status(self) -> List[Dict]:
        return [self.get_sla_status(s) for s in self._measurements.keys()]


class ObservabilitySystem:
    """
    可觀測性系統
    整合 Metrics、Traces、Logs
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent / "data"
        self.base_path = Path(base_path)
        self.obs_dir = self.base_path / "observability"
        self.obs_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

        self._metrics: Dict[str, List[Metric]] = {}
        self._traces: List[Dict] = []
        self._lock = threading.Lock()

    def record_metric(self, name: str, value: float,
                     metric_type: MetricType = MetricType.GAUGE,
                     tags: Dict[str, str] = None) -> None:
        with self._lock:
            metric = Metric(
                name=name,
                type=metric_type,
                value=value,
                timestamp=datetime.now().isoformat(),
                tags=tags or {},
            )
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(metric)

            self._cleanup_old_metrics(name)

    def _cleanup_old_metrics(self, name: str) -> None:
        cutoff = datetime.now() - timedelta(hours=24)
        self._metrics[name] = [
            m for m in self._metrics[name]
            if datetime.fromisoformat(m.timestamp) > cutoff
        ]

    def start_trace(self, operation: str, context: Dict = None) -> str:
        trace_id = f"{operation}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        trace = {
            "trace_id": trace_id,
            "operation": operation,
            "context": context or {},
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "spans": [],
        }
        with self._lock:
            self._traces.append(trace)
        return trace_id

    def end_trace(self, trace_id: str, success: bool = True) -> None:
        with self._lock:
            for trace in self._traces:
                if trace["trace_id"] == trace_id:
                    trace["end_time"] = datetime.now().isoformat()
                    trace["success"] = success
                    break

    def add_span(self, trace_id: str, span_name: str,
                duration_ms: float, metadata: Dict = None) -> None:
        with self._lock:
            for trace in self._traces:
                if trace["trace_id"] == trace_id:
                    trace["spans"].append({
                        "name": span_name,
                        "duration_ms": duration_ms,
                        "metadata": metadata or {},
                        "timestamp": datetime.now().isoformat(),
                    })
                    break

    def get_metrics_summary(self) -> Dict:
        with self._lock:
            summary = {}
            for name, metrics in self._metrics.items():
                if not metrics:
                    continue
                values = [m.value for m in metrics]
                summary[name] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "last": values[-1],
                }
            return summary

    def get_recent_traces(self, limit: int = 100) -> List[Dict]:
        with self._lock:
            return sorted(
                self._traces,
                key=lambda t: t.get("start_time", ""),
                reverse=True,
            )[:limit]


class LatencyTracker:
    """
    延遲追蹤器
    記錄各操作響應時間
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._measurements: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def record(self, operation: str, latency_ms: float) -> None:
        with self._lock:
            if operation not in self._measurements:
                self._measurements[operation] = []
            self._measurements[operation].append(latency_ms)

            if len(self._measurements[operation]) > 1000:
                self._measurements[operation] = self._measurements[operation][-1000:]

    def get_percentiles(self, operation: str) -> Dict:
        with self._lock:
            latencies = self._measurements.get(operation, [])
            if not latencies:
                return {"p50": 0, "p95": 0, "p99": 0}

            sorted_latencies = sorted(latencies)
            return {
                "p50": sorted_latencies[int(len(sorted_latencies) * 0.50)],
                "p95": sorted_latencies[int(len(sorted_latencies) * 0.95)],
                "p99": sorted_latencies[int(len(sorted_latencies) * 0.99)],
            }

    def get_summary(self) -> Dict:
        with self._lock:
            summary = {}
            for operation, latencies in self._measurements.items():
                if latencies:
                    sorted_lat = sorted(latencies)
                    summary[operation] = {
                        "count": len(latencies),
                        "avg": sum(latencies) / len(latencies),
                        "p50": sorted_lat[int(len(sorted_lat) * 0.50)],
                        "p95": sorted_lat[int(len(sorted_lat) * 0.95)],
                    }
            return summary


class SimpleDashboard:
    """
    簡單監控儀表板
    生成 HTML 格式的監控頁面
    """

    def __init__(self, observability: ObservabilitySystem,
                 cost_control: CostControlSystem,
                 sla_monitor: SLAMonitor):
        self.obs = observability
        self.cost = cost_control
        self.sla = sla_monitor

    def generate_html(self) -> str:
        metrics = self.obs.get_metrics_summary()
        costs = self.cost.get_cost_breakdown()
        sla_status = self.sla.get_all_sla_status()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Harnessing Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; }}
        .card {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
        .metric-label {{ color: #666; font-size: 14px; }}
        .status {{ display: inline-block; padding: 4px 12px; border-radius: 4px; }}
        .status-healthy {{ background: #4CAF50; color: white; }}
        .status-degraded {{ background: #FF9800; color: white; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f0f0f0; }}
    </style>
</head>
<body>
    <h1>Harnessing 監控儀表板</h1>
    <p>最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <div class="card">
        <h2>成本概覽</h2>
"""

        for model, data in costs.items():
            html += f"""
        <div class="metric">
            <div class="metric-value">${data['total_cost']:.4f}</div>
            <div class="metric-label">{model}</div>
        </div>
"""

        html += """
    </div>

    <div class="card">
        <h2>SLA 狀態</h2>
        <table>
            <tr>
                <th>服務</th>
                <th>狀態</th>
                <th>可用性</th>
                <th>P95 延遲</th>
            </tr>
"""

        for status in sla_status:
            status_class = "status-healthy" if status["status"] == "healthy" else "status-degraded"
            html += f"""
            <tr>
                <td>{status['service']}</td>
                <td><span class="status {status_class}">{status['status']}</span></td>
                <td>{status['availability']:.2%}</td>
                <td>{status.get('latency_p95', 0):.1f}ms</td>
            </tr>
"""

        html += """
        </table>
    </div>

    <div class="card">
        <h2>關鍵指標</h2>
"""

        for name, data in metrics.items():
            html += f"""
        <div class="metric">
            <div class="metric-value">{data['avg']:.2f}</div>
            <div class="metric-label">{name}</div>
        </div>
"""

        html += """
    </div>
</body>
</html>
"""
        return html

    def save_html(self, path: Path) -> None:
        html = self.generate_html()
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)


class ClaudeCodeAdapter:
    """
    Claude Code 架構適配器
    整合 Claude Code 的最佳實踐
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def apply_best_practices(self, task: Dict) -> Dict:
        recommendations = []

        if task.get("long_running"):
            recommendations.append({
                "practice": "Checkpoint-Resume",
                "reason": "Long-running task needs state persistence",
            })

        if task.get("risky_operation"):
            recommendations.append({
                "practice": "Human-in-the-Loop",
                "reason": "Risky operation requires approval",
            })

        if task.get("complex"):
            recommendations.append({
                "practice": "Goal Anchoring",
                "reason": "Complex task needs goal tracking",
            })

        return {
            "task": task,
            "recommendations": recommendations,
        }


class AnthropicAdapter:
    """
    Anthropic Agent SDK 適配器
    整合 Anthropic 官方框架的最佳實踐
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def apply_best_practices(self, task: Dict) -> Dict:
        recommendations = []

        if task.get("multi_step"):
            recommendations.append({
                "practice": "Tool Use Chain",
                "reason": "Multi-step task benefits from tool chaining",
            })

        if task.get("reasoning"):
            recommendations.append({
                "practice": "Extended Thinking",
                "reason": "Reasoning task benefits from extended thinking",
            })

        return {
            "task": task,
            "recommendations": recommendations,
        }


class GlobalIntegrationSkills:
    """
    全球整合技能統一入口
    整合所有 Phase 3 全球特色技巧
    """

    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent

        self.base_path = Path(base_path)
        data_path = self.base_path / "data"

        self.self_improvement = SelfImprovementEngine(data_path)
        self.cost_control = CostControlSystem(data_path)
        self.sla_monitor = SLAMonitor(data_path)
        self.observability = ObservabilitySystem(data_path)
        self.latency_tracker = LatencyTracker()
        self.dashboard = SimpleDashboard(
            self.observability, self.cost_control, self.sla_monitor
        )
        self.claude_adapter = ClaudeCodeAdapter()
        self.anthropic_adapter = AnthropicAdapter()

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def get_skills_status(self) -> Dict:
        return {
            "self_improvement": self.self_improvement.get_statistics(),
            "cost_control": self.cost_control.get_cost_breakdown(),
            "sla_status": self.sla_monitor.get_all_sla_status(),
            "metrics_summary": self.observability.get_metrics_summary(),
            "latency_summary": self.latency_tracker.get_summary(),
        }

    def generate_dashboard(self, output_path: Path = None) -> str:
        if output_path is None:
            output_path = self.base_path / "dashboard.html"
        self.dashboard.save_html(output_path)
        return str(output_path)


def main():
    skills = GlobalIntegrationSkills()
    print("Global Integration Skills initialized")
    print(json.dumps(skills.get_skills_status(), indent=2, default=str))


if __name__ == "__main__":
    main()
