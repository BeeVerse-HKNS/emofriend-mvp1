from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PhaseName(Enum):
    INITIAL = "phase_1_initial_pdf"
    COMPANY_SCAN = "phase_2_company_scan"
    DEEP_RESEARCH = "phase_3_deep_research"
    SYNTHESIS = "phase_4_synthesis"
    REPORT = "phase_5_report"


class LoopState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PhaseSpec:
    name: PhaseName
    duration_hours: float
    objective: str
    spawn_subagents: int
    tools_used: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)


@dataclass
class PhaseProgress:
    phase: PhaseName
    started_at: float
    ended_at: Optional[float] = None
    completed: bool = False
    subagents_spawned: int = 0
    artifacts_generated: int = 0
    notes: str = ""


@dataclass
class LoopStats:
    loop_id: str
    duration_hours: float
    state: LoopState
    phase_progress: List[PhaseProgress] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    remaining_seconds: float = 0.0
    started_at: float = 0.0
    completed_at: Optional[float] = None
    subagents_total: int = 0
    artifacts_total: int = 0
    auto_approval_count: int = 0
    pause_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "duration_hours": self.duration_hours,
            "state": self.state.value,
            "phase_progress": [
                {
                    "phase": p.phase.value,
                    "completed": p.completed,
                    "started_at": p.started_at,
                    "ended_at": p.ended_at,
                    "subagents_spawned": p.subagents_spawned,
                    "artifacts_generated": p.artifacts_generated,
                    "notes": p.notes,
                }
                for p in self.phase_progress
            ],
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "remaining_seconds": round(self.remaining_seconds, 3),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "subagents_total": self.subagents_total,
            "artifacts_total": self.artifacts_total,
            "auto_approval_count": self.auto_approval_count,
            "pause_count": self.pause_count,
        }


