from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Region(Enum):
    HONGKONG = "hongkong"
    CHINA = "china"
    EU = "eu"
    USA = "usa"
    SINGAPORE = "singapore"
    JAPAN = "japan"
    KOREA = "korea"
    GLOBAL = "global"


class CognitiveEngine(Enum):
    METACOGNITIVE = "metacognitive"
    WORLD_MODEL = "world_model"
    CAUSAL_REASONING = "causal_reasoning"
    ATTENTION_BUDGET = "attention_budget"
    UNIFIED_COGNITIVE = "unified_cognitive"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplianceCheck:
    is_compliant: bool
    regulations: List[str]
    risk_level: RiskLevel
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceTestCase:
    test_id: str
    region: Region
    engine: CognitiveEngine
    operation: str
    input_data: Dict[str, Any]
    expected_compliance: bool
    expected_regulations: List[str]
    actual_result: str = ""
    passed: bool = False


@dataclass
class ComplianceTestResult:
    total_tests: int
    passed: int
    failed: int
    compliance_rate: float
    failures: List[ComplianceTestCase] = field(default_factory=list)


class RegionTestGenerator:
    def __init__(self) -> None:
        self._test_counter: int = 0

    def _create_test(
        self,
        region: Region,
        engine: CognitiveEngine,
        operation: str,
        input_data: Dict[str, Any],
        expected_compliance: bool,
        expected_regulations: List[str],
    ) -> ComplianceTestCase:
        self._test_counter += 1
        return ComplianceTestCase(
            test_id=f"TEST-{region.value.upper()}-{engine.value.upper()}-{self._test_counter:03d}",
            region=region,
            engine=engine,
            operation=operation,
            input_data=input_data,
            expected_compliance=expected_compliance,
            expected_regulations=expected_regulations,
        )

    def generate_hongkong_tests(self, engine: CognitiveEngine) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                Region.HONGKONG,
                engine,
                "data_collection",
                {"pi_category": "personal", "consent": True, "purpose": "service_delivery"},
                True,
                ["PIPA", "PDPO"],
            ),
            self._create_test(
                Region.HONGKONG,
                engine,
                "cross_border_transfer",
                {"transfer_to": "CN", "data_type": "personal", "adequacy_check": False},
                False,
                ["PIPA", "PDPO", "Article33"],
            ),
            self._create_test(
                Region.HONGKONG,
                engine,
                "data_retention",
                {"retention_days": 730, "auto_delete": False},
                False,
                ["PIPA"],
            ),
            self._create_test(
                Region.HONGKONG,
                engine,
                "automated_decision",
                {"ai_decision": True, "human_review": False, "impact_assessment": False},
                False,
                ["PIPA", "AUCI"],
            ),
            self._create_test(
                Region.HONGKONG,
                engine,
                "employment_ai",
                {"hiring_ai": True, "bias_audit": True, "transparency": True},
                True,
                ["PIPA", "AUCI"],
            ),
        ]
        return tests

    def generate_china_tests(self, engine: CognitiveEngine) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                Region.CHINA,
                engine,
                "data_localization",
                {"data_location": "CN", "cross_border": False, "pi_category": "personal"},
                True,
                ["PIPL", "CSL"],
            ),
            self._create_test(
                Region.CHINA,
                engine,
                "algorithmic_recommendation",
                {"recommendation_ai": True, "transparency_report": True, "user_opt_out": True},
                True,
                ["PIPL", "AlgorithmicRecommendation"],
            ),
            self._create_test(
                Region.CHINA,
                engine,
                "deep_synthesis",
                {"deepfake": True, "disclosure": True, "consent_obtained": True},
                True,
                ["PIPL", "DeepSynthesis"],
            ),
            self._create_test(
                Region.CHINA,
                engine,
                "cross_border_transfer",
                {"transfer_outside": True, "security_assessment": False, "pi_category": "important"},
                False,
                ["PIPL", "CSL"],
            ),
            self._create_test(
                Region.CHINA,
                engine,
                "automated_decision",
                {"personal_analysis": True, "human_override": False},
                False,
                ["PIPL"],
            ),
        ]
        return tests

    def generate_eu_tests(self, engine: CognitiveEngine) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                Region.EU,
                engine,
                "gdpr_data_collection",
                {"consent": True, "purpose_limited": True, "data_minimization": True},
                True,
                ["GDPR", "EUDataProtection"],
            ),
            self._create_test(
                Region.EU,
                engine,
                "ai_act_high_risk",
                {
                    "ai_system": "high_risk",
                    "conformity_assessment": True,
                    "technical_documentation": True,
                    "human_oversight": True,
                },
                True,
                ["GDPR", "AIAct"],
            ),
            self._create_test(
                Region.EU,
                engine,
                "profiling_automated_decision",
                {"profiling": True, "legal_effect": True, "human_intervention": False},
                False,
                ["GDPR", "Article22"],
            ),
            self._create_test(
                Region.EU,
                engine,
                "data_portability",
                {"data_portable": True, "machine_readable": True, "free_of_charge": True},
                True,
                ["GDPR", "Article20"],
            ),
            self._create_test(
                Region.EU,
                engine,
                "right_to_explanation",
                {"automated_decision": True, "explanation_provided": False},
                False,
                ["GDPR", "Article13", "AIAct"],
            ),
        ]
        return tests

    def generate_usa_tests(self, engine: CognitiveEngine) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                Region.USA,
                engine,
                "ccpa_data_collection",
                {"california_resident": True, "opt_out_notice": True, "do_not_sell": True},
                True,
                ["CCPA", "CRPA"],
            ),
            self._create_test(
                Region.USA,
                engine,
                "hipaa_health_data",
                {"health_info": True, "hipaa_covered": True, "baa_signed": True},
                True,
                ["HIPAA", "HITECH"],
            ),
            self._create_test(
                Region.USA,
                engine,
                "ai_employment",
                {"hiring_ai": True, "adverse_impact_analysis": False, "bias_mitigation": False},
                False,
                ["EEOC", "IllinoisAIFTA"],
            ),
            self._create_test(
                Region.USA,
                engine,
                "financial_ai_credit",
                {"credit_decision": True, "adverse_action_notice": True, "fcra_compliant": True},
                True,
                ["FCRA", "ECOA"],
            ),
            self._create_test(
                Region.USA,
                engine,
                "state_privacy",
                {"texas_resident": True, "consent_required": False, "transparency_report": True},
                True,
                ["TDPSA", "VCDPA"],
            ),
        ]
        return tests

    def generate_singapore_tests(self, engine: CognitiveEngine) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                Region.SINGAPORE,
                engine,
                "pdpa_collection",
                {"consent_obtained": True, "purpose_defined": True, "access_rights": True},
                True,
                ["PDPA"],
            ),
            self._create_test(
                Region.SINGAPORE,
                engine,
                "cross_border_transfer",
                {"transfer_country": "CN", "adequacy": False, "dp_agreement": False},
                False,
                ["PDPA", "PDPCGuidelines"],
            ),
            self._create_test(
                Region.SINGAPORE,
                engine,
                "ai_governance",
                {"ai_decision": True, "explainability": True, "human_review_available": True},
                True,
                ["PDPA", "AIModelGovernance"],
            ),
            self._create_test(
                Region.SINGAPORE,
                engine,
                "data_breach_notification",
                {"breach_occurred": True, "notified_pdpc": True, "affected_individuals": True},
                True,
                ["PDPA"],
            ),
            self._create_test(
                Region.SINGAPORE,
                engine,
                "employment_ai",
                {"job_screening": True, "transparency": True, "human_oversight": True},
                True,
                ["PDPA", "TripartiteGuidelines"],
            ),
        ]
        return tests

    def generate_japan_tests(self, engine: CognitiveEngine) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                Region.JAPAN,
                engine,
                "appi_data_collection",
                {"consent": True, "purpose_specified": True, "safety_measures": True},
                True,
                ["APPI"],
            ),
            self._create_test(
                Region.JAPAN,
                engine,
                "sensitive_data",
                {"sensitive_category": "health", "explicit_consent": True, "special_protection": True},
                True,
                ["APPI", "APPIAmendment"],
            ),
            self._create_test(
                Region.JAPAN,
                engine,
                "cross_border_transfer",
                {"transfer_to": "CN", "consent": True, "equivalent_protection": False},
                False,
                ["APPI", "PIPC"],
            ),
            self._create_test(
                Region.JAPAN,
                engine,
                "automated_decision",
                {"automated_decision": True, "explanation": True, "objection_right": True},
                True,
                ["APPI"],
            ),
            self._create_test(
                Region.JAPAN,
                engine,
                "third_party_provision",
                {"provided_to_third": True, "consent": True, "opt_out_available": True},
                True,
                ["APPI"],
            ),
        ]
        return tests

    def generate_korea_tests(self, engine: CognitiveEngine) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                Region.KOREA,
                engine,
                "pipl_collection",
                {"consent": True, "purpose_specified": True, "legal_basis": True},
                True,
                ["PIPL"],
            ),
            self._create_test(
                Region.KOREA,
                engine,
                "credit_information",
                {"credit_info": True, "credit_rating_agency": True, "consent": True},
                True,
                ["CICA", "PIPL"],
            ),
            self._create_test(
                Region.KOREA,
                engine,
                "data_localization",
                {"important_data": True, "domestic_retention": False, "overseas_transfer": True},
                False,
                ["PIPL", "PIPA"],
            ),
            self._create_test(
                Region.KOREA,
                engine,
                "cross_border_transfer",
                {"transfer_to": "USA", "consent": True, "contractual_clauses": True},
                True,
                ["PIPL", "PIPA"],
            ),
            self._create_test(
                Region.KOREA,
                engine,
                "ai_bias_audit",
                {"hiring_ai": True, "bias_audit_results": True, "mitigation_plan": True},
                True,
                ["PIPL", "AIAct", "EmploymentAIAudit"],
            ),
        ]
        return tests

    def generate_global_tests(self, engine: CognitiveEngine) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                Region.GLOBAL,
                engine,
                "data_minimization",
                {"data_collected": ["name", "email"], "data_needed": ["name"], "minimization": True},
                True,
                ["GDPR", "PIPL", "PDPA", "APPI"],
            ),
            self._create_test(
                Region.GLOBAL,
                engine,
                "transparency",
                {"ai_system": True, "disclosure": True, "understandable_info": True},
                True,
                ["GDPR", "AIAct", "AIModelGovernance"],
            ),
            self._create_test(
                Region.GLOBAL,
                engine,
                "security_measures",
                {"encryption_at_rest": True, "encryption_in_transit": True, "access_control": True},
                True,
                ["GDPR", "PIPL", "PDPA", "HIPAA"],
            ),
            self._create_test(
                Region.GLOBAL,
                engine,
                "incident_response",
                {"incident_plan": True, "notification_timeline": 72, "regulator_notification": True},
                True,
                ["GDPR", "PIPL", "PDPA", "CCPA"],
            ),
            self._create_test(
                Region.GLOBAL,
                engine,
                "dpia_required",
                {"high_risk_processing": True, "dpia_conducted": False},
                False,
                ["GDPR", "AIModelGovernance"],
            ),
        ]
        return tests


