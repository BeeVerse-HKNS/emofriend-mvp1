from __future__ import annotations

import itertools
import math
import structlog
from dataclasses import dataclass, field
from typing import Any

from .base_engine import BaseInventionEngine
from .base_invention_engine import ConfidenceLevel, InventionResult

logger = structlog.get_logger()


@dataclass
class SymmetryGroup:
    group_type: str
    elements: list
    dimension: int


@dataclass
class GoldstoneMode:
    dimension: int
    range_min: float
    range_max: float
    novelty_score: float


@dataclass
class CompletenessReport:
    total_expected: int
    total_found: int
    completeness_ratio: float
    is_complete: bool


class SymmetryGroupIdentifier:
    def __init__(self) -> None:
        self._type_detectors = {
            "permutation": self._detect_permutation,
            "scale": self._detect_scale,
            "translation": self._detect_translation,
        }

    def identify(self, solution: Any) -> list[SymmetryGroup]:
        groups: list[SymmetryGroup] = []
        if isinstance(solution, (list, tuple)):
            groups.extend(self._detect_permutation(solution))
            groups.extend(self._detect_scale(solution))
            groups.extend(self._detect_translation(solution))
        elif isinstance(solution, dict):
            values = list(solution.values())
            groups.extend(self._detect_permutation(values))
            groups.extend(self._detect_scale(values))
            groups.extend(self._detect_translation(values))
        elif isinstance(solution, str):
            chars = list(solution)
            groups.extend(self._detect_permutation(chars))
        else:
            groups.append(SymmetryGroup(
                group_type="scale",
                elements=[solution],
                dimension=1,
            ))
        logger.info(
            "symmetry_groups_identified",
            total_groups=len(groups),
            types=[g.group_type for g in groups],
        )
        return groups

    def _detect_permutation(self, elements: list) -> list[SymmetryGroup]:
        groups: list[SymmetryGroup] = []
        n = len(elements)
        if n < 2:
            return groups
        seen_types: dict[type, list[int]] = {}
        for i, elem in enumerate(elements):
            t = type(elem)
            if t not in seen_types:
                seen_types[t] = []
            seen_types[t].append(i)
        for t, indices in seen_types.items():
            if len(indices) >= 2:
                perm_count = math.factorial(len(indices))
                groups.append(SymmetryGroup(
                    group_type="permutation",
                    elements=indices,
                    dimension=perm_count,
                ))
        return groups

    def _detect_scale(self, elements: list) -> list[SymmetryGroup]:
        groups: list[SymmetryGroup] = []
        numeric = [e for e in elements if isinstance(e, (int, float))]
        if len(numeric) < 2:
            return groups
        for i in range(len(numeric) - 1):
            for j in range(i + 1, len(numeric)):
                if numeric[j] != 0 and numeric[i] != 0:
                    ratio = numeric[i] / numeric[j]
                    if abs(ratio - round(ratio)) < 1e-9 and round(ratio) > 1:
                        groups.append(SymmetryGroup(
                            group_type="scale",
                            elements=[numeric[i], numeric[j]],
                            dimension=int(round(ratio)),
                        ))
        return groups

    def _detect_translation(self, elements: list) -> list[SymmetryGroup]:
        groups: list[SymmetryGroup] = []
        numeric = [e for e in elements if isinstance(e, (int, float))]
        if len(numeric) < 2:
            return groups
        diffs: dict[float, list[tuple[int, int]]] = {}
        for i in range(len(numeric) - 1):
            diff = numeric[i + 1] - numeric[i]
            rounded = round(diff, 10)
            if rounded not in diffs:
                diffs[rounded] = []
            diffs[rounded].append((i, i + 1))
        for diff, pairs in diffs.items():
            if len(pairs) >= 2:
                groups.append(SymmetryGroup(
                    group_type="translation",
                    elements=[p[0] for p in pairs],
                    dimension=len(pairs),
                ))
        return groups


