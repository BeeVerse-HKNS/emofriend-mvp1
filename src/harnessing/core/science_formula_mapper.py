from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BeeVerseOperator(Enum):
    UNION = "+"
    DIFFERENCE = "-"
    CROSS = "*"
    SPECIALIZE = "/"
    SELF_IMPROVE = "sq"
    DECOMPOSE = "sqrt"
    AMPLIFY = "^"
    ABSTRACT = "log"


@dataclass
class ScienceFormula:
    name: str
    formula: str
    discoverer: str
    year: int
    field: str
    operator_mapping: BeeVerseOperator
    mapping_rationale: str
    deep_connections: list[str] = field(default_factory=list)
    confidence: str = "⚠️"


@dataclass
class DeepConnection:
    connection_id: str
    left_domain: str
    right_domain: str
    bridge_concept: str
    operator_involved: BeeVerseOperator
    description: str
    confidence: str = "⚠️"


OPERATOR_SEMANTICS = {
    BeeVerseOperator.UNION: "combine domains into new capability",
    BeeVerseOperator.DIFFERENCE: "remove to concentrate on core",
    BeeVerseOperator.CROSS: "cross for emergent synergy",
    BeeVerseOperator.SPECIALIZE: "deep narrow breakthrough",
    BeeVerseOperator.SELF_IMPROVE: "apply to itself for qualitative shift",
    BeeVerseOperator.DECOMPOSE: "break down to discover hidden structure",
    BeeVerseOperator.AMPLIFY: "raise to power for exponential capability",
    BeeVerseOperator.ABSTRACT: "extract universal pattern",
}

OPERATOR_INVENTION_TEMPLATES = {
    BeeVerseOperator.UNION: [
        ("CrossDisciplineSynthesizer", "({field_a} + {field_b})", "unite two domains to create hybrid capability"),
        ("DomainBridgeBuilder", "({field_a} + {field_b} + {field_c})", "bridge three domains via shared abstractions"),
    ],
    BeeVerseOperator.DIFFERENCE: [
        ("CoreEssenceExtractor", "({field_a} - {field_b})", "strip away overlap to reveal unique contribution"),
        ("SignalPurifier", "({field_a} - noise)", "remove noise to isolate pure signal"),
    ],
    BeeVerseOperator.CROSS: [
        ("EmergentCapabilityForge", "({field_a} * {field_b})", "cross-pollinate for 1+1>2 emergent behavior"),
        ("SynergyAmplifier", "({field_a} * {field_b} * {field_c})", "triple synergy for novel emergence"),
    ],
    BeeVerseOperator.SPECIALIZE: [
        ("DomainExpertLens", "({field_a} / {field_b})", "apply general capability through domain-specific lens"),
        ("PrecisionBreakthrough", "({field_a} / constraint)", "focus capability on narrow constraint for breakthrough"),
    ],
    BeeVerseOperator.SELF_IMPROVE: [
        ("RecursiveMetaEngine", "sq({field_a})", "apply domain to itself for qualitative leap"),
        ("SelfOptimizingLoop", "sq(sq({field_a}))", "double recursion for meta-level improvement"),
    ],
    BeeVerseOperator.DECOMPOSE: [
        ("HiddenStructureRevealer", "sqrt({field_a})", "decompose complex system to find hidden components"),
        ("AtomicCapabilityExtractor", "sqrt({field_a} * {field_b})", "decompose synergy to find atomic building blocks"),
    ],
    BeeVerseOperator.AMPLIFY: [
        ("ExponentialBreakthroughEngine", "({field_a} ^ {field_b})", "amplify by another domain's power"),
        ("ParadigmShiftAccelerator", "({field_a} ^ 2)", "square for exponential paradigm shift"),
    ],
    BeeVerseOperator.ABSTRACT: [
        ("UniversalPatternExtractor", "log({field_a})", "extract universal pattern from specific domain"),
        ("MetaPrincipleDiscoverer", "log({field_a} + {field_b})", "abstract across combined domains for meta-principle"),
    ],
}


