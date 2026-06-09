from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


AI_LABEL = "本文由 AI 辅助生成"

_PII_PATTERNS: List[Tuple[str, str]] = [
    ("email", r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
    ("phone_cn_mobile", r'\b1[3-9]\d{9}\b'),
    ("id_card_cn", r'\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b'),
    ("credit_card", r'\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
    ("ip_address", r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
]

_CROSS_BORDER_INDICATORS: List[Tuple[str, str]] = [
    ("foreign_server_url", r'\bhttps?://(?:(?:[a-zA-Z0-9-]+\.)+(?:com|net|org|io|dev|co|me|ly|ai|app|cloud|aws|azure|gcp)\b[^\s]*)'),
    ("overseas_storage_ref", r'(?:海外|境外|国外|国外服务器|overseas|foreign\s+server|offshore\s+storage|data\s+stored\s+abroad)'),
    ("foreign_cloud_provider", r'\b(?:AWS|Amazon\s+Web\s+Services|Azure|Google\s+Cloud|GCP|DigitalOcean|Heroku|Vercel|Netlify|Cloudflare)\b'),
]

_DEFAULT_SENSITIVE_KEYWORDS: Dict[str, List[str]] = {
    "political": [
        "颠覆国家政权",
        "分裂国家",
        "推翻社会主义制度",
    ],
    "violent": [
        "恐怖袭击",
        "制造爆炸",
        "煽动暴力",
    ],
    "pornographic": [
        "色情直播",
        "淫秽物品",
        "传播淫秽",
    ],
}


@dataclass
class PIPLCheckResult:
    pii_found: List[Dict[str, str | int]]
    ai_labeled: bool
    sensitive_keywords: List[str]
    data_localization: Dict[str, List[str]]
    compliant: bool
    issues: List[str]
    warnings: List[str]


class PIPLComplianceChecker:

    def __init__(self) -> None:
        self._sensitive_keywords: Dict[str, Set[str]] = {
            cat: set(kws) for cat, kws in _DEFAULT_SENSITIVE_KEYWORDS.items()
        }
        self._compiled_pii: List[Tuple[str, re.Pattern[str]]] = [
            (name, re.compile(pat)) for name, pat in _PII_PATTERNS
        ]
        self._compiled_cross_border: List[Tuple[str, re.Pattern[str]]] = [
            (name, re.compile(pat, re.IGNORECASE)) for name, pat in _CROSS_BORDER_INDICATORS
        ]

    def check_pii(self, text: str) -> List[Dict[str, str | int]]:
        results: List[Dict[str, str | int]] = []
        for pii_type, pattern in self._compiled_pii:
            for match in pattern.finditer(text):
                results.append({
                    "type": pii_type,
                    "value": match.group(),
                    "position": match.start(),
                })
        results.sort(key=lambda r: r["position"])
        return results

    def check_ai_label(self, text: str) -> bool:
        return AI_LABEL in text

    def add_ai_label(self, text: str) -> str:
        if self.check_ai_label(text):
            return text
        separator = "\n" if text and not text.endswith("\n") else ""
        return f"{text}{separator}{AI_LABEL}"

    def check_sensitive_keywords(self, text: str) -> List[str]:
        found: List[str] = []
        for category, keywords in self._sensitive_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    found.append(keyword)
        return found

    def check_data_localization(self, text: str) -> Dict[str, List[str]]:
        indicators: Dict[str, List[str]] = {}
        for indicator_type, pattern in self._compiled_cross_border:
            matches = pattern.findall(text)
            if matches:
                indicators[indicator_type] = list(dict.fromkeys(matches))
        return indicators

    def add_keywords(self, category: str, keywords: List[str]) -> None:
        if category not in self._sensitive_keywords:
            self._sensitive_keywords[category] = set()
        self._sensitive_keywords[category].update(keywords)

    def check_all(self, text: str, is_ai_generated: bool = True) -> Dict[str, object]:
        pii_found = self.check_pii(text)
        ai_labeled = self.check_ai_label(text)
        sensitive_keywords = self.check_sensitive_keywords(text)
        data_localization = self.check_data_localization(text)

        issues: List[str] = []
        warnings: List[str] = []

        if pii_found:
            pii_types = sorted(set(p["type"] for p in pii_found))
            issues.append(f"PII detected: {', '.join(pii_types)}")

        if is_ai_generated and not ai_labeled:
            issues.append("AI-generated content missing required label")

        if sensitive_keywords:
            warnings.append(f"Sensitive keywords detected: {', '.join(sensitive_keywords)}")

        if data_localization:
            indicator_types = list(data_localization.keys())
            issues.append(f"Cross-border data transfer indicators: {', '.join(indicator_types)}")

        compliant = len(issues) == 0

        return {
            "pii_found": pii_found,
            "ai_labeled": ai_labeled,
            "sensitive_keywords": sensitive_keywords,
            "data_localization": data_localization,
            "compliant": compliant,
            "issues": issues,
            "warnings": warnings,
        }


def main() -> None:
    checker = PIPLComplianceChecker()

    print("=" * 60)
    print("PIPLComplianceChecker Demo")
    print("=" * 60)

    test_text = (
        "联系方式：邮箱 user@example.com，手机 13812345678，"
        "身份证号 110101199001011234，IP 192.168.1.1。"
        "数据存储在 AWS 海外服务器上。"
    )

    print("\n--- check_pii ---")
    pii = checker.check_pii(test_text)
    for p in pii:
        print(f"  [{p['type']}] \"{p['value']}\" at position {p['position']}")

    print("\n--- check_ai_label ---")
    print(f"  Labeled: {checker.check_ai_label(test_text)}")

    print("\n--- add_ai_label ---")
    labeled = checker.add_ai_label(test_text)
    print(f"  Labeled: {checker.check_ai_label(labeled)}")

    print("\n--- check_sensitive_keywords ---")
    safe_text = "这是一篇关于编程技术的文章"
    print(f"  Safe text keywords: {checker.check_sensitive_keywords(safe_text)}")

    print("\n--- check_data_localization ---")
    loc = checker.check_data_localization(test_text)
    for k, v in loc.items():
        print(f"  {k}: {v}")

    print("\n--- add_keywords ---")
    checker.add_keywords("political", ["测试关键词"])
    print(f"  Added custom keyword, categories: {list(checker._sensitive_keywords.keys())}")

    print("\n--- check_all (non-compliant) ---")
    result = checker.check_all(test_text, is_ai_generated=True)
    print(f"  Compliant: {result['compliant']}")
    print(f"  Issues: {result['issues']}")
    print(f"  Warnings: {result['warnings']}")

    print("\n--- check_all (compliant) ---")
    clean_text = "这是一篇普通的编程教程，不包含任何个人信息。"
    clean_labeled = checker.add_ai_label(clean_text)
    result_clean = checker.check_all(clean_labeled, is_ai_generated=True)
    print(f"  Compliant: {result_clean['compliant']}")
    print(f"  Issues: {result_clean['issues']}")
    print(f"  Warnings: {result_clean['warnings']}")

    print("\n" + "=" * 60)
    print("PIPLComplianceChecker Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
