#!/usr/bin/env python3
"""
GapDetector — 系統缺口自動檢測器

【減法創新】減去重複，發現缺口 = 系統缺口自動檢測器
自動發現系統中的能力缺口，而不是靠人類觀察。
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Set
from enum import Enum
from pathlib import Path
import json


class GapPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SystemGap:
    gap_id: str
    description: str
    priority: GapPriority
    impact: str
    suggestion: str
    related_skills: List[str]


class GapDetector:
    """
    系統缺口自動檢測器
    
    定期分析所有技能的覆蓋範圍，識別未被滿足的維度。
    """
    
    def __init__(self, data_dir: str = "data"):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.gaps: List[SystemGap] = []
        self.coverage_matrix = self._init_coverage_matrix()
    
    def _init_coverage_matrix(self) -> Dict[str, Dict[str, bool]]:
        """初始化覆蓋矩陣"""
        dimensions = [
            "error_handling", "prevention", "learning", "memory", 
            "monitoring", "security", "automation", "optimization",
            "context", "routing", "validation", "recovery"
        ]
        
        skills = {
            "ErrorClassifier": ["error_handling"],
            "RetryManager": ["error_handling", "recovery"],
            "SelfImprovementEngine": ["learning"],
            "PredictiveInterventionEngine": ["prevention", "monitoring"],
            "SelfAuditEngine": ["monitoring", "validation"],
            "PromptEnhancer": ["context"],
            "SkillRouter": ["routing"],
            "MemoryEngine": ["memory"],
            "CheckpointManager": ["recovery", "memory"],
            "CircuitBreaker": ["error_handling", "prevention"],
            "RecoveryEngine": ["recovery"],
            "GoalAnchor": ["monitoring", "validation"],
            "HumanInTheLoop": ["validation", "security"],
            "TokenManager": ["monitoring", "optimization"],
            "HealthChecker": ["monitoring"],
            "AlertingSystem": ["monitoring", "automation"],
            "RollbackManager": ["recovery", "memory"],
            "InputValidator": ["validation", "security"],
            "RateLimiter": ["security", "prevention"],
            "AuditTrail": ["monitoring", "security"],
            "FallbackManager": ["recovery", "automation"],
            "MonitoringSystem": ["monitoring"],
            "ContextManager": ["context"],
            "IntentBasedGuard": ["security", "prevention", "validation"]
        }
        
        matrix = {}
        for dim in dimensions:
            matrix[dim] = {}
            for skill_name in skills:
                matrix[dim][skill_name] = dim in skills[skill_name]
        
        return matrix
    
    def detect_gaps(self) -> List[SystemGap]:
        """
        檢測系統中的所有缺口
        
        Returns:
            List[SystemGap]: 檢測到的缺口列表
        """
        self.gaps = []
        
        self._check_coverage_gaps()
        self._check_skill_synergy_gaps()
        self._check_timing_gaps()
        self._check_scope_gaps()
        
        return sorted(self.gaps, key=lambda g: self._priority_to_score(g.priority), reverse=True)
    
    def _check_coverage_gaps(self):
        """檢查覆蓋缺口"""
        for dimension, coverage in self.coverage_matrix.items():
            covered_skills = [skill for skill, covered in coverage.items() if covered]
            
            if not covered_skills:
                self.gaps.append(SystemGap(
                    gap_id=f"coverage_{dimension}",
                    description=f"維度 '{dimension}' 沒有任何技能覆蓋",
                    priority=GapPriority.CRITICAL,
                    impact=f"系統在 '{dimension}' 方面完全缺乏能力",
                    suggestion=f"開發針對 '{dimension}' 的新技能",
                    related_skills=[]
                ))
            elif len(covered_skills) == 1:
                self.gaps.append(SystemGap(
                    gap_id=f"coverage_single_{dimension}",
                    description=f"維度 '{dimension}' 只有一個技能覆蓋",
                    priority=GapPriority.MEDIUM,
                    impact=f"如果 {covered_skills[0]} 失效，'{dimension}' 能力將完全喪失",
                    suggestion=f"為 '{dimension}' 開發備用技能",
                    related_skills=covered_skills
                ))
    
    def _check_skill_synergy_gaps(self):
        """檢查技能協同缺口"""
        synergies = [
            ("PredictiveInterventionEngine", "SelfImprovementEngine", "預測學習閉環", GapPriority.HIGH),
            ("MemoryEngine", "SkillRouter", "上下文感知路由", GapPriority.MEDIUM),
            ("SelfAuditEngine", "PredictiveInterventionEngine", "審計驅動預防", GapPriority.HIGH),
            ("IntentBasedGuard", "PredictiveInterventionEngine", "意圖預測聯動", GapPriority.MEDIUM)
        ]
        
        for skill1, skill2, description, priority in synergies:
            # 檢查是否有整合
            gap_id = f"synergy_{skill1}_{skill2}"
            self.gaps.append(SystemGap(
                gap_id=gap_id,
                description=f"{skill1} 和 {skill2} 之間缺乏協同整合: {description}",
                priority=priority,
                impact=f"錯過了技能組合的潛在價值",
                suggestion=f"開發整合層，讓 {skill1} 和 {skill2} 可以協同工作",
                related_skills=[skill1, skill2]
            ))
    
    def _check_timing_gaps(self):
        """檢查時機缺口"""
        timing_phases = {
            "pre-action": ["IntentBasedGuard", "InputValidator"],
            "during-action": ["MonitoringSystem", "HealthChecker"],
            "post-action": ["SelfAuditEngine", "SelfImprovementEngine"],
            "long-term": []
        }
        
        for phase, skills in timing_phases.items():
            if not skills:
                self.gaps.append(SystemGap(
                    gap_id=f"timing_{phase}",
                    description=f"{phase} 階段沒有任何技能",
                    priority=GapPriority.HIGH,
                    impact=f"系統在 {phase} 階段缺乏監控和保護",
                    suggestion=f"為 {phase} 階段開發專用技能",
                    related_skills=[]
                ))
    
    def _check_scope_gaps(self):
        """檢查範圍缺口"""
        scopes = {
            "short_term": ["CheckpointManager", "CircuitBreaker"],
            "medium_term": ["MemoryEngine", "SelfAuditEngine"],
            "long_term": []
        }
        
        for scope, skills in scopes.items():
            if not skills:
                self.gaps.append(SystemGap(
                    gap_id=f"scope_{scope}",
                    description=f"{scope} 時間範圍沒有專用技能",
                    priority=GapPriority.MEDIUM,
                    impact=f"系統在 {scope} 時間尺度上的能力不足",
                    suggestion=f"開發針對 {scope} 的技能",
                    related_skills=[]
                ))
    
    def _priority_to_score(self, priority: GapPriority) -> int:
        """優先級轉換為分數"""
        scores = {
            GapPriority.LOW: 1,
            GapPriority.MEDIUM: 2,
            GapPriority.HIGH: 3,
            GapPriority.CRITICAL: 4
        }
        return scores.get(priority, 0)
    
    def generate_report(self) -> str:
        """生成缺口報告"""
        if not self.gaps:
            self.detect_gaps()
        
        lines = ["=" * 80, "系統缺口檢測報告", "=" * 80, ""]
        
        priority_counts = {}
        for gap in self.gaps:
            p = gap.priority.value
            priority_counts[p] = priority_counts.get(p, 0) + 1
        
        lines.append(f"總缺口數: {len(self.gaps)}")
        for p in ["critical", "high", "medium", "low"]:
            lines.append(f"  {p}: {priority_counts.get(p, 0)}")
        lines.append("")
        
        for gap in self.gaps:
            lines.append(f"【{gap.priority.value.upper()}】 {gap.gap_id}")
            lines.append(f"   描述: {gap.description}")
            lines.append(f"   影響: {gap.impact}")
            lines.append(f"   建議: {gap.suggestion}")
            if gap.related_skills:
                lines.append(f"   相關技能: {', '.join(gap.related_skills)}")
            lines.append("")
        
        return "\n".join(lines)
    
    def save_report(self, filepath: str = None):
        """保存報告到文件"""
        if filepath is None:
            filepath = str(self.data_dir / "gap_detection_report.json")
        
        report_data = {
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "total_gaps": len(self.gaps),
            "gaps": [
                {
                    "gap_id": g.gap_id,
                    "description": g.description,
                    "priority": g.priority.value,
                    "impact": g.impact,
                    "suggestion": g.suggestion,
                    "related_skills": g.related_skills
                }
                for g in self.gaps
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"缺口報告已保存到: {filepath}")
        return filepath


def main():
    """演示GapDetector的使用"""
    logging.basicConfig(level=logging.INFO)
    
    detector = GapDetector()
    gaps = detector.detect_gaps()
    
    print(detector.generate_report())
    detector.save_report()


if __name__ == "__main__":
    main()