class ControlledSymmetryBreaker:
    def break_symmetry(
        self,
        solution: Any,
        group: SymmetryGroup,
        break_dimension: int | None = None,
    ) -> list[Any]:
        variants: list[Any] = []
        if group.group_type == "permutation":
            variants = self._break_permutation(solution, group, break_dimension)
        elif group.group_type == "scale":
            variants = self._break_scale(solution, group, break_dimension)
        elif group.group_type == "translation":
            variants = self._break_translation(solution, group, break_dimension)
        else:
            variants = [solution]
        logger.info(
            "symmetry_broken",
            group_type=group.group_type,
            variant_count=len(variants),
        )
        return variants

    def _break_permutation(
        self,
        solution: Any,
        group: SymmetryGroup,
        break_dimension: int | None,
    ) -> list[Any]:
        if isinstance(solution, (list, tuple)):
            elements = list(solution)
        elif isinstance(solution, dict):
            elements = list(solution.values())
        elif isinstance(solution, str):
            elements = list(solution)
        else:
            return [solution]
        indices = group.elements
        max_perms = min(math.factorial(len(indices)), 24)
        variants: list[Any] = []
        seen: set[tuple] = set()
        for perm in itertools.permutations(indices):
            if len(variants) >= max_perms:
                break
            key = tuple(perm)
            if key in seen:
                continue
            seen.add(key)
            new_elements = elements.copy()
            for orig_idx, new_idx in zip(indices, perm):
                new_elements[orig_idx] = elements[new_idx]
            if isinstance(solution, tuple):
                variants.append(tuple(new_elements))
            elif isinstance(solution, str):
                variants.append("".join(new_elements))
            else:
                variants.append(new_elements)
            if break_dimension and len(variants) >= break_dimension:
                break
        return variants

    def _break_scale(
        self,
        solution: Any,
        group: SymmetryGroup,
        break_dimension: int | None,
    ) -> list[Any]:
        if isinstance(solution, (list, tuple)):
            elements = list(solution)
        elif isinstance(solution, dict):
            elements = list(solution.values())
        else:
            return [solution]
        scale_factors = [0.5, 0.75, 1.25, 1.5, 2.0, 3.0]
        if break_dimension:
            scale_factors = scale_factors[:break_dimension]
        variants: list[Any] = []
        for sf in scale_factors:
            new_elements = [
                e * sf if isinstance(e, (int, float)) else e
                for e in elements
            ]
            if isinstance(solution, tuple):
                variants.append(tuple(new_elements))
            else:
                variants.append(new_elements)
        return variants

    def _break_translation(
        self,
        solution: Any,
        group: SymmetryGroup,
        break_dimension: int | None,
    ) -> list[Any]:
        if isinstance(solution, (list, tuple)):
            elements = list(solution)
        elif isinstance(solution, dict):
            elements = list(solution.values())
        else:
            return [solution]
        offsets = [-2.0, -1.0, 1.0, 2.0, 3.0, 5.0]
        if break_dimension:
            offsets = offsets[:break_dimension]
        variants: list[Any] = []
        for offset in offsets:
            new_elements = [
                e + offset if isinstance(e, (int, float)) else e
                for e in elements
            ]
            if isinstance(solution, tuple):
                variants.append(tuple(new_elements))
            else:
                variants.append(new_elements)
        return variants


class GoldstoneModeExplorer:
    def explore(self, variant: Any, broken_symmetry: SymmetryGroup) -> list[GoldstoneMode]:
        modes: list[GoldstoneMode] = []
        if broken_symmetry.group_type == "permutation":
            modes = self._explore_permutation_modes(variant, broken_symmetry)
        elif broken_symmetry.group_type == "scale":
            modes = self._explore_scale_modes(variant, broken_symmetry)
        elif broken_symmetry.group_type == "translation":
            modes = self._explore_translation_modes(variant, broken_symmetry)
        logger.info(
            "goldstone_modes_explored",
            group_type=broken_symmetry.group_type,
            mode_count=len(modes),
        )
        return modes

    def _explore_permutation_modes(
        self, variant: Any, broken_symmetry: SymmetryGroup
    ) -> list[GoldstoneMode]:
        modes: list[GoldstoneMode] = []
        n = len(broken_symmetry.elements)
        for dim in range(n):
            novelty = 1.0 - (1.0 / math.factorial(n - dim))
            modes.append(GoldstoneMode(
                dimension=dim,
                range_min=0.0,
                range_max=float(math.factorial(n - dim)),
                novelty_score=round(novelty, 4),
            ))
        return modes

    def _explore_scale_modes(
        self, variant: Any, broken_symmetry: SymmetryGroup
    ) -> list[GoldstoneMode]:
        modes: list[GoldstoneMode] = []
        scale_range = broken_symmetry.dimension if broken_symmetry.dimension > 0 else 2
        for dim in range(scale_range):
            novelty = 1.0 - (1.0 / (dim + 2))
            modes.append(GoldstoneMode(
                dimension=dim,
                range_min=1.0 / (dim + 2),
                range_max=float(dim + 2),
                novelty_score=round(novelty, 4),
            ))
        return modes

    def _explore_translation_modes(
        self, variant: Any, broken_symmetry: SymmetryGroup
    ) -> list[GoldstoneMode]:
        modes: list[GoldstoneMode] = []
        n = broken_symmetry.dimension
        for dim in range(n):
            novelty = 1.0 - (1.0 / (dim + 2))
            modes.append(GoldstoneMode(
                dimension=dim,
                range_min=-float(dim + 1),
                range_max=float(dim + 1),
                novelty_score=round(novelty, 4),
            ))
        return modes


