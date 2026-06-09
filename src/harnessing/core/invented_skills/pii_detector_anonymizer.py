from __future__ import annotations

import re
import structlog
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = structlog.get_logger()


class PIIType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    BANK_ACCOUNT = "bank_account"
    HK_ID = "hk_id"
    CHINA_ID = "china_id"
    UNKNOWN = "unknown"


class AnonymizationMethod(Enum):
    MASK = "mask"
    REDACT = "redact"
    PSEUDONYMIZE = "pseudonymize"
    HASH = "hash"


@dataclass
class PIIEntity:
    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class AnonymizationResult:
    original_text: str
    anonymized_text: str
    detected_entities: list[PIIEntity]
    anonymization_map: dict[str, str] = field(default_factory=dict)
    is_safe: bool = True


class PIIPatternRecognizer:
    PII_PATTERNS: dict[PIIType, list[tuple[str, float]]] = {
        PIIType.EMAIL: [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", 0.95),
        ],
        PIIType.PHONE: [
            (r"\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", 0.85),
            (r"\b\d{3}[-.\s]\d{4}[-.\s]\d{4}\b", 0.80),
            (r"\b\+852[-.\s]?\d{4}[-.\s]?\d{4}\b", 0.90),
            (r"\b\+86[-.\s]?\d{3}[-.\s]?\d{4}[-.\s]?\d{4}\b", 0.90),
        ],
        PIIType.SSN: [
            (r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b", 0.85),
        ],
        PIIType.CREDIT_CARD: [
            (r"\b(?:\d{4}[-.\s]?){3}\d{4}\b", 0.80),
            (r"\b\d{13,16}\b", 0.60),
        ],
        PIIType.IP_ADDRESS: [
            (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", 0.90),
            (r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b", 0.90),
        ],
        PIIType.HK_ID: [
            (r"\b[A-Z]{1,2}\d{6}[A-F0-9]\b", 0.85),
        ],
        PIIType.CHINA_ID: [
            (r"\b\d{17}[\dXx]\b", 0.85),
        ],
        PIIType.PASSPORT: [
            (r"\b[A-Z]{1,2}\d{6,9}\b", 0.70),
        ],
        PIIType.DATE_OF_BIRTH: [
            (r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", 0.60),
            (r"\b(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", 0.75),
        ],
        PIIType.BANK_ACCOUNT: [
            (r"\b\d{8,17}\b", 0.50),
        ],
    }

    def recognize(self, text: str) -> list[PIIEntity]:
        entities: list[PIIEntity] = []

        for pii_type, patterns in self.PII_PATTERNS.items():
            for pattern, confidence in patterns:
                for match in re.finditer(pattern, text):
                    entities.append(
                        PIIEntity(
                            pii_type=pii_type,
                            value=match.group(),
                            start=match.start(),
                            end=match.end(),
                            confidence=confidence,
                        )
                    )

        entities = self._remove_overlaps(entities)

        return entities

    def _remove_overlaps(self, entities: list[PIIEntity]) -> list[PIIEntity]:
        if not entities:
            return []

        entities.sort(key=lambda e: (e.start, -e.confidence))

        filtered: list[PIIEntity] = []
        for entity in entities:
            overlaps = False
            for existing in filtered:
                if entity.start < existing.end and entity.end > existing.start:
                    overlaps = True
                    break
            if not overlaps:
                filtered.append(entity)

        return filtered


class EntityExtractor:
    def __init__(self) -> None:
        self._name_patterns = [
            r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
            r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",
        ]

    def extract_names(self, text: str) -> list[PIIEntity]:
        entities: list[PIIEntity] = []

        for pattern in self._name_patterns:
            for match in re.finditer(pattern, text):
                entities.append(
                    PIIEntity(
                        pii_type=PIIType.NAME,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.60,
                    )
                )

        return entities

    def extract_addresses(self, text: str) -> list[PIIEntity]:
        address_patterns = [
            r"\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr)",
            r"(?:Room|Flat|Unit)\s*[A-Z]?\d+",
        ]

        entities: list[PIIEntity] = []
        for pattern in address_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(
                    PIIEntity(
                        pii_type=PIIType.ADDRESS,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.70,
                    )
                )

        return entities


class AnonymizationEngine:
    def __init__(self, method: AnonymizationMethod = AnonymizationMethod.PSEUDONYMIZE) -> None:
        self._method = method
        self._pseudonym_map: dict[str, str] = {}

    def anonymize(self, text: str, entities: list[PIIEntity]) -> tuple[str, dict[str, str]]:
        anonymization_map: dict[str, str] = {}

        sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)

        result = text
        for entity in sorted_entities:
            original_value = entity.value

            if original_value in self._pseudonym_map:
                replacement = self._pseudonym_map[original_value]
            else:
                replacement = self._generate_replacement(entity)
                self._pseudonym_map[original_value] = replacement

            anonymization_map[original_value] = replacement

            result = result[:entity.start] + replacement + result[entity.end:]

        return result, anonymization_map

    def _generate_replacement(self, entity: PIIEntity) -> str:
        if self._method == AnonymizationMethod.MASK:
            return self._mask_value(entity.value, entity.pii_type)
        elif self._method == AnonymizationMethod.REDACT:
            return f"[REDACTED_{entity.pii_type.value.upper()}]"
        elif self._method == AnonymizationMethod.PSEUDONYMIZE:
            return self._pseudonymize(entity)
        elif self._method == AnonymizationMethod.HASH:
            return f"[HASH_{hash(entity.value) % 1000000:06d}]"
        return "[ANONYMIZED]"

    def _mask_value(self, value: str, pii_type: PIIType) -> str:
        if pii_type == PIIType.EMAIL:
            parts = value.split("@")
            if len(parts) == 2:
                return f"{parts[0][:2]}***@{parts[1]}"
        elif pii_type == PIIType.PHONE:
            return value[:3] + "***" + value[-2:] if len(value) > 5 else "***"
        elif pii_type == PIIType.CREDIT_CARD:
            return "****-****-****-" + value[-4:] if len(value) >= 4 else "****"
        return "*" * len(value)

    def _pseudonymize(self, entity: PIIEntity) -> str:
        prefix = entity.pii_type.value.upper()[:3]
        unique_id = str(uuid.uuid4())[:8]
        return f"[{prefix}_{unique_id}]"

    def deanonymize(self, text: str, anonymization_map: dict[str, str]) -> str:
        result = text
        for original, pseudonym in anonymization_map.items():
            result = result.replace(pseudonym, original)
        return result


class ReIdentificationPreventer:
    RISK_PATTERNS = [
        (r"\b\d{4,}\b", "numeric_sequence"),
        (r"\b[A-Z]{2,}\d{3,}\b", "alphanumeric_code"),
        (r"\b(?:unique|id|identifier)\b", "identifier_keyword"),
    ]

    def check_reidentification_risk(self, text: str, anonymization_map: dict[str, str]) -> tuple[bool, list[str]]:
        risks: list[str] = []

        for pattern, risk_name in self.RISK_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                risks.append(f"Potential re-identification risk: {risk_name}")

        unique_pseudonyms = set(anonymization_map.values())
        if len(unique_pseudonyms) < len(anonymization_map.values()):
            risks.append("Duplicate pseudonyms detected")

        for pseudonym in anonymization_map.values():
            if pseudonym in text:
                remaining_text = text.replace(pseudonym, "", 1)
                if pseudonym in remaining_text:
                    risks.append(f"Pseudonym appears multiple times: {pseudonym[:20]}...")

        return len(risks) == 0, risks

    def validate_anonymization(self, original: str, anonymized: str, entities: list[PIIEntity]) -> tuple[bool, list[str]]:
        issues: list[str] = []

        for entity in entities:
            if entity.value in anonymized:
                issues.append(f"PII not fully anonymized: {entity.pii_type.value}")

        if len(original) != len(anonymized) and "REDACTED" not in anonymized:
            pass

        return len(issues) == 0, issues


class PIIDetectorAnonymizer:
    def __init__(self, method: AnonymizationMethod = AnonymizationMethod.PSEUDONYMIZE) -> None:
        self._formula = "S*K + G/A"
        self._capability = "pii_detector_anonymizer"

        self._pattern_recognizer = PIIPatternRecognizer()
        self._entity_extractor = EntityExtractor()
        self._anonymization_engine = AnonymizationEngine(method)
        self._reidentification_preventer = ReIdentificationPreventer()

    def analyze(self, text: str, include_names: bool = True, include_addresses: bool = True) -> AnonymizationResult:
        try:
            entities = self._pattern_recognizer.recognize(text)

            if include_names:
                name_entities = self._entity_extractor.extract_names(text)
                entities.extend(name_entities)

            if include_addresses:
                address_entities = self._entity_extractor.extract_addresses(text)
                entities.extend(address_entities)

            unique_entities: list[PIIEntity] = []
            seen_positions: set[tuple[int, int]] = set()
            for entity in entities:
                pos = (entity.start, entity.end)
                if pos not in seen_positions:
                    seen_positions.add(pos)
                    unique_entities.append(entity)
            entities = unique_entities

            anonymized_text, anonymization_map = self._anonymization_engine.anonymize(text, entities)

            is_safe, _ = self._reidentification_preventer.check_reidentification_risk(anonymized_text, anonymization_map)

            logger.info(
                "pii_anonymization_complete",
                capability=self._capability,
                entities_found=len(entities),
                is_safe=is_safe,
            )

            return AnonymizationResult(
                original_text=text,
                anonymized_text=anonymized_text,
                detected_entities=entities,
                anonymization_map=anonymization_map,
                is_safe=is_safe,
            )

        except Exception as exc:
            logger.error("pii_anonymization_failed", capability=self._capability, error=str(exc))
            return AnonymizationResult(
                original_text=text,
                anonymized_text=text,
                detected_entities=[],
                anonymization_map={},
                is_safe=False,
            )

    def execute(self, text: str, method: AnonymizationMethod | None = None) -> dict[str, Any]:
        if method is not None:
            self._anonymization_engine = AnonymizationEngine(method)

        result = self.analyze(text)

        return {
            "status": "success",
            "capability": self._capability,
            "formula": self._formula,
            "anonymized_text": result.anonymized_text,
            "entities_detected": len(result.detected_entities),
            "entity_types": list(set(e.pii_type.value for e in result.detected_entities)),
            "is_safe": result.is_safe,
            "anonymization_map": result.anonymization_map,
        }

    def detect_only(self, text: str) -> dict[str, Any]:
        entities = self._pattern_recognizer.recognize(text)
        entities.extend(self._entity_extractor.extract_names(text))
        entities.extend(self._entity_extractor.extract_addresses(text))

        return {
            "status": "success",
            "capability": self._capability,
            "formula": self._formula,
            "entities": [
                {
                    "type": e.pii_type.value,
                    "value": e.value,
                    "start": e.start,
                    "end": e.end,
                    "confidence": e.confidence,
                }
                for e in entities
            ],
            "has_pii": len(entities) > 0,
        }

    def deanonymize(self, anonymized_text: str, anonymization_map: dict[str, str]) -> str:
        return self._anonymization_engine.deanonymize(anonymized_text, anonymization_map)


if __name__ == "__main__":
    import json

    anonymizer = PIIDetectorAnonymizer(method=AnonymizationMethod.PSEUDONYMIZE)

    test_texts = [
        "My email is john.doe@example.com and my phone is +1-555-123-4567.",
        "SSN: 123-45-6789, Credit Card: 4532-1234-5678-9012",
        "Contact John Smith at john.smith@company.org or call +852-1234-5678",
        "HKID: A123456A, China ID: 110101199001011234",
        "No PII here, just regular text about programming.",
        "IP: 192.168.1.1, Server: server.example.com",
    ]

    print("=" * 60)
    print("PIIDetectorAnonymizer Unit Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for text in test_texts:
        result = anonymizer.execute(text)

        has_pii = result["entities_detected"] > 0
        expected_pii = "No PII" not in text

        is_correct = has_pii == expected_pii

        status = "PASS" if is_correct else "FAIL"
        if is_correct:
            passed += 1
        else:
            failed += 1

        print(f"\n[{status}] Input: {text[:50]}...")
        print(f"  Entities: {result['entities_detected']}")
        print(f"  Types: {result['entity_types']}")
        print(f"  Anonymized: {result['anonymized_text'][:60]}...")

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    assert failed == 0, f"{failed} tests failed"