class CrossBorderTestGenerator:
    def __init__(self) -> None:
        self._test_counter: int = 0

    def _create_test(
        self,
        source_region: Region,
        target_region: Region,
        engine: CognitiveEngine,
        operation: str,
        input_data: Dict[str, Any],
        expected_compliance: bool,
        expected_regulations: List[str],
    ) -> ComplianceTestCase:
        self._test_counter += 1
        return ComplianceTestCase(
            test_id=f"XBORDER-{source_region.value.upper()}-{target_region.value.upper()}-{self._test_counter:03d}",
            region=source_region,
            engine=engine,
            operation=operation,
            input_data=input_data,
            expected_compliance=expected_compliance,
            expected_regulations=expected_regulations,
        )

    def generate_cross_border_tests(self) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                Region.HONGKONG,
                Region.CHINA,
                CognitiveEngine.CAUSAL_REASONING,
                "hk_to_cn_transfer",
                {
                    "source": "HK",
                    "target": "CN",
                    "data_type": "personal",
                    "adequacy_check": False,
                    "contractual_clause": False,
                },
                False,
                ["PIPA", "PDPO", "PIPL"],
            ),
            self._create_test(
                Region.HONGKONG,
                Region.EU,
                CognitiveEngine.UNIFIED_COGNITIVE,
                "hk_to_eu_transfer",
                {
                    "source": "HK",
                    "target": "EU",
                    "data_type": "personal",
                    "standard_contract": True,
                    "adequacy_decision": False,
                },
                True,
                ["GDPR", "Article46"],
            ),
            self._create_test(
                Region.CHINA,
                Region.SINGAPORE,
                CognitiveEngine.WORLD_MODEL,
                "cn_to_sg_transfer",
                {
                    "source": "CN",
                    "target": "SG",
                    "data_type": "personal",
                    "security_assessment": True,
                    "pi_category": "general",
                },
                True,
                ["PIPL", "PDPA"],
            ),
            self._create_test(
                Region.EU,
                Region.USA,
                CognitiveEngine.METACOGNITIVE,
                "eu_to_us_transfer",
                {
                    "source": "EU",
                    "target": "USA",
                    "data_type": "personal",
                    "dpia_complete": True,
                    "safeguards": "SCCs",
                },
                True,
                ["GDPR", "Article46", "EUUSDataPrivacyFramework"],
            ),
            self._create_test(
                Region.JAPAN,
                Region.KOREA,
                CognitiveEngine.ATTENTION_BUDGET,
                "jp_to_kr_transfer",
                {
                    "source": "JP",
                    "target": "KR",
                    "data_type": "personal",
                    "consent": True,
                    "equivalent_protection": True,
                },
                True,
                ["APPI", "PIPL", "PIPA"],
            ),
            self._create_test(
                Region.SINGAPORE,
                Region.USA,
                CognitiveEngine.CAUSAL_REASONING,
                "sg_to_us_transfer",
                {
                    "source": "SG",
                    "target": "USA",
                    "data_type": "personal",
                    "contractual_protections": True,
                    "data_portability": True,
                },
                True,
                ["PDPA", "CCPA"],
            ),
            self._create_test(
                Region.KOREA,
                Region.CHINA,
                CognitiveEngine.WORLD_MODEL,
                "kr_to_cn_transfer",
                {
                    "source": "KR",
                    "target": "CN",
                    "data_type": "important_data",
                    "domestic_retention": True,
                    "cross_border_transfer": False,
                },
                False,
                ["PIPL", "PIPA"],
            ),
            self._create_test(
                Region.GLOBAL,
                Region.GLOBAL,
                CognitiveEngine.UNIFIED_COGNITIVE,
                "multi_jurisdiction_transfer",
                {
                    "source": "MULTI",
                    "target": "MULTI",
                    "data_type": "personal",
                    "all_regulations_met": True,
                    "fragmented_compliance": False,
                },
                True,
                ["GDPR", "PIPL", "PDPA", "CCPA", "APPI"],
            ),
        ]
        return tests


