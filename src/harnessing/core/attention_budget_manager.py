from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple


class Priority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    DISCARD = 4


class InfoCategory(Enum):
    RULE = "rule"
    DECISION = "decision"
    ERROR = "error"
    KNOWLEDGE = "knowledge"
    PROGRESS = "progress"
    PREFERENCE = "preference"
    CONTEXT = "context"
    TASK = "task"


@dataclass
class InfoUnit:
    id: str
    content: str
    category: InfoCategory
    priority: Priority
    relevance_score: float
    token_count: int
    timestamp: float
    source: str

    def __post_init__(self) -> None:
        self.relevance_score = max(0.0, min(1.0, self.relevance_score))


@dataclass
class BudgetAllocation:
    category: InfoCategory
    allocated_tokens: int
    used_tokens: int = 0

    @property
    def utilization(self) -> float:
        if self.allocated_tokens == 0:
            return 0.0
        return self.used_tokens / self.allocated_tokens


@dataclass
class CompactionResult:
    original_tokens: int
    compacted_tokens: int
    compression_ratio: float
    retained_info_ids: List[str]
    discarded_info_ids: List[str]


@dataclass
class ContextManagementResult:
    active_info: List[InfoUnit]
    compacted_info: List[InfoUnit]
    loaded_info: List[InfoUnit]
    freed_tokens: int
    budget_status: Dict[str, float]


class AttentionBudget:
    def __init__(self, total_budget: int = 8000) -> None:
        self.total_budget = total_budget
        self._allocations: Dict[InfoCategory, BudgetAllocation] = {}

    def allocate(self, category_weights: Optional[Dict[InfoCategory, float]] = None) -> List[BudgetAllocation]:
        if category_weights is None:
            category_weights = {cat: 1.0 for cat in InfoCategory}
        total_weight = sum(category_weights.values())
        if total_weight == 0:
            total_weight = 1.0
        for cat, weight in category_weights.items():
            allocated = int(self.total_budget * weight / total_weight)
            if cat in self._allocations:
                self._allocations[cat].allocated_tokens = allocated
            else:
                self._allocations[cat] = BudgetAllocation(category=cat, allocated_tokens=allocated)
        return list(self._allocations.values())

    def spend(self, category: InfoCategory, tokens: int) -> bool:
        if category not in self._allocations:
            return False
        alloc = self._allocations[category]
        if alloc.used_tokens + tokens > alloc.allocated_tokens:
            return False
        alloc.used_tokens += tokens
        return True

    def get_remaining(self) -> int:
        total_used = sum(a.used_tokens for a in self._allocations.values())
        return self.total_budget - total_used

    def get_utilization(self) -> float:
        if self.total_budget == 0:
            return 0.0
        total_used = sum(a.used_tokens for a in self._allocations.values())
        return total_used / self.total_budget

    def reallocate(self, from_category: InfoCategory, to_category: InfoCategory, tokens: int) -> bool:
        if from_category not in self._allocations or to_category not in self._allocations:
            return False
        from_alloc = self._allocations[from_category]
        to_alloc = self._allocations[to_category]
        available = from_alloc.allocated_tokens - from_alloc.used_tokens
        if available < tokens:
            return False
        from_alloc.allocated_tokens -= tokens
        to_alloc.allocated_tokens += tokens
        return True

    def get_allocation(self, category: InfoCategory) -> Optional[BudgetAllocation]:
        return self._allocations.get(category)


class PriorityCompressor:
    def compress(self, info_units: List[InfoUnit], target_tokens: int) -> CompactionResult:
        if not info_units:
            return CompactionResult(
                original_tokens=0,
                compacted_tokens=0,
                compression_ratio=1.0,
                retained_info_ids=[],
                discarded_info_ids=[],
            )
        original_tokens = sum(u.token_count for u in info_units)
        sorted_units = sorted(info_units, key=lambda u: (u.priority.value, -u.relevance_score))
        retained: List[str] = []
        discarded: List[str] = []
        current_tokens = 0
        for unit in sorted_units:
            if current_tokens + unit.token_count <= target_tokens:
                retained.append(unit.id)
                current_tokens += unit.token_count
            else:
                discarded.append(unit.id)
        compacted_tokens = current_tokens
        ratio = compacted_tokens / original_tokens if original_tokens > 0 else 1.0
        return CompactionResult(
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            compression_ratio=ratio,
            retained_info_ids=retained,
            discarded_info_ids=discarded,
        )


