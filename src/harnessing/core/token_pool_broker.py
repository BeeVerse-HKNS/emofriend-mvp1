from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ActorRole(Enum):
    MASTER = "master"
    SUB = "sub"
    UNKNOWN = "unknown"


class AllocationState(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    EXHAUSTED = "exhausted"


@dataclass
class TokenAllocation:
    actor: str
    budget: int
    used: int = 0
    available: int = 0
    role: ActorRole = ActorRole.SUB
    state: AllocationState = AllocationState.ACTIVE
    last_used_ts: float = field(default_factory=time.time)
    allocation_ts: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.available:
            self.available = max(0, self.budget - self.used)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actor": self.actor,
            "role": self.role.value,
            "budget": self.budget,
            "used": self.used,
            "available": self.available,
            "state": self.state.value,
            "utilization": round(self.used / self.budget, 4) if self.budget > 0 else 0.0,
        }


@dataclass
class BrokerStats:
    total_budget: int
    master_share: float
    allocations_created: int = 0
    consume_attempts: int = 0
    consume_successes: int = 0
    consume_denials: int = 0
    rebalances: int = 0
    tokens_redistributed: int = 0
    last_rebalance_ts: float = 0.0
    denial_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_budget": self.total_budget,
            "master_share": self.master_share,
            "allocations_created": self.allocations_created,
            "consume_attempts": self.consume_attempts,
            "consume_successes": self.consume_successes,
            "consume_denials": self.consume_denials,
            "rebalances": self.rebalances,
            "tokens_redistributed": self.tokens_redistributed,
            "last_rebalance_ts": self.last_rebalance_ts,
            "denial_rate": round(self.denial_rate, 4),
        }


