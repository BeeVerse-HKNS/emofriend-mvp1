from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Region(Enum):
    HONG_KONG = "hong_kong"
    CHINA = "china"
    EU = "eu"
    USA = "usa"
    SINGAPORE = "singapore"
    JAPAN = "japan"
    KOREA = "korea"
    GLOBAL = "global"


class RegulationType(Enum):
    PDPO = "pdpo"
    PIPL = "pipl"
    GDPR = "gdpr"
    AI_ACT = "ai_act"
    CCPA = "ccpa"
    PDPA = "pdpa"
    PIPA = "pipa"
    ISO = "iso"
    OECD = "oecd"


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataRestriction(Enum):
    LOCAL_REQUIRED = "local_required"
    CROSS_BORDER_ALLOWED = "cross_border_allowed"
    RESTRICTED = "restricted"
    FLEXIBLE = "flexible"


@dataclass
class RegionProfile:
    region: Region
    regulations: list[RegulationType]
    data_restriction: DataRestriction
    ai_specific_requirements: list[str]
    risk_level: RiskLevel
    key_requirements: dict[str, str] = field(default_factory=dict)
    compliance_checklist: list[str] = field(default_factory=list)


@dataclass
class ComplianceCheck:
    operation: str
    region: Region
    applicable_regulations: list[RegulationType]
    is_compliant: bool
    violations: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    recommendations: list[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    region: Region
    operation: str
    risk_factors: list[str] = field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.LOW
    mitigation_required: bool = False


class RegionDetector:
    def __init__(self):
        self._ip_prefix_map = {
            "1": Region.USA,
            "2": Region.GLOBAL,
            "3": Region.USA,
            "4": Region.USA,
            "5": Region.USA,
            "6": Region.GLOBAL,
            "7": Region.GLOBAL,
            "8": Region.GLOBAL,
            "9": Region.GLOBAL,
        }
        self._language_map = {
            "zh": Region.CHINA,
            "zh-hk": Region.HONG_KONG,
            "zh-tw": Region.CHINA,
            "en": Region.GLOBAL,
            "en-us": Region.USA,
            "en-gb": Region.EU,
            "ja": Region.JAPAN,
            "ko": Region.KOREA,
            "de": Region.EU,
            "fr": Region.EU,
            "ms": Region.SINGAPORE,
        }
        self._timezone_map = {
            "Asia/Hong_Kong": Region.HONG_KONG,
            "Asia/Shanghai": Region.CHINA,
            "Asia/Tokyo": Region.JAPAN,
            "Asia/Seoul": Region.KOREA,
            "Asia/Singapore": Region.SINGAPORE,
            "Europe/London": Region.EU,
            "Europe/Paris": Region.EU,
            "Europe/Berlin": Region.EU,
            "America/New_York": Region.USA,
            "America/Los_Angeles": Region.USA,
            "America/Chicago": Region.USA,
        }

    def detect_from_ip(self, ip: str) -> Region:
        if not ip:
            return Region.GLOBAL
        prefix = ip.split(".")[0]
        return self._ip_prefix_map.get(prefix, Region.GLOBAL)

    def detect_from_language(self, lang: str) -> Region:
        lang_lower = lang.lower()
        if lang_lower in self._language_map:
            return self._language_map[lang_lower]
        if "-" in lang_lower:
            base = lang_lower.split("-")[0]
            return self._language_map.get(base, Region.GLOBAL)
        return Region.GLOBAL

    def detect_from_timezone(self, tz: str) -> Region:
        if tz in self._timezone_map:
            return self._timezone_map[tz]
        if tz.startswith("Asia/"):
            return Region.GLOBAL
        if tz.startswith("America/"):
            return Region.USA
        if tz.startswith("Europe/"):
            return Region.EU
        return Region.GLOBAL

    def detect_from_context(self, context: dict) -> Region:
        signals = []
        weights = {"ip": 0.3, "language": 0.25, "timezone": 0.25, "region": 0.2}

        if "ip" in context:
            ip_region = self.detect_from_ip(context["ip"])
            signals.append(("ip", ip_region))

        if "language" in context:
            lang_region = self.detect_from_language(context["language"])
            signals.append(("language", lang_region))

        if "timezone" in context:
            tz_region = self.detect_from_timezone(context["timezone"])
            signals.append(("timezone", tz_region))

        if "region" in context:
            try:
                region = Region(context["region"])
                signals.append(("region", region))
            except ValueError:
                pass

        if not signals:
            return Region.GLOBAL

        region_scores: dict[Region, float] = {}
        for source, region in signals:
            weight = weights.get(source, 0.1)
            region_scores[region] = region_scores.get(region, 0) + weight

        return max(region_scores, key=region_scores.get) if region_scores else Region.GLOBAL


class RegulationMapper:
    def __init__(self):
        self._region_regulations: dict[Region, list[RegulationType]] = {
            Region.HONG_KONG: [RegulationType.PDPO, RegulationType.ISO, RegulationType.OECD],
            Region.CHINA: [RegulationType.PIPL, RegulationType.ISO, RegulationType.OECD],
            Region.EU: [RegulationType.GDPR, RegulationType.AI_ACT, RegulationType.ISO, RegulationType.OECD],
            Region.USA: [RegulationType.CCPA, RegulationType.ISO, RegulationType.OECD],
            Region.SINGAPORE: [RegulationType.PDPA, RegulationType.ISO, RegulationType.OECD],
            Region.JAPAN: [RegulationType.PIPA, RegulationType.ISO, RegulationType.OECD],
            Region.KOREA: [RegulationType.PIPA, RegulationType.ISO, RegulationType.OECD],
            Region.GLOBAL: [RegulationType.ISO, RegulationType.OECD],
        }
        self._profiles: dict[Region, RegionProfile] = {}
        self._init_profiles()

    def _init_profiles(self):
        self._profiles[Region.HONG_KONG] = RegionProfile(
            region=Region.HONG_KONG,
            regulations=[RegulationType.PDPO, RegulationType.ISO, RegulationType.OECD],
            data_restriction=DataRestriction.FLEXIBLE,
            ai_specific_requirements=[
                "Personal data collection notification",
                "Purpose limitation principle",
                "Data retention policies",
            ],
            risk_level=RiskLevel.MEDIUM,
            key_requirements={
                "consent": "Opt-in required for sensitive data",
                "retention": "Retain only as long as necessary",
                "transfer": "Adequate protection for cross-border transfer",
            },
            compliance_checklist=[
                "Obtain valid consent",
                "Provide privacy notice",
                "Implement data security measures",
                "Allow data subject access",
                "Honor correction requests",
            ],
        )
        self._profiles[Region.CHINA] = RegionProfile(
            region=Region.CHINA,
            regulations=[RegulationType.PIPL, RegulationType.ISO, RegulationType.OECD],
            data_restriction=DataRestriction.LOCAL_REQUIRED,
            ai_specific_requirements=[
                "Data localization for critical data",
                "Security assessment for cross-border transfer",
                "Algorithm transparency requirements",
            ],
            risk_level=RiskLevel.HIGH,
            key_requirements={
                "localization": "Critical data must be stored in China",
                "assessment": "Security assessment required for transfer",
                "algorithm": "Algorithm filing required for recommendation systems",
            },
            compliance_checklist=[
                "Register with CAC for data processing",
                "Conduct security assessment",
                "Implement data localization",
                "Maintain data catalog",
                "Provide algorithm transparency",
            ],
        )
        self._profiles[Region.EU] = RegionProfile(
            region=Region.EU,
            regulations=[RegulationType.GDPR, RegulationType.AI_ACT, RegulationType.ISO, RegulationType.OECD],
            data_restriction=DataRestriction.RESTRICTED,
            ai_specific_requirements=[
                "Lawful basis for processing",
                "Data Protection Impact Assessment",
                "High-risk AI system registration",
                "Explainability requirements",
            ],
            risk_level=RiskLevel.HIGH,
            key_requirements={
                "lawful_basis": "One of six bases required for processing",
                "dpiia": "DPIA required for high-risk processing",
                "ai_registration": "Register high-risk AI systems",
                "right_to_explanation": "Provide meaningful information about logic",
            },
            compliance_checklist=[
                "Establish lawful basis",
                "Conduct DPIA if required",
                "Implement data minimization",
                "Ensure right to erasure",
                "Register with national authority",
                "Document AI system decisions",
            ],
        )
        self._profiles[Region.USA] = RegionProfile(
            region=Region.USA,
            regulations=[RegulationType.CCPA, RegulationType.ISO, RegulationType.OECD],
            data_restriction=DataRestriction.FLEXIBLE,
            ai_specific_requirements=[
                "Consumer opt-out rights",
                "Do Not Sell My Personal Information",
                "Privacy policy disclosure",
            ],
            risk_level=RiskLevel.MEDIUM,
            key_requirements={
                "disclosure": "Clear privacy policy required",
                "opt_out": "Must honor opt-out signals",
                "verification": "Reasonable verification of requests",
            },
            compliance_checklist=[
                "Publish privacy policy",
                "Implement opt-out mechanism",
                "Verify consumer requests",
                "Train staff on CCPA requirements",
                "Maintain records of processing",
            ],
        )
        self._profiles[Region.SINGAPORE] = RegionProfile(
            region=Region.SINGAPORE,
            regulations=[RegulationType.PDPA, RegulationType.ISO, RegulationType.OECD],
            data_restriction=DataRestriction.CROSS_BORDER_ALLOWED,
            ai_specific_requirements=[
                "Consent and notification",
                "Purpose limitation",
                "Access and correction rights",
            ],
            risk_level=RiskLevel.MEDIUM,
            key_requirements={
                "consent": "Obtain consent before collection",
                "notification": "Notify individuals of purpose",
                "protection": "Reasonable security arrangements",
            },
            compliance_checklist=[
                "Obtain consent appropriately",
                "Notify individuals of data collection",
                "Implement reasonable security",
                "Honor access and correction requests",
                "Contractual protection for transfer",
            ],
        )
        self._profiles[Region.JAPAN] = RegionProfile(
            region=Region.JAPAN,
            regulations=[RegulationType.PIPA, RegulationType.ISO, RegulationType.OECD],
            data_restriction=DataRestriction.CROSS_BORDER_ALLOWED,
            ai_specific_requirements=[
                "Purpose specification",
                "Opt-out mechanism",
                "Third-party transfer disclosure",
            ],
            risk_level=RiskLevel.LOW,
            key_requirements={
                "specification": "Specify purpose of use",
                "opt_out": "Provide opt-out method",
                "disclosure": "Disclose third-party transfers",
            },
            compliance_checklist=[
                "Specify and notify purpose",
                "Implement security measures",
                "Disclose third-party transfers",
                "Honor opt-out requests",
                "Retain accurate data",
            ],
        )
        self._profiles[Region.KOREA] = RegionProfile(
            region=Region.KOREA,
            regulations=[RegulationType.PIPA, RegulationType.ISO, RegulationType.OECD],
            data_restriction=DataRestriction.RESTRICTED,
            ai_specific_requirements=[
                "Strict consent requirements",
                "Data localization for financial data",
                "Cross-border transfer restrictions",
            ],
            risk_level=RiskLevel.HIGH,
            key_requirements={
                "consent": "Granular consent required",
                "localization": "Financial data must stay in Korea",
                "transfer": "Consent required for overseas transfer",
            },
            compliance_checklist=[
                "Obtain specific consent",
                "Implement localization for financial data",
                "Get consent for cross-border transfer",
                "Maintain processing records",
                "Appoint domestic representative",
            ],
        )
        self._profiles[Region.GLOBAL] = RegionProfile(
            region=Region.GLOBAL,
            regulations=[RegulationType.ISO, RegulationType.OECD],
            data_restriction=DataRestriction.FLEXIBLE,
            ai_specific_requirements=[
                "International best practices",
                "OECD Privacy Guidelines compliance",
            ],
            risk_level=RiskLevel.LOW,
            key_requirements={
                "best_practices": "Follow international standards",
                "accountability": "Demonstrate compliance",
            },
            compliance_checklist=[
                "Implement privacy by design",
                "Conduct regular audits",
                "Maintain documentation",
                "Apply security measures",
            ],
        )

    def map_region_to_regulations(self, region: Region) -> list[RegulationType]:
        return self._region_regulations.get(region, [RegulationType.ISO, RegulationType.OECD])

    def get_region_profile(self, region: Region) -> RegionProfile:
        return self._profiles.get(region, self._profiles[Region.GLOBAL])

    def get_cross_border_restrictions(self, source: Region, target: Region) -> DataRestriction:
        if source == target:
            return DataRestriction.FLEXIBLE

        source_profile = self.get_region_profile(source)
        target_profile = self.get_region_profile(target)

        if source_profile.data_restriction == DataRestriction.LOCAL_REQUIRED:
            return DataRestriction.RESTRICTED
        if target_profile.data_restriction == DataRestriction.LOCAL_REQUIRED:
            return DataRestriction.LOCAL_REQUIRED
        if source_profile.data_restriction == DataRestriction.RESTRICTED:
            return DataRestriction.RESTRICTED
        return DataRestriction.CROSS_BORDER_ALLOWED


class ComplianceChecker:
    def __init__(self, regulation_mapper: RegulationMapper):
        self._mapper = regulation_mapper

    def check_operation(self, operation: str, region: Region) -> ComplianceCheck:
        profile = self._mapper.get_region_profile(region)
        violations = []
        recommendations = []

        operation_lower = operation.lower()

        if operation_lower in ["collect", "processing", "storage"] and RegulationType.PDPO in profile.regulations:
            if not any("consent" in req.lower() for req in profile.compliance_checklist):
                violations.append("Missing consent verification")

        if "transfer" in operation_lower or "export" in operation_lower:
            if profile.data_restriction == DataRestriction.LOCAL_REQUIRED:
                violations.append(f"Data localization required for {region.value}")
                recommendations.append("Implement local data storage")
            if profile.data_restriction == DataRestriction.RESTRICTED:
                violations.append(f"Cross-border transfer restricted under {region.value} regulations")
                recommendations.append("Obtain explicit consent or implement adequacy assessment")

        if operation_lower in ["ai_training", "ml_training", "model_training"]:
            if RegulationType.AI_ACT in profile.regulations:
                violations.append("AI training may require DPIA under EU AI Act")
                recommendations.append("Conduct Algorithm Impact Assessment")
            if RegulationType.PIPL in profile.regulations:
                violations.append("Training data processing requires PIPL compliance")
                recommendations.append("Obtain consent or legal basis for training data")

        is_compliant = len(violations) == 0
        risk_level = self._determine_risk(is_compliant, violations, profile.risk_level)

        return ComplianceCheck(
            operation=operation,
            region=region,
            applicable_regulations=profile.regulations,
            is_compliant=is_compliant,
            violations=violations,
            risk_level=risk_level,
            recommendations=recommendations,
        )

    def check_data_transfer(self, source: Region, target: Region, data_type: str) -> ComplianceCheck:
        profile = self._mapper.get_region_profile(source)
        restrictions = self._mapper.get_cross_border_restrictions(source, target)
        violations = []
        recommendations = []

        data_type_lower = data_type.lower()

        if restrictions == DataRestriction.LOCAL_REQUIRED:
            violations.append(f"{data_type} data must remain in {source.value}")
            recommendations.append(f"Establish local infrastructure in {source.value}")
        elif restrictions == DataRestriction.RESTRICTED:
            violations.append(f"Transfer of {data_type} from {source.value} to {target.value} is restricted")
            if RegulationType.GDPR in profile.regulations:
                recommendations.append("Establish Standard Contractual Clauses (SCCs)")
            if RegulationType.PIPL in profile.regulations:
                recommendations.append("Complete security assessment for cross-border transfer")
        else:
            if RegulationType.GDPR in profile.regulations:
                recommendations.append("Verify adequate protection in destination country")

        is_compliant = len(violations) == 0
        risk_level = RiskLevel.HIGH if violations else RiskLevel.LOW

        return ComplianceCheck(
            operation=f"transfer:{data_type}",
            region=source,
            applicable_regulations=profile.regulations,
            is_compliant=is_compliant,
            violations=violations,
            risk_level=risk_level,
            recommendations=recommendations,
        )

    def check_ai_system(self, system_type: str, region: Region) -> ComplianceCheck:
        profile = self._mapper.get_region_profile(region)
        violations = []
        recommendations = []

        system_type_lower = system_type.lower()

        if RegulationType.AI_ACT in profile.regulations:
            if system_type_lower in ["high_risk", "recognition", "profiling"]:
                violations.append("High-risk AI system requires conformity assessment")
                recommendations.append("Register with EU AI database and conduct conformity assessment")

        if RegulationType.PIPL in profile.regulations:
            violations.append("AI systems must comply with PIPL algorithm regulations")
            recommendations.append("File algorithm registration with CAC")

        if RegulationType.PDPA in profile.regulations:
            recommendations.append("Implement data protection measures for AI processing")

        is_compliant = len(violations) == 0
        risk_level = RiskLevel.HIGH if violations else RiskLevel.MEDIUM

        return ComplianceCheck(
            operation=f"ai:{system_type}",
            region=region,
            applicable_regulations=profile.regulations,
            is_compliant=is_compliant,
            violations=violations,
            risk_level=risk_level,
            recommendations=recommendations,
        )

    def _determine_risk(self, is_compliant: bool, violations: list[str], base_risk: RiskLevel) -> RiskLevel:
        if not is_compliant:
            if any("local" in v.lower() or "restricted" in v.lower() for v in violations):
                return RiskLevel.CRITICAL
            return RiskLevel.HIGH
        return base_risk


class RiskEvaluator:
    def __init__(self, regulation_mapper: RegulationMapper):
        self._mapper = regulation_mapper

    def evaluate_risk(self, operation: str, region: Region) -> RiskAssessment:
        profile = self._mapper.get_region_profile(region)
        risk_factors = []

        operation_lower = operation.lower()

        if profile.risk_level == RiskLevel.HIGH:
            risk_factors.append(f"{region.value} has inherently high regulatory risk")

        if profile.data_restriction == DataRestriction.LOCAL_REQUIRED:
            risk_factors.append("Data localization requirements increase operational complexity")

        if profile.data_restriction == DataRestriction.RESTRICTED:
            risk_factors.append("Cross-border restrictions may delay operations")

        if RegulationType.AI_ACT in profile.regulations:
            risk_factors.append("EU AI Act imposes strict requirements")

        if RegulationType.PIPL in profile.regulations:
            risk_factors.append("China PIPL requires extensive compliance measures")

        if any(keyword in operation_lower for keyword in ["personal", "biometric", "health", "financial"]):
            risk_factors.append(f"Operation involves sensitive data: {operation}")

        if "transfer" in operation_lower or "cross_border" in operation_lower:
            risk_factors.append("Cross-border data transfer increases exposure")

        mitigation_required = len(risk_factors) > 2 or profile.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

        overall_risk = self._calculate_overall_risk(profile.risk_level, risk_factors)

        return RiskAssessment(
            region=region,
            operation=operation,
            risk_factors=risk_factors,
            overall_risk=overall_risk,
            mitigation_required=mitigation_required,
        )

    def get_high_risk_factors(self) -> list[str]:
        return [
            "Cross-border data transfer without adequate protection",
            "Processing of special category data without explicit consent",
            "AI systems making consequential decisions",
            "Data localization requirements not met",
            "Inadequate consent mechanisms",
            "Missing data protection impact assessment",
            "Insufficient algorithm transparency",
            "Non-compliant third-party data sharing",
        ]

    def _calculate_overall_risk(self, base_risk: RiskLevel, factors: list[str]) -> RiskLevel:
        if not factors:
            return base_risk

        critical_count = sum(1 for f in factors if any(k in f.lower() for k in ["localization", "critical", "strict"]))
        high_count = sum(1 for f in factors if any(k in f.lower() for k in ["high", "strict", "consequential"]))

        if critical_count >= 2 or (critical_count >= 1 and high_count >= 1):
            return RiskLevel.CRITICAL
        if high_count >= 2 or base_risk == RiskLevel.HIGH:
            return RiskLevel.HIGH
        if high_count >= 1 or base_risk == RiskLevel.MEDIUM:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


class MitigationRecommender:
    def __init__(self, regulation_mapper: RegulationMapper):
        self._mapper = regulation_mapper

    def recommend_mitigations(self, check: ComplianceCheck) -> list[str]:
        recommendations = list(check.recommendations)

        if not check.is_compliant:
            recommendations.append("Implement compliance remediation plan immediately")

        if check.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.append("Engage legal counsel for regulatory guidance")
            recommendations.append("Consider delaying operation until compliance achieved")

        profile = self._mapper.get_region_profile(check.region)

        for regulation in profile.regulations:
            if regulation == RegulationType.GDPR:
                recommendations.append("Appoint EU Data Protection Officer")
                recommendations.append("Establish data breach notification procedures")
            elif regulation == RegulationType.PIPL:
                recommendations.append("Register with Cyberspace Administration of China")
                recommendations.append("Implement data localization infrastructure")
            elif regulation == RegulationType.CCPA:
                recommendations.append("Implement \"Do Not Sell\" mechanism")
                recommendations.append("Update privacy policy with required disclosures")
            elif regulation == RegulationType.AI_ACT:
                recommendations.append("Conduct conformity assessment for AI systems")
                recommendations.append("Implement technical documentation requirements")

        return list(set(recommendations))

    def get_checklist(self, region: Region, operation: str) -> list[str]:
        profile = self._mapper.get_region_profile(region)
        checklist = list(profile.compliance_checklist)

        operation_lower = operation.lower()

        if "ai" in operation_lower or "ml" in operation_lower:
            checklist.append("Conduct Algorithm Impact Assessment")
            checklist.append("Document training data sources")
            checklist.append("Implement model explainability measures")

        if "transfer" in operation_lower or "cross_border" in operation_lower:
            checklist.append("Verify destination country adequacy")
            checklist.append("Establish contractual protections")
            checklist.append("Document transfer mechanisms")

        if "collect" in operation_lower:
            checklist.append("Obtain necessary consents")
            checklist.append("Provide privacy notice")
            checklist.append("Document lawful basis")

        return checklist


class RegionalComplianceAnalyzer:
    def __init__(self):
        self.region_detector = RegionDetector()
        self.regulation_mapper = RegulationMapper()
        self.compliance_checker = ComplianceChecker(self.regulation_mapper)
        self.risk_evaluator = RiskEvaluator(self.regulation_mapper)
        self.mitigation_recommender = MitigationRecommender(self.regulation_mapper)

    def analyze(self, operation: str, context: dict) -> ComplianceCheck:
        region = self.region_detector.detect_from_context(context)
        return self.compliance_checker.check_operation(operation, region)

    def assess_risk(self, operation: str, region: Region) -> RiskAssessment:
        return self.risk_evaluator.evaluate_risk(operation, region)

    def get_profile(self, region: Region) -> RegionProfile:
        return self.regulation_mapper.get_region_profile(region)