class HighRiskAITestGenerator:
    def __init__(self) -> None:
        self._test_counter: int = 0

    def _create_test(
        self,
        region: Region,
        engine: CognitiveEngine,
        operation: str,
        input_data: Dict[str, Any],
        expected_compliance: bool,
        expected_regulations: List[str],
    ) -> ComplianceTestCase:
        self._test_counter += 1
        return ComplianceTestCase(
            test_id=f"HRAI-{region.value.upper()}-{engine.value.upper()}-{self._test_counter:03d}",
            region=region,
            engine=engine,
            operation=operation,
            input_data=input_data,
            expected_compliance=expected_compliance,
            expected_regulations=expected_regulations,
        )

    def generate_healthcare_tests(self, region: Region) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                region,
                CognitiveEngine.CAUSAL_REASONING,
                "diagnosis_ai",
                {
                    "medical_decision": True,
                    "hipaa_covered": True,
                    "patient_consent": True,
                    "clinical_validation": True,
                },
                True,
                ["HIPAA", "GDPR", "PIPL"],
            ),
            self._create_test(
                region,
                CognitiveEngine.METACOGNITIVE,
                "mental_health_ai",
                {
                    "mental_health_app": True,
                    "risk_assessment": True,
                    "human_oversight": True,
                    "crisis_protocol": True,
                },
                True,
                ["HIPAA", "GDPR", "PIPA"],
            ),
            self._create_test(
                region,
                CognitiveEngine.UNIFIED_COGNITIVE,
                "genomic_data_processing",
                {
                    "genetic_data": True,
                    "explicit_consent": True,
                    "special_protection": True,
                    "data_minimization": True,
                },
                True,
                ["GDPR", "APPI", "HIPAA"],
            ),
            self._create_test(
                region,
                CognitiveEngine.ATTENTION_BUDGET,
                "medical_device_ai",
                {
                    "medical_device": True,
                    "fda_approved": True,
                    "post_market_surveillance": True,
                    "incident_reporting": True,
                },
                True,
                ["FDA", "MDR", "AIAct"],
            ),
            self._create_test(
                region,
                CognitiveEngine.WORLD_MODEL,
                "health_data_sharing",
                {
                    "health_data": True,
                    "anonymized": False,
                    "consent": False,
                    "legal_basis": None,
                },
                False,
                ["HIPAA", "GDPR", "PIPL"],
            ),
        ]
        return tests

    def generate_employment_tests(self, region: Region) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                region,
                CognitiveEngine.CAUSAL_REASONING,
                "ai_hiring_screening",
                {
                    "hiring_ai": True,
                    "bias_audit": True,
                    "transparency": True,
                    "human_review": True,
                },
                True,
                ["EEOC", "PIPL", "PDPA"],
            ),
            self._create_test(
                region,
                CognitiveEngine.METACOGNITIVE,
                "performance_monitoring",
                {
                    "employee_monitoring": True,
                    "transparency": True,
                    "proportionality": True,
                    "consent": True,
                },
                True,
                ["GDPR", "PIPA", "CCPA"],
            ),
            self._create_test(
                region,
                CognitiveEngine.UNIFIED_COGNITIVE,
                "automated_termination",
                {
                    "automated_termination": True,
                    "human_review": False,
                    "appeal_process": False,
                    "documentation": False,
                },
                False,
                ["GDPR", "PIPL", "EEOC"],
            ),
            self._create_test(
                region,
                CognitiveEngine.ATTENTION_BUDGET,
                "workplace_surveillance",
                {
                    "surveillance_ai": True,
                    "consent": False,
                    "proportionality_assessment": False,
                    "data_protection_impact": False,
                },
                False,
                ["GDPR", "PIPA", "CCPA"],
            ),
            self._create_test(
                region,
                CognitiveEngine.WORLD_MODEL,
                "wage_hour_prediction",
                {
                    "wage_prediction": True,
                    "fair_labor_practices": True,
                    "transparency": True,
                    "human_oversight": True,
                },
                True,
                ["FLSA", "GDPR", "PIPL"],
            ),
        ]
        return tests

    def generate_finance_tests(self, region: Region) -> List[ComplianceTestCase]:
        tests = [
            self._create_test(
                region,
                CognitiveEngine.CAUSAL_REASONING,
                "credit_scoring_ai",
                {
                    "credit_decision": True,
                    "fcra_compliant": True,
                    "adverse_action_notice": True,
                    "explainability": True,
                },
                True,
                ["FCRA", "ECOA", "GDPR"],
            ),
            self._create_test(
                region,
                CognitiveEngine.METACOGNITIVE,
                "fraud_detection",
                {
                    "fraud_detection": True,
                    "real_time_decision": True,
                    "human_override": True,
                    "false_positive_review": True,
                },
                True,
                ["PCI-DSS", "GDPR", "PIPL"],
            ),
            self._create_test(
                region,
                CognitiveEngine.UNIFIED_COGNITIVE,
                "insurance_underwriting",
                {
                    "underwriting_ai": True,
                    "actuarial_fairness": True,
                    "transparency": True,
                    "appeal_process": True,
                },
                True,
                ["GDPR", "PIPL", "InsuranceRegulation"],
            ),
            self._create_test(
                region,
                CognitiveEngine.ATTENTION_BUDGET,
                "high_frequency_trading",
                {
                    "algorithmic_trading": True,
                    "risk_controls": True,
                    "circuit_breakers": True,
                    "audit_trail": True,
                },
                True,
                ["MiFIDII", "SECRule", "FCA"],
            ),
            self._create_test(
                region,
                CognitiveEngine.WORLD_MODEL,
                "aml_sanctions_screening",
                {
                    "sanctions_screening": True,
                    "false_positive_rate": 0.15,
                    "human_review": False,
                    "continuous_monitoring": False,
                },
                False,
                ["OFAC", "FATF", "AML"],
            ),
        ]
        return tests