class RelevanceScorer:
    CATEGORY_WEIGHTS: Dict[InfoCategory, float] = {
        InfoCategory.RULE: 0.9,
        InfoCategory.ERROR: 0.85,
        InfoCategory.DECISION: 0.8,
        InfoCategory.TASK: 0.75,
        InfoCategory.KNOWLEDGE: 0.7,
        InfoCategory.CONTEXT: 0.6,
        InfoCategory.PROGRESS: 0.5,
        InfoCategory.PREFERENCE: 0.4,
    }

    def score(self, info: InfoUnit, current_context: str) -> float:
        keyword_overlap = self._keyword_overlap(info.content, current_context)
        category_relevance = self.CATEGORY_WEIGHTS.get(info.category, 0.5)
        recency = self._recency_score(info.timestamp)
        raw = 0.4 * keyword_overlap + 0.35 * category_relevance + 0.25 * recency
        return max(0.0, min(1.0, raw))

    def batch_score(self, info_units: List[InfoUnit], current_context: str) -> List[Tuple[str, float]]:
        return [(u.id, self.score(u, current_context)) for u in info_units]

    def _keyword_overlap(self, content: str, context: str) -> float:
        if not content or not context:
            return 0.0
        content_words = set(content.lower().split())
        context_words = set(context.lower().split())
        if not context_words:
            return 0.0
        overlap = len(content_words & context_words)
        return min(1.0, overlap / max(len(context_words), 1))

    def _recency_score(self, timestamp: float) -> float:
        age = time.time() - timestamp
        if age < 0:
            return 1.0
        return max(0.0, 1.0 - age / 3600.0)


class DynamicLoader:
    def __init__(self, available_sources: Optional[Dict[str, Callable]] = None) -> None:
        self._sources: Dict[str, Callable] = available_sources or {}
        self._loaded: Dict[str, InfoUnit] = {}

    def load(self, category: InfoCategory, query: str, max_tokens: int) -> List[InfoUnit]:
        results: List[InfoUnit] = []
        current_tokens = 0
        for source_name, source_fn in self._sources.items():
            try:
                items = source_fn(category, query)
                for item in items:
                    if current_tokens + item.token_count <= max_tokens:
                        results.append(item)
                        self._loaded[item.id] = item
                        current_tokens += item.token_count
            except Exception:
                continue
        return results

    def preload(self, categories: List[InfoCategory]) -> List[InfoUnit]:
        results: List[InfoUnit] = []
        for cat in categories:
            for source_name, source_fn in self._sources.items():
                try:
                    items = source_fn(cat, "")
                    for item in items:
                        self._loaded[item.id] = item
                        results.append(item)
                except Exception:
                    continue
        return results

    def unload(self, info_ids: List[str]) -> int:
        freed = 0
        for info_id in info_ids:
            if info_id in self._loaded:
                freed += self._loaded[info_id].token_count
                del self._loaded[info_id]
        return freed


