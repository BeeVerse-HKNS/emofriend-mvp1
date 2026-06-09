from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class BridgeType(str, Enum):
    OVERLAP = "overlap"
    COMPLEMENT = "complement"
    AMPLIFY = "amplify"
    CASCADE = "cascade"


class BridgeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


@dataclass
class DomainProfile:
    domain_name: str
    categories: list[str]
    key_dimensions: list[str]
    skill_count: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SynergyBridge:
    bridge_id: str
    domain_a: str
    domain_b: str
    bridge_type: BridgeType
    effectiveness: float = 0.0
    status: BridgeStatus = BridgeStatus.INACTIVE
    shared_categories: list[str] = field(default_factory=list)
    shared_dimensions: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SynergyResult:
    synergy_type: BridgeType
    domain_a: str
    domain_b: str
    score: float
    shared_elements: list[str]
    complement_elements: list[str]


class SynergyDetector:
    def __init__(self, overlap_weight: float = 0.4, complement_weight: float = 0.3, skill_weight: float = 0.3):
        self.overlap_weight = overlap_weight
        self.complement_weight = complement_weight
        self.skill_weight = skill_weight
        self.logger = logging.getLogger(__name__)

    def find_overlap(self, profile_a: DomainProfile, profile_b: DomainProfile) -> list[str]:
        return list(set(profile_a.categories) & set(profile_b.categories))

    def find_complement(self, profile_a: DomainProfile, profile_b: DomainProfile) -> list[str]:
        a_only = set(profile_a.categories) - set(profile_b.categories)
        b_only = set(profile_b.categories) - set(profile_a.categories)
        return list(a_only | b_only)

    def find_dimension_overlap(self, profile_a: DomainProfile, profile_b: DomainProfile) -> list[str]:
        return list(set(profile_a.key_dimensions) & set(profile_b.key_dimensions))

    def find_dimension_complement(self, profile_a: DomainProfile, profile_b: DomainProfile) -> list[str]:
        a_only = set(profile_a.key_dimensions) - set(profile_b.key_dimensions)
        b_only = set(profile_b.key_dimensions) - set(profile_a.key_dimensions)
        return list(a_only | b_only)

    def calculate_synergy_score(self, profile_a: DomainProfile, profile_b: DomainProfile) -> float:
        cat_overlap = len(self.find_overlap(profile_a, profile_b))
        cat_complement = len(self.find_complement(profile_a, profile_b))
        dim_overlap = len(self.find_dimension_overlap(profile_a, profile_b))
        dim_complement = len(self.find_dimension_complement(profile_a, profile_b))

        total_cats = len(set(profile_a.categories) | set(profile_b.categories))
        total_dims = len(set(profile_a.key_dimensions) | set(profile_b.key_dimensions))

        overlap_score = (cat_overlap + dim_overlap) / max(total_cats + total_dims, 1)
        complement_score = (cat_complement + dim_complement) / max(total_cats + total_dims, 1)
        skill_score = min(profile_a.skill_count + profile_b.skill_count, 20) / 20.0

        synergy = (
            overlap_score * self.overlap_weight
            + complement_score * self.complement_weight
            + skill_score * self.skill_weight
        )
        return round(synergy, 4)

    def detect_synergies(
        self, profile_a: DomainProfile, profile_b: DomainProfile, min_score: float = 0.1
    ) -> list[SynergyResult]:
        results = []
        score = self.calculate_synergy_score(profile_a, profile_b)

        if score < min_score:
            return results

        cat_overlap = self.find_overlap(profile_a, profile_b)
        cat_complement = self.find_complement(profile_a, profile_b)
        dim_overlap = self.find_dimension_overlap(profile_a, profile_b)

        if cat_overlap and dim_overlap:
            results.append(SynergyResult(
                synergy_type=BridgeType.OVERLAP,
                domain_a=profile_a.domain_name,
                domain_b=profile_b.domain_name,
                score=score,
                shared_elements=cat_overlap + dim_overlap,
                complement_elements=[],
            ))

        if cat_complement:
            complement_score = len(cat_complement) / max(
                len(set(profile_a.categories) | set(profile_b.categories)), 1
            )
            if complement_score >= 0.2:
                results.append(SynergyResult(
                    synergy_type=BridgeType.COMPLEMENT,
                    domain_a=profile_a.domain_name,
                    domain_b=profile_b.domain_name,
                    score=round(score * complement_score, 4),
                    shared_elements=[],
                    complement_elements=cat_complement,
                ))

        if score >= 0.5:
            results.append(SynergyResult(
                synergy_type=BridgeType.AMPLIFY,
                domain_a=profile_a.domain_name,
                domain_b=profile_b.domain_name,
                score=score,
                shared_elements=cat_overlap + dim_overlap,
                complement_elements=cat_complement,
            ))

        return results


