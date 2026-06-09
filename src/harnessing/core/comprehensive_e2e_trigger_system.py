"""
Comprehensive E2E Testing Trigger System
自動觸發端到端測試系統

觸發條件：
1. 代碼變更檢測（文件修改、新增、刪除）
2. 聲稱完成前檢測（report completion）
3. 用戶請求交付時檢測
4. 新功能添加時檢測
5. UI/UX 變更時檢測
6. i18n 變更時檢測

公式：Trigger = (CodeChange ∨ CompletionClaim ∨ DeliveryRequest ∨ NewFeature ∨ UIUXChange ∨ i18nChange) ∧ ¬SkipCondition
"""

import os
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


class TriggerReason(Enum):
    CODE_CHANGE = "code_change"
    COMPLETION_CLAIM = "completion_claim"
    DELIVERY_REQUEST = "delivery_request"
    NEW_FEATURE = "new_feature"
    UI_UX_CHANGE = "ui_ux_change"
    I18N_CHANGE = "i18n_change"
    DEPENDENCY_CHANGE = "dependency_change"
    CONFIG_CHANGE = "config_change"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class TriggerSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TriggerEvent:
    reason: TriggerReason
    severity: TriggerSeverity
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    file_paths: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "reason": self.reason.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "file_paths": self.file_paths
        }


@dataclass
class TriggerResult:
    should_trigger: bool
    events: List[TriggerEvent] = field(default_factory=list)
    skip_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_trigger": self.should_trigger,
            "events": [e.to_dict() for e in self.events],
            "skip_reason": self.skip_reason
        }


class FileChangeDetector:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.file_hashes: Dict[str, str] = {}
        self.hash_file = project_root / ".e2e_file_hashes.json"
        self._load_hashes()
    
    def _load_hashes(self):
        if self.hash_file.exists():
            try:
                with open(self.hash_file, 'r', encoding='utf-8') as f:
                    self.file_hashes = json.load(f)
            except:
                self.file_hashes = {}
    
    def _save_hashes(self):
        with open(self.hash_file, 'w', encoding='utf-8') as f:
            json.dump(self.file_hashes, f, indent=2)
    
    def _compute_hash(self, file_path: Path) -> str:
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def detect_changes(self, patterns: List[str]) -> Tuple[List[str], List[str], List[str]]:
        added = []
        modified = []
        deleted = list(self.file_hashes.keys())
        
        for pattern in patterns:
            for file_path in self.project_root.rglob(pattern):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(self.project_root))
                    current_hash = self._compute_hash(file_path)
                    
                    if rel_path in self.file_hashes:
                        deleted.remove(rel_path)
                        if self.file_hashes[rel_path] != current_hash:
                            modified.append(rel_path)
                            self.file_hashes[rel_path] = current_hash
                    else:
                        added.append(rel_path)
                        self.file_hashes[rel_path] = current_hash
        
        self._save_hashes()
        return added, modified, deleted


class CompletionClaimDetector:
    def __init__(self):
        self.completion_keywords = [
            "完成", "completed", "done", "finished", "success",
            "修復完成", "已修復", "fixed", "resolved",
            "任務完成", "task completed", "ready",
            "可以交付", "ready for user", "交付"
        ]
        self.false_positive_keywords = [
            "TODO", "仍需", "pending", "in progress",
            "待處理", "未完成", "remaining"
        ]
    
    def detect_completion_claim(self, text: str) -> Tuple[bool, Optional[str]]:
        text_lower = text.lower()
        
        has_completion = any(kw in text_lower for kw in self.completion_keywords)
        has_false_positive = any(kw in text_lower for kw in self.false_positive_keywords)
        
        if has_completion and not has_false_positive:
            matched_kw = next(kw for kw in self.completion_keywords if kw in text_lower)
            return True, matched_kw
        
        return False, None


class UIUXChangeDetector:
    def __init__(self):
        self.ui_patterns = [
            "*.py",
            "*.html",
            "*.css",
            "*.js",
            "*.tsx",
            "*.jsx",
            "*.vue",
            "*.svelte"
        ]
        self.ui_keywords = [
            "st.", "streamlit", "gradio", "flask", "django",
            "react", "vue", "svelte", "angular",
            "button", "input", "select", "form", "layout",
            "sidebar", "columns", "tabs", "expander",
            "metric", "chart", "plot", "table"
        ]
        self.i18n_patterns = [
            "i18n/**",
            "translations/**",
            "locales/**",
            "*.json"
        ]
    
    def is_ui_file(self, file_path: Path) -> bool:
        return any(file_path.match(p) for p in self.ui_patterns)
    
    def has_ui_changes(self, content: str) -> bool:
        return any(kw in content for kw in self.ui_keywords)
    
    def is_i18n_file(self, file_path: Path) -> bool:
        return any(file_path.match(p) for p in self.i18n_patterns)


