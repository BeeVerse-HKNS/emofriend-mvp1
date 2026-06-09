import re
from itertools import permutations

from harnessing.core.science_formula_mapper import ScienceFormulaMapper


CAPABILITY_DIMS = {
    "K": "Knowledge (knowledge base, documentation, research)",
    "R": "Reasoning (logical inference, deduction, induction)",
    "C": "Creativity (novel solutions, lateral thinking, brainstorming)",
    "M": "Memory (persistent storage, recall, context management)",
    "S": "SelfHealing (error recovery, self-repair, resilience)",
    "G": "Guardrails (safety rules, constraints, boundaries)",
    "A": "Automation (task execution, workflow, scheduling)",
    "P": "Prediction (forecasting, trend analysis, anticipation)",
    "F": "Formula (meta-thinking, self-referential improvement)",
    "H": "Hardware (physical constraints, resource limits, compute)",
}

SCIENCE_DIMS = {
    "E": "Energy (transformation, power, capacity, dynamics)",
    "N": "Entropy (disorder, uncertainty, information, chaos)",
    "W": "Wave (oscillation, propagation, interference, resonance)",
    "D": "Field (influence range, gradient, potential, domain)",
}

OPERATORS = {
    "+": "UNITE — combine domains into new capability",
    "-": "FOCUS — remove to concentrate on core",
    "*": "SYNERGY — cross for 1+1>2 emergent capability",
    "/": "SPECIALIZE — deep narrow breakthrough",
    "sq": "SELF-IMPROVE — apply to itself, qualitative shift",
    "sqrt": "DECOMPOSE — break down to discover hidden structure",
    "^": "AMPLIFY — raise to power for exponential capability",
    "log": "ABSTRACT — extract universal pattern",
}

SCIENCE_OPS = {
    "⊕": "SUPERPOSITION — maintain multiple states simultaneously",
    "Ξ": "EMERGENCE — detect phase transitions in capability space",
    "S()": "ENTROPY — measure and manage system disorder",
    "𝔽()": "FIELD — model invention space as potential field",
    "Σ⁻¹": "SYMMETRY_BREAKING — generate variants by breaking symmetry",
}

ALL_OPERATORS = {**OPERATORS, **SCIENCE_OPS}

BRACKET_PATTERNS = [
    "({0} {1} {2}) {3} {4}",
    "{0} {1} ({2} {3} {4})",
    "({0} {1} {2}) {3} ({4} {5} {6})",
    "{0} {1} ({2} {3} ({4} {5} {6}))",
    "(({0} {1} {2}) {3} {4}) {5} {6}",
]