class AutonomousDeepResearchLoop:
    DEFAULT_PHASE_PLAN: List[PhaseSpec] = [
        PhaseSpec(
            name=PhaseName.INITIAL,
            duration_hours=1.0,
            objective="处理PDF + 初步知识扫描",
            spawn_subagents=2,
            tools_used=["pdf_extractor", "kb_search"],
            deliverables=["initial_kb_dump"],
        ),
        PhaseSpec(
            name=PhaseName.COMPANY_SCAN,
            duration_hours=2.0,
            objective="扫描广东数据产业核心企业",
            spawn_subagents=5,
            tools_used=["web_search", "web_fetch"],
            deliverables=["company_profiles_20plus"],
        ),
        PhaseSpec(
            name=PhaseName.DEEP_RESEARCH,
            duration_hours=3.0,
            objective="深挖5家头部企业业务模型",
            spawn_subagents=5,
            tools_used=["web_search", "web_fetch", "kb_search"],
            deliverables=["deep_research_5_companies"],
        ),
        PhaseSpec(
            name=PhaseName.SYNTHESIS,
            duration_hours=1.0,
            objective="公式思维法生成新业务模型",
            spawn_subagents=3,
            tools_used=["formula_thinking", "kb_search"],
            deliverables=["business_proposals_3plus"],
        ),
        PhaseSpec(
            name=PhaseName.REPORT,
            duration_hours=1.0,
            objective="汇总报告 + 自动发布",
            spawn_subagents=1,
            tools_used=["report_generator"],
            deliverables=["final_report"],
        ),
    ]

    def __init__(
        self,
        duration_hours: float = 8.0,
        phase_plan: Optional[List[PhaseSpec]] = None,
        spawn_callback: Optional[Callable[[PhaseSpec], List[str]]] = None,
        auto_approve: bool = True,
    ) -> None:
        if duration_hours <= 0:
            raise ValueError("duration_hours must be > 0")
        self._loop_id = f"LOOP-{uuid.uuid4().hex[:8]}"
        self._duration_hours = duration_hours
        self._phase_plan = phase_plan or self._scale_phase_plan(duration_hours)
        self._spawn_callback = spawn_callback
        self._auto_approve = auto_approve
        self._state = LoopState.IDLE
        self._stats = LoopStats(
            loop_id=self._loop_id,
            duration_hours=duration_hours,
            state=LoopState.IDLE,
        )
        self._lock = threading.RLock()
        self._current_phase_idx = -1
        self._started_at: Optional[float] = None
        self._completed_at: Optional[float] = None
        logger.info(
            "AutonomousDeepResearchLoop %s initialized (duration=%.3fh, phases=%d)",
            self._loop_id,
            duration_hours,
            len(self._phase_plan),
        )

    def _scale_phase_plan(self, duration_hours: float) -> List[PhaseSpec]:
        base_total = sum(p.duration_hours for p in self.DEFAULT_PHASE_PLAN)
        scale = duration_hours / base_total if base_total > 0 else 1.0
        scaled: List[PhaseSpec] = []
        for p in self.DEFAULT_PHASE_PLAN:
            scaled.append(
                PhaseSpec(
                    name=p.name,
                    duration_hours=p.duration_hours * scale,
                    objective=p.objective,
                    spawn_subagents=p.spawn_subagents,
                    tools_used=list(p.tools_used),
                    deliverables=list(p.deliverables),
                )
            )
        return scaled

    @property
    def loop_id(self) -> str:
        return self._loop_id

    @property
    def duration_hours(self) -> float:
        return self._duration_hours

    @property
    def state(self) -> LoopState:
        return self._state

    def start(self) -> Dict[str, Any]:
        with self._lock:
            if self._state == LoopState.RUNNING:
                return {"status": "already_running", "loop_id": self._loop_id}
            self._state = LoopState.RUNNING
            self._started_at = time.time()
            self._stats.started_at = self._started_at
            self._stats.state = LoopState.RUNNING
        logger.info("Loop %s started", self._loop_id)
        return {"status": "started", "loop_id": self._loop_id, "phases": len(self._phase_plan)}

    def pause(self) -> None:
        with self._lock:
            if self._state == LoopState.RUNNING:
                self._state = LoopState.PAUSED
                self._stats.pause_count += 1
                self._stats.state = LoopState.PAUSED

    def resume(self) -> None:
        with self._lock:
            if self._state == LoopState.PAUSED:
                self._state = LoopState.RUNNING
                self._stats.state = LoopState.RUNNING

    def tick(self, now: Optional[float] = None) -> Optional[PhaseProgress]:
        with self._lock:
            if self._state != LoopState.RUNNING or self._started_at is None:
                return None
            now = now if now is not None else time.time()
            self._stats.elapsed_seconds = now - self._started_at
            self._stats.remaining_seconds = max(0.0, self._duration_hours * 3600.0 - self._stats.elapsed_seconds)
            boundaries = self._phase_boundaries()
            new_idx = -1
            for i, (start, _end) in enumerate(boundaries):
                if start <= self._stats.elapsed_seconds < _end or i == len(boundaries) - 1 and self._stats.elapsed_seconds >= start:
                    new_idx = i
                    break
            if new_idx < 0:
                new_idx = 0
            if new_idx != self._current_phase_idx:
                if self._current_phase_idx >= 0 and self._current_phase_idx < len(self._stats.phase_progress):
                    prev = self._stats.phase_progress[self._current_phase_idx]
                    if prev.ended_at is None:
                        prev.ended_at = now
                        prev.completed = True
                if new_idx >= len(self._stats.phase_progress):
                    spec = self._phase_plan[new_idx]
                    sub_count = self._maybe_spawn(spec)
                    self._stats.phase_progress.append(
                        PhaseProgress(
                            phase=spec.name,
                            started_at=now,
                            subagents_spawned=sub_count,
                            artifacts_generated=len(spec.deliverables),
                        )
                    )
                    self._stats.subagents_total += sub_count
                    self._stats.artifacts_total += len(spec.deliverables)
                    self._stats.auto_approval_count += 1
                else:
                    cur = self._stats.phase_progress[new_idx]
                    if cur.started_at == 0.0:
                        cur.started_at = now
                self._current_phase_idx = new_idx
            if self._stats.remaining_seconds <= 0.0:
                self._finalize(now)
            return self._stats.phase_progress[new_idx] if self._stats.phase_progress else None

    def _phase_boundaries(self) -> List[tuple]:
        boundaries: List[tuple] = []
        cursor = 0.0
        for spec in self._phase_plan:
            dur = spec.duration_hours * 3600.0
            boundaries.append((cursor, cursor + dur))
            cursor += dur
        return boundaries

    def _maybe_spawn(self, spec: PhaseSpec) -> int:
        if self._spawn_callback is None:
            return spec.spawn_subagents
        if not self._auto_approve:
            return 0
        try:
            result = self._spawn_callback(spec)
            return len(result) if result else spec.spawn_subagents
        except Exception as exc:  # noqa: BLE001
            logger.warning("spawn_callback failed: %s; falling back to spec count", exc)
            return spec.spawn_subagents

    def _finalize(self, now: float) -> None:
        if self._current_phase_idx >= 0 and self._current_phase_idx < len(self._stats.phase_progress):
            last = self._stats.phase_progress[self._current_phase_idx]
            if last.ended_at is None:
                last.ended_at = now
                last.completed = True
        self._state = LoopState.COMPLETED
        self._stats.state = LoopState.COMPLETED
        self._stats.completed_at = now
        self._completed_at = now

    def add_phase_note(self, phase: PhaseName, note: str) -> None:
        with self._lock:
            for p in self._stats.phase_progress:
                if p.phase == phase:
                    p.notes = note
                    return

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            if self._state == LoopState.RUNNING and self._started_at is not None:
                self._stats.elapsed_seconds = time.time() - self._started_at
                self._stats.remaining_seconds = max(
                    0.0, self._duration_hours * 3600.0 - self._stats.elapsed_seconds
                )
            return self._stats.to_dict()

    def export_plan(self) -> str:
        return json.dumps(
            [
                {
                    "name": p.name.value,
                    "duration_hours": p.duration_hours,
                    "objective": p.objective,
                    "spawn_subagents": p.spawn_subagents,
                    "tools_used": p.tools_used,
                    "deliverables": p.deliverables,
                }
                for p in self._phase_plan
            ],
            ensure_ascii=False,
            indent=2,
        )
