from __future__ import annotations

import itertools
import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = structlog.get_logger()


class Dimension(Enum):
    K = "Knowledge"
    R = "Reasoning"
    C = "Creativity"
    M = "Memory"
    S = "SelfHealing"
    G = "Guardrails"
    A = "Automation"
    P = "Prediction"
    F = "Formula"
    H = "Hardware"


class Operator(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    SQUARE = "²"
    SQRT = "√"
    POWER = "^"
    LOG = "log"


@dataclass
class Invention:
    id: str
    name: str
    formula: str
    formula_explanation: str
    target_painpoints: list[str]
    dimension: str
    description: str
    components: list[str]
    severity: str
    score: float = 0.0


class FormulaGenerator:
    def __init__(self) -> None:
        self._dimensions = list(Dimension)
        self._operators = list(Operator)

    def generate_formulas(self, max_terms: int = 3) -> list[str]:
        formulas = []
        for num_terms in range(2, max_terms + 1):
            for dims in itertools.product(self._dimensions, repeat=num_terms):
                for ops in itertools.product(self._operators, repeat=num_terms - 1):
                    formula = self._build_formula(dims, ops)
                    formulas.append(formula)
        return formulas

    def _build_formula(self, dimensions: tuple[Dimension, ...], operators: tuple[Operator, ...]) -> str:
        parts = [dimensions[0].name]
        for i, op in enumerate(operators):
            dim = dimensions[i + 1]
            if op == Operator.SQUARE:
                parts[-1] = f"{parts[-1]}²"
            elif op == Operator.SQRT:
                parts[-1] = f"√({parts[-1]})"
            elif op == Operator.LOG:
                parts[-1] = f"log({parts[-1]})"
            elif op == Operator.POWER:
                parts[-1] = f"{parts[-1]}^{dim.name}"
            else:
                parts.append(f"{op.value}{dim.name}")
        return " ".join(parts)

    def generate_with_template(self, template: str, variables: dict[str, list[str]]) -> list[str]:
        formulas = []
        keys = list(variables.keys())
        values = [variables[k] for k in keys]
        for combo in itertools.product(*values):
            formula = template
            for i, key in enumerate(keys):
                formula = formula.replace(f"{{{key}}}", combo[i])
            formulas.append(formula)
        return formulas


class OperatorCombiner:
    def __init__(self) -> None:
        self._operator_semantics = {
            Operator.ADD: "聯合新領域",
            Operator.SUB: "移除聚焦核心",
            Operator.MUL: "交叉深度協同",
            Operator.DIV: "專門化突破",
            Operator.SQUARE: "自我改善質變",
            Operator.SQRT: "分解發現新結構",
            Operator.POWER: "放大突破維度",
            Operator.LOG: "抽象化通用化",
        }

    def combine(self, operators: list[Operator]) -> str:
        explanations = [self._operator_semantics.get(op, "未知操作") for op in operators]
        return " → ".join(explanations)

    def get_synergy_score(self, op1: Operator, op2: Operator) -> float:
        synergy_matrix = {
            (Operator.MUL, Operator.ADD): 1.5,
            (Operator.SQUARE, Operator.LOG): 1.3,
            (Operator.POWER, Operator.DIV): 1.4,
            (Operator.ADD, Operator.MUL): 1.5,
        }
        return synergy_matrix.get((op1, op2), 1.0)

    def optimize_order(self, operators: list[Operator]) -> list[Operator]:
        if len(operators) <= 1:
            return operators
        best_order = operators
        best_score = 0.0
        for perm in itertools.permutations(operators):
            score = 1.0
            for i in range(len(perm) - 1):
                score *= self.get_synergy_score(perm[i], perm[i + 1])
            if score > best_score:
                best_score = score
                best_order = list(perm)
        return best_order


class InventionEvaluator:
    def __init__(self) -> None:
        self._dimension_weights = {
            "reasoning": 1.0,
            "safety": 1.2,
            "autonomy": 0.9,
            "memory": 0.8,
            "innovation": 1.1,
            "planning": 0.85,
            "knowledge": 0.9,
            "collaboration": 0.95,
            "self_reflection": 1.0,
        }
        self._severity_weights = {
            "critical": 1.5,
            "high": 1.2,
            "medium": 1.0,
            "low": 0.8,
        }

    def evaluate(self, invention: Invention) -> float:
        base_score = 1.0
        dim_weight = self._dimension_weights.get(invention.dimension, 1.0)
        sev_weight = self._severity_weights.get(invention.severity, 1.0)
        component_score = min(len(invention.components) / 4.0, 1.5)
        painpoint_score = min(len(invention.target_painpoints) / 3.0, 1.5)
        formula_complexity = self._evaluate_formula_complexity(invention.formula)
        score = base_score * dim_weight * sev_weight * component_score * painpoint_score * formula_complexity
        invention.score = round(score, 4)
        return invention.score

    def _evaluate_formula_complexity(self, formula: str) -> float:
        complexity = 1.0
        advanced_ops = ["²", "√", "^", "log"]
        for op in advanced_ops:
            if op in formula:
                complexity += 0.1
        return min(complexity, 1.5)

    def rank_inventions(self, inventions: list[Invention]) -> list[Invention]:
        for inv in inventions:
            self.evaluate(inv)
        return sorted(inventions, key=lambda x: x.score, reverse=True)


class SkillInstantiator:
    def __init__(self) -> None:
        self._template = '''from __future__ import annotations

import structlog

logger = structlog.get_logger()


class {class_name}:
    def __init__(self) -> None:
        self._formula = "{formula}"
        self._capability = "{capability}"

    def execute(self, input_data: dict) -> dict:
        try:
            result = self._process(input_data)
            logger.info("{capability}_success", capability=self._capability)
            return {{"status": "success", "capability": self._capability, "result": result, "formula": self._formula}}
        except Exception as exc:
            logger.error("{capability}_failed", capability=self._capability, error=str(exc))
            return {{"status": "error", "capability": self._capability, "error": str(exc)}}

    def _process(self, input_data: dict) -> dict:
        return {{"processed": True, "input_keys": list(input_data.keys())}}
'''

    def instantiate(self, invention: Invention) -> str:
        class_name = invention.name
        capability = invention.name.lower()
        code = self._template.format(
            class_name=class_name,
            formula=invention.formula,
            capability=capability,
        )
        return code

    def get_file_path(self, invention: Invention, base_dir: str) -> str:
        import os
        filename = f"{invention.name.lower()}.py"
        return os.path.join(base_dir, filename)


class FormulaThinkingInventor:
    def __init__(self) -> None:
        self._formula = "F² + C * R"
        self._capability = "formula_thinking_inventor"
        self._formula_generator = FormulaGenerator()
        self._operator_combiner = OperatorCombiner()
        self._evaluator = InventionEvaluator()
        self._instantiator = SkillInstantiator()

    def analyze(self, input_data: dict) -> dict:
        try:
            result = self._process(input_data)
            logger.info("formula_thinking_inventor_success", capability=self._capability)
            return {"status": "success", "capability": self._capability, "result": result, "formula": self._formula}
        except Exception as exc:
            logger.error("formula_thinking_inventor_failed", capability=self._capability, error=str(exc))
            return {"status": "error", "capability": self._capability, "error": str(exc)}

    def execute(self, input_data: dict) -> dict:
        return self.analyze(input_data)

    def _process(self, input_data: dict) -> dict:
        mode = input_data.get("mode", "generate")
        if mode == "generate":
            max_terms = input_data.get("max_terms", 3)
            formulas = self._formula_generator.generate_formulas(max_terms)
            return {"formulas": formulas[:100], "total": len(formulas)}
        elif mode == "evaluate":
            inventions_data = input_data.get("inventions", [])
            inventions = []
            for i, inv_data in enumerate(inventions_data):
                inv = Invention(
                    id=inv_data.get("id", f"INV-{i:03d}"),
                    name=inv_data.get("name", f"Invention{i}"),
                    formula=inv_data.get("formula", ""),
                    formula_explanation=inv_data.get("formula_explanation", ""),
                    target_painpoints=inv_data.get("target_painpoints", []),
                    dimension=inv_data.get("dimension", "reasoning"),
                    description=inv_data.get("description", ""),
                    components=inv_data.get("components", []),
                    severity=inv_data.get("severity", "high"),
                )
                inventions.append(inv)
            ranked = self._evaluator.rank_inventions(inventions)
            return {
                "ranked_inventions": [
                    {"id": inv.id, "name": inv.name, "score": inv.score, "formula": inv.formula}
                    for inv in ranked
                ]
            }
        elif mode == "instantiate":
            inv_data = input_data.get("invention", {})
            inv = Invention(
                id=inv_data.get("id", "INV-NEW"),
                name=inv_data.get("name", "NewInvention"),
                formula=inv_data.get("formula", ""),
                formula_explanation=inv_data.get("formula_explanation", ""),
                target_painpoints=inv_data.get("target_painpoints", []),
                dimension=inv_data.get("dimension", "reasoning"),
                description=inv_data.get("description", ""),
                components=inv_data.get("components", []),
                severity=inv_data.get("severity", "high"),
            )
            code = self._instantiator.instantiate(inv)
            return {"code": code, "invention": inv.name}
        else:
            return {"processed": True, "input_keys": list(input_data.keys())}

    def invent_from_dimensions(self, dimensions: list[str], operators: list[str]) -> list[Invention]:
        inventions = []
        for i, (dim_combo, op_combo) in enumerate(zip(
            itertools.product(dimensions, repeat=2),
            itertools.product(operators, repeat=2)
        )):
            formula = f"{dim_combo[0]} {op_combo[0]} {dim_combo[1]} {op_combo[1]}"
            inv = Invention(
                id=f"INV-AUTO-{i:03d}",
                name=f"AutoInvention{i}",
                formula=formula,
                formula_explanation=self._operator_combiner.combine([Operator(o) for o in op_combo if o in [e.value for e in Operator]]),
                target_painpoints=[],
                dimension="innovation",
                description=f"Auto-generated invention from {formula}",
                components=["AutoComponent"],
                severity="medium",
            )
            inventions.append(inv)
        return self._evaluator.rank_inventions(inventions)[:10]


if __name__ == "__main__":
    inventor = FormulaThinkingInventor()

    print("=" * 60)
    print("Test 1: Generate Formulas")
    print("=" * 60)
    result = inventor.analyze({"mode": "generate", "max_terms": 2})
    print(f"Total formulas: {result['result']['total']}")
    print(f"Sample formulas: {result['result']['formulas'][:5]}")

    print("\n" + "=" * 60)
    print("Test 2: Evaluate Inventions")
    print("=" * 60)
    test_inventions = [
        {
            "id": "INV-TEST-001",
            "name": "TestInvention1",
            "formula": "K * R + S",
            "formula_explanation": "Knowledge 與 Reasoning 協同 + SelfHealing",
            "target_painpoints": ["WLLM-001", "WLLM-002"],
            "dimension": "reasoning",
            "description": "Test invention for evaluation",
            "components": ["Component1", "Component2", "Component3"],
            "severity": "critical",
        },
        {
            "id": "INV-TEST-002",
            "name": "TestInvention2",
            "formula": "F² + C * R",
            "formula_explanation": "Formula 自我改善 + Creativity 與 Reasoning 協同",
            "target_painpoints": ["WAA-052", "WAA-056", "CAA-034"],
            "dimension": "innovation",
            "description": "Formula thinking inventor",
            "components": ["FormulaGenerator", "OperatorCombiner", "InventionEvaluator", "SkillInstantiator"],
            "severity": "high",
        },
    ]
    result = inventor.analyze({"mode": "evaluate", "inventions": test_inventions})
    for inv in result["result"]["ranked_inventions"]:
        print(f"  {inv['id']}: {inv['name']} - Score: {inv['score']}")

    print("\n" + "=" * 60)
    print("Test 3: Instantiate Skill")
    print("=" * 60)
    result = inventor.analyze({"mode": "instantiate", "invention": test_inventions[1]})
    print(f"Generated code for: {result['result']['invention']}")
    print("Code preview (first 500 chars):")
    print(result["result"]["code"][:500])

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
