from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from itertools import permutations
from typing import Generator, Optional


INVENTORY_FACTORS = {
    'K': {'name': 'Knowledge', 'description': '知識庫 + RAG + Memory', 'modules': ['memory_engine', 'beeverse_rag_retriever', 'knowledge_base']},
    'R': {'name': 'Reasoning', 'description': '思考方法 + 推理引擎', 'modules': ['tree_of_thought', 'analogical_reasoning', 'commonsense_reasoning']},
    'C': {'name': 'Creativity', 'description': '公式思維 + 創造力', 'modules': ['formula_brainstormer', 'formula_driven_universal_coverage']},
    'M': {'name': 'Memory', 'description': '記憶引擎 + 螺旋學習', 'modules': ['meta_helical_learning', 'working_refresh_mechanism']},
    'S': {'name': 'SelfHealing', 'description': '自癒 + 恢復 + 熔斷', 'modules': ['self_healing_engine', 'lightweight_recovery', 'catastrophic_recovery_platform']},
    'G': {'name': 'Guardrails', 'description': '防護 + 合規 + 隱私', 'modules': ['intent_based_guard', 'self_audit_engine', 'compliance_engine', 'privacy_shield']},
    'A': {'name': 'Automation', 'description': '自動化 + 整合技巧', 'modules': ['automation_skills', 'chinese_integration_skills', 'global_integration_skills']},
    'P': {'name': 'Prediction', 'description': '預測 + 干預 + 模式識別', 'modules': ['predictive_intervention_engine', 'invention_pattern_learner']},
    'F': {'name': 'Formula', 'description': '公式引擎 + 發明系統', 'modules': ['formula_thinking_engine', 'long_formula_invention_engine']},
    'H': {'name': 'Hardware', 'description': '硬件 + 本地 LLM', 'modules': ['beeverse_core', 'beeverse_engine', 'beeverse_amplifier', 'model_router', 'mixed_llm_engine']},
    'U': {'name': 'Uncertainty', 'description': '不確定性量化 + 信心校準', 'modules': ['metacognitive_reflection_engine']},
    'W': {'name': 'WorldModel', 'description': '世界模型構建 + 實體圖譜', 'modules': ['world_model_constructor']},
    'T': {'name': 'Temporal', 'description': '時間推理 + 序列追蹤', 'modules': ['world_model_constructor', 'ten_year_projection_engine']},
    'Q': {'name': 'Quality', 'description': '質量評估 + 元認知反思', 'modules': ['metacognitive_reflection_engine']},
    'D': {'name': 'Dependency', 'description': '因果依賴 + 干預模擬', 'modules': ['causal_reasoning_engine']},
}

SCENARIO_DIMENSIONS = [
    'failure', 'recovery', 'security', 'data', 'human', 'system',
    'network', 'resource', 'integration', 'timing', 'compliance',
    'supply_chain', 'environmental', 'privacy', 'business_continuity',
]

SCENARIO_CATEGORIES = [
    'availability', 'reliability', 'safety', 'integrity', 'confidentiality',
    'performance', 'scalability', 'maintainability', 'observability',
    'resilience', 'adaptability', 'efficiency', 'robustness',
    'fault_tolerance', 'self_healing',
]

FACTOR_COVERAGE_MAP = {
    'K': {'coverage': {'availability', 'reliability', 'integrity', 'maintainability', 'observability'}, 'synergy': 1.0},
    'R': {'coverage': {'safety', 'integrity', 'fault_tolerance', 'robustness', 'adaptability'}, 'synergy': 1.0},
    'C': {'coverage': {'adaptability', 'scalability', 'resilience', 'self_healing', 'efficiency'}, 'synergy': 1.0},
    'M': {'coverage': {'availability', 'reliability', 'maintainability', 'observability', 'self_healing'}, 'synergy': 1.0},
    'S': {'coverage': {'reliability', 'resilience', 'fault_tolerance', 'self_healing', 'robustness'}, 'synergy': 1.0},
    'G': {'coverage': {'safety', 'confidentiality', 'integrity', 'compliance', 'robustness'}, 'synergy': 1.0},
    'A': {'coverage': {'efficiency', 'scalability', 'performance', 'maintainability', 'availability'}, 'synergy': 1.0},
    'P': {'coverage': {'resilience', 'adaptability', 'fault_tolerance', 'observability', 'reliability'}, 'synergy': 1.0},
    'F': {'coverage': {'adaptability', 'self_healing', 'scalability', 'efficiency', 'resilience'}, 'synergy': 1.0},
    'H': {'coverage': {'performance', 'availability', 'reliability', 'scalability', 'efficiency'}, 'synergy': 1.0},
    'U': {'coverage': {'safety', 'integrity', 'robustness', 'observability', 'reliability'}, 'synergy': 1.0},
    'W': {'coverage': {'availability', 'reliability', 'maintainability', 'adaptability', 'observability'}, 'synergy': 1.0},
    'T': {'coverage': {'resilience', 'adaptability', 'observability', 'reliability', 'efficiency'}, 'synergy': 1.0},
    'Q': {'coverage': {'safety', 'integrity', 'reliability', 'robustness', 'observability'}, 'synergy': 1.0},
    'D': {'coverage': {'safety', 'integrity', 'fault_tolerance', 'robustness', 'adaptability'}, 'synergy': 1.0},
}

