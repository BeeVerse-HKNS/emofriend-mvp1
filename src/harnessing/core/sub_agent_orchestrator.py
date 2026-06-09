from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .sub_agent_memo_cache import MemoCache
from .sub_agent_pipeline import Pipeline, Task as PipelineTask
from .sub_agent_quorum import Decision, Quorum
from .sub_agent_stream import ProgressEvent, Streamer
from .parallelism_governor import Governor

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    FAST = "fast"
    SAFE = "safe"
    STREAMING = "streaming"
    VOTED = "voted"
    PIPELINED = "pipelined"


@dataclass
class OrchestrationRequest:
    prompt: str
    compute_fn: Optional[Callable] = None
    mode: ExecutionMode = ExecutionMode.FAST
    voters: int = 3
    depends_on: List[str] = field(default_factory=list)
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    task_id: str
    value: Any
    mode: ExecutionMode
    duration_ms: float
    cache_hit: bool = False
    votes: Optional[List[str]] = None
    progress_events: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TelemetryEvent:
    timestamp: float
    event_type: str
    task_id: Optional[str]
    data: Dict[str, Any] = field(default_factory=dict)


class SubAgentOrchestrator:
    def __init__(
        self,
        memo_cache: Optional[MemoCache] = None,
        governor: Optional[Governor] = None,
        quorum: Optional[Quorum] = None,
        pipeline: Optional[Pipeline] = None,
        streamer: Optional[Streamer] = None,
        enable_telemetry: bool = True,
    ) -> None:
        self.memo_cache = memo_cache or MemoCache()
        self.governor = governor or Governor()
        self.quorum = quorum or Quorum()
        self.pipeline = pipeline or Pipeline()
        self.streamer = streamer or Streamer()
        self.enable_telemetry = enable_telemetry
        self._telemetry: List[TelemetryEvent] = []
        self._results: Dict[str, OrchestrationResult] = {}
        self._auto_tune_window: List[Dict[str, Any]] = []

    async def run(self, request: OrchestrationRequest) -> OrchestrationResult:
        start = time.time()
        task_id = request.task_id or self._fingerprint(request.prompt)
        self._record_event("task_start", task_id, {"mode": request.mode.value})
        if request.mode == ExecutionMode.FAST:
            result = await self._run_fast(task_id, request)
        elif request.mode == ExecutionMode.SAFE:
            result = await self._run_safe(task_id, request)
        elif request.mode == ExecutionMode.STREAMING:
            result = await self._run_streaming(task_id, request)
        elif request.mode == ExecutionMode.VOTED:
            result = await self._run_voted(task_id, request)
        elif request.mode == ExecutionMode.PIPELINED:
            result = await self._run_pipelined(task_id, request)
        else:
            raise ValueError(f"Unknown execution mode: {request.mode}")
        result.duration_ms = (time.time() - start) * 1000
        self._results[task_id] = result
        self._record_event("task_end", task_id, {
            "duration_ms": result.duration_ms,
            "cache_hit": result.cache_hit,
        })
        if self.enable_telemetry:
            self._auto_tune(result, request)
        return result

    async def run_batch(self, requests: List[OrchestrationRequest]) -> List[OrchestrationResult]:
        independent = [r for r in requests if not r.depends_on]
        dependent = [r for r in requests if r.depends_on]
        results: List[OrchestrationResult] = []

        async def _guarded(req: OrchestrationRequest) -> OrchestrationResult:
            await asyncio.to_thread(self.governor.acquire)
            try:
                return await self.run(req)
            finally:
                self.governor.release()

        tasks = [_guarded(r) for r in independent]
        results.extend(await asyncio.gather(*tasks))
        for req in dependent:
            parents = {r.task_id or self._fingerprint(r.prompt): r for r in requests}
            for dep_id in req.depends_on:
                if dep_id in parents:
                    parent_res = next((r for r in results if r.task_id == dep_id), None)
                    if parent_res is not None:
                        req.metadata[f"dep_{dep_id}"] = parent_res.value
            results.append(await _guarded(req))
        return results

    async def _run_fast(self, task_id: str, request: OrchestrationRequest) -> OrchestrationResult:
        if request.compute_fn is None:
            raise ValueError("FAST mode requires compute_fn")
        value, hit = self.memo_cache.get_or_compute(request.prompt, request.compute_fn)
        return OrchestrationResult(
            task_id=task_id,
            value=value,
            mode=ExecutionMode.FAST,
            duration_ms=0.0,
            cache_hit=hit,
        )

    async def _run_safe(self, task_id: str, request: OrchestrationRequest) -> OrchestrationResult:
        return await self._run_fast(task_id, request)

    async def _run_streaming(self, task_id: str, request: OrchestrationRequest) -> OrchestrationResult:
        if request.compute_fn is None:
            raise ValueError("STREAMING mode requires compute_fn")
        total = int(request.metadata.get("total", 100))
        last_percent = 0.0
        last_partial: Any = None
        events_count = 0
        async for event in self.streamer.stream(request.compute_fn, total=total):
            last_percent = event.percent
            last_partial = event.partial
            events_count += 1
        return OrchestrationResult(
            task_id=task_id,
            value=last_partial,
            mode=ExecutionMode.STREAMING,
            duration_ms=0.0,
            progress_events=events_count,
            metadata={"final_percent": last_percent},
        )

    async def _run_voted(self, task_id: str, request: OrchestrationRequest) -> OrchestrationResult:
        decision: Decision = self.quorum.decide(
            request.prompt,
            voters=request.voters,
        )
        return OrchestrationResult(
            task_id=task_id,
            value=decision.result,
            mode=ExecutionMode.VOTED,
            duration_ms=0.0,
            votes=decision.votes,
            metadata={
                "confidence": decision.confidence,
                "voter_count": decision.voter_count,
            },
        )

    async def _run_pipelined(self, task_id: str, request: OrchestrationRequest) -> OrchestrationResult:
        pipeline_tasks_config = request.metadata.get("pipeline_tasks", [])
        for t in pipeline_tasks_config:
            self.pipeline.add_task(PipelineTask(
                id=t["id"],
                fn=t["fn"],
                depends_on=t.get("depends_on", []),
            ))
        results = self.pipeline.execute()
        return OrchestrationResult(
            task_id=task_id,
            value=results,
            mode=ExecutionMode.PIPELINED,
            duration_ms=0.0,
            metadata={"pipeline_results": results},
        )

    def _fingerprint(self, prompt: str) -> str:
        import hashlib
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]

    def _record_event(self, event_type: str, task_id: Optional[str], data: Dict[str, Any]) -> None:
        if not self.enable_telemetry:
            return
        event = TelemetryEvent(
            timestamp=time.time(),
            event_type=event_type,
            task_id=task_id,
            data=data,
        )
        self._telemetry.append(event)
        if len(self._telemetry) > 1000:
            self._telemetry = self._telemetry[-1000:]

    def _auto_tune(self, result: OrchestrationResult, request: OrchestrationRequest) -> None:
        self._auto_tune_window.append({
            "timestamp": time.time(),
            "mode": request.mode.value,
            "duration_ms": result.duration_ms,
            "cache_hit": result.cache_hit,
        })
        if len(self._auto_tune_window) > 100:
            self._auto_tune_window = self._auto_tune_window[-100:]
        if len(self._auto_tune_window) >= 20:
            cache_hit_rate = sum(1 for w in self._auto_tune_window if w["cache_hit"]) / len(self._auto_tune_window)
            if cache_hit_rate < 0.2 and request.mode == ExecutionMode.FAST:
                logger.info("Low cache hit rate (%.2f), consider SAFE mode", cache_hit_rate)

    def get_telemetry(self) -> List[TelemetryEvent]:
        return list(self._telemetry)

    def get_results(self) -> Dict[str, OrchestrationResult]:
        return dict(self._results)

    def stats(self) -> Dict[str, Any]:
        return {
            "telemetry_count": len(self._telemetry),
            "results_count": len(self._results),
            "memo_cache": self.memo_cache.stats,
            "governor": self.governor.stats(),
            "quorum": self.quorum.stats(),
            "streamer": self.streamer.stats(),
            "auto_tune_window_size": len(self._auto_tune_window),
        }
