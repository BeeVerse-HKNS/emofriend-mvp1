from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TimeHorizon(str, Enum):
    NOW = "now_2026"
    NEAR = "near_2027_2028"
    MID = "mid_2029_2031"
    FAR = "far_2032_2036"


class CapabilityCategory(str, Enum):
    REASONING = "reasoning"
    MEMORY = "memory"
    PLANNING = "planning"
    CREATIVITY = "creativity"
    AUTOMATION = "automation"
    COLLABORATION = "collaboration"
    SAFETY = "safety"
    LEARNING = "learning"
    PERCEPTION = "perception"
    ACTION = "action"


class GapPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MilestoneStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    AT_RISK = "at_risk"


class ReadinessStatus(str, Enum):
    NOT_READY = "not_ready"
    PARTIAL = "partial"
    READY = "ready"


HORIZON_YEAR_MAP: dict[TimeHorizon, int] = {
    TimeHorizon.NOW: 2026,
    TimeHorizon.NEAR: 2028,
    TimeHorizon.MID: 2031,
    TimeHorizon.FAR: 2036,
}


@dataclass
class Capability:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = ""
    category: CapabilityCategory = CapabilityCategory.REASONING
    current_maturity: float = 0.0
    projected_maturity: dict[TimeHorizon, float] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class Trend:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = ""
    category: CapabilityCategory = CapabilityCategory.REASONING
    current_velocity: float = 0.0
    acceleration: float = 0.0
    evidence_count: int = 0
    confidence: float = 0.0


@dataclass
class Gap:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = ""
    category: CapabilityCategory = CapabilityCategory.REASONING
    current_coverage: float = 0.0
    required_coverage: float = 0.0
    gap_size: float = 0.0
    time_horizon: TimeHorizon = TimeHorizon.NOW
    priority: GapPriority = GapPriority.MEDIUM


@dataclass
class Milestone:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = ""
    target_year: int = 2026
    category: CapabilityCategory = CapabilityCategory.REASONING
    description: str = ""
    prerequisites: list[str] = field(default_factory=list)
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED


@dataclass
class ReadinessItem:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = ""
    category: CapabilityCategory = CapabilityCategory.REASONING
    current_status: ReadinessStatus = ReadinessStatus.NOT_READY
    required_by_year: int = 2026
    action_needed: str = ""


@dataclass
class ProjectionResult:
    capabilities_by_horizon: dict[TimeHorizon, list[Capability]] = field(default_factory=dict)
    gaps: list[Gap] = field(default_factory=list)
    readiness_items: list[ReadinessItem] = field(default_factory=list)
    roadmap: list[Milestone] = field(default_factory=list)
    critical_gaps: list[Gap] = field(default_factory=list)
    immediate_actions: list[ReadinessItem] = field(default_factory=list)


class TrendExtrapolator:
    def __init__(self) -> None:
        self._trends: dict[str, Trend] = {}

    def add_trend(self, trend: Trend) -> str:
        self._trends[trend.id] = trend
        return trend.id

    def get_all_trends(self) -> list[Trend]:
        return list(self._trends.values())

    def extrapolate(self, category: CapabilityCategory, horizon: TimeHorizon) -> list[Capability]:
        category_trends = [t for t in self._trends.values() if t.category == category]
        if not category_trends:
            return []

        target_year = HORIZON_YEAR_MAP[horizon]
        years_delta = target_year - 2026
        results: list[Capability] = []

        for trend in category_trends:
            linear = trend.current_velocity * years_delta
            exponential = trend.current_velocity * (1.0 + trend.acceleration) ** years_delta - trend.current_velocity
            blend = min(1.0, trend.confidence)
            projected = linear * (1.0 - blend * 0.3) + exponential * (blend * 0.3)
            projected_maturity = min(1.0, max(0.0, projected))

            projected_dict: dict[TimeHorizon, float] = {}
            for h in TimeHorizon:
                h_year = HORIZON_YEAR_MAP[h]
                h_delta = h_year - 2026
                h_linear = trend.current_velocity * h_delta
                h_exp = trend.current_velocity * (1.0 + trend.acceleration) ** h_delta - trend.current_velocity
                h_val = h_linear * (1.0 - blend * 0.3) + h_exp * (blend * 0.3)
                projected_dict[h] = round(min(1.0, max(0.0, h_val)), 4)

            cap = Capability(
                name=trend.name,
                category=trend.category,
                current_maturity=round(min(1.0, max(0.0, trend.current_velocity)), 4),
                projected_maturity=projected_dict,
                description=f"Extrapolated from trend: {trend.name}",
            )
            results.append(cap)

        return results