class ComprehensiveE2ETriggerSystem:
    """
    自動觸發端到端測試系統
    
    觸發條件：
    1. 代碼變更檢測
    2. 聲稱完成前檢測
    3. 用戶請求交付時檢測
    4. 新功能添加時檢測
    5. UI/UX 變更時檢測
    6. i18n 變更時檢測
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.file_detector = FileChangeDetector(project_root)
        self.completion_detector = CompletionClaimDetector()
        self.uiux_detector = UIUXChangeDetector()
        
        self.config = {
            "watch_patterns": ["**/*.py", "**/*.json", "**/*.yaml", "**/*.yml"],
            "skip_patterns": ["**/test_*.py", "**/__pycache__/**", "**/.git/**"],
            "min_severity_for_trigger": TriggerSeverity.MEDIUM,
            "auto_run_on_critical": True
        }
        
        self.trigger_history: List[TriggerEvent] = []
        self.history_file = project_root / ".e2e_trigger_history.json"
        self._load_history()
    
    def _load_history(self):
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        event = TriggerEvent(
                            reason=TriggerReason(item["reason"]),
                            severity=TriggerSeverity(item["severity"]),
                            timestamp=datetime.fromisoformat(item["timestamp"]),
                            details=item.get("details", {}),
                            file_paths=item.get("file_paths", [])
                        )
                        self.trigger_history.append(event)
            except:
                self.trigger_history = []
    
    def _save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump([e.to_dict() for e in self.trigger_history], f, indent=2)
    
    def check_code_changes(self) -> TriggerEvent:
        added, modified, deleted = self.file_detector.detect_changes(
            self.config["watch_patterns"]
        )
        
        all_changes = added + modified + deleted
        
        if not all_changes:
            return TriggerEvent(
                reason=TriggerReason.CODE_CHANGE,
                severity=TriggerSeverity.LOW,
                timestamp=datetime.now(),
                details={"changes": 0}
            )
        
        severity = TriggerSeverity.HIGH if len(all_changes) > 5 else TriggerSeverity.MEDIUM
        
        return TriggerEvent(
            reason=TriggerReason.CODE_CHANGE,
            severity=severity,
            timestamp=datetime.now(),
            details={
                "added": len(added),
                "modified": len(modified),
                "deleted": len(deleted),
                "total_changes": len(all_changes)
            },
            file_paths=all_changes[:20]
        )
    
    def check_completion_claim(self, text: str) -> Optional[TriggerEvent]:
        is_claim, keyword = self.completion_detector.detect_completion_claim(text)
        
        if is_claim:
            return TriggerEvent(
                reason=TriggerReason.COMPLETION_CLAIM,
                severity=TriggerSeverity.CRITICAL,
                timestamp=datetime.now(),
                details={
                    "matched_keyword": keyword,
                    "text_preview": text[:200]
                }
            )
        return None
    
    def check_uiux_changes(self, file_paths: List[Path]) -> Optional[TriggerEvent]:
        ui_files = []
        i18n_files = []
        
        for fp in file_paths:
            if self.uiux_detector.is_ui_file(fp):
                try:
                    content = fp.read_text(encoding='utf-8')
                    if self.uiux_detector.has_ui_changes(content):
                        ui_files.append(str(fp.relative_to(self.project_root)))
                except:
                    pass
            
            if self.uiux_detector.is_i18n_file(fp):
                i18n_files.append(str(fp.relative_to(self.project_root)))
        
        events = []
        
        if ui_files:
            events.append(TriggerEvent(
                reason=TriggerReason.UI_UX_CHANGE,
                severity=TriggerSeverity.HIGH,
                timestamp=datetime.now(),
                details={"ui_files_count": len(ui_files)},
                file_paths=ui_files
            ))
        
        if i18n_files:
            events.append(TriggerEvent(
                reason=TriggerReason.I18N_CHANGE,
                severity=TriggerSeverity.HIGH,
                timestamp=datetime.now(),
                details={"i18n_files_count": len(i18n_files)},
                file_paths=i18n_files
            ))
        
        return events
    
    def should_trigger_e2e_test(
        self,
        completion_text: Optional[str] = None,
        changed_files: Optional[List[Path]] = None,
        is_delivery_request: bool = False,
        is_new_feature: bool = False
    ) -> TriggerResult:
        events = []
        skip_reason = None
        
        if completion_text:
            event = self.check_completion_claim(completion_text)
            if event:
                events.append(event)
        
        if is_delivery_request:
            events.append(TriggerEvent(
                reason=TriggerReason.DELIVERY_REQUEST,
                severity=TriggerSeverity.CRITICAL,
                timestamp=datetime.now()
            ))
        
        if is_new_feature:
            events.append(TriggerEvent(
                reason=TriggerReason.NEW_FEATURE,
                severity=TriggerSeverity.HIGH,
                timestamp=datetime.now()
            ))
        
        code_event = self.check_code_changes()
        if code_event.severity != TriggerSeverity.LOW:
            events.append(code_event)
        
        if changed_files:
            uiux_events = self.check_uiux_changes(changed_files)
            events.extend(uiux_events)
        
        critical_events = [e for e in events if e.severity == TriggerSeverity.CRITICAL]
        high_events = [e for e in events if e.severity == TriggerSeverity.HIGH]
        
        should_trigger = (
            len(critical_events) > 0 or
            len(high_events) > 0 or
            any(e.severity >= self.config["min_severity_for_trigger"] for e in events)
        )
        
        if should_trigger:
            for event in events:
                self.trigger_history.append(event)
            self._save_history()
        
        return TriggerResult(
            should_trigger=should_trigger,
            events=events,
            skip_reason=skip_reason
        )
    
    def get_trigger_summary(self) -> Dict[str, Any]:
        if not self.trigger_history:
            return {"total_triggers": 0}
        
        recent = [e for e in self.trigger_history if 
                  e.timestamp > datetime.now() - timedelta(hours=24)]
        
        by_reason = {}
        for event in self.trigger_history:
            reason = event.reason.value
            by_reason[reason] = by_reason.get(reason, 0) + 1
        
        return {
            "total_triggers": len(self.trigger_history),
            "recent_24h": len(recent),
            "by_reason": by_reason,
            "last_trigger": self.trigger_history[-1].timestamp.isoformat() if self.trigger_history else None
        }


def check_before_completion(text: str, project_root: Path) -> Tuple[bool, str]:
    """
    在聲稱完成前調用此函數
    
    返回：(should_run_test, message)
    """
    trigger_system = ComprehensiveE2ETriggerSystem(project_root)
    result = trigger_system.should_trigger_e2e_test(completion_text=text)
    
    if result.should_trigger:
        reasons = [e.reason.value for e in result.events]
        return True, f"⚠️ 檢測到完成聲明，必須運行端到端測試。觸發原因：{', '.join(reasons)}"
    
    return False, "✅ 無需運行端到端測試"


def check_before_delivery(project_root: Path) -> Tuple[bool, str]:
    """
    在交付給用戶前調用此函數
    
    返回：(should_run_test, message)
    """
    trigger_system = ComprehensiveE2ETriggerSystem(project_root)
    result = trigger_system.should_trigger_e2e_test(is_delivery_request=True)
    
    if result.should_trigger:
        return True, "⚠️ 交付前必須運行端到端測試"
    
    return False, "✅ 無需運行端到端測試"


if __name__ == "__main__":
    import sys
    
    project_root = Path(__file__).parent.parent.parent.parent
    
    trigger_system = ComprehensiveE2ETriggerSystem(project_root)
    
    print("=" * 60)
    print("Comprehensive E2E Testing Trigger System")
    print("=" * 60)
    
    summary = trigger_system.get_trigger_summary()
    print(f"\n📊 觸發統計：")
    print(f"  總觸發次數: {summary['total_triggers']}")
    print(f"  最近 24h: {summary.get('recent_24h', 0)}")
    if summary.get('by_reason'):
        print(f"  按原因分佈:")
        for reason, count in summary['by_reason'].items():
            print(f"    - {reason}: {count}")
    
    print("\n" + "=" * 60)
    print("測試觸發條件")
    print("=" * 60)
    
    test_texts = [
        "任務完成，已修復所有問題",
        "修復完成，可以交付給用戶",
        "正在進行中，TODO: 還需要測試",
        "這是一個普通的回覆"
    ]
    
    for text in test_texts:
        print(f"\n測試文本: 「{text[:30]}...」")
        should_trigger, message = check_before_completion(text, project_root)
        print(f"結果: {message}")
    
    print("\n" + "=" * 60)
    print("✅ ComprehensiveE2ETriggerSystem 測試完成")
    print("=" * 60)