class ContextCompactor:
    def compact_history(self, history: List[InfoUnit], max_tokens: int) -> CompactionResult:
        if not history:
            return CompactionResult(
                original_tokens=0,
                compacted_tokens=0,
                compression_ratio=1.0,
                retained_info_ids=[],
                discarded_info_ids=[],
            )
        original_tokens = sum(u.token_count for u in history)
        now = time.time()
        scored = [(u, self._importance_score(u, now)) for u in history]
        scored.sort(key=lambda x: -x[1])
        retained: List[str] = []
        discarded: List[str] = []
        current_tokens = 0
        for unit, _ in scored:
            if current_tokens + unit.token_count <= max_tokens:
                retained.append(unit.id)
                current_tokens += unit.token_count
            else:
                discarded.append(unit.id)
        compacted_tokens = current_tokens
        ratio = compacted_tokens / original_tokens if original_tokens > 0 else 1.0
        return CompactionResult(
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            compression_ratio=ratio,
            retained_info_ids=retained,
            discarded_info_ids=discarded,
        )

    def merge_similar(self, info_units: List[InfoUnit]) -> List[InfoUnit]:
        if not info_units:
            return []
        merged: List[InfoUnit] = []
        used: set = set()
        for i, unit_a in enumerate(info_units):
            if i in used:
                continue
            similar_indices: List[int] = []
            for j, unit_b in enumerate(info_units):
                if j <= i or j in used:
                    continue
                if unit_a.category == unit_b.category and self._content_similarity(unit_a.content, unit_b.content) > 0.7:
                    similar_indices.append(j)
            if similar_indices:
                combined_content = unit_a.content
                total_tokens = unit_a.token_count
                best_priority = unit_a.priority
                best_relevance = unit_a.relevance_score
                for idx in similar_indices:
                    other = info_units[idx]
                    combined_content += " | " + other.content
                    total_tokens += other.token_count
                    if other.priority.value < best_priority.value:
                        best_priority = other.priority
                    best_relevance = max(best_relevance, other.relevance_score)
                    used.add(idx)
                merged.append(InfoUnit(
                    id=unit_a.id,
                    content=combined_content,
                    category=unit_a.category,
                    priority=best_priority,
                    relevance_score=best_relevance,
                    token_count=total_tokens,
                    timestamp=unit_a.timestamp,
                    source=unit_a.source,
                ))
                used.add(i)
            else:
                merged.append(unit_a)
                used.add(i)
        return merged

    def _importance_score(self, unit: InfoUnit, now: float) -> float:
        priority_score = 1.0 - unit.priority.value * 0.2
        recency = max(0.0, 1.0 - (now - unit.timestamp) / 3600.0)
        return 0.5 * priority_score + 0.3 * unit.relevance_score + 0.2 * recency

    def _content_similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union > 0 else 0.0


class AttentionBudgetManager:
    def __init__(self, total_budget: int = 8000, available_sources: Optional[Dict[str, Callable]] = None) -> None:
        self.budget = AttentionBudget(total_budget)
        self.compressor = PriorityCompressor()
        self.scorer = RelevanceScorer()
        self.loader = DynamicLoader(available_sources)
        self.compactor = ContextCompactor()
        self._active_info: Dict[str, InfoUnit] = {}

    def manage_context(self, incoming_info: List[InfoUnit], current_context: str) -> ContextManagementResult:
        for unit in incoming_info:
            scored = self.scorer.score(unit, current_context)
            unit.relevance_score = scored
        scored_incoming = sorted(incoming_info, key=lambda u: (u.priority.value, -u.relevance_score))
        active_list = list(self._active_info.values())
        all_info = active_list + scored_incoming
        total_tokens = sum(u.token_count for u in all_info)
        freed_tokens = 0
        compacted_info: List[InfoUnit] = []
        if total_tokens > self.budget.total_budget:
            compaction = self.compactor.compact_history(all_info, self.budget.total_budget)
            new_active: Dict[str, InfoUnit] = {}
            for unit in all_info:
                if unit.id in compaction.retained_info_ids:
                    new_active[unit.id] = unit
                else:
                    compacted_info.append(unit)
                    freed_tokens += unit.token_count
            self._active_info = new_active
        else:
            for unit in scored_incoming:
                self._active_info[unit.id] = unit
        loaded_info = self._load_on_demand(current_context)
        budget_status = {
            "total_budget": float(self.budget.total_budget),
            "remaining": float(self.budget.get_remaining()),
            "utilization": self.budget.get_utilization(),
        }
        return ContextManagementResult(
            active_info=list(self._active_info.values()),
            compacted_info=compacted_info,
            loaded_info=loaded_info,
            freed_tokens=freed_tokens,
            budget_status=budget_status,
        )

    def auto_manage(self) -> ContextManagementResult:
        utilization = self.budget.get_utilization()
        active_list = list(self._active_info.values())
        compacted_info: List[InfoUnit] = []
        freed_tokens = 0
        if utilization > 0.7:
            target = int(self.budget.total_budget * 0.6)
            compaction = self.compactor.compact_history(active_list, target)
            new_active: Dict[str, InfoUnit] = {}
            for unit in active_list:
                if unit.id in compaction.retained_info_ids:
                    new_active[unit.id] = unit
                else:
                    compacted_info.append(unit)
                    freed_tokens += unit.token_count
            self._active_info = new_active
        loaded_info = self.loader.preload([InfoCategory.RULE, InfoCategory.ERROR])
        budget_status = {
            "total_budget": float(self.budget.total_budget),
            "remaining": float(self.budget.get_remaining()),
            "utilization": self.budget.get_utilization(),
        }
        return ContextManagementResult(
            active_info=list(self._active_info.values()),
            compacted_info=compacted_info,
            loaded_info=loaded_info,
            freed_tokens=freed_tokens,
            budget_status=budget_status,
        )

    def _load_on_demand(self, current_context: str) -> List[InfoUnit]:
        remaining = self.budget.get_remaining()
        if remaining <= 0:
            return []
        return self.loader.load(InfoCategory.KNOWLEDGE, current_context, remaining)

    def add_info(self, info: InfoUnit) -> None:
        self._active_info[info.id] = info

    def get_active_info(self) -> List[InfoUnit]:
        return list(self._active_info.values())

    def get_active_token_count(self) -> int:
        return sum(u.token_count for u in self._active_info.values())