class GapForecaster:
    def __init__(self) -> None:
        self._gaps: list[Gap] = []

    def forecast(self, current_capabilities: list[Capability], target_year: int) -> list[Gap]:
        self._gaps = []
        horizon = self._year_to_horizon(target_year)

        for cap in current_capabilities:
            projected = cap.projected_maturity.get(horizon, cap.current_maturity)
            required = 0.8 if target_year <= 2028 else 0.9 if target_year <= 2031 else 0.95
            gap_size = max(0.0, required - projected)

            if gap_size > 0.01:
                priority = GapPriority.CRITICAL if gap_size > 0.4 else GapPriority.HIGH if gap_size > 0.25 else GapPriority.MEDIUM if gap_size > 0.1 else GapPriority.LOW
                gap = Gap(
                    name=f"{cap.name} gap",
                    category=cap.category,
                    current_coverage=round(projected, 4),
                    required_coverage=round(required, 4),
                    gap_size=round(gap_size, 4),
                    time_horizon=horizon,
                    priority=priority,
                )
                self._gaps.append(gap)

        return self._gaps

    def prioritize_gaps(self, gaps: list[Gap]) -> list[Gap]:
        priority_order = {GapPriority.CRITICAL: 0, GapPriority.HIGH: 1, GapPriority.MEDIUM: 2, GapPriority.LOW: 3}
        return sorted(gaps, key=lambda g: (priority_order.get(g.priority, 99), -g.gap_size))

    def get_critical_gaps(self) -> list[Gap]:
        return [g for g in self._gaps if g.priority == GapPriority.CRITICAL]

    def _year_to_horizon(self, year: int) -> TimeHorizon:
        if year <= 2026:
            return TimeHorizon.NOW
        elif year <= 2028:
            return TimeHorizon.NEAR
        elif year <= 2031:
            return TimeHorizon.MID
        return TimeHorizon.FAR


class ReadinessBuilder:
    def __init__(self) -> None:
        self._items: list[ReadinessItem] = []

    def assess_readiness(self, gaps: list[Gap]) -> list[ReadinessItem]:
        self._items = []
        for gap in gaps:
            if gap.gap_size > 0.4:
                status = ReadinessStatus.NOT_READY
                action = f"Urgent: build {gap.category.value} capability from {gap.current_coverage:.0%} to {gap.required_coverage:.0%}"
            elif gap.gap_size > 0.15:
                status = ReadinessStatus.PARTIAL
                action = f"Accelerate {gap.category.value} capability development"
            else:
                status = ReadinessStatus.READY
                action = f"Monitor {gap.category.value} capability trajectory"

            required_year = HORIZON_YEAR_MAP.get(gap.time_horizon, 2026)
            item = ReadinessItem(
                name=f"Readiness: {gap.name}",
                category=gap.category,
                current_status=status,
                required_by_year=required_year,
                action_needed=action,
            )
            self._items.append(item)

        return self._items

    def build_action_plan(self, readiness_items: list[ReadinessItem]) -> list[dict]:
        plan: list[dict] = []
        sorted_items = sorted(readiness_items, key=lambda r: r.required_by_year)
        for item in sorted_items:
            plan.append({
                "name": item.name,
                "category": item.category.value,
                "status": item.current_status.value,
                "required_by": item.required_by_year,
                "action": item.action_needed,
            })
        return plan

    def get_immediate_actions(self) -> list[ReadinessItem]:
        return [i for i in self._items if i.current_status == ReadinessStatus.NOT_READY]


class MilestoneTracker:
    def __init__(self) -> None:
        self._milestones: dict[str, Milestone] = {}

    def add_milestone(self, milestone: Milestone) -> str:
        self._milestones[milestone.id] = milestone
        return milestone.id

    def update_status(self, milestone_id: str, status: str) -> bool:
        ms = self._milestones.get(milestone_id)
        if ms is None:
            return False
        try:
            ms.status = MilestoneStatus(status)
            return True
        except ValueError:
            return False

    def get_milestones_by_year(self, year: int) -> list[Milestone]:
        return [m for m in self._milestones.values() if m.target_year == year]

    def get_roadmap(self) -> list[Milestone]:
        return sorted(self._milestones.values(), key=lambda m: m.target_year)

    def get_at_risk(self) -> list[Milestone]:
        return [m for m in self._milestones.values() if m.status == MilestoneStatus.AT_RISK]