class ScienceFormulaMapper:
    def __init__(self):
        self.formulas: dict[str, ScienceFormula] = {}
        self.connections: list[DeepConnection] = []
        self._init_historical_formulas()
        self._init_deep_connections()

    def _init_historical_formulas(self):
        historical = [
            ScienceFormula(
                name="Mass-Energy Equivalence",
                formula="E=mc²",
                discoverer="Albert Einstein",
                year=1905,
                field="Physics",
                operator_mapping=BeeVerseOperator.AMPLIFY,
                mapping_rationale="mass amplified by speed of light squared produces energy; exponential amplification of rest mass",
                deep_connections=["conservation_law_symmetry_entropy", "quantum_superposition_fuzzy_logic"],
                confidence="✅",
            ),
            ScienceFormula(
                name="Newton's Second Law",
                formula="F=ma",
                discoverer="Isaac Newton",
                year=1687,
                field="Classical Mechanics",
                operator_mapping=BeeVerseOperator.CROSS,
                mapping_rationale="force emerges from cross of mass and acceleration; multiplicative interaction produces emergent quantity",
                deep_connections=["conservation_law_symmetry_entropy"],
                confidence="✅",
            ),
            ScienceFormula(
                name="Pythagorean Theorem",
                formula="a²+b²=c²",
                discoverer="Pythagoras",
                year=-500,
                field="Geometry",
                operator_mapping=BeeVerseOperator.UNION,
                mapping_rationale="union of two orthogonal squares produces the hypotenuse square; additive combination of perpendicular contributions",
                deep_connections=["phase_transition_critical_emergence"],
                confidence="✅",
            ),
            ScienceFormula(
                name="Euler's Identity",
                formula="e^(iπ)+1=0",
                discoverer="Leonhard Euler",
                year=1748,
                field="Mathematics",
                operator_mapping=BeeVerseOperator.ABSTRACT,
                mapping_rationale="abstracts the deepest connection between five fundamental constants; logarithmic/exponential unification of disparate domains",
                deep_connections=["conservation_law_symmetry_entropy", "quantum_superposition_fuzzy_logic"],
                confidence="✅",
            ),
            ScienceFormula(
                name="Schrödinger Equation",
                formula="iℏ∂ψ/∂t=Ĥψ",
                discoverer="Erwin Schrödinger",
                year=1926,
                field="Quantum Mechanics",
                operator_mapping=BeeVerseOperator.ABSTRACT,
                mapping_rationale="wave function abstracts particle behavior into probability amplitude; universal pattern extraction from quantum reality",
                deep_connections=["quantum_superposition_fuzzy_logic", "conservation_law_symmetry_entropy"],
                confidence="✅",
            ),
            ScienceFormula(
                name="Navier-Stokes Equations",
                formula="ρ(∂v/∂t+v·∇v)=-∇p+μ∇²v+f",
                discoverer="Claude-Louis Navier / George Stokes",
                year=1822,
                field="Fluid Dynamics",
                operator_mapping=BeeVerseOperator.CROSS,
                mapping_rationale="velocity and pressure fields cross to produce complex flow behavior; multiplicative interaction of transport phenomena",
                deep_connections=["phase_transition_critical_emergence"],
                confidence="✅",
            ),
            ScienceFormula(
                name="Maxwell's Equations",
                formula="∇·E=ρ/ε₀, ∇×E=-∂B/∂t, ∇·B=0, ∇×B=μ₀J+μ₀ε₀∂E/∂t",
                discoverer="James Clerk Maxwell",
                year=1865,
                field="Electromagnetism",
                operator_mapping=BeeVerseOperator.UNION,
                mapping_rationale="union of electric and magnetic fields into unified electromagnetic theory; combining separate domains reveals deeper unity",
                deep_connections=["conservation_law_symmetry_entropy"],
                confidence="✅",
            ),
            ScienceFormula(
                name="Bayes' Theorem",
                formula="P(A|B)=P(B|A)P(A)/P(B)",
                discoverer="Thomas Bayes",
                year=1763,
                field="Statistics",
                operator_mapping=BeeVerseOperator.SPECIALIZE,
                mapping_rationale="prior belief specialized by observed evidence; dividing by evidence normalizes and focuses the hypothesis space",
                deep_connections=["quantum_superposition_fuzzy_logic"],
                confidence="✅",
            ),
            ScienceFormula(
                name="Gödel's First Incompleteness Theorem",
                formula="∀T∈ConsistentRecursive⇒∃G∈T: G⊬T∧¬G⊬T",
                discoverer="Kurt Gödel",
                year=1931,
                field="Mathematical Logic",
                operator_mapping=BeeVerseOperator.SELF_IMPROVE,
                mapping_rationale="formal system applied to itself reveals inherent limitations; self-referential application produces qualitative shift in understanding",
                deep_connections=["conservation_law_symmetry_entropy", "quantum_superposition_fuzzy_logic"],
                confidence="✅",
            ),
            ScienceFormula(
                name="Boltzmann Entropy",
                formula="S=k·ln(W)",
                discoverer="Ludwig Boltzmann",
                year=1877,
                field="Statistical Mechanics",
                operator_mapping=BeeVerseOperator.ABSTRACT,
                mapping_rationale="logarithmic abstraction of microstate count reveals macroscopic entropy; extracting universal pattern from combinatorial complexity",
                deep_connections=["conservation_law_symmetry_entropy", "phase_transition_critical_emergence"],
                confidence="✅",
            ),
            ScienceFormula(
                name="Heisenberg Uncertainty Principle",
                formula="ΔxΔp≥ℏ/2",
                discoverer="Werner Heisenberg",
                year=1927,
                field="Quantum Mechanics",
                operator_mapping=BeeVerseOperator.DIFFERENCE,
                mapping_rationale="precision in one observable removes precision from conjugate observable; trade-off as difference/focus operation",
                deep_connections=["quantum_superposition_fuzzy_logic"],
                confidence="✅",
            ),
        ]

        for f in historical:
            self.formulas[f.name] = f

    def _init_deep_connections(self):
        self.connections = [
            DeepConnection(
                connection_id="conservation_law_symmetry_entropy",
                left_domain="Conservation Laws",
                right_domain="Symmetry Groups",
                bridge_concept="Information Entropy",
                operator_involved=BeeVerseOperator.ABSTRACT,
                description="Noether's theorem links continuous symmetries to conservation laws; Shannon entropy bridges both to information theory. The abstract pattern: invariance ↔ conserved quantity ↔ information content.",
                confidence="✅",
            ),
            DeepConnection(
                connection_id="quantum_superposition_fuzzy_logic",
                left_domain="Quantum Superposition",
                right_domain="Fuzzy Logic",
                bridge_concept="Multi-valued Reasoning",
                operator_involved=BeeVerseOperator.CROSS,
                description="Quantum superposition and fuzzy logic both reject binary true/false for graded truth values. Their cross produces multi-valued reasoning systems that handle uncertainty with richer structure than either alone.",
                confidence="⚠️",
            ),
            DeepConnection(
                connection_id="phase_transition_critical_emergence",
                left_domain="Phase Transitions",
                right_domain="Critical Phenomena",
                bridge_concept="Emergent Behavior",
                operator_involved=BeeVerseOperator.UNION,
                description="Statistical mechanics unifies phase transitions with critical phenomena via universality classes. Union of microscopic interactions produces macroscopic emergent behavior that cannot be reduced to individual components.",
                confidence="✅",
            ),
            DeepConnection(
                connection_id="godel_self_reference_recursion",
                left_domain="Gödel Incompleteness",
                right_domain="Recursive Function Theory",
                bridge_concept="Self-Reference",
                operator_involved=BeeVerseOperator.SELF_IMPROVE,
                description="Gödel's theorem and recursive function theory share self-reference as core mechanism. Applying a system to itself (sq operator) reveals both its power and its limits — the foundation of meta-cognition.",
                confidence="✅",
            ),
            DeepConnection(
                connection_id="bayes_entropy_learning",
                left_domain="Bayesian Inference",
                right_domain="Information Entropy",
                bridge_concept="Learning Theory",
                operator_involved=BeeVerseOperator.SPECIALIZE,
                description="Bayesian updating minimizes KL divergence (relative entropy). Specializing prior distributions through evidence is mathematically equivalent to reducing entropy — learning as entropy minimization.",
                confidence="✅",
            ),
        ]

    def map_formula(self, formula: ScienceFormula) -> BeeVerseOperator:
        return formula.operator_mapping

    def discover_connections(self, formula_a: str, formula_b: str) -> list[DeepConnection]:
        fa = self.formulas.get(formula_a)
        fb = self.formulas.get(formula_b)
        if fa is None or fb is None:
            return []

        found: list[DeepConnection] = []
        shared_connection_ids = set(fa.deep_connections) & set(fb.deep_connections)
        for conn in self.connections:
            if conn.connection_id in shared_connection_ids:
                found.append(conn)

        operator_pair = {fa.operator_mapping, fb.operator_mapping}
        for conn in self.connections:
            if conn not in found:
                if conn.operator_involved in operator_pair:
                    if fa.field in (conn.left_domain, conn.right_domain, conn.bridge_concept):
                        found.append(conn)
                    elif fb.field in (conn.left_domain, conn.right_domain, conn.bridge_concept):
                        found.append(conn)

        if not found:
            found.append(DeepConnection(
                connection_id=f"auto_{formula_a}_{formula_b}",
                left_domain=fa.field,
                right_domain=fb.field,
                bridge_concept=f"{fa.operator_mapping.value}-{fb.operator_mapping.value} operator bridge",
                operator_involved=fa.operator_mapping,
                description=f"Structural bridge between {fa.name} ({fa.operator_mapping.value}) and {fb.name} ({fb.operator_mapping.value}) via shared operator semantics: {OPERATOR_SEMANTICS.get(fa.operator_mapping, '')} intersects {OPERATOR_SEMANTICS.get(fb.operator_mapping, '')}.",
                confidence="⚠️",
            ))

        return found

    def get_formulas_by_operator(self, operator: BeeVerseOperator) -> list[ScienceFormula]:
        return [f for f in self.formulas.values() if f.operator_mapping == operator]

    def get_formulas_by_field(self, field: str) -> list[ScienceFormula]:
        field_lower = field.lower()
        return [f for f in self.formulas.values() if field_lower in f.field.lower()]

    def generate_invention_directions(self, formula: ScienceFormula) -> list[dict]:
        directions: list[dict] = []
        templates = OPERATOR_INVENTION_TEMPLATES.get(formula.operator_mapping, [])

        for template_name, pattern, rationale in templates:
            filled_pattern = pattern.format(
                field_a=formula.field,
                field_b="ComplementaryDomain",
                field_c="TertiaryDomain",
            )
            directions.append({
                "direction": f"{template_name} inspired by {formula.name}",
                "formula_pattern": filled_pattern,
                "rationale": f"{rationale}. Based on {formula.name} ({formula.formula}): {formula.mapping_rationale}.",
                "confidence": formula.confidence,
            })

        for op in BeeVerseOperator:
            if op == formula.operator_mapping:
                continue
            cross_pattern = f"({formula.operator_mapping.value}({formula.field}) {op.value} NewDomain)"
            directions.append({
                "direction": f"{OPERATOR_SEMANTICS.get(op, 'transform')} applied to {formula.name}",
                "formula_pattern": cross_pattern,
                "rationale": f"Apply {op.value} ({OPERATOR_SEMANTICS.get(op, '')}) to the structural pattern of {formula.name}, creating a novel combination that the original domain could not produce alone.",
                "confidence": "⚠️",
            })

        return directions

    def export_mappings(self) -> dict:
        formulas_export = {}
        for name, f in self.formulas.items():
            formulas_export[name] = {
                "name": f.name,
                "formula": f.formula,
                "discoverer": f.discoverer,
                "year": f.year,
                "field": f.field,
                "operator_mapping": f.operator_mapping.value,
                "operator_name": f.operator_mapping.name,
                "mapping_rationale": f.mapping_rationale,
                "deep_connections": f.deep_connections,
                "confidence": f.confidence,
            }

        connections_export = []
        for c in self.connections:
            connections_export.append({
                "connection_id": c.connection_id,
                "left_domain": c.left_domain,
                "right_domain": c.right_domain,
                "bridge_concept": c.bridge_concept,
                "operator_involved": c.operator_involved.value,
                "operator_name": c.operator_involved.name,
                "description": c.description,
                "confidence": c.confidence,
            })

        operator_summary: dict[str, list[str]] = {}
        for op in BeeVerseOperator:
            operator_summary[op.value] = [
                f.name for f in self.formulas.values() if f.operator_mapping == op
            ]

        return {
            "formulas": formulas_export,
            "connections": connections_export,
            "operator_summary": operator_summary,
            "total_formulas": len(self.formulas),
            "total_connections": len(self.connections),
        }

    def to_json(self) -> str:
        return json.dumps(self.export_mappings(), indent=2, ensure_ascii=False)