class FormulaBrainstormer:

    def __init__(self):
        self.dim_keys = list(CAPABILITY_DIMS.keys())
        self.science_dim_keys = list(SCIENCE_DIMS.keys())
        self.all_dim_keys = self.dim_keys + self.science_dim_keys
        self.all_dims = {**CAPABILITY_DIMS, **SCIENCE_DIMS}
        self.op_keys = list(OPERATORS.keys())
        self.science_op_keys = list(SCIENCE_OPS.keys())
        self.all_op_keys = list(ALL_OPERATORS.keys())
        self.science_mapper = ScienceFormulaMapper()

    def brainstorm(self, problem: str, relevant_dims: list = None, max_formulas: int = 20) -> dict:
        if relevant_dims is None:
            relevant_dims = self._infer_dims(problem)

        if len(relevant_dims) < 2:
            relevant_dims = relevant_dims[:2] if len(relevant_dims) >= 2 else self.dim_keys[:3]

        formulas = self._generate_formulas(relevant_dims, max_formulas)
        scored = self._score_formulas(formulas, problem)

        return {
            "problem": problem,
            "relevant_dims": {d: self.all_dims[d] for d in relevant_dims},
            "total_generated": len(formulas),
            "top_formulas": scored[:max_formulas],
        }

    def brainstorm_with_science(self, base_dimensions: list[str], max_formulas: int = 20) -> list[dict]:
        combined = []
        for d in base_dimensions:
            if d in self.all_dims:
                combined.append(d)

        science_dims = [d for d in combined if d in SCIENCE_DIMS]
        capability_dims = [d for d in combined if d in CAPABILITY_DIMS]

        base_formulas = self._generate_formulas(combined, max_formulas)

        science_enriched = []
        for cap_d in capability_dims:
            for sci_d in self.science_dim_keys:
                for op in ["+", "*", "/", "^"]:
                    science_enriched.append({
                        "formula": f"({cap_d} {op} {sci_d})",
                        "dims": [cap_d, sci_d],
                        "op": op,
                        "semantic": self._semantic(cap_d, op, sci_d),
                        "source": "science_cross",
                    })

        for sci_d in science_dims:
            for op in ["sq", "^", "log"]:
                science_enriched.append({
                    "formula": f"{op}({sci_d})",
                    "dims": [sci_d],
                    "op": op,
                    "semantic": self._unary_semantic(sci_d, op),
                    "source": "science_unary",
                })

        for sci_d in science_dims:
            for cap_d in capability_dims:
                for op in ["*", "+", "^"]:
                    science_enriched.append({
                        "formula": f"({sci_d} {op} {cap_d})",
                        "dims": [sci_d, cap_d],
                        "op": op,
                        "semantic": self._semantic(sci_d, op, cap_d),
                        "source": "science_cross",
                    })

        for sf in self.science_mapper.formulas.values():
            for direction in self.science_mapper.generate_invention_directions(sf)[:2]:
                science_enriched.append({
                    "formula": direction["formula_pattern"],
                    "dims": list(set(combined[:2] + [sf.field[:1]])),
                    "op": sf.operator_mapping.value,
                    "semantic": f"{sf.name} ({sf.formula}) → {direction['rationale']}",
                    "source": "science_mapper",
                    "confidence": sf.confidence,
                })

        all_formulas = base_formulas + science_enriched

        for f in all_formulas:
            f["score"] = self._score_single(f, " ".join(self.all_dims.get(d, d) for d in combined))

        all_formulas.sort(key=lambda x: x["score"], reverse=True)
        return all_formulas[:max_formulas]

    def _score_single(self, f: dict, context: str) -> int:
        score = 0
        c_words = set(re.findall(r"\w+", context.lower()))
        semantic_words = set(re.findall(r"\w+", f.get("semantic", "").lower()))
        overlap = c_words & semantic_words
        score += len(overlap) * 2

        op = f.get("op", "")
        if isinstance(op, str) and len(op) == 1:
            if op == "+":
                score += 1
            elif op == "*":
                score += 3
            elif op == "/":
                score += 2
            elif op == "-":
                score += 1
        elif isinstance(op, str) and len(op) > 1:
            score += 2

        formula_str = str(f.get("formula", ""))
        if "sq" in formula_str:
            score += 2
        if "log" in formula_str:
            score += 2
        if "^" in formula_str:
            score += 3

        if f.get("source") == "science_mapper":
            score += 4
        elif f.get("source") == "science_cross":
            score += 2

        return score

    def _infer_dims(self, problem: str) -> list:
        p = problem.lower()
        dim_scores = {}
        for dim, desc in self.all_dims.items():
            desc_words = desc.lower().split()
            score = sum(1 for w in desc_words if len(w) > 3 and w in p)
            dim_scores[dim] = score

        keyword_map = {
            "K": ["knowledge", "research", "documentation", "kb", "知識", "研究"],
            "R": ["reasoning", "logic", "infer", "deduc", "推理", "邏輯"],
            "C": ["creativ", "novel", "brainstorm", "innovat", "創意", "創新"],
            "M": ["memory", "storage", "recall", "context", "記憶", "存儲"],
            "S": ["heal", "recover", "repair", "resilien", "修復", "恢復"],
            "G": ["guard", "safety", "constraint", "rule", "護欄", "約束"],
            "A": ["automat", "workflow", "schedul", "execut", "自動化", "工作流"],
            "P": ["predict", "forecast", "trend", "anticip", "預測", "趨勢"],
            "F": ["formula", "meta", "self-refer", "improv", "公式", "元思考"],
            "H": ["hardware", "resource", "compute", "vram", "ram", "硬件", "資源"],
            "E": ["energy", "power", "capacit", "dynam", "transformat", "能量", "動力"],
            "N": ["entropy", "disorder", "uncertain", "chaos", "information", "熵", "混亂"],
            "W": ["wave", "oscil", "propagat", "interfer", "resonan", "波", "振盪"],
            "D": ["field", "gradient", "potential", "domain", "influence", "場", "梯度"],
        }

        for dim, keywords in keyword_map.items():
            for kw in keywords:
                if kw in p:
                    dim_scores[dim] = dim_scores.get(dim, 0) + 2

        sorted_dims = sorted(dim_scores.items(), key=lambda x: x[1], reverse=True)
        top = [d for d, s in sorted_dims[:4] if s > 0]
        if len(top) < 2:
            top = [d for d, _ in sorted_dims[:3]]
        return top

    def _generate_formulas(self, dims: list, max_count: int) -> list:
        formulas = []
        binary_ops = ["+", "-", "*", "/"]
        unary_ops = ["sq", "sqrt", "^", "log"]

        for i, d1 in enumerate(dims):
            for d2 in dims[i + 1:]:
                for op in binary_ops:
                    formulas.append({
                        "formula": f"({d1} {op} {d2})",
                        "dims": [d1, d2],
                        "op": op,
                        "semantic": self._semantic(d1, op, d2),
                    })

        for d in dims:
            for op in unary_ops:
                formulas.append({
                    "formula": f"{op}({d})",
                    "dims": [d],
                    "op": op,
                    "semantic": self._unary_semantic(d, op),
                })

        if len(dims) >= 3:
            for perm in permutations(dims[:3], 3):
                for op1 in binary_ops[:2]:
                    for op2 in binary_ops[:2]:
                        formulas.append({
                            "formula": f"({perm[0]} {op1} {perm[1]}) {op2} {perm[2]}",
                            "dims": list(perm),
                            "op": f"{op1}{op2}",
                            "semantic": self._semantic(perm[0], op1, perm[1]) + f" then {OPERATORS.get(op2, op2)} with {perm[2]}",
                        })

        return formulas[:max_count * 3]

    def _semantic(self, d1: str, op: str, d2: str) -> str:
        dims = self.all_dims
        semantics = {
            "+": f"{dims.get(d1, d1).split('(')[0].strip()} UNITED WITH {dims.get(d2, d2).split('(')[0].strip()}",
            "-": f"{dims.get(d1, d1).split('(')[0].strip()} FOCUSED BY REMOVING {dims.get(d2, d2).split('(')[0].strip()} overlap",
            "*": f"{dims.get(d1, d1).split('(')[0].strip()} CROSSED WITH {dims.get(d2, d2).split('(')[0].strip()} for emergent synergy",
            "/": f"{dims.get(d1, d1).split('(')[0].strip()} SPECIALIZED BY {dims.get(d2, d2).split('(')[0].strip()} perspective",
        }
        return semantics.get(op, f"{d1} {op} {d2}")

    def _unary_semantic(self, d: str, op: str) -> str:
        dims = self.all_dims
        dim_name = dims.get(d, d).split("(")[0].strip()
        semantics = {
            "sq": f"{dim_name} SELF-IMPROVED (applied to itself)",
            "sqrt": f"{dim_name} DECOMPOSED (break down to discover hidden structure)",
            "^": f"{dim_name} AMPLIFIED (exponential capability boost)",
            "log": f"{dim_name} ABSTRACTED (extract universal pattern)",
        }
        return semantics.get(op, f"{op}({d})")

    def _score_formulas(self, formulas: list, problem: str) -> list:
        p_words = set(re.findall(r"\w+", problem.lower()))
        for f in formulas:
            score = 0
            semantic_words = set(re.findall(r"\w+", f["semantic"].lower()))
            overlap = p_words & semantic_words
            score += len(overlap) * 2

            op = f["op"]
            if isinstance(op, str) and len(op) == 1:
                if op == "+":
                    score += 1
                elif op == "*":
                    score += 3
                elif op == "/":
                    score += 2
                elif op == "-":
                    score += 1
            elif isinstance(op, str) and len(op) > 1:
                score += 2

            if "sq" in str(f.get("formula", "")):
                score += 2
            if "log" in str(f.get("formula", "")):
                score += 2
            if "^" in str(f.get("formula", "")):
                score += 3

            f["score"] = score

        formulas.sort(key=lambda x: x["score"], reverse=True)
        return formulas

    def format_results(self, result: dict) -> str:
        lines = [
            f"Formula Brainstorming for: {result['problem']}",
            f"Relevant Dimensions: {', '.join(f'{k}={v}' for k, v in result['relevant_dims'].items())}",
            f"Total Formulas Generated: {result['total_generated']}",
            "",
            "Top Invention Ideas:",
            "",
        ]
        for i, f in enumerate(result["top_formulas"], 1):
            lines.append(f"{i}. {f['formula']}")
            lines.append(f"   Semantic: {f['semantic']}")
            lines.append(f"   Score: {f['score']}")
            lines.append("")
        return "\n".join(lines)