class TenYearProjectionEngine:
    def __init__(self) -> None:
        self.trend_extrapolator = TrendExtrapolator()
        self.gap_forecaster = GapForecaster()
        self.readiness_builder = ReadinessBuilder()
        self.milestone_tracker = MilestoneTracker()
        self._populate_default_data()

    def _populate_default_data(self) -> None:
        default_capabilities = [
            Capability(name="Chain-of-Thought Reasoning", category=CapabilityCategory.REASONING, current_maturity=0.65, description="Multi-step logical reasoning"),
            Capability(name="Long-Term Memory", category=CapabilityCategory.MEMORY, current_maturity=0.45, description="Persistent context across sessions"),
            Capability(name="Multi-Step Planning", category=CapabilityCategory.PLANNING, current_maturity=0.55, description="Decompose goals into executable plans"),
            Capability(name="Creative Generation", category=CapabilityCategory.CREATIVITY, current_maturity=0.60, description="Novel and diverse content creation"),
            Capability(name="Workflow Automation", category=CapabilityCategory.AUTOMATION, current_maturity=0.50, description="End-to-end task execution"),
            Capability(name="Multi-Agent Collaboration", category=CapabilityCategory.COLLABORATION, current_maturity=0.35, description="Coordinate multiple agents"),
            Capability(name="Safety Guardrails", category=CapabilityCategory.SAFETY, current_maturity=0.70, description="Prevent harmful outputs and actions"),
            Capability(name="Self-Improvement", category=CapabilityCategory.LEARNING, current_maturity=0.40, description="Learn from experience and feedback"),
            Capability(name="Multi-Modal Perception", category=CapabilityCategory.PERCEPTION, current_maturity=0.55, description="Process text, image, audio, video"),
            Capability(name="Tool Use & API Integration", category=CapabilityCategory.ACTION, current_maturity=0.60, description="Interact with external tools and APIs"),
        ]
        self._default_capabilities = default_capabilities

        default_trends = [
            Trend(name="Reasoning Scaling", category=CapabilityCategory.REASONING, current_velocity=0.08, acceleration=0.12, evidence_count=150, confidence=0.85),
            Trend(name="Memory Architecture Evolution", category=CapabilityCategory.MEMORY, current_velocity=0.06, acceleration=0.18, evidence_count=80, confidence=0.70),
            Trend(name="Planning Complexity Growth", category=CapabilityCategory.PLANNING, current_velocity=0.07, acceleration=0.10, evidence_count=120, confidence=0.80),
            Trend(name="Creative Model Divergence", category=CapabilityCategory.CREATIVITY, current_velocity=0.05, acceleration=0.08, evidence_count=60, confidence=0.65),
            Trend(name="Automation Adoption Curve", category=CapabilityCategory.AUTOMATION, current_velocity=0.09, acceleration=0.15, evidence_count=200, confidence=0.90),
        ]
        for t in default_trends:
            self.trend_extrapolator.add_trend(t)

        default_milestones = [
            Milestone(name="Reliable Multi-Step Reasoning", target_year=2026, category=CapabilityCategory.REASONING, description="Agents reason through 10+ step problems reliably", status=MilestoneStatus.IN_PROGRESS),
            Milestone(name="Persistent Agent Memory", target_year=2027, category=CapabilityCategory.MEMORY, description="Agents maintain context across 100+ sessions"),
            Milestone(name="Autonomous Project Planning", target_year=2028, category=CapabilityCategory.PLANNING, description="Agents plan and execute multi-day projects"),
            Milestone(name="Creative Partner Parity", target_year=2029, category=CapabilityCategory.CREATIVITY, description="AI matches human creative professionals"),
            Milestone(name="Full Workflow Automation", target_year=2029, category=CapabilityCategory.AUTOMATION, description="End-to-end business process automation"),
            Milestone(name="Seamless Multi-Agent Teams", target_year=2030, category=CapabilityCategory.COLLABORATION, description="10+ agent teams coordinate autonomously"),
            Milestone(name="Self-Evolving Safety", target_year=2030, category=CapabilityCategory.SAFETY, description="Safety systems adapt to novel threats autonomously"),
            Milestone(name="Continuous Self-Improvement", target_year=2031, category=CapabilityCategory.LEARNING, description="Agents improve without human intervention"),
            Milestone(name="Unified Perception", target_year=2033, category=CapabilityCategory.PERCEPTION, description="Real-time multi-modal understanding at human parity"),
            Milestone(name="Autonomous API Ecosystem", target_year=2036, category=CapabilityCategory.ACTION, description="Agents discover, learn, and master new APIs autonomously"),
        ]
        for m in default_milestones:
            self.milestone_tracker.add_milestone(m)

    def project(self, current_capabilities: Optional[list[Capability]] = None) -> ProjectionResult:
        caps = current_capabilities if current_capabilities is not None else self._default_capabilities

        capabilities_by_horizon: dict[TimeHorizon, list[Capability]] = {}
        for horizon in TimeHorizon:
            horizon_caps: list[Capability] = []
            for cat in CapabilityCategory:
                extrapolated = self.trend_extrapolator.extrapolate(cat, horizon)
                horizon_caps.extend(extrapolated)

            for cap in caps:
                existing = next((c for c in horizon_caps if c.name == cap.name), None)
                if existing is None:
                    projected_val = cap.projected_maturity.get(horizon, cap.current_maturity)
                    new_cap = Capability(
                        name=cap.name,
                        category=cap.category,
                        current_maturity=cap.current_maturity,
                        projected_maturity={h: cap.projected_maturity.get(h, cap.current_maturity) for h in TimeHorizon},
                        dependencies=cap.dependencies,
                        description=cap.description,
                    )
                    horizon_caps.append(new_cap)

            capabilities_by_horizon[horizon] = horizon_caps

        all_projected: list[Capability] = []
        for cap in caps:
            projected_maturity: dict[TimeHorizon, float] = {}
            for h in TimeHorizon:
                extrapolated = self.trend_extrapolator.extrapolate(cap.category, h)
                match = next((e for e in extrapolated if e.name == cap.name), None)
                if match:
                    projected_maturity[h] = match.projected_maturity.get(h, cap.current_maturity)
                else:
                    projected_maturity[h] = cap.projected_maturity.get(h, cap.current_maturity)
            all_projected.append(Capability(
                name=cap.name,
                category=cap.category,
                current_maturity=cap.current_maturity,
                projected_maturity=projected_maturity,
                dependencies=cap.dependencies,
                description=cap.description,
            ))

        gaps = self.gap_forecaster.forecast(all_projected, 2036)
        prioritized_gaps = self.gap_forecaster.prioritize_gaps(gaps)
        critical_gaps = self.gap_forecaster.get_critical_gaps()
        readiness_items = self.readiness_builder.assess_readiness(prioritized_gaps)
        immediate_actions = self.readiness_builder.get_immediate_actions()
        roadmap = self.milestone_tracker.get_roadmap()

        return ProjectionResult(
            capabilities_by_horizon=capabilities_by_horizon,
            gaps=prioritized_gaps,
            readiness_items=readiness_items,
            roadmap=roadmap,
            critical_gaps=critical_gaps,
            immediate_actions=immediate_actions,
        )

    def generate_roadmap_report(self) -> str:
        result = self.project()
        lines: list[str] = []
        lines.append("# Agentic AI 10-Year Projection Report (2026-2036)")
        lines.append("")
        lines.append("## Formula: (F ^ T) * P — Formula amplified by Temporal × Prediction")
        lines.append("")

        lines.append("## Capability Projections by Horizon")
        lines.append("")
        for horizon in TimeHorizon:
            year = HORIZON_YEAR_MAP[horizon]
            lines.append(f"### {horizon.value.replace('_', ' ').title()} ({year})")
            caps = result.capabilities_by_horizon.get(horizon, [])
            for cap in sorted(caps, key=lambda c: c.category.value):
                proj = cap.projected_maturity.get(horizon, cap.current_maturity)
                bar_len = int(proj * 20)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                lines.append(f"- **{cap.name}** [{cap.category.value}]: {bar} {proj:.1%}")
            lines.append("")

        lines.append("## Gap Analysis")
        lines.append("")
        if result.gaps:
            lines.append("| Gap | Category | Current | Required | Gap Size | Priority |")
            lines.append("|-----|----------|---------|----------|----------|----------|")
            for gap in result.gaps:
                lines.append(f"| {gap.name} | {gap.category.value} | {gap.current_coverage:.1%} | {gap.required_coverage:.1%} | {gap.gap_size:.1%} | {gap.priority.value} |")
        else:
            lines.append("No gaps detected.")
        lines.append("")

        if result.critical_gaps:
            lines.append("### Critical Gaps")
            for gap in result.critical_gaps:
                lines.append(f"- ⚠️ **{gap.name}**: {gap.gap_size:.1%} gap ({gap.current_coverage:.1%} → {gap.required_coverage:.1%})")
            lines.append("")

        lines.append("## Readiness Assessment")
        lines.append("")
        if result.readiness_items:
            for item in result.readiness_items:
                icon = "🔴" if item.current_status == ReadinessStatus.NOT_READY else "🟡" if item.current_status == ReadinessStatus.PARTIAL else "🟢"
                lines.append(f"- {icon} **{item.name}** (by {item.required_by_year}): {item.action_needed}")
        lines.append("")

        if result.immediate_actions:
            lines.append("### Immediate Actions Required")
            for item in result.immediate_actions:
                lines.append(f"- 🚨 **{item.name}**: {item.action_needed}")
            lines.append("")

        lines.append("## Roadmap")
        lines.append("")
        for ms in result.roadmap:
            icon = "✅" if ms.status == MilestoneStatus.COMPLETED else "🔄" if ms.status == MilestoneStatus.IN_PROGRESS else "⚠️" if ms.status == MilestoneStatus.AT_RISK else "⬜"
            lines.append(f"- {icon} **{ms.target_year}** — {ms.name} [{ms.category.value}]: {ms.description}")
        lines.append("")

        return "\n".join(lines)
