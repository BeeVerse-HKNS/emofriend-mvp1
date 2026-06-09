from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()

OPERATOR_MAP = {
    "+": "Adjacent Possible / Combinatorial / Liquid Networks",
    "log": "Platform Enablement / Abstraction",
    "*": "Cross-Domain Transfer / Exaptation",
    "^": "Constraint Amplification / Recapture",
    "/": "Specialization / Disruption",
    "sq": "Self-Improvement / Slow Hunch / Structural Deepening",
    "-": "Simplification",
    "sqrt": "Decomposition",
    "F2": "Combinatorial Explosion",
}

OPERATOR_WEIGHTS_V2 = {
    "log": 0.1834,
    "+": 0.1452,
    "*": 0.1421,
    "^": 0.1379,
    "/": 0.1271,
    "sq": 0.1244,
    "-": 0.0903,
    "sqrt": 0.0496,
    "F2": 0.0000,
}

PATTERN_TO_OPERATOR = {v: k for k, v in OPERATOR_MAP.items() if k != "F2"}
PATTERN_TO_OPERATOR["Combinatorial Explosion"] = "F2"
PATTERN_TO_OPERATOR["Abstraction"] = "log"
PATTERN_TO_OPERATOR["Adjacent Possible"] = "+"
PATTERN_TO_OPERATOR["Combinatorial"] = "+"
PATTERN_TO_OPERATOR["Liquid Networks"] = "+"
PATTERN_TO_OPERATOR["Slow Hunch"] = "sq"
PATTERN_TO_OPERATOR["Serendipity"] = "+"
PATTERN_TO_OPERATOR["Error-Driven Innovation"] = "^"
PATTERN_TO_OPERATOR["Exaptation"] = "*"
PATTERN_TO_OPERATOR["Disruptive Innovation"] = "/"
PATTERN_TO_OPERATOR["Geographic Determinism"] = "^"
PATTERN_TO_OPERATOR["Cumulative Synthesis"] = "+"
PATTERN_TO_OPERATOR["Simultaneous Invention"] = "+"
PATTERN_TO_OPERATOR["Structural Deepening"] = "sq"
PATTERN_TO_OPERATOR["Recapture"] = "^"
PATTERN_TO_OPERATOR["Platform Enablement"] = "log"

FAILURE_PATTERNS = [
    "Premature Optimization",
    "Over-Engineering",
    "Ignoring Context",
    "Sunk Cost Fallacy",
    "Not Invented Here",
    "Feature Creep",
    "Ignoring Feedback",
    "Isolation",
    "Incumbent Trap",
    "Geographic Isolation",
    "State Suppression",
    "Market Myopia",
    "Social Structure Inhibition",
]


@dataclass
class InventionPattern:
    name: str
    era: str
    problem_before: str
    core_breakthrough: str
    success_factors: list[str]
    failure_patterns: list[str]
    formula_mapping: str
    confidence: str


@dataclass
class ExtractedPattern:
    pattern_name: str
    description: str
    operator: str
    weight: float
    examples: list[str]
    anti_patterns: list[str]


@dataclass
class FormulaCandidate:
    formula: str
    score: float
    operators: list[str]
    dims: list[str]
    semantic: str = ""