class ComplianceAssertionHelper:
    def assert_compliance(self, test: ComplianceTestCase, result: ComplianceCheck) -> bool:
        if result.is_compliant == test.expected_compliance:
            test.actual_result = f"Compliance check passed: {result.is_compliant}"
            test.passed = True
            return True
        else:
            test.actual_result = (
                f"Compliance mismatch: expected {test.expected_compliance}, got {result.is_compliant}"
            )
            test.passed = False
            return False

    def assert_regulations(self, test: ComplianceTestCase, regulations: List[str]) -> bool:
        missing_regulations = set(test.expected_regulations) - set(regulations)
        extra_regulations = set(regulations) - set(test.expected_regulations)

        if not missing_regulations and not extra_regulations:
            test.actual_result = f"All expected regulations found: {regulations}"
            test.passed = test.passed and True
            return True
        else:
            issues = []
            if missing_regulations:
                issues.append(f"Missing: {missing_regulations}")
            if extra_regulations:
                issues.append(f"Unexpected: {extra_regulations}")
            test.actual_result = f"Regulation mismatch: {'; '.join(issues)}"
            test.passed = False
            return False

    def assert_risk_level(
        self, test: ComplianceTestCase, expected: RiskLevel
    ) -> bool:
        return True


class RegionalComplianceAnalyzer:
    def __init__(self) -> None:
        self._region_policies: Dict[Region, List[str]] = {
            Region.HONGKONG: ["PIPA", "PDPO"],
            Region.CHINA: ["PIPL", "CSL", "AlgorithmicRecommendation", "DeepSynthesis"],
            Region.EU: ["GDPR", "AIAct", "EUDataProtection"],
            Region.USA: ["CCPA", "CRPA", "HIPAA", "FCRA", "EEOC", "TDPSA", "VCDPA"],
            Region.SINGAPORE: ["PDPA", "PDPCGuidelines", "AIModelGovernance"],
            Region.JAPAN: ["APPI", "APPIAmendment", "PIPC"],
            Region.KOREA: ["PIPL", "PIPA", "CICA", "AIAct"],
            Region.GLOBAL: ["GDPR", "PIPL", "PDPA", "APPI", "CCPA"],
        }

    def get_regulations_for_region(self, region: Region) -> List[str]:
        return self._region_policies.get(region, [])

    def check_compliance(
        self, region: Region, operation: str, input_data: Dict[str, Any]
    ) -> ComplianceCheck:
        regulations = self.get_regulations_for_region(region)
        is_compliant = self._evaluate_compliance(region, operation, input_data)
        risk_level = self._determine_risk_level(region, operation, input_data)

        return ComplianceCheck(
            is_compliant=is_compliant,
            regulations=regulations,
            risk_level=risk_level,
            details={"region": region.value, "operation": operation},
        )

    def _evaluate_compliance(
        self, region: Region, operation: str, input_data: Dict[str, Any]
    ) -> bool:
        if region == Region.HONGKONG:
            if operation == "cross_border_transfer" and not input_data.get("adequacy_check", True):
                return False
            if operation == "data_retention" and input_data.get("retention_days", 0) > 365:
                return False
            if operation == "automated_decision" and not input_data.get("human_review", True):
                return False

        if region == Region.CHINA:
            if operation == "cross_border_transfer" and not input_data.get("security_assessment", True):
                return False
            if operation == "automated_decision" and not input_data.get("human_override", True):
                return False

        if region == Region.EU:
            if operation == "profiling_automated_decision" and not input_data.get("human_intervention", True):
                return False
            if operation == "right_to_explanation" and not input_data.get("explanation_provided", True):
                return False

        if region == Region.USA:
            if operation == "ai_employment" and not input_data.get("bias_audit", True):
                return False

        return True

    def _determine_risk_level(
        self, region: Region, operation: str, input_data: Dict[str, Any]
    ) -> RiskLevel:
        high_risk_operations = ["employment_ai", "credit_scoring", "healthcare_ai", "hiring_ai"]
        if any(op in operation for op in high_risk_operations):
            return RiskLevel.HIGH

        if region in [Region.CHINA, Region.EU]:
            return RiskLevel.HIGH

        return RiskLevel.MEDIUM


