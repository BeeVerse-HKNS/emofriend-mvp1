from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class GapSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HandlingStrategy(str, Enum):
    CREATE_HANDLER = "create_handler"
    EXTEND_EXISTING = "extend_existing"
    DELEGATE = "delegate"
    IGNORE = "ignore"


class FillStatus(str, Enum):
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    FAILED = "failed"
    SKIPPED = "skipped"


GAP_SEVERITY_PRIORITY: dict[str, int] = {
    GapSeverity.CRITICAL.value: 0,
    GapSeverity.HIGH.value: 1,
    GapSeverity.MEDIUM.value: 2,
    GapSeverity.LOW.value: 3,
}


@dataclass
class CoverageGap:
    gap_id: str
    category: str
    severity: GapSeverity
    dimensions_missing: list[str]
    count: int
    priority: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TargetedHandler:
    handler_id: str
    target_gap: str
    handling_strategy: HandlingStrategy
    effectiveness_score: float = 0.0
    dimensions_covered: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FillResult:
    gap_id: str
    handler_id: str
    status: FillStatus
    coverage_improvement: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class GapScanner:
    def __init__(self):
        self._scan_history: list[dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def scan_by_category(self, coverage_data: dict[str, Any]) -> list[CoverageGap]:
        categories = coverage_data.get("categories", {})
        gaps = []
        gap_counter = 0

        for category_name, category_info in categories.items():
            coverage_pct = category_info.get("coverage", 1.0)
            if coverage_pct < 1.0:
                gap_counter += 1
                missing_dims = category_info.get("missing_dimensions", [])
                count = category_info.get("gap_count", 1)
                severity = self._classify_severity(coverage_pct)
                priority = self._calculate_priority(coverage_pct, count, severity)

                gap = CoverageGap(
                    gap_id=f"GAP-{gap_counter:04d}",
                    category=category_name,
                    severity=severity,
                    dimensions_missing=missing_dims,
                    count=count,
                    priority=priority,
                )
                gaps.append(gap)

        gaps.sort(key=lambda g: g.priority, reverse=True)
        self._scan_history.append({
            "scan_type": "by_category",
            "gaps_found": len(gaps),
            "timestamp": datetime.now().isoformat(),
        })
        return gaps

    def scan_by_severity(self, coverage_data: dict[str, Any]) -> list[CoverageGap]:
        categories = coverage_data.get("categories", {})
        gaps = []
        gap_counter = 0

        for category_name, category_info in categories.items():
            severity_levels = category_info.get("severity_gaps", {})
            for sev_level, sev_info in severity_levels.items():
                coverage_pct = sev_info.get("coverage", 1.0)
                if coverage_pct < 1.0:
                    gap_counter += 1
                    missing_dims = sev_info.get("missing_dimensions", [])
                    count = sev_info.get("gap_count", 1)
                    severity = GapSeverity(sev_level) if sev_level in [e.value for e in GapSeverity] else GapSeverity.MEDIUM
                    priority = self._calculate_priority(coverage_pct, count, severity)

                    gap = CoverageGap(
                        gap_id=f"GAP-{gap_counter:04d}",
                        category=category_name,
                        severity=severity,
                        dimensions_missing=missing_dims,
                        count=count,
                        priority=priority,
                    )
                    gaps.append(gap)

        gaps.sort(key=lambda g: GAP_SEVERITY_PRIORITY.get(g.severity.value, 99))
        self._scan_history.append({
            "scan_type": "by_severity",
            "gaps_found": len(gaps),
            "timestamp": datetime.now().isoformat(),
        })
        return gaps

    def scan_by_dimension(self, coverage_data: dict[str, Any]) -> list[CoverageGap]:
        dimensions = coverage_data.get("dimensions", {})
        gaps = []
        gap_counter = 0

        for dim_name, dim_info in dimensions.items():
            coverage_pct = dim_info.get("coverage", 1.0)
            if coverage_pct < 1.0:
                gap_counter += 1
                affected_categories = dim_info.get("affected_categories", ["unknown"])
                count = dim_info.get("gap_count", 1)
                severity = self._classify_severity(coverage_pct)
                priority = self._calculate_priority(coverage_pct, count, severity)

                for cat in affected_categories:
                    gap = CoverageGap(
                        gap_id=f"GAP-{gap_counter:04d}",
                        category=cat,
                        severity=severity,
                        dimensions_missing=[dim_name],
                        count=count,
                        priority=priority,
                    )
                    gaps.append(gap)

        gaps.sort(key=lambda g: g.priority, reverse=True)
        self._scan_history.append({
            "scan_type": "by_dimension",
            "gaps_found": len(gaps),
            "timestamp": datetime.now().isoformat(),
        })
        return gaps

    def _classify_severity(self, coverage_pct: float) -> GapSeverity:
        if coverage_pct < 0.25:
            return GapSeverity.CRITICAL
        elif coverage_pct < 0.5:
            return GapSeverity.HIGH
        elif coverage_pct < 0.75:
            return GapSeverity.MEDIUM
        return GapSeverity.LOW

    def _calculate_priority(self, coverage_pct: float, count: int, severity: GapSeverity) -> float:
        severity_weight = {
            GapSeverity.CRITICAL.value: 4.0,
            GapSeverity.HIGH.value: 3.0,
            GapSeverity.MEDIUM.value: 2.0,
            GapSeverity.LOW.value: 1.0,
        }
        gap_magnitude = 1.0 - coverage_pct
        return gap_magnitude * severity_weight.get(severity.value, 1.0) * min(count, 100)


class GapFillerSystem:
    def __init__(self):
        self.scanner = GapScanner()
        self.filled_gaps: list[FillResult] = []
        self._handler_counter: int = 0
        self._handlers: dict[str, TargetedHandler] = {}
        self.logger = logging.getLogger(__name__)

    def scan_gaps(self, coverage_data: dict[str, Any]) -> list[CoverageGap]:
        category_gaps = self.scanner.scan_by_category(coverage_data)
        severity_gaps = self.scanner.scan_by_severity(coverage_data)
        dimension_gaps = self.scanner.scan_by_dimension(coverage_data)

        all_gaps = category_gaps + severity_gaps + dimension_gaps
        seen_ids: set[str] = set()
        unique_gaps = []
        for gap in all_gaps:
            key = f"{gap.category}:{','.join(sorted(gap.dimensions_missing))}"
            if key not in seen_ids:
                seen_ids.add(key)
                unique_gaps.append(gap)

        unique_gaps.sort(key=lambda g: g.priority, reverse=True)
        return unique_gaps

    def create_handler(self, gap: CoverageGap) -> TargetedHandler:
        self._handler_counter += 1
        handler_id = f"HDL-{self._handler_counter:04d}"

        strategy = self._select_strategy(gap)
        effectiveness = self._estimate_effectiveness(gap, strategy)

        handler = TargetedHandler(
            handler_id=handler_id,
            target_gap=gap.gap_id,
            handling_strategy=strategy,
            effectiveness_score=effectiveness,
            dimensions_covered=gap.dimensions_missing,
        )

        self._handlers[handler_id] = handler
        self.logger.info(
            "handler_created",
            extra={
                "handler_id": handler_id,
                "target_gap": gap.gap_id,
                "strategy": strategy.value,
                "effectiveness": effectiveness,
            },
        )
        return handler

    def fill_gap(self, handler: TargetedHandler) -> dict[str, Any]:
        if handler.effectiveness_score >= 0.8:
            status = FillStatus.FILLED
            improvement = handler.effectiveness_score
        elif handler.effectiveness_score >= 0.5:
            status = FillStatus.PARTIALLY_FILLED
            improvement = handler.effectiveness_score
        elif handler.effectiveness_score >= 0.2:
            status = FillStatus.FAILED
            improvement = 0.0
        else:
            status = FillStatus.SKIPPED
            improvement = 0.0

        result = FillResult(
            gap_id=handler.target_gap,
            handler_id=handler.handler_id,
            status=status,
            coverage_improvement=improvement,
            details={
                "strategy": handler.handling_strategy.value,
                "dimensions_covered": handler.dimensions_covered,
                "effectiveness_score": handler.effectiveness_score,
            },
        )

        self.filled_gaps.append(result)
        self.logger.info(
            "gap_filled",
            extra={
                "gap_id": handler.target_gap,
                "handler_id": handler.handler_id,
                "status": status.value,
                "improvement": improvement,
            },
        )
        return {
            "gap_id": result.gap_id,
            "handler_id": result.handler_id,
            "status": result.status.value,
            "coverage_improvement": result.coverage_improvement,
            "details": result.details,
            "timestamp": result.timestamp,
        }

    def batch_fill(self, gaps: list[CoverageGap]) -> list[dict[str, Any]]:
        results = []
        for gap in gaps:
            handler = self.create_handler(gap)
            result = self.fill_gap(handler)
            results.append(result)
        return results

    def get_fill_summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        total_improvement = 0.0
        for result in self.filled_gaps:
            status_counts[result.status.value] = status_counts.get(result.status.value, 0) + 1
            total_improvement += result.coverage_improvement

        return {
            "total_gaps_processed": len(self.filled_gaps),
            "status_distribution": status_counts,
            "total_coverage_improvement": round(total_improvement, 4),
            "average_improvement": round(total_improvement / len(self.filled_gaps), 4) if self.filled_gaps else 0.0,
            "handlers_created": len(self._handlers),
        }

    def _select_strategy(self, gap: CoverageGap) -> HandlingStrategy:
        if gap.severity == GapSeverity.CRITICAL:
            return HandlingStrategy.CREATE_HANDLER
        elif gap.severity == GapSeverity.HIGH:
            return HandlingStrategy.EXTEND_EXISTING
        elif gap.count > 10:
            return HandlingStrategy.DELEGATE
        return HandlingStrategy.CREATE_HANDLER

    def _estimate_effectiveness(self, gap: CoverageGap, strategy: HandlingStrategy) -> float:
        base_scores = {
            HandlingStrategy.CREATE_HANDLER: 0.9,
            HandlingStrategy.EXTEND_EXISTING: 0.75,
            HandlingStrategy.DELEGATE: 0.6,
            HandlingStrategy.IGNORE: 0.0,
        }
        base = base_scores.get(strategy, 0.5)
        dim_factor = min(len(gap.dimensions_missing) / 5.0, 1.0)
        severity_factor = {
            GapSeverity.CRITICAL.value: 1.0,
            GapSeverity.HIGH.value: 0.95,
            GapSeverity.MEDIUM.value: 0.85,
            GapSeverity.LOW.value: 0.7,
        }.get(gap.severity.value, 0.8)

        return round(base * (1.0 - dim_factor * 0.2) * severity_factor, 4)
