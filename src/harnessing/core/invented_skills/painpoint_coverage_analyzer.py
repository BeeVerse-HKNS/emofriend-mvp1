"""
INV-001 PainpointCoverageAnalyzer
Formula: log(K) + R * P
Explanation: 抽象化知識庫 + 推理與預測交叉協同 = 自動分析痛點覆蓋率
Target Painpoints: WLLM-002, CLLM-014, HD-007
"""

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class Painpoint:
    id: str
    category: str
    description: str
    severity: str
    covered: bool = False
    coverage_methods: List[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    total_painpoints: int
    covered_painpoints: int
    coverage_rate: float
    gaps: List[Painpoint]
    by_category: Dict[str, Dict[str, Any]]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PainpointParser:
    def __init__(self, knowledge_base_path: Optional[Path] = None):
        self.knowledge_base_path = knowledge_base_path
        self._painpoints: Dict[str, Painpoint] = {}

    def parse_from_json(self, json_path: Path) -> Dict[str, Painpoint]:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data.get('painpoints', []):
            painpoint = Painpoint(
                id=item['id'],
                category=item.get('category', 'unknown'),
                description=item.get('description', ''),
                severity=item.get('severity', 'medium'),
                covered=item.get('covered', False),
                coverage_methods=item.get('coverage_methods', [])
            )
            self._painpoints[painpoint.id] = painpoint
        
        return self._painpoints

    def parse_from_dict(self, data: Dict[str, Any]) -> Dict[str, Painpoint]:
        for item in data.get('painpoints', []):
            painpoint = Painpoint(
                id=item['id'],
                category=item.get('category', 'unknown'),
                description=item.get('description', ''),
                severity=item.get('severity', 'medium'),
                covered=item.get('covered', False),
                coverage_methods=item.get('coverage_methods', [])
            )
            self._painpoints[painpoint.id] = painpoint
        return self._painpoints

    def get_painpoint(self, painpoint_id: str) -> Optional[Painpoint]:
        return self._painpoints.get(painpoint_id)

    def get_all_painpoints(self) -> Dict[str, Painpoint]:
        return self._painpoints


class CoverageCalculator:
    def __init__(self, knowledge_weight: float = 1.0, reasoning_weight: float = 1.0):
        self.knowledge_weight = knowledge_weight
        self.reasoning_weight = reasoning_weight

    def calculate_coverage_rate(self, painpoints: Dict[str, Painpoint]) -> float:
        if not painpoints:
            return 0.0
        covered = sum(1 for p in painpoints.values() if p.covered)
        return covered / len(painpoints)

    def calculate_formula_score(self, knowledge_size: int, reasoning_score: float, prediction_score: float) -> float:
        k_score = math.log(knowledge_size + 1) if knowledge_size > 0 else 0
        r_p_score = reasoning_score * prediction_score
        return self.knowledge_weight * k_score + self.reasoning_weight * r_p_score

    def calculate_by_category(self, painpoints: Dict[str, Painpoint]) -> Dict[str, Dict[str, Any]]:
        categories: Dict[str, Dict[str, Any]] = {}
        
        for painpoint in painpoints.values():
            cat = painpoint.category
            if cat not in categories:
                categories[cat] = {'total': 0, 'covered': 0, 'painpoints': []}
            
            categories[cat]['total'] += 1
            if painpoint.covered:
                categories[cat]['covered'] += 1
            categories[cat]['painpoints'].append(painpoint.id)
        
        for cat in categories:
            total = categories[cat]['total']
            covered = categories[cat]['covered']
            categories[cat]['coverage_rate'] = covered / total if total > 0 else 0.0
        
        return categories


class GapReporter:
    def __init__(self, severity_order: List[str] = None):
        self.severity_order = severity_order or ['critical', 'high', 'medium', 'low']

    def identify_gaps(self, painpoints: Dict[str, Painpoint]) -> List[Painpoint]:
        gaps = [p for p in painpoints.values() if not p.covered]
        return sorted(gaps, key=lambda p: self.severity_order.index(p.severity) if p.severity in self.severity_order else 99)

    def generate_report(self, painpoints: Dict[str, Painpoint], calculator: CoverageCalculator) -> CoverageReport:
        gaps = self.identify_gaps(painpoints)
        by_category = calculator.calculate_by_category(painpoints)
        coverage_rate = calculator.calculate_coverage_rate(painpoints)
        
        return CoverageReport(
            total_painpoints=len(painpoints),
            covered_painpoints=len(painpoints) - len(gaps),
            coverage_rate=coverage_rate,
            gaps=gaps,
            by_category=by_category
        )

    def export_report(self, report: CoverageReport, output_path: Path) -> None:
        data = {
            'timestamp': report.timestamp,
            'total_painpoints': report.total_painpoints,
            'covered_painpoints': report.covered_painpoints,
            'coverage_rate': report.coverage_rate,
            'gap_count': len(report.gaps),
            'gaps': [
                {
                    'id': p.id,
                    'category': p.category,
                    'description': p.description,
                    'severity': p.severity
                }
                for p in report.gaps
            ],
            'by_category': report.by_category
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class PainpointCoverageAnalyzer:
    """
    INV-001: PainpointCoverageAnalyzer
    Formula: log(K) + R * P
    
    自動分析 LLM 痛點並生成覆蓋率報告
    """

    def __init__(self, knowledge_base_path: Optional[Path] = None):
        self.parser = PainpointParser(knowledge_base_path)
        self.calculator = CoverageCalculator()
        self.reporter = GapReporter()

    def analyze(self, painpoints_data: Dict[str, Any]) -> CoverageReport:
        painpoints = self.parser.parse_from_dict(painpoints_data)
        return self.reporter.generate_report(painpoints, self.calculator)

    def analyze_from_file(self, json_path: Path) -> CoverageReport:
        painpoints = self.parser.parse_from_json(json_path)
        return self.reporter.generate_report(painpoints, self.calculator)

    def get_coverage_score(self, knowledge_size: int, reasoning_score: float, prediction_score: float) -> float:
        return self.calculator.calculate_formula_score(knowledge_size, reasoning_score, prediction_score)

    def export_analysis(self, report: CoverageReport, output_path: Path) -> None:
        self.reporter.export_report(report, output_path)


if __name__ == "__main__":
    test_data = {
        'painpoints': [
            {'id': 'WLLM-002', 'category': 'llm', 'description': 'Context window limit', 'severity': 'critical', 'covered': True, 'coverage_methods': ['sliding_window']},
            {'id': 'CLLM-014', 'category': 'llm', 'description': 'Hallucination', 'severity': 'high', 'covered': False, 'coverage_methods': []},
            {'id': 'HD-007', 'category': 'hardware', 'description': 'GPU memory limit', 'severity': 'high', 'covered': True, 'coverage_methods': ['quantization']},
            {'id': 'WAA-001', 'category': 'agent', 'description': 'Infinite loop', 'severity': 'critical', 'covered': False, 'coverage_methods': []},
        ]
    }

    analyzer = PainpointCoverageAnalyzer()
    report = analyzer.analyze(test_data)
    
    print(f"Total Painpoints: {report.total_painpoints}")
    print(f"Covered: {report.covered_painpoints}")
    print(f"Coverage Rate: {report.coverage_rate:.2%}")
    print(f"Gaps: {len(report.gaps)}")
    
    for gap in report.gaps:
        print(f"  - {gap.id}: {gap.description} ({gap.severity})")
    
    formula_score = analyzer.get_coverage_score(knowledge_size=100, reasoning_score=0.8, prediction_score=0.9)
    print(f"Formula Score (log(K) + R*P): {formula_score:.4f}")
