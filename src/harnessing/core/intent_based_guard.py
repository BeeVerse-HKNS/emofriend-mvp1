#!/usr/bin/env python3
"""
IntentBasedGuard — 基於意圖的事前防護系統

【加法創新】Prompt理解 + 預防系統 = 基於意圖的事前防護
在用戶執行危險操作前就預測到風險並提醒，而不是等錯誤發生。
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class IntentRisk:
    intent_type: str
    risk_level: RiskLevel
    risk_description: str
    suggested_actions: List[str]
    confidence: float


class IntentBasedGuard:
    """
    基於意圖的事前防護系統
    
    在用戶執行操作前，分析其意圖的風險級別，並提供預防性建議。
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.risk_patterns = self._init_risk_patterns()
        self.intervention_history: List[Dict] = []
    
    def _init_risk_patterns(self) -> Dict[str, Dict]:
        """初始化風險模式數據庫"""
        return {
            "delete": {
                "keywords": ["delete", "remove", "drop", "destroy", "erase", "rm", "del"],
                "risk_level": RiskLevel.HIGH,
                "description": "刪除操作可能導致數據丟失",
                "suggestions": [
                    "確認是否有備份",
                    "先在測試環境驗證",
                    "考慮使用軟刪除而非硬刪除"
                ]
            },
            "modify_config": {
                "keywords": ["config", "configure", "setting", "setup", "init", "deploy"],
                "risk_level": RiskLevel.MEDIUM,
                "description": "配置修改可能影響系統穩定性",
                "suggestions": [
                    "備份當前配置",
                    "逐步驗證每個更改",
                    "準備回滾方案"
                ]
            },
            "external_api": {
                "keywords": ["api", "key", "token", "secret", "credential", "password"],
                "risk_level": RiskLevel.CRITICAL,
                "description": "涉及敏感憑證的操作",
                "suggestions": [
                    "使用環境變量存儲敏感信息",
                    "不要硬編碼憑證",
                    "檢查.gitignore是否包含敏感文件"
                ]
            },
            "publish": {
                "keywords": ["publish", "release", "deploy", "push", "submit"],
                "risk_level": RiskLevel.HIGH,
                "description": "發布操作可能影響用戶",
                "suggestions": [
                    "在測試環境充分驗證",
                    "準備應急回滾方案",
                    "確認發布時間窗口合適"
                ]
            },
            "mass_operation": {
                "keywords": ["all", "every", "batch", "bulk", "mass", "multiple"],
                "risk_level": RiskLevel.MEDIUM,
                "description": "批量操作影響範圍廣",
                "suggestions": [
                    "先小範圍測試",
                    "確認操作範圍",
                    "準備撤銷機制"
                ]
            }
        }
    
    def analyze_intent(self, prompt: str) -> IntentRisk:
        """
        分析用戶意圖的風險級別
        
        Args:
            prompt: 用戶輸入的prompt
            
        Returns:
            IntentRisk: 風險分析結果
        """
        prompt_lower = prompt.lower()
        
        highest_risk = RiskLevel.SAFE
        matched_intent = "unknown"
        matched_description = "未檢測到風險"
        matched_suggestions = []
        total_confidence = 0.0
        match_count = 0
        
        for intent_type, pattern in self.risk_patterns.items():
            keyword_matches = sum(1 for kw in pattern["keywords"] if kw in prompt_lower)
            
            if keyword_matches > 0:
                match_count += 1
                confidence = min(keyword_matches / len(pattern["keywords"]), 1.0)
                total_confidence += confidence
                
                if self._risk_level_to_score(pattern["risk_level"]) > self._risk_level_to_score(highest_risk):
                    highest_risk = pattern["risk_level"]
                    matched_intent = intent_type
                    matched_description = pattern["description"]
                    matched_suggestions = pattern["suggestions"]
        
        if match_count == 0:
            return IntentRisk(
                intent_type="safe",
                risk_level=RiskLevel.SAFE,
                risk_description="未檢測到風險",
                suggested_actions=[],
                confidence=1.0
            )
        
        avg_confidence = total_confidence / match_count
        
        return IntentRisk(
            intent_type=matched_intent,
            risk_level=highest_risk,
            risk_description=matched_description,
            suggested_actions=matched_suggestions,
            confidence=avg_confidence
        )
    
    def _risk_level_to_score(self, level: RiskLevel) -> int:
        """將風險級別轉換為數字分數用於比較"""
        scores = {
            RiskLevel.SAFE: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4
        }
        return scores.get(level, 0)
    
    def should_intervene(self, risk: IntentRisk) -> Tuple[bool, str]:
        """
        判斷是否需要執行干預
        
        Returns:
            (是否需要干預, 干預理由)
        """
        if risk.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return True, f"檢測到{self._risk_level_to_chinese(risk.risk_level)}風險"
        elif risk.risk_level == RiskLevel.MEDIUM and risk.confidence > 0.7:
            return True, f"檢測到中等風險，可信度較高"
        return False, "風險級別較低，無需干預"
    
    def _risk_level_to_chinese(self, level: RiskLevel) -> str:
        """風險級別轉換為中文"""
        mapping = {
            RiskLevel.SAFE: "安全",
            RiskLevel.LOW: "低",
            RiskLevel.MEDIUM: "中等",
            RiskLevel.HIGH: "高",
            RiskLevel.CRITICAL: "嚴重"
        }
        return mapping.get(level, "未知")
    
    def generate_warning(self, risk: IntentRisk) -> str:
        """生成警告信息"""
        warning_lines = [
            f"⚠️  【{self._risk_level_to_chinese(risk.risk_level)}風險預警】",
            f"   檢測到的意圖: {risk.intent_type}",
            f"   風險描述: {risk.risk_description}",
            f"   可信度: {risk.confidence:.1%}"
        ]
        
        if risk.suggested_actions:
            warning_lines.append("   建議措施:")
            for idx, action in enumerate(risk.suggested_actions, 1):
                warning_lines.append(f"   {idx}. {action}")
        
        return "\n".join(warning_lines)
    
    def record_intervention(self, risk: IntentRisk, action_taken: str):
        """記錄干預歷史"""
        record = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "intent_type": risk.intent_type,
            "risk_level": risk.risk_level.value,
            "confidence": risk.confidence,
            "action_taken": action_taken
        }
        self.intervention_history.append(record)
        self.logger.info(f"記錄干預: {record}")
    
    def get_intervention_summary(self, limit: int = 10) -> List[Dict]:
        """獲取干預歷史摘要"""
        return self.intervention_history[-limit:]


def main():
    """演示IntentBasedGuard的使用"""
    logging.basicConfig(level=logging.INFO)
    
    guard = IntentBasedGuard()
    
    test_prompts = [
        "我想刪除所有日誌文件",
        "幫我配置一下API Key",
        "創建一個新的Python文件",
        "準備發布新版本到生產環境",
        "批量修改100個文件的內容"
    ]
    
    print("=" * 80)
    print("IntentBasedGuard — 基於意圖的事前防護系統演示")
    print("=" * 80)
    print()
    
    for prompt in test_prompts:
        print(f"測試Prompt: {prompt}")
        print("-" * 80)
        
        risk = guard.analyze_intent(prompt)
        should_intervene, reason = guard.should_intervene(risk)
        
        if should_intervene:
            print(guard.generate_warning(risk))
            guard.record_intervention(risk, "用戶查看警告後確認")
        else:
            print(f"✅ {reason}")
        
        print()


if __name__ == "__main__":
    main()