CONFLICT_REGISTRY = {
    'overlaps': [
        {
            'id': 'OV-001',
            'group': 'Self-Improvement & Self-Monitoring',
            'factors_affected': ['M', 'S', 'G'],
            'modules': ['meta_self_improvement_engine', 'meta_helical_learning', 'self_audit_engine', 'self_healing_engine'],
            'severity': 'HIGH',
            'recommendation': 'KEEP_SEPARATE',
            'synergy_penalty': 0.15,
        },
        {
            'id': 'OV-002',
            'group': 'Intent/Guard Duplicate Classes',
            'factors_affected': ['G'],
            'modules': ['intent_based_guard.py', 'human_error_shield.py'],
            'severity': 'CRITICAL',
            'recommendation': 'MERGE',
            'synergy_penalty': 0.30,
        },
        {
            'id': 'OV-003',
            'group': 'Alerting System Duplicate',
            'factors_affected': ['A', 'G'],
            'modules': ['automation_skills.py', 'error_ecosystem.py'],
            'severity': 'CRITICAL',
            'recommendation': 'MERGE',
            'synergy_penalty': 0.30,
        },
        {
            'id': 'OV-004',
            'group': 'Recovery Engine Duplicate',
            'factors_affected': ['S'],
            'modules': ['self_healing_engine.py', 'catastrophic_recovery_platform.py'],
            'severity': 'CRITICAL',
            'recommendation': 'MERGE',
            'synergy_penalty': 0.30,
        },
        {
            'id': 'OV-005',
            'group': 'Error Classifier Duplicate',
            'factors_affected': ['A', 'G'],
            'modules': ['automation_skills.py', 'error_ecosystem.py'],
            'severity': 'CRITICAL',
            'recommendation': 'MERGE',
            'synergy_penalty': 0.30,
        },
        {
            'id': 'OV-006',
            'group': 'Gap Detection 3 Implementations',
            'factors_affected': ['K', 'F'],
            'modules': ['gap_detector.py', 'gap_filler_system.py', 'beeverse_skill_gap_analyzer.py'],
            'severity': 'MEDIUM',
            'recommendation': 'ARCHIVE',
            'synergy_penalty': 0.10,
        },
        {
            'id': 'OV-007',
            'group': 'Prediction/Prevention Overlap',
            'factors_affected': ['P', 'G'],
            'modules': ['predictive_intervention_engine.py', 'intent_based_guard.py', 'self_audit_engine.py'],
            'severity': 'LOW',
            'recommendation': 'KEEP_SEPARATE',
            'synergy_penalty': 0.05,
        },
    ],
    'rule_contradictions': [
        {
            'id': 'RC-001',
            'rules': ['Rule 9', 'Rule 58'],
            'description': '3+ approaches vs DataDecidesDirection',
            'severity': 'HIGH',
            'resolution': 'Rule 58 overrides when sample >= 10M',
        },
        {
            'id': 'RC-002',
            'rules': ['Rule 10', 'Rule 24'],
            'description': 'Step-by-step verification vs autonomous execution',
            'severity': 'HIGH',
            'resolution': 'Rule 10 means internal QA, not user approval',
        },
        {
            'id': 'RC-003',
            'rules': ['Rule 9', 'Rule 19'],
            'description': '3+ approaches vs YAGNI',
            'severity': 'MEDIUM',
            'resolution': 'Expand Rule 9 exceptions for obvious solutions',
        },
        {
            'id': 'RC-004',
            'rules': ['Rules 45-59', 'Rule 19'],
            'description': 'Invention rigor vs YAGNI',
            'severity': 'MEDIUM',
            'resolution': 'Tiered approach: 1K -> 1M -> 10M',
        },
        {
            'id': 'RC-005',
            'rules': ['Rule 26', 'Rule 9'],
            'description': 'Universal application vs Rule 9 exceptions',
            'severity': 'LOW',
            'resolution': 'Exceptions are part of rule definition',
        },
        {
            'id': 'RC-006',
            'rules': ['Rule 18', 'Rules 51/55'],
            'description': 'Need boundary vs formula invention',
            'severity': 'MEDIUM',
            'resolution': 'Formula invention has explicit exception',
        },
    ],
    'quality_issues': {
        'invented_skills_stubs': 43,
        'invented_skills_real': 0,
        'data_archive_candidates': 45,
        'data_total': 76,
        'script_one_time': 98,
        'script_total': 175,
    },
}

def _compute_factor_quality() -> dict:
    quality = {}
    for f_key, f_info in FACTOR_COVERAGE_MAP.items():
        base_synergy = f_info['synergy']
        penalty = 0.0
        conflicts = []
        for ov in CONFLICT_REGISTRY['overlaps']:
            if f_key in ov['factors_affected']:
                penalty += ov['synergy_penalty']
                conflicts.append(ov['id'])
        adjusted_synergy = max(base_synergy - penalty, 0.1)
        quality[f_key] = {
            'base_synergy': base_synergy,
            'penalty': penalty,
            'adjusted_synergy': adjusted_synergy,
            'conflict_ids': conflicts,
            'health': 'CRITICAL' if penalty >= 0.5 else 'DEGRADED' if penalty >= 0.2 else 'HEALTHY',
        }
    return quality