class VariantCompletenessChecker:
    def check(
        self, variants: list[Any], symmetry_group: SymmetryGroup
    ) -> CompletenessReport:
        total_expected = self._compute_expected(symmetry_group)
        total_found = len(variants)
        ratio = total_found / total_expected if total_expected > 0 else 0.0
        report = CompletenessReport(
            total_expected=total_expected,
            total_found=total_found,
            completeness_ratio=round(ratio, 4),
            is_complete=total_found >= total_expected,
        )
        logger.info(
            "completeness_checked",
            total_expected=report.total_expected,
            total_found=report.total_found,
            completeness_ratio=report.completeness_ratio,
            is_complete=report.is_complete,
        )
        return report

    def _compute_expected(self, symmetry_group: SymmetryGroup) -> int:
        if symmetry_group.group_type == "permutation":
            n = len(symmetry_group.elements)
            return min(math.factorial(n), 24)
        elif symmetry_group.group_type == "scale":
            return 6
        elif symmetry_group.group_type == "translation":
            return 6
        return 1


class SymmetryBreakingCreativity(BaseInventionEngine):
    name = "SymmetryBreakingCreativity"
    invention_id = "SCI-005"
    operator = "Σ⁻¹"
    formula = "Σ⁻¹(solution) → break(symmetry) → explore(Goldstone_modes)"
    category = "SCI"
    description = "Generate creative variants by deliberately breaking symmetry"

    def __init__(self) -> None:
        self._identifier = SymmetryGroupIdentifier()
        self._breaker = ControlledSymmetryBreaker()
        self._explorer = GoldstoneModeExplorer()
        self._checker = VariantCompletenessChecker()

    def execute(self, context: dict[str, Any]) -> InventionResult:
        solution = context.get("solution")
        if solution is None:
            logger.error("no_solution_in_context")
            return InventionResult(
                output={},
                confidence=ConfidenceLevel.UNCERTAIN,
                invention_id=self.invention_id,
            )
        symmetry_groups = self._identifier.identify(solution)
        if not symmetry_groups:
            logger.info("no_symmetry_found")
            return InventionResult(
                output={"solution": solution, "symmetry_groups": [], "variants": [], "goldstone_modes": [], "completeness": None},
                confidence=ConfidenceLevel.INFERRED,
                invention_id=self.invention_id,
            )
        all_variants: list[Any] = []
        all_modes: list[dict[str, Any]] = []
        completeness_reports: list[dict[str, Any]] = []
        for group in symmetry_groups:
            break_dim = context.get("break_dimension")
            variants = self._breaker.break_symmetry(solution, group, break_dim)
            all_variants.extend(variants)
            for variant in variants:
                modes = self._explorer.explore(variant, group)
                for mode in modes:
                    all_modes.append({
                        "dimension": mode.dimension,
                        "range_min": mode.range_min,
                        "range_max": mode.range_max,
                        "novelty_score": mode.novelty_score,
                        "broken_group_type": group.group_type,
                    })
            report = self._checker.check(variants, group)
            completeness_reports.append({
                "group_type": group.group_type,
                "total_expected": report.total_expected,
                "total_found": report.total_found,
                "completeness_ratio": report.completeness_ratio,
                "is_complete": report.is_complete,
            })
        output = {
            "solution": solution,
            "symmetry_groups": [
                {"group_type": g.group_type, "elements": g.elements, "dimension": g.dimension}
                for g in symmetry_groups
            ],
            "variants": all_variants,
            "goldstone_modes": all_modes,
            "completeness": completeness_reports,
            "total_variants": len(all_variants),
            "total_modes": len(all_modes),
        }
        confidence = ConfidenceLevel.VERIFIED if all(
            r.get("is_complete", False) for r in completeness_reports
        ) else ConfidenceLevel.INFERRED
        return InventionResult(
            output=output,
            confidence=confidence,
            synergy_detected=self.get_synergy_partners(),
            invention_id=self.invention_id,
        )

    def validate(self, result: InventionResult) -> bool:
        if not result.is_valid():
            return False
        output = result.output
        if "solution" not in output:
            return False
        if "symmetry_groups" not in output:
            return False
        if "variants" not in output:
            return False
        if "goldstone_modes" not in output:
            return False
        if "completeness" not in output:
            return False
        return True

    def get_synergy_partners(self) -> list[str]:
        return ["SCI-004", "SCI-002", "EWF-002"]
