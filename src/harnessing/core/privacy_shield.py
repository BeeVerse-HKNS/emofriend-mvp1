#!/usr/bin/env python3
"""
PrivacyShield — 隱私保護系統

四大模組：
1. PIIDetector — 偵測個人識別信息（PII）
2. ConsentManager — 管理用戶數據處理同意
3. AnonymizationEngine — 匿名化數據同時保留效用
4. PrivacyShield — 主協調器

遵循零外部依賴原則，全部使用標準庫實現
"""

import re
import hashlib
import uuid
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from pathlib import Path


class PIIType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    HK_ID_CARD = "hk_id_card"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    NAME = "name"


class AnonymizationStrategy(Enum):
    HASHING = "hashing"
    GENERALIZATION = "generalization"
    SUPPRESSION = "suppression"
    PSEUDONYMIZATION = "pseudonymization"


class ConsentStatus(Enum):
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class TransferResult(Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    CONDITIONAL = "conditional"


class DataRegion(Enum):
    HK = "hk"
    CN = "cn"
    EU = "eu"
    US = "us"
    OTHER = "other"


@dataclass
class PIIFinding:
    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class ConsentRecord:
    user_id: str
    purpose: str
    data_types: List[str]
    status: ConsentStatus
    granted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    revoked_at: Optional[str] = None


@dataclass
class ProcessResult:
    allowed: bool
    data: Any
    pii_findings: List[PIIFinding] = field(default_factory=list)
    consent_required: bool = False
    reason: str = ""


@dataclass
class CrossBorderResult:
    transfer: TransferResult
    source_region: DataRegion
    target_region: DataRegion
    reason: str = ""
    conditions: List[str] = field(default_factory=list)


class PIIDetector:

    PATTERNS: Dict[PIIType, List[Tuple[str, float]]] = {
        PIIType.EMAIL: [
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 1.0),
        ],
        PIIType.PHONE: [
            (r'\b(\+852[-\s]?)?\d{4}[-\s]?\d{4}\b', 0.95),
            (r'\b(\+86[-\s]?)?1[3-9]\d{9}\b', 0.9),
            (r'\b\+\d{1,3}[-\s]\d{2,4}[-\s]\d{3,8}\b', 0.7),
        ],
        PIIType.HK_ID_CARD: [
            (r'\b[A-Z]{1,2}\d{6}\([\dA-Fa-f]\)', 0.95),
        ],
        PIIType.CREDIT_CARD: [
            (r'\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 0.95),
            (r'\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 0.95),
            (r'\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b', 0.9),
            (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 0.7),
        ],
        PIIType.IP_ADDRESS: [
            (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 0.9),
        ],
        PIIType.NAME: [
            (r'\b(Mr|Mrs|Ms|Miss|Dr|Prof)\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', 0.8),
            (r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b', 0.6),
        ],
    }

    def scan_text(self, text: str) -> List[PIIFinding]:
        findings = []
        for pii_type, patterns in self.PATTERNS.items():
            for pattern, confidence in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    findings.append(PIIFinding(
                        pii_type=pii_type,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=confidence,
                    ))
        findings.sort(key=lambda f: (f.start, -(f.end - f.start)))
        deduped = []
        for f in findings:
            if deduped and f.start < deduped[-1].end:
                if (f.end - f.start) > (deduped[-1].end - deduped[-1].start):
                    deduped[-1] = f
            else:
                deduped.append(f)
        return deduped

    def mask_pii(self, text: str, mask_char: str = "***") -> str:
        findings = self.scan_text(text)
        if not findings:
            return text
        result = []
        prev_end = 0
        for finding in findings:
            if finding.start >= prev_end:
                result.append(text[prev_end:finding.start])
                result.append(mask_char)
                prev_end = finding.end
        result.append(text[prev_end:])
        return "".join(result)


class ConsentManager:

    def __init__(self):
        self._consents: Dict[str, Dict[str, ConsentRecord]] = defaultdict(dict)
        self._audit_log: List[Dict[str, Any]] = []

    def grant_consent(self, user_id: str, purpose: str, data_types: List[str]) -> ConsentRecord:
        record = ConsentRecord(
            user_id=user_id,
            purpose=purpose,
            data_types=data_types,
            status=ConsentStatus.GRANTED,
        )
        self._consents[user_id][purpose] = record
        self._audit_log.append({
            "action": "grant",
            "user_id": user_id,
            "purpose": purpose,
            "data_types": data_types,
            "timestamp": datetime.now().isoformat(),
        })
        return record

    def revoke_consent(self, user_id: str, purpose: str) -> Optional[ConsentRecord]:
        if user_id in self._consents and purpose in self._consents[user_id]:
            record = self._consents[user_id][purpose]
            record.status = ConsentStatus.REVOKED
            record.revoked_at = datetime.now().isoformat()
            self._audit_log.append({
                "action": "revoke",
                "user_id": user_id,
                "purpose": purpose,
                "timestamp": datetime.now().isoformat(),
            })
            return record
        return None

    def has_consent(self, user_id: str, purpose: str, data_type: str) -> bool:
        if user_id not in self._consents:
            return False
        if purpose not in self._consents[user_id]:
            return False
        record = self._consents[user_id][purpose]
        if record.status != ConsentStatus.GRANTED:
            return False
        return data_type in record.data_types

    def get_consent_status(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self._consents:
            return {"user_id": user_id, "consents": {}}
        consents = {}
        for purpose, record in self._consents[user_id].items():
            consents[purpose] = {
                "status": record.status.value,
                "data_types": record.data_types,
                "granted_at": record.granted_at,
                "revoked_at": record.revoked_at,
            }
        return {"user_id": user_id, "consents": consents}


class AnonymizationEngine:

    def __init__(self):
        self._pseudonym_map: Dict[str, str] = {}
        self._detector = PIIDetector()

    def anonymize(self, data: Any, strategy: AnonymizationStrategy) -> Any:
        if isinstance(data, str):
            return self._anonymize_text(data, strategy)
        elif isinstance(data, dict):
            return self._anonymize_dict(data, strategy)
        elif isinstance(data, list):
            return [self.anonymize(item, strategy) for item in data]
        return data

    def is_anonymized(self, data: Any) -> bool:
        if isinstance(data, str):
            findings = self._detector.scan_text(data)
            return len(findings) == 0
        elif isinstance(data, dict):
            for value in data.values():
                if not self.is_anonymized(value):
                    return False
            return True
        elif isinstance(data, list):
            for item in data:
                if not self.is_anonymized(item):
                    return False
            return True
        return True

    def _anonymize_text(self, text: str, strategy: AnonymizationStrategy) -> str:
        findings = self._detector.scan_text(text)
        if not findings:
            return text

        if strategy == AnonymizationStrategy.SUPPRESSION:
            return self._detector.mask_pii(text, "")

        result = []
        prev_end = 0
        for finding in findings:
            if finding.start < prev_end:
                continue
            result.append(text[prev_end:finding.start])
            if strategy == AnonymizationStrategy.HASHING:
                result.append(self._hash_value(finding.value))
            elif strategy == AnonymizationStrategy.GENERALIZATION:
                result.append(self._generalize_value(finding))
            elif strategy == AnonymizationStrategy.PSEUDONYMIZATION:
                result.append(self._pseudonymize_value(finding))
            else:
                result.append("***")
            prev_end = finding.end
        result.append(text[prev_end:])
        return "".join(result)

    def _anonymize_dict(self, data: Dict, strategy: AnonymizationStrategy) -> Dict:
        result = {}
        for key, value in data.items():
            result[key] = self.anonymize(value, strategy)
        return result

    def _hash_value(self, value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    def _generalize_value(self, finding: PIIFinding) -> str:
        generalizations = {
            PIIType.EMAIL: "[email]",
            PIIType.PHONE: "[phone]",
            PIIType.HK_ID_CARD: "[hk_id]",
            PIIType.CREDIT_CARD: "[credit_card]",
            PIIType.IP_ADDRESS: "[ip_address]",
            PIIType.NAME: "[name]",
        }
        return generalizations.get(finding.pii_type, "[redacted]")

    def _pseudonymize_value(self, finding: PIIFinding) -> str:
        key = f"{finding.pii_type.value}:{finding.value}"
        if key not in self._pseudonym_map:
            self._pseudonym_map[key] = f"{finding.pii_type.value}_{uuid.uuid4().hex[:8]}"
        return self._pseudonym_map[key]


class PrivacyShield:

    ADEQUACY_DECISIONS: Dict[DataRegion, List[DataRegion]] = {
        DataRegion.EU: [DataRegion.EU, DataRegion.HK],
        DataRegion.HK: [DataRegion.HK, DataRegion.EU],
        DataRegion.CN: [DataRegion.CN],
        DataRegion.US: [DataRegion.US, DataRegion.EU],
        DataRegion.OTHER: [],
    }

    def __init__(self):
        self.detector = PIIDetector()
        self.consent_manager = ConsentManager()
        self.anonymization_engine = AnonymizationEngine()
        self._user_data_store: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._processing_log: List[Dict[str, Any]] = []

    def process_data(
        self,
        data: Any,
        user_id: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> ProcessResult:
        text = data if isinstance(data, str) else json.dumps(data, default=str)
        findings = self.detector.scan_text(text)

        if not findings:
            if user_id:
                self._user_data_store[user_id].append({
                    "data": data,
                    "purpose": purpose,
                    "timestamp": datetime.now().isoformat(),
                    "pii_found": False,
                })
            return ProcessResult(
                allowed=True,
                data=data,
                pii_findings=[],
                consent_required=False,
                reason="No PII detected",
            )

        pii_types = list(set(f.pii_type.value for f in findings))

        if user_id and purpose:
            all_consented = True
            for pii_type in pii_types:
                if not self.consent_manager.has_consent(user_id, purpose, pii_type):
                    all_consented = False
                    break

            if all_consented:
                self._user_data_store[user_id].append({
                    "data": data,
                    "purpose": purpose,
                    "timestamp": datetime.now().isoformat(),
                    "pii_found": True,
                    "pii_types": pii_types,
                })
                return ProcessResult(
                    allowed=True,
                    data=data,
                    pii_findings=findings,
                    consent_required=False,
                    reason="PII detected but consent granted",
                )
            else:
                return ProcessResult(
                    allowed=False,
                    data=None,
                    pii_findings=findings,
                    consent_required=True,
                    reason=f"PII detected ({', '.join(pii_types)}) but consent not granted for all types",
                )

        anonymized = self.anonymization_engine.anonymize(
            data, AnonymizationStrategy.GENERALIZATION
        )
        return ProcessResult(
            allowed=True,
            data=anonymized,
            pii_findings=findings,
            consent_required=True,
            reason="PII detected and anonymized (no user_id/purpose provided)",
        )

    def check_cross_border_transfer(
        self,
        data: Any,
        source_region: DataRegion,
        target_region: DataRegion,
    ) -> CrossBorderResult:
        if source_region == target_region:
            return CrossBorderResult(
                transfer=TransferResult.ALLOWED,
                source_region=source_region,
                target_region=target_region,
                reason="Same region, no transfer restrictions",
            )

        text = data if isinstance(data, str) else json.dumps(data, default=str)
        findings = self.detector.scan_text(text)

        if not findings:
            return CrossBorderResult(
                transfer=TransferResult.ALLOWED,
                source_region=source_region,
                target_region=target_region,
                reason="No PII in data, transfer allowed",
            )

        adequate_targets = self.ADEQUACY_DECISIONS.get(source_region, [])
        if target_region in adequate_targets:
            return CrossBorderResult(
                transfer=TransferResult.CONDITIONAL,
                source_region=source_region,
                target_region=target_region,
                reason="Adequacy decision exists but PII requires safeguards",
                conditions=[
                    "Encrypt data in transit and at rest",
                    "Implement data processing agreement",
                    "Notify data subjects of transfer",
                ],
            )

        return CrossBorderResult(
            transfer=TransferResult.BLOCKED,
            source_region=source_region,
            target_region=target_region,
            reason=f"No adequacy decision from {source_region.value} to {target_region.value}, PII transfer blocked",
            conditions=[
                "Require explicit consent from data subjects",
                "Implement Standard Contractual Clauses",
                "Conduct Transfer Impact Assessment",
            ],
        )

    def handle_deletion_request(self, user_id: str) -> Dict[str, Any]:
        deleted_count = 0
        if user_id in self._user_data_store:
            deleted_count = len(self._user_data_store[user_id])
            del self._user_data_store[user_id]

        if user_id in self.consent_manager._consents:
            for purpose in list(self.consent_manager._consents[user_id].keys()):
                self.consent_manager.revoke_consent(user_id, purpose)

        self._processing_log.append({
            "action": "deletion_request",
            "user_id": user_id,
            "records_deleted": deleted_count,
            "timestamp": datetime.now().isoformat(),
        })

        return {
            "user_id": user_id,
            "records_deleted": deleted_count,
            "consents_revoked": True,
            "status": "completed",
        }


def main():
    print("=" * 60)
    print("PrivacyShield 系統演示")
    print("=" * 60)

    detector = PIIDetector()

    print("\n--- PIIDetector: 掃描文本 ---")
    test_text = (
        "用戶 chan.tai.man@example.com 電話 +852-9123-4567 "
        "身份證 A123456(7) 信用卡 4111-1111-1111-1111 "
        "IP 192.168.1.100 姓名 Mr. Chan Tai Man"
    )
    findings = detector.scan_text(test_text)
    print(f"原文: {test_text}")
    print(f"偵測到 {len(findings)} 個 PII:")
    for f in findings:
        print(f"  [{f.pii_type.value}] \"{f.value}\" (位置 {f.start}-{f.end}, 信心 {f.confidence:.0%})")

    print("\n--- PIIDetector: 遮蔽 PII ---")
    masked = detector.mask_pii(test_text)
    print(f"遮蔽後: {masked}")

    consent_mgr = ConsentManager()

    print("\n--- ConsentManager: 管理同意 ---")
    consent_mgr.grant_consent("user_001", "marketing", ["email", "name"])
    consent_mgr.grant_consent("user_001", "analytics", ["email", "phone", "ip_address"])
    print(f"user_001 marketing email 同意: {consent_mgr.has_consent('user_001', 'marketing', 'email')}")
    print(f"user_001 marketing phone 同意: {consent_mgr.has_consent('user_001', 'marketing', 'phone')}")
    print(f"user_001 同意狀態: {json.dumps(consent_mgr.get_consent_status('user_001'), indent=2, ensure_ascii=False)}")

    consent_mgr.revoke_consent("user_001", "marketing")
    print(f"撤銷 marketing 後: {consent_mgr.has_consent('user_001', 'marketing', 'email')}")

    anon_engine = AnonymizationEngine()

    print("\n--- AnonymizationEngine: 四種匿名化策略 ---")
    for strategy in AnonymizationStrategy:
        result = anon_engine.anonymize(test_text, strategy)
        print(f"  {strategy.value:20s}: {result}")

    print(f"\n原文是否含 PII: {not anon_engine.is_anonymized(test_text)}")
    print(f"遮蔽後是否含 PII: {not anon_engine.is_anonymized(masked)}")

    shield = PrivacyShield()

    print("\n--- PrivacyShield: 處理數據 ---")
    result_no_consent = shield.process_data(test_text)
    print(f"無同意處理: allowed={result_no_consent.allowed}, reason={result_no_consent.reason}")
    print(f"匿名化數據: {result_no_consent.data}")

    shield.consent_manager.grant_consent("user_001", "marketing", ["email", "phone", "hk_id_card", "credit_card", "ip_address", "name"])
    result_with_consent = shield.process_data(test_text, user_id="user_001", purpose="marketing")
    print(f"\n有同意處理: allowed={result_with_consent.allowed}, reason={result_with_consent.reason}")

    shield.consent_manager.revoke_consent("user_001", "marketing")
    result_no_full_consent = shield.process_data(test_text, user_id="user_001", purpose="marketing")
    print(f"同意不足: allowed={result_no_full_consent.allowed}, consent_required={result_no_full_consent.consent_required}")

    print("\n--- PrivacyShield: 跨境傳輸檢查 ---")
    clean_data = "這是一段沒有 PII 的普通文本"
    print(f"HK→EU (無 PII): {shield.check_cross_border_transfer(clean_data, DataRegion.HK, DataRegion.EU).transfer.value}")

    hk_to_eu = shield.check_cross_border_transfer(test_text, DataRegion.HK, DataRegion.EU)
    print(f"HK→EU (有 PII): {hk_to_eu.transfer.value}, 條件: {hk_to_eu.conditions}")

    hk_to_cn = shield.check_cross_border_transfer(test_text, DataRegion.HK, DataRegion.CN)
    print(f"HK→CN (有 PII): {hk_to_cn.transfer.value}, 原因: {hk_to_cn.reason}")

    eu_to_us = shield.check_cross_border_transfer(test_text, DataRegion.EU, DataRegion.US)
    print(f"EU→US (有 PII): {eu_to_us.transfer.value}, 原因: {eu_to_us.reason}")

    print("\n--- PrivacyShield: 刪除請求 ---")
    shield.consent_manager.grant_consent("user_002", "analytics", ["email"])
    shield.process_data("test@example.com", user_id="user_002", purpose="analytics")
    deletion = shield.handle_deletion_request("user_002")
    print(f"刪除結果: {json.dumps(deletion, indent=2, ensure_ascii=False)}")

    print("\n" + "=" * 60)
    print("PrivacyShield 演示完成 ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