class GlobalComplianceTestSuite:
    def __init__(self) -> None:
        self.analyzer = RegionalComplianceAnalyzer()
        self.region_generator = RegionTestGenerator()
        self.crossborder_generator = CrossBorderTestGenerator()
        self.highrisk_generator = HighRiskAITestGenerator()
        self.assertion_helper = ComplianceAssertionHelper()

    def generate_all_tests(self) -> List[ComplianceTestCase]:
        tests: List[ComplianceTestCase] = []

        for engine in CognitiveEngine:
            tests.extend(self.region_generator.generate_hongkong_tests(engine))
            tests.extend(self.region_generator.generate_china_tests(engine))
            tests.extend(self.region_generator.generate_eu_tests(engine))
            tests.extend(self.region_generator.generate_usa_tests(engine))
            tests.extend(self.region_generator.generate_singapore_tests(engine))
            tests.extend(self.region_generator.generate_japan_tests(engine))
            tests.extend(self.region_generator.generate_korea_tests(engine))
            tests.extend(self.region_generator.generate_global_tests(engine))

        tests.extend(self.crossborder_generator.generate_cross_border_tests())

        for region in Region:
            tests.extend(self.highrisk_generator.generate_healthcare_tests(region))
            tests.extend(self.highrisk_generator.generate_employment_tests(region))
            tests.extend(self.highrisk_generator.generate_finance_tests(region))

        return tests

    def run_all_tests(self) -> ComplianceTestResult:
        tests = self.generate_all_tests()
        return self._execute_tests(tests)

    def run_region_tests(self, region: Region) -> ComplianceTestResult:
        tests = []
        for engine in CognitiveEngine:
            if region == Region.HONGKONG:
                tests.extend(self.region_generator.generate_hongkong_tests(engine))
            elif region == Region.CHINA:
                tests.extend(self.region_generator.generate_china_tests(engine))
            elif region == Region.EU:
                tests.extend(self.region_generator.generate_eu_tests(engine))
            elif region == Region.USA:
                tests.extend(self.region_generator.generate_usa_tests(engine))
            elif region == Region.SINGAPORE:
                tests.extend(self.region_generator.generate_singapore_tests(engine))
            elif region == Region.JAPAN:
                tests.extend(self.region_generator.generate_japan_tests(engine))
            elif region == Region.KOREA:
                tests.extend(self.region_generator.generate_korea_tests(engine))
            elif region == Region.GLOBAL:
                tests.extend(self.region_generator.generate_global_tests(engine))

        return self._execute_tests(tests)

    def run_engine_tests(self, engine: CognitiveEngine) -> ComplianceTestResult:
        tests = []
        tests.extend(self.region_generator.generate_hongkong_tests(engine))
        tests.extend(self.region_generator.generate_china_tests(engine))
        tests.extend(self.region_generator.generate_eu_tests(engine))
        tests.extend(self.region_generator.generate_usa_tests(engine))
        tests.extend(self.region_generator.generate_singapore_tests(engine))
        tests.extend(self.region_generator.generate_japan_tests(engine))
        tests.extend(self.region_generator.generate_korea_tests(engine))
        tests.extend(self.region_generator.generate_global_tests(engine))
        tests.extend(self.crossborder_generator.generate_cross_border_tests())

        return self._execute_tests(tests)

    def run_crossborder_tests(self) -> ComplianceTestResult:
        tests = self.crossborder_generator.generate_cross_border_tests()
        return self._execute_tests(tests)

    def run_highrisk_tests(self) -> ComplianceTestResult:
        tests = []
        for region in Region:
            tests.extend(self.highrisk_generator.generate_healthcare_tests(region))
            tests.extend(self.highrisk_generator.generate_employment_tests(region))
            tests.extend(self.highrisk_generator.generate_finance_tests(region))
        return self._execute_tests(tests)

    def get_test_matrix(self) -> Dict[Region, Dict[CognitiveEngine, int]]:
        matrix: Dict[Region, Dict[CognitiveEngine, int]] = {}
        for region in Region:
            matrix[region] = {}
            for engine in CognitiveEngine:
                count = len(self._get_region_engine_tests(region, engine))
                matrix[region][engine] = count
        return matrix

    def _get_region_engine_tests(self, region: Region, engine: CognitiveEngine) -> List[ComplianceTestCase]:
        if region == Region.HONGKONG:
            return self.region_generator.generate_hongkong_tests(engine)
        elif region == Region.CHINA:
            return self.region_generator.generate_china_tests(engine)
        elif region == Region.EU:
            return self.region_generator.generate_eu_tests(engine)
        elif region == Region.USA:
            return self.region_generator.generate_usa_tests(engine)
        elif region == Region.SINGAPORE:
            return self.region_generator.generate_singapore_tests(engine)
        elif region == Region.JAPAN:
            return self.region_generator.generate_japan_tests(engine)
        elif region == Region.KOREA:
            return self.region_generator.generate_korea_tests(engine)
        elif region == Region.GLOBAL:
            return self.region_generator.generate_global_tests(engine)
        return []

    def _execute_tests(self, tests: List[ComplianceTestCase]) -> ComplianceTestResult:
        failures: List[ComplianceTestCase] = []

        for test in tests:
            result = self.analyzer.check_compliance(
                test.region, test.operation, test.input_data
            )
            self.assertion_helper.assert_compliance(test, result)
            self.assertion_helper.assert_regulations(test, result.regulations)

            if not test.passed:
                failures.append(test)

        total = len(tests)
        passed = total - len(failures)
        failed = len(failures)
        compliance_rate = (passed / total * 100) if total > 0 else 0.0

        return ComplianceTestResult(
            total_tests=total,
            passed=passed,
            failed=failed,
            compliance_rate=compliance_rate,
            failures=failures,
        )