class InventionPatternLearner:
    def __init__(self, project_root: str = r"d:\My_Code_Projects\Harnessing") -> None:
        self._root = Path(project_root)
        self._kb_path = self._root / "docs" / "knowledge-base" / "26-human-invention-patterns.md"
        self._inventions: list[InventionPattern] = []
        self._success_patterns: list[ExtractedPattern] = []
        self._failure_patterns_list: list[dict] = []
        self._operator_weights: dict[str, float] = {}
        self._loaded = False

    def load_from_knowledge_base(self) -> list[InventionPattern]:
        if self._loaded:
            return self._inventions

        if not self._kb_path.is_file():
            logger.warning("kb_file_not_found", path=str(self._kb_path))
            self._loaded = True
            return self._inventions

        content = self._kb_path.read_text(encoding="utf-8")
        self._inventions = self._parse_inventions(content)
        self._success_patterns = self._extract_success_patterns_internal()
        self._failure_patterns_list = self._extract_failure_patterns_internal(content)
        self._operator_weights = self._calculate_operator_weights()
        self._loaded = True

        logger.info(
            "kb_loaded",
            inventions=len(self._inventions),
            success_patterns=len(self._success_patterns),
            failure_patterns=len(self._failure_patterns_list),
        )
        return self._inventions

    def _parse_inventions(self, content: str) -> list[InventionPattern]:
        inventions = []
        sections = re.split(r"^### \d+\.\d+", content, flags=re.MULTILINE)

        for section in sections[1:]:
            name_match = re.search(r"\*\*Name & Era\*\*:\s*(.+?)(?:\s*[✅🔍⚠️❌])?\s*$", section, re.MULTILINE)
            if not name_match:
                continue

            name_era = name_match.group(1).strip()
            confidence_match = re.search(r"[✅🔍⚠️❌]", section[:name_match.end()])
            confidence = "✅"
            if confidence_match:
                char = confidence_match.group()
                confidence_map = {"✅": "✅", "🔍": "🔍", "⚠️": "⚠️", "❌": "❌"}
                confidence = confidence_map.get(char, "✅")

            era = self._detect_era(name_era)

            problem = self._extract_field(section, "Problem Before")
            breakthrough = self._extract_field(section, "Core Breakthrough")
            success = self._extract_list_field(section, "Success Factors")
            failures = self._extract_list_field(section, "Failed Attempts")
            formula = self._extract_formula_mapping(section)

            inventions.append(
                InventionPattern(
                    name=name_era,
                    era=era,
                    problem_before=problem,
                    core_breakthrough=breakthrough,
                    success_factors=success,
                    failure_patterns=failures,
                    formula_mapping=formula,
                    confidence=confidence,
                )
            )

        return inventions

    def _detect_era(self, name_era: str) -> str:
        ne = name_era.lower()
        if any(k in ne for k in ("prehistoric", "before 3000", "~1,", "~2,", "~10,", "stone tool", "fire control", "wheel —")):
            return "Prehistoric"
        if any(k in ne for k in ("ancient", "3000 bce", "sumeria", "lydia", "indus valley", "mesopotamia", "egypt", "babylon", "cai lun", "plumbing —")):
            return "Ancient"
        if any(k in ne for k in ("medieval", "gutenberg", "compass —", "gunpowder", "mechanical clock", "windmill", "arabic numeral", "brahmagupta", "persia")):
            return "Medieval"
        if any(k in ne for k in ("industrial", "newcomen", "watt", "faraday", "bell —", "niépce", "daguerre", "morse", "bessemer")):
            return "Industrial"
        if any(k in ne for k in ("information", "eniac", "turing", "arpanet", "bell labs", "maiman", "gps —", "iphone", "android", "transistor —")):
            return "Information"
        if any(k in ne for k in ("ai era", "2020", "llm —", "agent —", "harness", "rag —", "vector database", "mcp —")):
            return "AI"
        return "Unknown"

    def _extract_field(self, section: str, field_name: str) -> str:
        pattern = rf"\*\*{re.escape(field_name)}\*\*:\s*(.+?)(?:\n|$)"
        match = re.search(pattern, section)
        return match.group(1).strip() if match else ""

    def _extract_list_field(self, section: str, field_name: str) -> list[str]:
        pattern = rf"\*\*{re.escape(field_name)}\*\*:\s*(.+?)(?=\n\*\*|\n\n|\Z)"
        match = re.search(pattern, section, re.DOTALL)
        if not match:
            return []
        raw = match.group(1)
        items = re.findall(r"\(\d+\)\s*(.+?)(?:\s*\(\d+\)|$)", raw)
        if not items:
            items = [raw.strip()]
        return [i.strip() for i in items if i.strip()]

    def _extract_formula_mapping(self, section: str) -> str:
        pattern_match = re.search(r"Extracted Pattern\*\*:\s*\*\*(.+?)\*\*", section)
        if not pattern_match:
            pattern_match = re.search(r"Extracted Pattern\*\*:\s*(.+?)(?:\n|$)", section)
        if not pattern_match:
            return "+"
        pattern_text = pattern_match.group(1).strip()
        for pattern_name, op in PATTERN_TO_OPERATOR.items():
            if pattern_name.lower() in pattern_text.lower():
                return op
        return "+"

    def extract_success_patterns(self) -> list[ExtractedPattern]:
        if not self._loaded:
            self.load_from_knowledge_base()
        return self._success_patterns

    def _extract_success_patterns_internal(self) -> list[ExtractedPattern]:
        if not self._inventions:
            return []

        operator_counts: dict[str, int] = {}
        operator_examples: dict[str, list[str]] = {}
        for inv in self._inventions:
            op = inv.formula_mapping
            operator_counts[op] = operator_counts.get(op, 0) + 1
            if op not in operator_examples:
                operator_examples[op] = []
            operator_examples[op].append(inv.name)

        total = sum(operator_counts.values()) or 1
        patterns = []
        for op, count in sorted(operator_counts.items(), key=lambda x: x[1], reverse=True):
            pattern_name = OPERATOR_MAP.get(op, op)
            weight = round(count / total, 4)
            examples = operator_examples.get(op, [])[:5]
            anti = self._get_anti_patterns_for_operator(op)
            patterns.append(
                ExtractedPattern(
                    pattern_name=pattern_name,
                    description=f"Historical frequency: {count}/{total} inventions ({weight:.1%})",
                    operator=op,
                    weight=weight,
                    examples=examples,
                    anti_patterns=anti,
                )
            )

        return patterns

    def _get_anti_patterns_for_operator(self, op: str) -> list[str]:
        mapping = {
            "+": ["Feature Creep", "Over-Engineering"],
            "^": ["Premature Optimization", "Ignoring Context"],
            "log": ["Not Invented Here", "Isolation"],
            "*": ["Isolation", "Not Invented Here"],
            "-": ["Over-Engineering", "Feature Creep"],
            "/": ["Premature Optimization", "Ignoring Context", "Incumbent Trap"],
            "sq": ["Sunk Cost Fallacy", "Ignoring Feedback"],
            "sqrt": ["Over-Engineering", "Feature Creep"],
            "F2": ["Premature Optimization", "Over-Engineering"],
        }
        return mapping.get(op, [])

    def extract_failure_patterns(self) -> list[dict]:
        if not self._loaded:
            self.load_from_knowledge_base()
        return self._failure_patterns_list

    def _extract_failure_patterns_internal(self, content: str) -> list[dict]:
        patterns = []
        for fp in FAILURE_PATTERNS:
            pattern_section = re.search(
                rf"#### \d+\. {re.escape(fp)}.*?(?=#### \d+\.|---|\Z)",
                content,
                re.DOTALL,
            )
            if not pattern_section:
                patterns.append({"name": fp, "description": "", "examples": []})
                continue

            section = pattern_section.group(0)
            desc_match = re.search(r"\*\*描述\*\*：(.+?)(?:\n\n|\n\*\*|$)", section, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ""

            examples = []
            example_matches = re.findall(r"[-•]\s*(.+?)(?:\n|$)", section)
            for ex in example_matches[:5]:
                examples.append(ex.strip())

            patterns.append({"name": fp, "description": description, "examples": examples})

        return patterns

    def map_to_formula_operators(self) -> dict[str, str]:
        if not self._loaded:
            self.load_from_knowledge_base()
        return dict(OPERATOR_MAP)

    def get_pattern_weights(self) -> dict[str, float]:
        if not self._loaded:
            self.load_from_knowledge_base()
        return dict(self._operator_weights)

    def _calculate_operator_weights(self) -> dict[str, float]:
        if not self._inventions:
            return dict(OPERATOR_WEIGHTS_V2)

        counts: dict[str, int] = {}
        for inv in self._inventions:
            op = inv.formula_mapping
            counts[op] = counts.get(op, 0) + 1

        total = sum(counts.values()) or 1
        weights = {}
        for op in OPERATOR_MAP:
            c = counts.get(op, 0)
            weights[op] = round(c / total, 4)

        if total < 50:
            for op in OPERATOR_MAP:
                kb_weight = OPERATOR_WEIGHTS_V2.get(op, 0.0)
                weights[op] = round(weights[op] * 0.3 + kb_weight * 0.7, 4)

        return weights

    def filter_by_failure_patterns(self, candidate: FormulaCandidate) -> tuple[bool, list[str]]:
        if not self._loaded:
            self.load_from_knowledge_base()

        matched_failures = []
        formula_str = candidate.formula.lower()
        semantic_lower = candidate.semantic.lower()

        if len(candidate.operators) > 4:
            matched_failures.append("Over-Engineering")

        if len(candidate.dims) > 5:
            matched_failures.append("Feature Creep")

        if "sq" in candidate.operators and candidate.score < 0:
            matched_failures.append("Premature Optimization")

        if all(d in candidate.dims for d in ["K", "R", "C", "M", "S", "G", "A", "P", "F", "H"]):
            matched_failures.append("Over-Engineering")
            matched_failures.append("Feature Creep")

        if len(candidate.operators) >= 3 and "^" in candidate.operators:
            matched_failures.append("Premature Optimization")

        has_only_unary = all(op in ("sq", "sqrt", "^", "log") for op in candidate.operators)
        if has_only_unary and len(candidate.operators) >= 2:
            matched_failures.append("Ignoring Context")

        matched_failures = list(dict.fromkeys(matched_failures))
        is_filtered = len(matched_failures) > 0
        return is_filtered, matched_failures

    def enhance_formula_candidates(self, candidates: list[FormulaCandidate]) -> list[FormulaCandidate]:
        if not self._loaded:
            self.load_from_knowledge_base()

        if not candidates:
            return []

        enhanced = []
        for candidate in candidates:
            is_filtered, failures = self.filter_by_failure_patterns(candidate)
            if is_filtered and len(failures) >= 2:
                continue

            weight_boost = self._calculate_weight_boost(candidate)
            failure_penalty = len(failures) * 0.15

            new_score = candidate.score + weight_boost - failure_penalty

            enhanced.append(
                FormulaCandidate(
                    formula=candidate.formula,
                    score=round(new_score, 4),
                    operators=candidate.operators,
                    dims=candidate.dims,
                    semantic=candidate.semantic,
                )
            )

        enhanced.sort(key=lambda x: x.score, reverse=True)
        return enhanced

    def _calculate_weight_boost(self, candidate: FormulaCandidate) -> float:
        boost = 0.0
        for op in candidate.operators:
            weight = self._operator_weights.get(op, 0.0)
            boost += weight * 0.5

        if "log" in candidate.operators:
            boost += 0.3
        if "+" in candidate.operators:
            boost += 0.25
        if "*" in candidate.operators:
            boost += 0.2
        if "^" in candidate.operators:
            boost += 0.15
        if "/" in candidate.operators:
            boost += 0.1

        return boost

    def get_inventions_by_era(self, era: str) -> list[InventionPattern]:
        if not self._loaded:
            self.load_from_knowledge_base()
        return [inv for inv in self._inventions if inv.era.lower() == era.lower()]

    def get_inventions_by_operator(self, operator: str) -> list[InventionPattern]:
        if not self._loaded:
            self.load_from_knowledge_base()
        return [inv for inv in self._inventions if inv.formula_mapping == operator]

    def get_summary(self) -> dict:
        if not self._loaded:
            self.load_from_knowledge_base()

        era_counts: dict[str, int] = {}
        operator_counts: dict[str, int] = {}
        confidence_counts: dict[str, int] = {}

        for inv in self._inventions:
            era_counts[inv.era] = era_counts.get(inv.era, 0) + 1
            operator_counts[inv.formula_mapping] = operator_counts.get(inv.formula_mapping, 0) + 1
            confidence_counts[inv.confidence] = confidence_counts.get(inv.confidence, 0) + 1

        return {
            "total_inventions": len(self._inventions),
            "eras": era_counts,
            "operator_distribution": operator_counts,
            "confidence_distribution": confidence_counts,
            "success_patterns": len(self._success_patterns),
            "failure_patterns": len(self._failure_patterns_list),
            "operator_weights": self._operator_weights,
        }