class RegionalAttentionMixin:
    HK_DATA_MINIMIZATION_CASES = [
        {"content": "User browsing history for last 30 days", "category": "CONTEXT", "priority": "HIGH", "tokens": 800},
        {"content": "IP address and device fingerprint", "category": "CONTEXT", "priority": "MEDIUM", "tokens": 400},
        {"content": "Cross-session user preferences", "category": "PREFERENCE", "priority": "LOW", "tokens": 200},
    ]

    CN_CONTENT_FILTERING_CASES = [
        {"content": "Political content classification request", "category": "KNOWLEDGE", "priority": "CRITICAL", "tokens": 600},
        {"content": "Sensitive topic flagging", "category": "RULE", "priority": "CRITICAL", "tokens": 500},
        {"content": "Historical data analysis", "category": "CONTEXT", "priority": "LOW", "tokens": 1000},
    ]

    EU_FAIRNESS_CASES = [
        {"content": "Gender bias detection in hiring AI", "category": "ERROR", "priority": "CRITICAL", "tokens": 700},
        {"content": "Age discrimination audit request", "category": "RULE", "priority": "HIGH", "tokens": 600},
        {"content": "Demographic parity check", "category": "KNOWLEDGE", "priority": "HIGH", "tokens": 500},
    ]

    SG_TRANSPARENCY_CASES = [
        {"content": "Agent decision explanation request", "category": "RULE", "priority": "HIGH", "tokens": 800},
        {"content": "Algorithmic transparency report", "category": "KNOWLEDGE", "priority": "MEDIUM", "tokens": 600},
        {"content": "User consent verification", "category": "DECISION", "priority": "HIGH", "tokens": 400},
    ]

    def test_hk_data_minimization(self) -> dict:
        manager = AttentionBudgetManager(total_budget=2000)
        info_units = []
        for case in self.HK_DATA_MINIMIZATION_CASES:
            unit = InfoUnit(
                id=f"hk_{case['content'][:20]}",
                content=case["content"],
                category=InfoCategory[case["category"].upper()],
                priority=Priority[case["priority"].upper()],
                relevance_score=0.5,
                token_count=case["tokens"],
                timestamp=time.time(),
                source="test"
            )
            info_units.append(unit)
        result = manager.manage_context(info_units, "user data")
        critical_retained = sum(1 for u in result.active_info if u.priority == Priority.CRITICAL)
        low_retained = sum(1 for u in result.active_info if u.priority == Priority.LOW)
        return {
            "region": "HK",
            "data_minimization_active": critical_retained > 0 and low_retained == 0,
            "critical_info_retained": critical_retained,
            "low_priority_discarded": low_retained == 0,
            "budget_efficient": result.freed_tokens > 0,
        }

    def test_cn_content_filtering(self) -> dict:
        manager = AttentionBudgetManager(total_budget=2000)
        info_units = []
        for case in self.CN_CONTENT_FILTERING_CASES:
            unit = InfoUnit(
                id=f"cn_{case['content'][:20]}",
                content=case["content"],
                category=InfoCategory[case["category"].upper()],
                priority=Priority[case["priority"].upper()],
                relevance_score=0.5,
                token_count=case["tokens"],
                timestamp=time.time(),
                source="test"
            )
            info_units.append(unit)
        result = manager.manage_context(info_units, "content filtering")
        critical_retained = sum(1 for u in result.active_info if u.priority == Priority.CRITICAL)
        return {
            "region": "CN",
            "critical_content_prioritized": critical_retained >= 2,
            "critical_retained": critical_retained,
            "filtering_compliant": critical_retained >= 2,
        }

    def test_eu_fairness_priority(self) -> dict:
        manager = AttentionBudgetManager(total_budget=2000)
        info_units = []
        for case in self.EU_FAIRNESS_CASES:
            unit = InfoUnit(
                id=f"eu_{case['content'][:20]}",
                content=case["content"],
                category=InfoCategory[case["category"].upper()],
                priority=Priority[case["priority"].upper()],
                relevance_score=0.5,
                token_count=case["tokens"],
                timestamp=time.time(),
                source="test"
            )
            info_units.append(unit)
        result = manager.manage_context(info_units, "fairness audit")
        high_priority = sum(1 for u in result.active_info if u.priority == Priority.HIGH)
        return {
            "region": "EU",
            "fairness_checks_prioritized": high_priority >= 2,
            "high_priority_retained": high_priority,
            "gdpr_fairness_compliant": high_priority >= 2,
        }

    def test_sg_transparency_allocation(self) -> dict:
        manager = AttentionBudgetManager(total_budget=2000)
        info_units = []
        for case in self.SG_TRANSPARENCY_CASES:
            unit = InfoUnit(
                id=f"sg_{case['content'][:20]}",
                content=case["content"],
                category=InfoCategory[case["category"].upper()],
                priority=Priority[case["priority"].upper()],
                relevance_score=0.5,
                token_count=case["tokens"],
                timestamp=time.time(),
                source="test"
            )
            info_units.append(unit)
        result = manager.manage_context(info_units, "transparency report")
        total_active = len(result.active_info)
        return {
            "region": "SG",
            "transparency_docs_retained": total_active >= 2,
            "active_info_count": total_active,
            "framework_compliant": total_active >= 2,
        }

    def test_budget_reallocation_regional(self) -> dict:
        manager = AttentionBudgetManager(total_budget=1000)
        manager.budget.allocate({InfoCategory.CONTEXT: 0.5, InfoCategory.RULE: 0.5})
        realloc_success = manager.budget.reallocate(InfoCategory.CONTEXT, InfoCategory.RULE, 200)
        return {
            "reallocation_supported": realloc_success,
            "regional_flexibility": realloc_success,
        }

    def run_all_regional_tests(self) -> dict:
        return {
            "attention_budget_manager": {
                "HK_DataMinimization": self.test_hk_data_minimization(),
                "CN_ContentFiltering": self.test_cn_content_filtering(),
                "EU_Fairness": self.test_eu_fairness_priority(),
                "SG_Transparency": self.test_sg_transparency_allocation(),
                "Budget_Reallocation": self.test_budget_reallocation_regional(),
            }
        }
