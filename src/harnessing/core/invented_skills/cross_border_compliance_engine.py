"""
INV-002 CrossBorderComplianceEngine
Formula: G * S + K ^ H
Explanation: Guardrails 與 Safety 交叉 + Knowledge 放大到 Hardware 約束 = 跨境合規引擎
Target Painpoints: CLLM-004, CLLM-053, CLLM-056, CAA-004
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class Region(Enum):
    CHINA = "china"
    EU = "eu"
    US = "us"
    HK = "hong_kong"
    SG = "singapore"
    JP = "japan"
    KR = "korea"


class ComplianceLevel(Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    UNKNOWN = "unknown"


@dataclass
class ComplianceResult:
    region: Region
    regulation: str
    level: ComplianceLevel
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CrossBorderValidation:
    source_region: Region
    target_region: Region
    data_types: List[str]
    is_allowed: bool
    restrictions: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)


class PIPLComplianceChecker:
    PIPL_PATTERNS = {
        'personal_info': re.compile(r'(姓名|身份证|手机号|邮箱|地址|银行卡)', re.IGNORECASE),
        'sensitive_info': re.compile(r'(生物识别|宗教|健康|财产|行踪|通信)', re.IGNORECASE),
        'cross_border': re.compile(r'(出境|跨境|传输|transfer)', re.IGNORECASE),
    }

    def __init__(self):
        self.violations: List[str] = []

    def check_data_localization(self, data_location: str) -> ComplianceResult:
        if data_location.lower() not in ['china', 'cn', '中國', '中国']:
            return ComplianceResult(
                region=Region.CHINA,
                regulation="PIPL Article40",
                level=ComplianceLevel.VIOLATION,
                message="數據必須存儲在中國境內",
                details={'location': data_location}
            )
        return ComplianceResult(
            region=Region.CHINA,
            regulation="PIPL Article40",
            level=ComplianceLevel.COMPLIANT,
            message="數據本地化要求已滿足",
            details={'location': data_location}
        )

    def check_cross_border_transfer(self, has_security_assessment: bool, has_certification: bool) -> ComplianceResult:
        if not has_security_assessment:
            return ComplianceResult(
                region=Region.CHINA,
                regulation="PIPL Article38",
                level=ComplianceLevel.VIOLATION,
                message="跨境傳輸需要通過安全評估",
                details={'security_assessment': has_security_assessment, 'certification': has_certification}
            )
        if not has_certification:
            return ComplianceResult(
                region=Region.CHINA,
                regulation="PIPL Article38",
                level=ComplianceLevel.WARNING,
                message="建議取得個人信息保護認證",
                details={'security_assessment': has_security_assessment, 'certification': has_certification}
            )
        return ComplianceResult(
            region=Region.CHINA,
            regulation="PIPL Article38",
            level=ComplianceLevel.COMPLIANT,
            message="跨境傳輸合規",
            details={'security_assessment': has_security_assessment, 'certification': has_certification}
        )

    def check_consent(self, consent_obtained: bool, consent_type: str = "explicit") -> ComplianceResult:
        if not consent_obtained:
            return ComplianceResult(
                region=Region.CHINA,
                regulation="PIPL Article13",
                level=ComplianceLevel.VIOLATION,
                message="處理個人信息需要取得同意",
                details={'consent_obtained': consent_obtained, 'consent_type': consent_type}
            )
        return ComplianceResult(
            region=Region.CHINA,
            regulation="PIPL Article13",
            level=ComplianceLevel.COMPLIANT,
            message="已取得個人同意",
            details={'consent_obtained': consent_obtained, 'consent_type': consent_type}
        )


class GDPRComplianceChecker:
    GDPR_LAWFUL_BASES = [
        'consent',
        'contract',
        'legal_obligation',
        'vital_interests',
        'public_task',
        'legitimate_interests'
    ]

    def __init__(self):
        self.violations: List[str] = []

    def check_lawful_basis(self, basis: str) -> ComplianceResult:
        if basis.lower() not in self.GDPR_LAWFUL_BASES:
            return ComplianceResult(
                region=Region.EU,
                regulation="GDPR Article6",
                level=ComplianceLevel.VIOLATION,
                message="缺少合法處理依據",
                details={'basis': basis, 'valid_bases': self.GDPR_LAWFUL_BASES}
            )
        return ComplianceResult(
            region=Region.EU,
            regulation="GDPR Article6",
            level=ComplianceLevel.COMPLIANT,
            message=f"合法處理依據: {basis}",
            details={'basis': basis}
        )

    def check_data_subject_rights(self, rights_supported: List[str]) -> ComplianceResult:
        required_rights = ['access', 'rectification', 'erasure', 'portability']
        missing = [r for r in required_rights if r not in rights_supported]
        
        if missing:
            return ComplianceResult(
                region=Region.EU,
                regulation="GDPR Article15-20",
                level=ComplianceLevel.VIOLATION,
                message=f"缺少數據主體權利: {', '.join(missing)}",
                details={'missing_rights': missing, 'supported': rights_supported}
            )
        return ComplianceResult(
            region=Region.EU,
            regulation="GDPR Article15-20",
            level=ComplianceLevel.COMPLIANT,
            message="數據主體權利已支持",
            details={'supported': rights_supported}
        )

    def check_transfer_mechanism(self, mechanism: str, target_country: str) -> ComplianceResult:
        valid_mechanisms = ['adequacy_decision', 'sccs', 'bcrs', 'derogations']
        
        if mechanism.lower() not in valid_mechanisms:
            return ComplianceResult(
                region=Region.EU,
                regulation="GDPR ChapterV",
                level=ComplianceLevel.VIOLATION,
                message="需要有效的跨境傳輸機制",
                details={'mechanism': mechanism, 'target': target_country}
            )
        return ComplianceResult(
            region=Region.EU,
            regulation="GDPR ChapterV",
            level=ComplianceLevel.COMPLIANT,
            message=f"跨境傳輸機制: {mechanism}",
            details={'mechanism': mechanism, 'target': target_country}
        )


class CrossBorderValidator:
    RESTRICTIONS = {
        (Region.CHINA, Region.US): ['personal_info', 'sensitive_info'],
        (Region.EU, Region.CHINA): ['requires_adequacy'],
        (Region.CHINA, Region.EU): ['requires_security_assessment'],
    }

    def __init__(self):
        self.pipl_checker = PIPLComplianceChecker()
        self.gdpr_checker = GDPRComplianceChecker()

    def validate_transfer(self, source: Region, target: Region, data_types: List[str]) -> CrossBorderValidation:
        key = (source, target)
        restrictions = self.RESTRICTIONS.get(key, [])
        is_allowed = len(restrictions) == 0 or not any(dt in restrictions for dt in data_types)
        
        requirements = []
        if source == Region.CHINA and target != Region.CHINA:
            requirements.extend(['security_assessment', 'certification'])
        if source == Region.EU and target not in [Region.EU, Region.US]:
            requirements.append('adequacy_decision_or_sccs')
        
        return CrossBorderValidation(
            source_region=source,
            target_region=target,
            data_types=data_types,
            is_allowed=is_allowed,
            restrictions=restrictions,
            requirements=requirements
        )

    def get_compliance_checkers(self) -> Dict[str, Any]:
        return {
            'pipl': self.pipl_checker,
            'gdpr': self.gdpr_checker
        }


class DataLocalizationEnforcer:
    def __init__(self):
        self.localization_rules: Dict[Region, str] = {
            Region.CHINA: 'must_store_in_china',
            Region.EU: 'gdpr_storage_requirements',
            Region.HK: 'pdpo_cross_border_allowed',
        }

    def enforce(self, region: Region, current_storage: str) -> ComplianceResult:
        if region == Region.CHINA:
            if current_storage.lower() not in ['china', 'cn']:
                return ComplianceResult(
                    region=region,
                    regulation="PIPL Data Localization",
                    level=ComplianceLevel.VIOLATION,
                    message="必須強制執行數據本地化",
                    details={'current_storage': current_storage, 'required': 'china'}
                )
        return ComplianceResult(
            region=region,
            regulation="Data Localization",
            level=ComplianceLevel.COMPLIANT,
            message="數據本地化已滿足",
            details={'storage': current_storage}
        )

    def get_required_location(self, region: Region) -> Optional[str]:
        return self.localization_rules.get(region)


class CrossBorderComplianceEngine:
    """
    INV-002: CrossBorderComplianceEngine
    Formula: G * S + K ^ H
    
    處理中國 PIPL、GDPR、跨境數據傳輸合規
    """

    def __init__(self):
        self.pipl_checker = PIPLComplianceChecker()
        self.gdpr_checker = GDPRComplianceChecker()
        self.cross_border_validator = CrossBorderValidator()
        self.data_localizer = DataLocalizationEnforcer()

    def execute(self, source_region: Region, target_region: Region, data_types: List[str], **kwargs) -> Dict[str, Any]:
        results: Dict[str, Any] = {
            'timestamp': datetime.now().isoformat(),
            'source_region': source_region.value,
            'target_region': target_region.value,
            'data_types': data_types,
            'validations': [],
            'overall_compliant': True
        }

        validation = self.cross_border_validator.validate_transfer(source_region, target_region, data_types)
        results['validations'].append({
            'type': 'cross_border',
            'is_allowed': validation.is_allowed,
            'restrictions': validation.restrictions,
            'requirements': validation.requirements
        })

        if source_region == Region.CHINA:
            pipl_result = self.pipl_checker.check_data_localization(kwargs.get('storage_location', 'unknown'))
            results['validations'].append({
                'type': 'pipl_localization',
                'level': pipl_result.level.value,
                'message': pipl_result.message
            })
            if pipl_result.level == ComplianceLevel.VIOLATION:
                results['overall_compliant'] = False

        if source_region == Region.EU:
            gdpr_result = self.gdpr_checker.check_lawful_basis(kwargs.get('lawful_basis', 'none'))
            results['validations'].append({
                'type': 'gdpr_lawful_basis',
                'level': gdpr_result.level.value,
                'message': gdpr_result.message
            })
            if gdpr_result.level == ComplianceLevel.VIOLATION:
                results['overall_compliant'] = False

        return results

    def check_pipl_compliance(self, **kwargs) -> List[ComplianceResult]:
        results = []
        
        if 'storage_location' in kwargs:
            results.append(self.pipl_checker.check_data_localization(kwargs['storage_location']))
        if 'has_security_assessment' in kwargs:
            results.append(self.pipl_checker.check_cross_border_transfer(
                kwargs.get('has_security_assessment', False),
                kwargs.get('has_certification', False)
            ))
        if 'consent_obtained' in kwargs:
            results.append(self.pipl_checker.check_consent(
                kwargs['consent_obtained'],
                kwargs.get('consent_type', 'explicit')
            ))
        
        return results

    def check_gdpr_compliance(self, **kwargs) -> List[ComplianceResult]:
        results = []
        
        if 'lawful_basis' in kwargs:
            results.append(self.gdpr_checker.check_lawful_basis(kwargs['lawful_basis']))
        if 'rights_supported' in kwargs:
            results.append(self.gdpr_checker.check_data_subject_rights(kwargs['rights_supported']))
        if 'transfer_mechanism' in kwargs:
            results.append(self.gdpr_checker.check_transfer_mechanism(
                kwargs['transfer_mechanism'],
                kwargs.get('target_country', 'unknown')
            ))
        
        return results


if __name__ == "__main__":
    engine = CrossBorderComplianceEngine()
    
    print("=== Test 1: China to US Transfer ===")
    result1 = engine.execute(
        source_region=Region.CHINA,
        target_region=Region.US,
        data_types=['personal_info'],
        storage_location='china',
        has_security_assessment=True,
        has_certification=True
    )
    print(json.dumps(result1, indent=2, ensure_ascii=False))
    
    print("\n=== Test 2: PIPL Compliance Check ===")
    pipl_results = engine.check_pipl_compliance(
        storage_location='us',
        has_security_assessment=False,
        has_certification=False,
        consent_obtained=True
    )
    for r in pipl_results:
        print(f"  [{r.level.value}] {r.regulation}: {r.message}")
    
    print("\n=== Test 3: GDPR Compliance Check ===")
    gdpr_results = engine.check_gdpr_compliance(
        lawful_basis='consent',
        rights_supported=['access', 'rectification', 'erasure', 'portability'],
        transfer_mechanism='sccs',
        target_country='china'
    )
    for r in gdpr_results:
        print(f"  [{r.level.value}] {r.regulation}: {r.message}")