class CrossDomainSynergy:
    def __init__(self):
        self.detector = SynergyDetector()
        self.active_bridges: list[SynergyBridge] = []
        self._domain_profiles: dict[str, DomainProfile] = {}
        self._bridge_counter: int = 0
        self._activation_log: list[dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)

    def profile_domain(self, skills: list[dict[str, Any]], domain_name: str | None = None) -> DomainProfile:
        if domain_name is None:
            domain_name = skills[0].get("domain", "unknown") if skills else "unknown"

        categories: list[str] = []
        dimensions: list[str] = []
        for skill in skills:
            cats = skill.get("categories", [])
            dims = skill.get("dimensions", [])
            categories.extend(cats)
            dimensions.extend(dims)

        categories = list(set(categories))
        dimensions = list(set(dimensions))

        profile = DomainProfile(
            domain_name=domain_name,
            categories=categories,
            key_dimensions=dimensions,
            skill_count=len(skills),
        )
        self._domain_profiles[domain_name] = profile
        return profile

    def detect_synergies(
        self, profile_a: DomainProfile, profile_b: DomainProfile, min_score: float = 0.1
    ) -> list[dict[str, Any]]:
        synergy_results = self.detector.detect_synergies(profile_a, profile_b, min_score=min_score)
        return [
            {
                "synergy_type": s.synergy_type.value,
                "domain_a": s.domain_a,
                "domain_b": s.domain_b,
                "score": s.score,
                "shared_elements": s.shared_elements,
                "complement_elements": s.complement_elements,
            }
            for s in synergy_results
        ]

    def create_bridge(self, synergy: dict[str, Any]) -> SynergyBridge:
        self._bridge_counter += 1
        bridge_id = f"BRG-{self._bridge_counter:04d}"

        bridge_type = BridgeType(synergy.get("synergy_type", BridgeType.OVERLAP.value))
        effectiveness = synergy.get("score", 0.0)
        shared = synergy.get("shared_elements", [])

        bridge = SynergyBridge(
            bridge_id=bridge_id,
            domain_a=synergy.get("domain_a", ""),
            domain_b=synergy.get("domain_b", ""),
            bridge_type=bridge_type,
            effectiveness=effectiveness,
            shared_categories=[e for e in shared if e in self._get_all_categories()],
            shared_dimensions=[e for e in shared if e not in self._get_all_categories()],
        )

        self.logger.info(
            "bridge_created",
            extra={
                "bridge_id": bridge_id,
                "domain_a": bridge.domain_a,
                "domain_b": bridge.domain_b,
                "bridge_type": bridge.bridge_type.value,
                "effectiveness": effectiveness,
            },
        )
        return bridge

    def activate_bridge(self, bridge: SynergyBridge) -> dict[str, Any]:
        bridge.status = BridgeStatus.ACTIVE
        self.active_bridges.append(bridge)

        activation = {
            "bridge_id": bridge.bridge_id,
            "domain_a": bridge.domain_a,
            "domain_b": bridge.domain_b,
            "bridge_type": bridge.bridge_type.value,
            "effectiveness": bridge.effectiveness,
            "status": bridge.status.value,
            "activated_at": datetime.now().isoformat(),
        }
        self._activation_log.append(activation)

        self.logger.info(
            "bridge_activated",
            extra={"bridge_id": bridge.bridge_id, "effectiveness": bridge.effectiveness},
        )
        return activation

    def get_active_synergies(self) -> list[dict[str, Any]]:
        return [
            {
                "bridge_id": b.bridge_id,
                "domain_a": b.domain_a,
                "domain_b": b.domain_b,
                "bridge_type": b.bridge_type.value,
                "effectiveness": b.effectiveness,
                "status": b.status.value,
                "shared_categories": b.shared_categories,
                "shared_dimensions": b.shared_dimensions,
            }
            for b in self.active_bridges
        ]

    def get_synergy_summary(self) -> dict[str, Any]:
        type_counts: dict[str, int] = defaultdict(int)
        total_effectiveness = 0.0
        for bridge in self.active_bridges:
            type_counts[bridge.bridge_type.value] += 1
            total_effectiveness += bridge.effectiveness

        return {
            "total_domains": len(self._domain_profiles),
            "total_bridges": len(self.active_bridges),
            "bridge_type_distribution": dict(type_counts),
            "average_effectiveness": round(
                total_effectiveness / len(self.active_bridges), 4
            ) if self.active_bridges else 0.0,
            "total_effectiveness": round(total_effectiveness, 4),
        }

    def _get_all_categories(self) -> set[str]:
        cats: set[str] = set()
        for profile in self._domain_profiles.values():
            cats.update(profile.categories)
        return cats