FACTOR_QUALITY_MAP = _compute_factor_quality()

ABSTRACT_DIMENSIONS = {'complexity', 'observability', 'scalability', 'universality', 'generality'}
EMERGENT_DIMENSIONS = {'emergence', 'synergy', 'transcendence', 'meta_cognition', 'breakthrough'}
META_DIMENSIONS = {'self_reference', 'recursive_improvement', 'meta_learning', 'self_awareness', 'autogenesis'}
BREAKTHROUGH_DIMENSIONS = {'exponential_growth', 'paradigm_shift', 'disruption', 'quantum_leap', 'singularity'}


@dataclass
class FormulaNode:
    factor: Optional[str] = None
    operator: Optional[str] = None
    left: Optional[FormulaNode] = None
    right: Optional[FormulaNode] = None

    def evaluate(self, context: dict) -> dict:
        if self.factor is not None:
            factor_info = FACTOR_COVERAGE_MAP.get(self.factor, {'coverage': set(), 'synergy': 1.0})
            factor_meta = INVENTORY_FACTORS.get(self.factor, {'name': self.factor, 'description': '', 'modules': []})
            return {
                'coverage': set(factor_info['coverage']),
                'synergy': factor_info['synergy'],
                'invention_name': factor_meta['name'],
                'factors_used': [self.factor],
                'operators_used': [],
            }

        if self.operator is None:
            return {'coverage': set(), 'synergy': 0.0, 'invention_name': '', 'factors_used': [], 'operators_used': []}

        operator_map = _get_operator_map()
        engine = operator_map.get(self.operator)
        if engine is None:
            return {'coverage': set(), 'synergy': 0.0, 'invention_name': '', 'factors_used': [], 'operators_used': []}

        left_result = self.left.evaluate(context) if self.left else {'coverage': set(), 'synergy': 0.0, 'invention_name': '', 'factors_used': [], 'operators_used': []}
        right_result = self.right.evaluate(context) if self.right else None

        result = engine.apply(left_result, right_result, context)

        all_factors = list(left_result.get('factors_used', []))
        if right_result:
            all_factors.extend(right_result.get('factors_used', []))
        all_ops = list(left_result.get('operators_used', []))
        if right_result:
            all_ops.extend(right_result.get('operators_used', []))
        all_ops.append(self.operator)

        result['factors_used'] = all_factors
        result['operators_used'] = all_ops
        return result

    def to_string(self) -> str:
        if self.factor is not None:
            return self.factor
        if self.operator is None:
            return ''

        op = self.operator
        left_str = self.left.to_string() if self.left else ''

        if op == 'log':
            return f'log({left_str})'
        if op == 'sq':
            return f'sq({left_str})'

        right_str = self.right.to_string() if self.right else ''
        return f'({left_str} {op} {right_str})'

    def complexity(self) -> int:
        if self.factor is not None:
            return 0
        count = 1
        if self.left:
            count += self.left.complexity()
        if self.right:
            count += self.right.complexity()
        return count


class OperatorEngine(ABC):
    symbol: str = ''
    name: str = ''
    description: str = ''

    @abstractmethod
    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        ...


