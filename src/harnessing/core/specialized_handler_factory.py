from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class HandlerStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    DEPRECATED = "deprecated"


class DispatchResult(str, Enum):
    DISPATCHED = "dispatched"
    NO_HANDLER = "no_handler"
    HANDLER_BUSY = "handler_busy"


@dataclass
class HandlerTemplate:
    template_id: str
    base_skill: str
    specialization: str
    target_categories: list[str]
    target_severities: list[str]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SpecializedHandler:
    handler_id: str
    base_skill: str
    specialization: str
    categories: list[str]
    severities: list[str]
    dimensions: list[str]
    status: HandlerStatus = HandlerStatus.ACTIVE
    dispatch_count: int = 0
    effectiveness: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class HandlerSpecializer:
    def __init__(self):
        self._specialization_rules: dict[str, dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)

    def add_specialization_rule(self, specialization: str, config: dict[str, Any]) -> None:
        self._specialization_rules[specialization] = config

    def specialize(
        self,
        template: HandlerTemplate,
        handler_id: str,
        extra_dimensions: list[str] | None = None,
    ) -> SpecializedHandler:
        config = self._specialization_rules.get(template.specialization, {})

        narrowed_categories = self._narrow_categories(
            template.target_categories, config
        )
        deepened_severities = self._deepen_severities(
            template.target_severities, config
        )
        specific_dimensions = self._add_dimensions(
            template, config, extra_dimensions or []
        )

        effectiveness = self._calculate_effectiveness(
            len(narrowed_categories), len(deepened_severities), len(specific_dimensions)
        )

        handler = SpecializedHandler(
            handler_id=handler_id,
            base_skill=template.base_skill,
            specialization=template.specialization,
            categories=narrowed_categories,
            severities=deepened_severities,
            dimensions=specific_dimensions,
            effectiveness=effectiveness,
        )

        self.logger.info(
            "handler_specialized",
            extra={
                "handler_id": handler_id,
                "base_skill": template.base_skill,
                "specialization": template.specialization,
                "categories": narrowed_categories,
                "effectiveness": effectiveness,
            },
        )
        return handler

    def _narrow_categories(
        self, categories: list[str], config: dict[str, Any]
    ) -> list[str]:
        focus = config.get("category_focus")
        if focus:
            return [c for c in categories if c in focus] if isinstance(focus, list) else [focus]
        return categories[:max(1, len(categories) // 2 + 1)]

    def _deepen_severities(
        self, severities: list[str], config: dict[str, Any]
    ) -> list[str]:
        depth = config.get("severity_depth", "deep")
        all_severities = ["low", "medium", "high", "critical"]
        if depth == "deep":
            return [s for s in all_severities if s not in severities] + severities
        elif depth == "critical_only":
            return ["critical", "high"]
        return severities

    def _add_dimensions(
        self,
        template: HandlerTemplate,
        config: dict[str, Any],
        extra: list[str],
    ) -> list[str]:
        base_dims = [f"{template.base_skill}_{template.specialization}_dim"]
        config_dims = config.get("additional_dimensions", [])
        return list(set(base_dims + config_dims + extra))

    def _calculate_effectiveness(
        self, cat_count: int, sev_count: int, dim_count: int
    ) -> float:
        cat_score = min(cat_count / 3.0, 1.0) * 0.3
        sev_score = min(sev_count / 4.0, 1.0) * 0.4
        dim_score = min(dim_count / 5.0, 1.0) * 0.3
        return round(cat_score + sev_score + dim_score, 4)


class HandlerPool:
    def __init__(self):
        self._handlers: dict[str, SpecializedHandler] = {}
        self._skill_index: dict[str, list[str]] = defaultdict(list)
        self.logger = logging.getLogger(__name__)

    def register(self, handler: SpecializedHandler) -> None:
        self._handlers[handler.handler_id] = handler
        self._skill_index[handler.base_skill].append(handler.handler_id)
        self.logger.info(
            "handler_registered",
            extra={"handler_id": handler.handler_id, "base_skill": handler.base_skill},
        )

    def get_handler(self, handler_id: str) -> SpecializedHandler | None:
        return self._handlers.get(handler_id)

    def list_handlers(self, base_skill: str | None = None) -> list[SpecializedHandler]:
        if base_skill:
            handler_ids = self._skill_index.get(base_skill, [])
            return [self._handlers[hid] for hid in handler_ids if hid in self._handlers]
        return list(self._handlers.values())

    def find_best_handler(self, scenario: dict[str, Any]) -> SpecializedHandler | None:
        scenario_category = scenario.get("category", "")
        scenario_severity = scenario.get("severity", "medium")

        candidates = []
        for handler in self._handlers.values():
            if handler.status != HandlerStatus.ACTIVE:
                continue
            score = self._match_score(handler, scenario_category, scenario_severity)
            if score > 0:
                candidates.append((handler, score))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _match_score(
        self, handler: SpecializedHandler, category: str, severity: str
    ) -> float:
        score = 0.0
        if category in handler.categories:
            score += 0.5
        else:
            return 0.0
        if severity in handler.severities:
            score += 0.3
        score += handler.effectiveness * 0.2
        return score

    def remove_handler(self, handler_id: str) -> bool:
        if handler_id not in self._handlers:
            return False
        handler = self._handlers[handler_id]
        if handler.base_skill in self._skill_index:
            self._skill_index[handler.base_skill] = [
                hid for hid in self._skill_index[handler.base_skill] if hid != handler_id
            ]
        del self._handlers[handler_id]
        return True


class SpecializedHandlerFactory:
    def __init__(self):
        self.specializer = HandlerSpecializer()
        self.pool = HandlerPool()
        self.handler_registry: dict[str, dict[str, Any]] = {}
        self._template_counter: int = 0
        self._handler_counter: int = 0
        self._dispatch_log: list[dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def create_template(
        self,
        base_skill: str,
        specialization: str,
        target_categories: list[str] | None = None,
        target_severities: list[str] | None = None,
    ) -> HandlerTemplate:
        self._template_counter += 1
        template = HandlerTemplate(
            template_id=f"TMPL-{self._template_counter:04d}",
            base_skill=base_skill,
            specialization=specialization,
            target_categories=target_categories or [base_skill],
            target_severities=target_severities or ["medium", "high", "critical"],
        )
        self.handler_registry[template.template_id] = {
            "type": "template",
            "base_skill": base_skill,
            "specialization": specialization,
            "created_at": template.created_at,
        }
        return template

    def specialize(
        self,
        template: HandlerTemplate,
        extra_dimensions: list[str] | None = None,
    ) -> dict[str, Any]:
        self._handler_counter += 1
        handler_id = f"SPH-{self._handler_counter:04d}"

        handler = self.specializer.specialize(
            template, handler_id, extra_dimensions=extra_dimensions
        )
        self.pool.register(handler)

        self.handler_registry[handler_id] = {
            "type": "specialized_handler",
            "base_skill": handler.base_skill,
            "specialization": handler.specialization,
            "categories": handler.categories,
            "severities": handler.severities,
            "effectiveness": handler.effectiveness,
        }

        return {
            "handler_id": handler.handler_id,
            "base_skill": handler.base_skill,
            "specialization": handler.specialization,
            "categories": handler.categories,
            "severities": handler.severities,
            "dimensions": handler.dimensions,
            "effectiveness": handler.effectiveness,
            "status": handler.status.value,
        }

    def dispatch(self, scenario: dict[str, Any]) -> dict[str, Any]:
        handler = self.pool.find_best_handler(scenario)

        if handler is None:
            result = {
                "scenario": scenario,
                "result": DispatchResult.NO_HANDLER.value,
                "handler_id": None,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            handler.dispatch_count += 1
            result = {
                "scenario": scenario,
                "result": DispatchResult.DISPATCHED.value,
                "handler_id": handler.handler_id,
                "specialization": handler.specialization,
                "effectiveness": handler.effectiveness,
                "timestamp": datetime.now().isoformat(),
            }

        self._dispatch_log.append(result)
        self.logger.info(
            "scenario_dispatched",
            extra={"result": result["result"], "handler_id": result.get("handler_id")},
        )
        return result

    def get_handler_stats(self) -> dict[str, Any]:
        handlers = self.pool.list_handlers()
        total_dispatches = sum(h.dispatch_count for h in handlers)
        avg_effectiveness = (
            sum(h.effectiveness for h in handlers) / len(handlers) if handlers else 0.0
        )

        skill_distribution: dict[str, int] = defaultdict(int)
        for h in handlers:
            skill_distribution[h.base_skill] += 1

        return {
            "total_handlers": len(handlers),
            "total_dispatches": total_dispatches,
            "average_effectiveness": round(avg_effectiveness, 4),
            "skill_distribution": dict(skill_distribution),
            "total_templates": self._template_counter,
            "dispatch_log_size": len(self._dispatch_log),
        }