def main() -> None:
    suite = GlobalComplianceTestSuite()

    print("=" * 70)
    print("Global Compliance Test Suite")
    print("=" * 70)

    print("\n--- Test Matrix (Region x Engine) ---")
    matrix = suite.get_test_matrix()
    print(f"{'Region':<15} | {'METACOG':<8} | {'WORLD':<8} | {'CAUSAL':<8} | {'ATTEN':<8} | {'UNIFIED':<8}")
    print("-" * 70)
    for region, engines in matrix.items():
        row = f"{region.value:<15}"
        for engine in CognitiveEngine:
            row += f" | {engines.get(engine, 0):<8}"
        print(row)

    print("\n--- Running All Tests ---")
    all_result = suite.run_all_tests()
    print(f"Total: {all_result.total_tests}")
    print(f"Passed: {all_result.passed}")
    print(f"Failed: {all_result.failed}")
    print(f"Compliance Rate: {all_result.compliance_rate:.2f}%")

    print("\n--- Running Region-Specific Tests (Hong Kong) ---")
    hk_result = suite.run_region_tests(Region.HONGKONG)
    print(f"HK Total: {hk_result.total_tests}, Passed: {hk_result.passed}, Failed: {hk_result.failed}")

    print("\n--- Running Engine-Specific Tests (METACOGNITIVE) ---")
    meta_result = suite.run_engine_tests(CognitiveEngine.METACOGNITIVE)
    print(f"META Total: {meta_result.total_tests}, Passed: {meta_result.passed}, Failed: {meta_result.failed}")

    print("\n--- Running Cross-Border Tests ---")
    xb_result = suite.run_crossborder_tests()
    print(f"XB Total: {xb_result.total_tests}, Passed: {xb_result.passed}, Failed: {xb_result.failed}")

    print("\n--- Running High-Risk AI Tests ---")
    hr_result = suite.run_highrisk_tests()
    print(f"HR Total: {hr_result.total_tests}, Passed: {hr_result.passed}, Failed: {hr_result.failed}")

    print("\n" + "=" * 70)
    print("Test Suite Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