class AbstractionEngine(OperatorEngine):
    symbol = 'log'
    name = 'AbstractionEngine'
    description = '抽象化引擎：Extract universal patterns from specific factors'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        coverage = left_result['coverage'] | ABSTRACT_DIMENSIONS
        synergy = left_result['synergy'] * 1.2
        invention_name = f"Abstract{left_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class IntegrationEngine(OperatorEngine):
    symbol = '+'
    name = 'IntegrationEngine'
    description = '整合引擎：Combine factors for broader coverage'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        if right_result is None:
            return left_result
        coverage = left_result['coverage'] | right_result['coverage']
        synergy = (left_result['synergy'] + right_result['synergy']) / 2 * 1.1
        invention_name = f"{left_result['invention_name']}Plus{right_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class FocusEngine(OperatorEngine):
    symbol = '-'
    name = 'FocusEngine'
    description = '聚焦引擎：Remove overlap, focus on unique contribution'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        if right_result is None:
            return left_result
        coverage = left_result['coverage'] - right_result['coverage']
        synergy = left_result['synergy'] * 1.3
        invention_name = f"Focused{left_result['invention_name']}Minus{right_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class SynergyEngine(OperatorEngine):
    symbol = '*'
    name = 'SynergyEngine'
    description = '協同引擎：Deep cross-pollination between factors'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        if right_result is None:
            return left_result
        intersection = left_result['coverage'] & right_result['coverage']
        coverage = intersection | EMERGENT_DIMENSIONS
        synergy = left_result['synergy'] * right_result['synergy'] * 1.5
        invention_name = f"{left_result['invention_name']}Synergy{right_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class SpecializationEngine(OperatorEngine):
    symbol = '/'
    name = 'SpecializationEngine'
    description = '專門化引擎：Focus one factor on another domain'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        if right_result is None:
            return left_result
        right_domain = right_result['coverage']
        specialized = set()
        for dim in left_result['coverage']:
            specialized.add(f"{dim}_in_{right_result['invention_name']}")
        specialized |= (left_result['coverage'] & right_domain)
        synergy = left_result['synergy'] * 2.0
        invention_name = f"{left_result['invention_name']}SpecializedIn{right_result['invention_name']}"
        return {
            'coverage': specialized,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class SelfImprovementEngine(OperatorEngine):
    symbol = 'sq'
    name = 'SelfImprovementEngine'
    description = '自我改善引擎：Apply factor to itself for qualitative leap'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        coverage = left_result['coverage'] | META_DIMENSIONS
        synergy = left_result['synergy'] ** 2
        invention_name = f"SelfImproved{left_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class AmplificationEngine(OperatorEngine):
    symbol = '^'
    name = 'AmplificationEngine'
    description = '放大引擎：Amplify one factor by another power'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        if right_result is None:
            coverage = left_result['coverage'] | BREAKTHROUGH_DIMENSIONS
            synergy = left_result['synergy'] ** 1.1
            invention_name = f"{left_result['invention_name']}Amplified"
            return {
                'coverage': coverage,
                'synergy': synergy,
                'invention_name': invention_name,
            }
        coverage = left_result['coverage'] | right_result['coverage'] | BREAKTHROUGH_DIMENSIONS
        synergy = left_result['synergy'] ** (1 + right_result['synergy'] * 0.1)
        invention_name = f"{left_result['invention_name']}AmplifiedBy{right_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class SuperpositionEngine(OperatorEngine):
    symbol = '⊕'
    name = 'SuperpositionEngine'
    description = '疊加引擎：Maintain multiple states simultaneously until collapse'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        if right_result is None:
            return left_result
        coverage = left_result['coverage'] | right_result['coverage'] | EMERGENT_DIMENSIONS
        synergy = (left_result['synergy'] + right_result['synergy']) * 1.3
        invention_name = f"Superposed{left_result['invention_name']}And{right_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class EmergenceOperatorEngine(OperatorEngine):
    symbol = 'Ξ'
    name = 'EmergenceOperatorEngine'
    description = '湧現引擎：Detect phase transitions in capability space'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        coverage = left_result['coverage'] | EMERGENT_DIMENSIONS | META_DIMENSIONS
        synergy = left_result['synergy'] ** 1.5
        invention_name = f"Emergent{left_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class EntropyEngine(OperatorEngine):
    symbol = 'S()'
    name = 'EntropyEngine'
    description = '熵引擎：Measure and manage system disorder'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        coverage = left_result['coverage'] | {'maintainability', 'observability', 'resilience', 'self_healing'}
        synergy = left_result['synergy'] * 1.4
        invention_name = f"EntropyManaged{left_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class FieldEngine(OperatorEngine):
    symbol = '𝔽()'
    name = 'FieldEngine'
    description = '場論引擎：Model invention space as potential field'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        coverage = left_result['coverage'] | BREAKTHROUGH_DIMENSIONS
        if right_result:
            coverage |= right_result['coverage']
        synergy = left_result['synergy'] * 1.6
        invention_name = f"FieldGuided{left_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


class SymmetryBreakingEngine(OperatorEngine):
    symbol = 'Σ⁻¹'
    name = 'SymmetryBreakingEngine'
    description = '對稱破缺引擎：Generate variants by breaking symmetry'

    def apply(self, left_result: dict, right_result: Optional[dict], context: dict) -> dict:
        coverage = left_result['coverage'] | {'adaptability', 'scalability', 'creativity', 'innovation'}
        synergy = left_result['synergy'] * 1.8
        invention_name = f"SymmetryBroken{left_result['invention_name']}"
        return {
            'coverage': coverage,
            'synergy': synergy,
            'invention_name': invention_name,
        }


ELEMENT_OPS = [AbstractionEngine(), IntegrationEngine(), FocusEngine(),
               SynergyEngine(), SpecializationEngine(), SelfImprovementEngine(),
               AmplificationEngine()]

SPACE_OPS = [SuperpositionEngine(), EmergenceOperatorEngine(), EntropyEngine(),
             FieldEngine(), SymmetryBreakingEngine()]

ALL_OPS = ELEMENT_OPS + SPACE_OPS


def _get_operator_map() -> dict[str, OperatorEngine]:
    return {e.symbol: e for e in ALL_OPS}


@dataclass
class FormulaResult:
    formula: FormulaNode = field(default_factory=FormulaNode)
    formula_string: str = ''
    coverage: set = field(default_factory=set)
    coverage_rate: float = 0.0
    synergy_score: float = 0.0
    invention_name: str = ''
    invention_description: str = ''
    factors_used: list = field(default_factory=list)
    operators_used: list = field(default_factory=list)
    sequence_signature: str = ''


class FormulaGenerator:
    def __init__(self, factors: dict, operators: list[OperatorEngine]):
        self.factors = factors
        self.operators = operators
        self.factor_keys = list(factors.keys())
        self.binary_symbols = [op.symbol for op in operators if op.symbol not in ('log', 'sq')]
        self.unary_symbols = [op.symbol for op in operators if op.symbol in ('log', 'sq')]

    def generate(self, max_depth: int = 3) -> Generator[FormulaNode, None, None]:
        yield from self._generate_depth(1, max_depth, self.factor_keys)

    def _generate_depth(self, current_depth: int, max_depth: int, available_factors: list[str]) -> Generator[FormulaNode, None, None]:
        if current_depth > max_depth:
            return

        for f in available_factors:
            yield FormulaNode(factor=f)

        if current_depth >= max_depth:
            return

        for f in available_factors:
            for un_op in self.unary_symbols:
                for child in self._generate_depth(current_depth + 1, max_depth, available_factors):
                    node = FormulaNode(operator=un_op, left=child)
                    yield node

        for perm_len in range(2, min(len(available_factors), max_depth - current_depth + 2) + 1):
            if current_depth + 1 > max_depth and perm_len > 2:
                break
            for perm in permutations(available_factors, perm_len):
                for bin_op in self.binary_symbols:
                    for bracket_tree in self._generate_bracket_trees(list(perm), bin_op, current_depth, max_depth):
                        yield bracket_tree

    def _generate_bracket_trees(self, factors_ordered: list[str], bin_op: str, current_depth: int, max_depth: int) -> Generator[FormulaNode, None, None]:
        if len(factors_ordered) == 1:
            yield FormulaNode(factor=factors_ordered[0])
            return
        if len(factors_ordered) == 2:
            left = FormulaNode(factor=factors_ordered[0])
            right = FormulaNode(factor=factors_ordered[1])
            yield FormulaNode(operator=bin_op, left=left, right=right)
            return

        for i in range(1, len(factors_ordered)):
            left_factors = factors_ordered[:i]
            right_factors = factors_ordered[i:]

            for left_node in self._gen_subtrees(left_factors, current_depth, max_depth):
                for right_node in self._gen_subtrees(right_factors, current_depth, max_depth):
                    yield FormulaNode(operator=bin_op, left=left_node, right=right_node)

    def _gen_subtrees(self, factors: list[str], current_depth: int, max_depth: int) -> Generator[FormulaNode, None, None]:
        if len(factors) == 1:
            yield FormulaNode(factor=factors[0])
            for un_op in self.unary_symbols:
                yield FormulaNode(operator=un_op, left=FormulaNode(factor=factors[0]))
            return

        yield from self._generate_bracket_trees(factors, self.binary_symbols[0] if self.binary_symbols else '+', current_depth, max_depth)

    def generate_with_factors(self, factor_subset: list[str], max_depth: int = 3) -> Generator[FormulaNode, None, None]:
        yield from self._generate_depth(1, max_depth, factor_subset)

    def count_total_formulas(self, max_depth: int = 3) -> dict:
        result = {}
        for d in range(1, max_depth + 1):
            count = self._count_at_depth(d, len(self.factor_keys))
            result[d] = count
        return result

    def _count_at_depth(self, depth: int, n_factors: int) -> int:
        if depth == 1:
            return n_factors

        count = n_factors

        unary_count = len(self.unary_symbols)
        child_count = self._count_at_depth(depth - 1, n_factors)
        count += unary_count * child_count

        binary_count = len(self.binary_symbols)
        for k in range(2, min(n_factors, depth + 1) + 1):
            perms = math.perm(n_factors, k)
            catalan = self._catalan(k - 1)
            count += binary_count * perms * catalan

        return count

    @staticmethod
    def _catalan(n: int) -> int:
        if n <= 0:
            return 1
        return math.comb(2 * n, n) // (n + 1)


class FormulaEvaluator:
    def __init__(self, scenario_dimensions: list[str] | None = None, scenario_categories: list[str] | None = None):
        self.scenario_dimensions = set(scenario_dimensions or SCENARIO_DIMENSIONS)
        self.scenario_categories = set(scenario_categories or SCENARIO_CATEGORIES)
        self.total_coverage_size = len(self.scenario_dimensions) + len(self.scenario_categories)

    def evaluate(self, formula: FormulaNode) -> FormulaResult:
        context = {
            'dimensions': self.scenario_dimensions,
            'categories': self.scenario_categories,
        }
        eval_result = formula.evaluate(context)

        coverage = eval_result.get('coverage', set())
        coverage_rate = len(coverage) / max(self.total_coverage_size, 1)
        synergy_score = eval_result.get('synergy', 0.0)
        invention_name = eval_result.get('invention_name', '')
        factors_used = eval_result.get('factors_used', [])
        operators_used = eval_result.get('operators_used', [])

        formula_string = formula.to_string()
        sequence_signature = self._compute_signature(formula_string, factors_used, operators_used)

        description = self._generate_description(invention_name, factors_used, operators_used, coverage, synergy_score)

        return FormulaResult(
            formula=formula,
            formula_string=formula_string,
            coverage=coverage,
            coverage_rate=min(coverage_rate, 1.0),
            synergy_score=synergy_score,
            invention_name=invention_name,
            invention_description=description,
            factors_used=factors_used,
            operators_used=operators_used,
            sequence_signature=sequence_signature,
        )

    def rank(self, formulas: list[FormulaNode], top_k: int = 10) -> list[FormulaResult]:
        results = [self.evaluate(f) for f in formulas]
        results.sort(key=lambda r: (r.coverage_rate, r.synergy_score), reverse=True)
        return results[:top_k]

    @staticmethod
    def _compute_signature(formula_string: str, factors: list[str], operators: list[str]) -> str:
        raw = f"{formula_string}|{''.join(sorted(factors))}|{''.join(sorted(operators))}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _generate_description(invention_name: str, factors: list[str], operators: list[str], coverage: set, synergy: float) -> str:
        factor_names = [INVENTORY_FACTORS.get(f, {}).get('name', f) for f in factors]
        op_desc_map = {
            'log': '抽象化', '+': '整合', '-': '聚焦', '*': '協同',
            '/': '專門化', 'sq': '自我改善', '^': '放大',
        }
        op_descs = [op_desc_map.get(op, op) for op in operators]
        return f"{invention_name}：透過{'、'.join(op_descs)}運算，結合{'、'.join(factor_names)}能力維度，覆蓋 {len(coverage)} 個場景維度，synergy 分數 {synergy:.2f}"


class ConflictResolutionFormulaGenerator:
    def __init__(self, architecture: FormulaOperatorArchitecture):
        self.arch = architecture

    def generate_resolution_formulas(self, overlap_id: str) -> list[FormulaResult]:
        overlap = None
        for ov in CONFLICT_REGISTRY['overlaps']:
            if ov['id'] == overlap_id:
                overlap = ov
                break
        if overlap is None:
            return []

        factors = overlap['factors_affected']
        recommendation = overlap['recommendation']
        results = []

        if recommendation == 'MERGE':
            merge_formula = self._build_merge_formula(factors)
            result = self.arch.evaluator.evaluate(merge_formula)
            result.invention_description = f"衝突解決公式（{overlap['group']}）：合併重複類別，消除 {overlap['severity']} 級衝突"
            results.append(result)

            abstract_formula = self._build_abstract_formula(factors)
            result2 = self.arch.evaluator.evaluate(abstract_formula)
            result2.invention_description = f"衝突解決公式（{overlap['group']}）：抽象化統一接口，保留各自實作"
            results.append(result2)

        elif recommendation == 'ARCHIVE':
            focus_formula = self._build_focus_formula(factors)
            result = self.arch.evaluator.evaluate(focus_formula)
            result.invention_description = f"衝突解決公式（{overlap['group']}）：聚焦最佳實作，歸檔過時版本"
            results.append(result)

        elif recommendation == 'KEEP_SEPARATE':
            synergy_formula = self._build_synergy_formula(factors)
            result = self.arch.evaluator.evaluate(synergy_formula)
            result.invention_description = f"衝突解決公式（{overlap['group']}）：協同不同信號源，統一協調"
            results.append(result)

        return results

    def generate_all_resolutions(self) -> dict[str, list[FormulaResult]]:
        all_results = {}
        for ov in CONFLICT_REGISTRY['overlaps']:
            results = self.generate_resolution_formulas(ov['id'])
            if results:
                all_results[ov['id']] = results
        return all_results

    def generate_rule_resolution_formulas(self, contradiction_id: str) -> list[dict]:
        contradiction = None
        for rc in CONFLICT_REGISTRY['rule_contradictions']:
            if rc['id'] == contradiction_id:
                contradiction = rc
                break
        if contradiction is None:
            return []

        return [{
            'contradiction_id': contradiction['id'],
            'rules': contradiction['rules'],
            'severity': contradiction['severity'],
            'resolution': contradiction['resolution'],
            'formula_suggestion': self._suggest_rule_formula(contradiction),
        }]

    def generate_all_rule_resolutions(self) -> list[dict]:
        results = []
        for rc in CONFLICT_REGISTRY['rule_contradictions']:
            results.extend(self.generate_rule_resolution_formulas(rc['id']))
        return results

    def _build_merge_formula(self, factors: list[str]) -> FormulaNode:
        if len(factors) < 2:
            return FormulaNode(factor=factors[0])
        left = FormulaNode(factor=factors[0])
        for f in factors[1:]:
            left = FormulaNode(operator='+', left=left, right=FormulaNode(factor=f))
        return FormulaNode(operator='log', left=left)

    def _build_abstract_formula(self, factors: list[str]) -> FormulaNode:
        if len(factors) < 2:
            return FormulaNode(operator='log', left=FormulaNode(factor=factors[0]))
        left = FormulaNode(factor=factors[0])
        for f in factors[1:]:
            left = FormulaNode(operator='+', left=left, right=FormulaNode(factor=f))
        return FormulaNode(operator='log', left=left)

    def _build_focus_formula(self, factors: list[str]) -> FormulaNode:
        if len(factors) < 2:
            return FormulaNode(factor=factors[0])
        return FormulaNode(operator='-', left=FormulaNode(factor=factors[0]), right=FormulaNode(factor=factors[-1]))

    def _build_synergy_formula(self, factors: list[str]) -> FormulaNode:
        if len(factors) < 2:
            return FormulaNode(factor=factors[0])
        return FormulaNode(operator='*', left=FormulaNode(factor=factors[0]), right=FormulaNode(factor=factors[1]))

    def _suggest_rule_formula(self, contradiction: dict) -> str:
        severity = contradiction['severity']
        if severity == 'HIGH':
            return f"sq({contradiction['rules'][0]}) - {contradiction['rules'][1]}：自我改善高優先級規則，減去低優先級衝突部分"
        elif severity == 'MEDIUM':
            return f"log({contradiction['rules'][0]} + {contradiction['rules'][1]})：抽象化兩條規則，找到更高層次嘅統一原則"
        else:
            return f"{contradiction['rules'][0]} + {contradiction['rules'][1]}：明確例外範圍，兩者共存"

    def assess_factor_health(self) -> dict[str, dict]:
        return FACTOR_QUALITY_MAP

    def assess_system_health(self) -> dict:
        total_penalty = sum(q['penalty'] for q in FACTOR_QUALITY_MAP.values())
        avg_synergy = sum(q['adjusted_synergy'] for q in FACTOR_QUALITY_MAP.values()) / max(len(FACTOR_QUALITY_MAP), 1)
        critical_factors = [k for k, q in FACTOR_QUALITY_MAP.items() if q['health'] == 'CRITICAL']
        degraded_factors = [k for k, q in FACTOR_QUALITY_MAP.items() if q['health'] == 'DEGRADED']
        healthy_factors = [k for k, q in FACTOR_QUALITY_MAP.items() if q['health'] == 'HEALTHY']

        return {
            'total_conflict_penalty': total_penalty,
            'average_adjusted_synergy': avg_synergy,
            'critical_factors': critical_factors,
            'degraded_factors': degraded_factors,
            'healthy_factors': healthy_factors,
            'overlap_count': len(CONFLICT_REGISTRY['overlaps']),
            'critical_overlap_count': sum(1 for ov in CONFLICT_REGISTRY['overlaps'] if ov['severity'] == 'CRITICAL'),
            'rule_contradiction_count': len(CONFLICT_REGISTRY['rule_contradictions']),
            'high_severity_contradiction_count': sum(1 for rc in CONFLICT_REGISTRY['rule_contradictions'] if rc['severity'] == 'HIGH'),
            'stub_skill_percentage': CONFLICT_REGISTRY['quality_issues']['invented_skills_stubs'] / max(CONFLICT_REGISTRY['quality_issues']['invented_skills_stubs'] + CONFLICT_REGISTRY['quality_issues']['invented_skills_real'], 1) * 100,
            'overall_health': 'CRITICAL' if critical_factors else 'DEGRADED' if degraded_factors else 'HEALTHY',
        }


class FormulaOperatorArchitecture:
    def __init__(self):
        self.factors = INVENTORY_FACTORS
        self.operators = ALL_OPS
        self.generator = FormulaGenerator(self.factors, self.operators)
        self.evaluator = FormulaEvaluator()
        self.conflict_resolver = ConflictResolutionFormulaGenerator(self)

    def invent(self, max_depth: int = 3, top_k: int = 20) -> list[FormulaResult]:
        formulas = list(self.generator.generate(max_depth=max_depth))
        return self.evaluator.rank(formulas, top_k=top_k)

    def invent_for_gap(self, gap_dimensions: list[str], max_depth: int = 3) -> list[FormulaResult]:
        relevant_factors = []
        for f_key, f_info in FACTOR_COVERAGE_MAP.items():
            if f_info['coverage'] & set(gap_dimensions):
                relevant_factors.append(f_key)

        if not relevant_factors:
            relevant_factors = list(self.factors.keys())[:5]

        formulas = list(self.generator.generate_with_factors(relevant_factors, max_depth=max_depth))
        results = [self.evaluator.evaluate(f) for f in formulas]

        for r in results:
            gap_overlap = len(r.coverage & set(gap_dimensions))
            r.coverage_rate = gap_overlap / max(len(gap_dimensions), 1)

        results.sort(key=lambda r: (r.coverage_rate, r.synergy_score), reverse=True)
        return results

    def explain(self, formula: FormulaNode) -> str:
        result = self.evaluator.evaluate(formula)

        op_explain_map = {
            'log': 'log 運算將 {left} 抽象化，提取其通用模式，升維至更高層次嘅認知框架',
            '+': '+ 運算整合 {left} 同 {right}，聯合兩者嘅覆蓋範圍，形成更全面嘅能力',
            '-': '- 運算從 {left} 中減去同 {right} 重疊嘅部分，聚焦於 {left} 獨有嘅貢獻',
            '*': '* 運算讓 {left} 同 {right} 深度交叉，產生湧現（emergent）嘅全新能力',
            '/': '/ 運算將 {left} 專門化聚焦於 {right} 嘅領域，實現領域突破',
            'sq': 'sq 運算將 {left} 應用於自身，遞歸增強，實現質變飛躍',
            '^': '^ 運算以 {right} 嘅力量放大 {left}，產生指數級突破',
        }

        parts = []
        self._explain_recursive(formula, op_explain_map, parts)

        header = f"【{result.invention_name}】"
        coverage_str = f"覆蓋維度：{', '.join(sorted(result.coverage))}" if result.coverage else "覆蓋維度：無"
        synergy_str = f"Synergy 分數：{result.synergy_score:.4f}"
        factors_str = f"使用嘅能力維度：{', '.join(result.factors_used)}"
        ops_str = f"使用嘅運算符：{', '.join(result.operators_used)}"

        return f"{header}\n公式：{result.formula_string}\n{''.join(parts)}\n{coverage_str}\n{synergy_str}\n{factors_str}\n{ops_str}"

    def _explain_recursive(self, node: FormulaNode, op_map: dict, parts: list) -> str:
        if node.factor is not None:
            factor_meta = INVENTORY_FACTORS.get(node.factor, {'name': node.factor, 'description': ''})
            return factor_meta['name']

        left_name = self._explain_recursive(node.left, op_map, parts) if node.left else ''
        right_name = self._explain_recursive(node.right, op_map, parts) if node.right else ''

        template = op_map.get(node.operator, '{left} ○ {right}')
        explanation = template.replace('{left}', left_name).replace('{right}', right_name)
        parts.append(f"\n→ {explanation}")

        return node.to_string()

    def count_search_space(self, max_depth: int = 4) -> dict:
        return self.generator.count_total_formulas(max_depth=max_depth)

    def resolve_conflicts(self) -> dict[str, list[FormulaResult]]:
        return self.conflict_resolver.generate_all_resolutions()

    def resolve_rule_contradictions(self) -> list[dict]:
        return self.conflict_resolver.generate_all_rule_resolutions()

    def assess_health(self) -> dict:
        return self.conflict_resolver.assess_system_health()

    def factor_quality_report(self) -> dict[str, dict]:
        return self.conflict_resolver.assess_factor_health()

    def invent_with_conflict_awareness(self, max_depth: int = 3, top_k: int = 20) -> list[FormulaResult]:
        formulas = list(self.generator.generate(max_depth=max_depth))
        results = []
        for f in formulas:
            result = self.evaluator.evaluate(f)
            quality = FACTOR_QUALITY_MAP
            total_penalty = sum(quality.get(fk, {}).get('penalty', 0.0) for fk in result.factors_used)
            penalty_ratio = max(1.0 - total_penalty * 0.3, 0.1)
            result.synergy_score = result.synergy_score * penalty_ratio
            results.append(result)
        results.sort(key=lambda r: (r.coverage_rate, r.synergy_score), reverse=True)
        return results[:top_k]


if __name__ == '__main__':
    arch = FormulaOperatorArchitecture()

    print("=" * 60)
    print("Formula Operator Architecture — 快速演示")
    print("=" * 60)

    print("\n📊 搜索空間統計：")
    space = arch.count_search_space(max_depth=3)
    for depth, count in space.items():
        print(f"  Depth {depth}: {count:,} 條公式")

    print("\n🔬 Top 10 發明（max_depth=2）：")
    top_inventions = arch.invent(max_depth=2, top_k=10)
    for i, inv in enumerate(top_inventions, 1):
        print(f"  {i}. {inv.invention_name}")
        print(f"     公式：{inv.formula_string}")
        print(f"     覆蓋率：{inv.coverage_rate:.2%} | Synergy：{inv.synergy_score:.4f}")
        print(f"     維度數：{len(inv.coverage)} | 簽名：{inv.sequence_signature}")

    print("\n🎯 缺口導向發明（gap = ['confidentiality', 'compliance']）：")
    gap_inventions = arch.invent_for_gap(['confidentiality', 'compliance'], max_depth=2)
    for i, inv in enumerate(gap_inventions[:5], 1):
        print(f"  {i}. {inv.invention_name} — 覆蓋率：{inv.coverage_rate:.2%}")

    print("\n📖 公式解釋示例：")
    sample = FormulaNode(
        operator='+',
        left=FormulaNode(operator='log', left=FormulaNode(factor='S')),
        right=FormulaNode(operator='*', left=FormulaNode(factor='K'), right=FormulaNode(factor='C')),
    )
    explanation = arch.explain(sample)
    print(explanation)

    print("\n🔬 另一個示例 — sq(K) ^ H：")
    sample2 = FormulaNode(
        operator='^',
        left=FormulaNode(operator='sq', left=FormulaNode(factor='K')),
        right=FormulaNode(factor='H'),
    )
    explanation2 = arch.explain(sample2)
    print(explanation2)

    print("\n🔍 衝突感知 Factor 質量評估：")
    health = arch.assess_health()
    print(f"  系統整體健康：{health['overall_health']}")
    print(f"  CRITICAL 因子：{health['critical_factors']}")
    print(f"  DEGRADED 因子：{health['degraded_factors']}")
    print(f"  HEALTHY 因子：{health['healthy_factors']}")
    print(f"  平均調整後 Synergy：{health['average_adjusted_synergy']:.4f}")
    print(f"  CRITICAL 重疊數：{health['critical_overlap_count']}")
    print(f"  HIGH 級規則矛盾數：{health['high_severity_contradiction_count']}")
    print(f"  Stub 技能百分比：{health['stub_skill_percentage']:.1f}%")

    print("\n🔧 衝突解決公式：")
    resolutions = arch.resolve_conflicts()
    for ov_id, results in resolutions.items():
        print(f"  {ov_id}:")
        for r in results:
            print(f"    → {r.formula_string} | {r.invention_description}")

    print("\n⚖️ 規則矛盾解決建議：")
    rule_resolutions = arch.resolve_rule_contradictions()
    for rr in rule_resolutions:
        print(f"  {rr['contradiction_id']} ({rr['severity']}): {rr['rules']}")
        print(f"    解決方案：{rr['resolution']}")
        print(f"    公式建議：{rr['formula_suggestion']}")

    print("\n🧠 衝突感知 Top 5 發明（adjusted synergy）：")
    conflict_aware = arch.invent_with_conflict_awareness(max_depth=2, top_k=5)
    for i, inv in enumerate(conflict_aware, 1):
        print(f"  {i}. {inv.invention_name}")
        print(f"     公式：{inv.formula_string} | 調整後 Synergy：{inv.synergy_score:.4f}")

    print("\n✅ Formula Operator Architecture 演示完成")