class TokenPoolBroker:
    IDLE_TIMEOUT_S = 300.0

    def __init__(self, total_budget: int, master_share: float = 0.4) -> None:
        if total_budget <= 0:
            raise ValueError("total_budget must be > 0")
        if not 0.0 <= master_share <= 1.0:
            raise ValueError("master_share must be in [0, 1]")
        self._total_budget = total_budget
        self._master_share = master_share
        self._master_budget = int(total_budget * master_share)
        self._sub_pool_budget = total_budget - self._master_budget
        self._sub_total = 0
        self._allocations: Dict[str, TokenAllocation] = {}
        self._lock = threading.RLock()
        self._stats = BrokerStats(
            total_budget=total_budget,
            master_share=master_share,
        )
        logger.info(
            "TokenPoolBroker initialized (total=%d, master=%d, sub_pool=%d)",
            total_budget,
            self._master_budget,
            self._sub_pool_budget,
        )

    @property
    def total_budget(self) -> int:
        return self._total_budget

    @property
    def master_share(self) -> float:
        return self._master_share

    def allocate(self, actor: str) -> TokenAllocation:
        with self._lock:
            role = self._classify(actor)
            if role == ActorRole.MASTER:
                budget = self._master_budget
                allocation = TokenAllocation(
                    actor=actor,
                    budget=budget,
                    used=0,
                    available=budget,
                    role=role,
                    state=AllocationState.ACTIVE,
                )
                self._allocations[actor] = allocation
            else:
                is_new = actor not in self._allocations
                if is_new:
                    self._sub_total += 1
                fair_share = self._sub_pool_budget // max(self._sub_total, 1)
                if is_new:
                    for existing in list(self._allocations.keys()):
                        if existing == actor:
                            continue
                        if self._classify(existing) == ActorRole.SUB:
                            ex_alloc = self._allocations[existing]
                            ex_alloc.budget = fair_share
                            ex_alloc.available = max(0, fair_share - ex_alloc.used)
                    allocation = TokenAllocation(
                        actor=actor,
                        budget=fair_share,
                        used=0,
                        available=fair_share,
                        role=role,
                        state=AllocationState.ACTIVE,
                    )
                    self._allocations[actor] = allocation
                else:
                    allocation = self._allocations[actor]
            self._stats.allocations_created += 1
            logger.debug("Allocated %d tokens to %s (role=%s, sub_total=%d)", allocation.budget, actor, role.value, self._sub_total)
            return allocation

    def _classify(self, actor: str) -> ActorRole:
        a = actor.lower()
        if a in ("master", "master_agent", "main"):
            return ActorRole.MASTER
        if a.startswith("sub") or a.startswith("agent_") or a.startswith("worker_"):
            return ActorRole.SUB
        return ActorRole.SUB

    def consume(self, actor: str, tokens: int) -> bool:
        if tokens <= 0:
            return True
        with self._lock:
            self._stats.consume_attempts += 1
            if actor not in self._allocations:
                self._allocate_locked(actor)
            alloc = self._allocations[actor]
            if alloc.available < tokens:
                self._stats.consume_denials += 1
                alloc.state = AllocationState.EXHAUSTED
                self._update_denial_rate()
                logger.info("Denied %d tokens to %s (available=%d)", tokens, actor, alloc.available)
                return False
            alloc.used += tokens
            alloc.available -= tokens
            alloc.last_used_ts = time.time()
            if alloc.available == 0:
                alloc.state = AllocationState.EXHAUSTED
            else:
                alloc.state = AllocationState.ACTIVE
            self._stats.consume_successes += 1
            self._update_denial_rate()
            return True

    def _allocate_locked(self, actor: str) -> None:
        if actor in self._allocations:
            return
        role = self._classify(actor)
        if role == ActorRole.MASTER:
            budget = self._master_budget
        else:
            sub_count = max(1, sum(1 for a in self._allocations if self._classify(a) == ActorRole.SUB))
            budget = self._sub_pool_budget // sub_count
        self._allocations[actor] = TokenAllocation(
            actor=actor,
            budget=budget,
            used=0,
            available=budget,
            role=role,
        )
        self._stats.allocations_created += 1

    def rebalance(self) -> Dict[str, int]:
        with self._lock:
            self._stats.rebalances += 1
            now = time.time()
            idle_actors: List[str] = []
            exhausted_actors: List[str] = []
            for name, alloc in self._allocations.items():
                if alloc.role == ActorRole.MASTER:
                    continue
                if alloc.state == AllocationState.EXHAUSTED or alloc.available == 0:
                    exhausted_actors.append(name)
                elif now - alloc.last_used_ts > self.IDLE_TIMEOUT_S:
                    idle_actors.append(name)
            available = sum(self._allocations[a].available for a in idle_actors)
            redistribution: Dict[str, int] = {}
            if not exhausted_actors or available == 0:
                self._stats.last_rebalance_ts = now
                return redistribution
            per_actor = available // len(exhausted_actors)
            remainder = available - per_actor * len(exhausted_actors)
            for i, name in enumerate(exhausted_actors):
                give = per_actor + (remainder if i == 0 else 0)
                if give <= 0:
                    continue
                alloc = self._allocations[name]
                alloc.budget += give
                alloc.available += give
                alloc.state = AllocationState.ACTIVE
                redistribution[name] = give
                self._stats.tokens_redistributed += give
            for name in idle_actors:
                alloc = self._allocations[name]
                give = alloc.available
                alloc.budget -= give
                alloc.available = 0
                alloc.state = AllocationState.IDLE
            self._stats.last_rebalance_ts = now
            logger.info("Rebalanced %d tokens across %d exhausted actors", sum(redistribution.values()), len(redistribution))
            return redistribution

    def release(self, actor: str) -> int:
        with self._lock:
            if actor not in self._allocations:
                return 0
            freed = self._allocations[actor].available
            del self._allocations[actor]
            return freed

    def get_allocation(self, actor: str) -> Optional[TokenAllocation]:
        return self._allocations.get(actor)

    def get_all_allocations(self) -> List[TokenAllocation]:
        return list(self._allocations.values())

    def _update_denial_rate(self) -> None:
        total = self._stats.consume_attempts
        if total > 0:
            self._stats.denial_rate = self._stats.consume_denials / total

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            base = self._stats.to_dict()
            base["active_actors"] = sum(
                1 for a in self._allocations.values() if a.state == AllocationState.ACTIVE
            )
            base["idle_actors"] = sum(
                1 for a in self._allocations.values() if a.state == AllocationState.IDLE
            )
            base["exhausted_actors"] = sum(
                1 for a in self._allocations.values() if a.state == AllocationState.EXHAUSTED
            )
            base["sub_pool_remaining"] = self._sub_pool_budget
            base["master_budget"] = self._master_budget
            return base
